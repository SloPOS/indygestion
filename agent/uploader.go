package main

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	_ "github.com/eventials/go-tus"
	"github.com/google/uuid"
)

type jobState struct {
	cancel context.CancelFunc
	speed  float64
}

type Uploader struct {
	queue      *JobQueue
	cfgStore   *ConfigStore
	notifier   *Notifier
	network    *NetworkMonitor
	httpClient *http.Client

	mu      sync.RWMutex
	active  map[string]*jobState
	pending chan struct{}
	stopCh  chan struct{}
}

func NewUploader(queue *JobQueue, cfg *ConfigStore, notifier *Notifier, network *NetworkMonitor) *Uploader {
	c := cfg.Get()
	return &Uploader{
		queue:      queue,
		cfgStore:   cfg,
		notifier:   notifier,
		network:    network,
		httpClient: &http.Client{Timeout: 60 * time.Second},
		active:     make(map[string]*jobState),
		pending:    make(chan struct{}, c.MaxConcurrent),
		stopCh:     make(chan struct{}),
	}
}

func (u *Uploader) Start(ctx context.Context) {
	u.recoverInterrupted()
	go u.scheduler(ctx)
	go u.networkLoop(ctx)
}

func (u *Uploader) enqueueSignal() {
	select {
	case u.pending <- struct{}{}:
	default:
	}
}

func (u *Uploader) scheduler(ctx context.Context) {
	u.enqueueSignal()
	for {
		select {
		case <-ctx.Done():
			return
		case <-u.stopCh:
			return
		case <-u.pending:
			u.fillSlots(ctx)
		}
	}
}

func (u *Uploader) fillSlots(parent context.Context) {
	cfg := u.cfgStore.Get()
	for {
		u.mu.RLock()
		activeCount := len(u.active)
		u.mu.RUnlock()
		if activeCount >= cfg.MaxConcurrent || !u.network.IsOnline() {
			return
		}
		jobs, err := u.queue.ListByStatus(StatusQueued)
		if err != nil || len(jobs) == 0 {
			return
		}
		job := jobs[0]
		u.startJob(parent, job)
	}
}

func (u *Uploader) startJob(parent context.Context, job UploadJob) {
	ctx, cancel := context.WithCancel(parent)
	u.mu.Lock()
	if _, exists := u.active[job.ID]; exists {
		u.mu.Unlock()
		cancel()
		return
	}
	u.active[job.ID] = &jobState{cancel: cancel}
	u.mu.Unlock()

	go func() {
		defer func() {
			u.mu.Lock()
			delete(u.active, job.ID)
			u.mu.Unlock()
			u.enqueueSignal()
		}()
		_ = u.queue.UpdateStatus(job.ID, StatusUploading, "")
		err := u.uploadWithRetry(ctx, job.ID)
		if err == nil {
			j, _ := u.queue.Get(job.ID)
			if j != nil {
				u.notifier.UploadComplete(j.FileName)
			}
		}
	}()
}

func (u *Uploader) uploadWithRetry(ctx context.Context, jobID string) error {
	cfg := u.cfgStore.Get()
	for {
		job, err := u.queue.Get(jobID)
		if err != nil {
			return err
		}
		err = u.uploadOnce(ctx, *job)
		if err == nil {
			_ = u.queue.UpdateStatus(jobID, StatusCompleted, "")
			_ = u.queue.UpdateProgress(jobID, 100, job.FileSize, 0)
			return nil
		}
		if errors.Is(err, context.Canceled) {
			return err
		}
		_ = u.queue.IncrementRetry(jobID)
		job, _ = u.queue.Get(jobID)
		if !cfg.AutoRetry || job.RetryCount >= cfg.MaxRetries {
			_ = u.queue.UpdateStatus(jobID, StatusFailed, err.Error())
			u.notifier.UploadFailed(job.FileName, err.Error())
			return err
		}
		time.Sleep(time.Duration(cfg.RetryDelaySeconds) * time.Second)
	}
}

func (u *Uploader) uploadOnce(ctx context.Context, job UploadJob) error {
	f, err := os.Open(job.FilePath)
	if err != nil {
		_ = u.queue.UpdateStatus(job.ID, StatusFailed, err.Error())
		return err
	}
	defer f.Close()

	chunkBytes := u.cfgStore.Get().ChunkSizeMb * 1024 * 1024
	uploadURL := job.TusUploadURL
	offset := int64(0)

	if uploadURL == "" {
		uploadURL, err = u.createTusUpload(ctx, job.ServerURL, job.FileSize, filepath.Base(job.FilePath))
		if err != nil {
			return err
		}
		if err := u.queue.UpdateTusUploadURL(job.ID, uploadURL); err != nil {
			return err
		}
	} else {
		offset, err = u.currentOffset(ctx, uploadURL)
		if err != nil {
			return err
		}
	}

	if _, err := f.Seek(offset, io.SeekStart); err != nil {
		return err
	}

	start := time.Now()
	bytesUploaded := offset
	buf := make([]byte, chunkBytes)
	for {
		select {
		case <-ctx.Done():
			_ = u.queue.UpdateStatus(job.ID, StatusPaused, "")
			return ctx.Err()
		default:
		}
		n, readErr := f.Read(buf)
		if n > 0 {
			if err := u.patchChunk(ctx, uploadURL, offset, buf[:n]); err != nil {
				return err
			}
			offset += int64(n)
			bytesUploaded += int64(n)
			progress := float64(bytesUploaded) * 100 / float64(job.FileSize)
			speed := float64(bytesUploaded) / time.Since(start).Seconds()
			u.setSpeed(job.ID, speed)
			_ = u.queue.UpdateProgress(job.ID, progress, bytesUploaded, speed)
		}
		if readErr != nil {
			if errors.Is(readErr, io.EOF) {
				break
			}
			return readErr
		}
	}
	return nil
}

func (u *Uploader) createTusUpload(ctx context.Context, serverURL string, size int64, filename string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, serverURL, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Tus-Resumable", "1.0.0")
	req.Header.Set("Upload-Length", strconv.FormatInt(size, 10))
	req.Header.Set("Upload-Metadata", fmt.Sprintf("filename %s", base64Encode(filename)))
	resp, err := u.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("tus create failed: %s %s", resp.Status, string(b))
	}
	loc := resp.Header.Get("Location")
	if strings.HasPrefix(loc, "http://") || strings.HasPrefix(loc, "https://") {
		return loc, nil
	}
	return strings.TrimRight(serverURL, "/") + "/" + strings.TrimLeft(loc, "/"), nil
}

func (u *Uploader) currentOffset(ctx context.Context, uploadURL string) (int64, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodHead, uploadURL, nil)
	if err != nil {
		return 0, err
	}
	req.Header.Set("Tus-Resumable", "1.0.0")
	resp, err := u.httpClient.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return 0, fmt.Errorf("tus head failed: %s", resp.Status)
	}
	offsetStr := resp.Header.Get("Upload-Offset")
	if offsetStr == "" {
		return 0, nil
	}
	return strconv.ParseInt(offsetStr, 10, 64)
}

func (u *Uploader) patchChunk(ctx context.Context, uploadURL string, offset int64, chunk []byte) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodPatch, uploadURL, bytes.NewReader(chunk))
	if err != nil {
		return err
	}
	req.Header.Set("Tus-Resumable", "1.0.0")
	req.Header.Set("Upload-Offset", strconv.FormatInt(offset, 10))
	req.Header.Set("Content-Type", "application/offset+octet-stream")
	resp, err := u.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNoContent {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("tus patch failed: %s %s", resp.Status, string(b))
	}
	return nil
}

func (u *Uploader) Enqueue(filePath, serverURL string) (UploadJob, error) {
	st, err := os.Stat(filePath)
	if err != nil {
		return UploadJob{}, err
	}
	job := UploadJob{
		ID:           uuid.NewString(),
		FilePath:     filePath,
		FileName:     filepath.Base(filePath),
		FileSize:     st.Size(),
		ServerURL:    serverURL,
		Status:       StatusQueued,
		Progress:     0,
		CreatedAt:    time.Now().UTC(),
		UpdatedAt:    time.Now().UTC(),
		BytesUploaded: 0,
	}
	if err := u.queue.Add(job); err != nil {
		return UploadJob{}, err
	}
	u.enqueueSignal()
	return job, nil
}

func (u *Uploader) Pause(id string) {
	u.mu.RLock()
	st, ok := u.active[id]
	u.mu.RUnlock()
	if ok {
		st.cancel()
	}
	_ = u.queue.UpdateStatus(id, StatusPaused, "")
}

func (u *Uploader) Resume(id string) {
	j, err := u.queue.Get(id)
	if err != nil {
		return
	}
	if j.Status == StatusPaused || j.Status == StatusFailed || j.Status == StatusQueued {
		_ = u.queue.UpdateStatus(id, StatusQueued, "")
		u.enqueueSignal()
	}
}

func (u *Uploader) Cancel(id string) {
	u.Pause(id)
	_ = u.queue.UpdateStatus(id, StatusCancelled, "")
}

func (u *Uploader) PauseAll() {
	jobs, _ := u.queue.ListByStatus(StatusUploading, StatusQueued)
	for _, j := range jobs {
		u.Pause(j.ID)
	}
}

func (u *Uploader) ResumeAll() {
	jobs, _ := u.queue.ListByStatus(StatusPaused)
	for _, j := range jobs {
		u.Resume(j.ID)
	}
}

func (u *Uploader) recoverInterrupted() {
	jobs, _ := u.queue.ListByStatus(StatusUploading)
	for _, j := range jobs {
		_ = u.queue.UpdateStatus(j.ID, StatusQueued, "")
	}
	u.enqueueSignal()
}

func (u *Uploader) Shutdown() {
	close(u.stopCh)
	u.PauseAll()
}

func (u *Uploader) networkLoop(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case ev := <-u.network.Events():
			if !ev.Online {
				u.notifier.NetworkDisconnected()
				u.PauseAll()
			} else {
				u.notifier.NetworkRestored()
				time.Sleep(5 * time.Second)
				u.ResumeAll()
			}
		}
	}
}

func (u *Uploader) setSpeed(id string, speed float64) {
	u.mu.Lock()
	defer u.mu.Unlock()
	if st, ok := u.active[id]; ok {
		st.speed = speed
	}
}

func (u *Uploader) Speed(id string) float64 {
	u.mu.RLock()
	defer u.mu.RUnlock()
	if st, ok := u.active[id]; ok {
		return st.speed
	}
	return 0
}

func base64Encode(s string) string {
	const table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
	b := []byte(s)
	var out strings.Builder
	for i := 0; i < len(b); i += 3 {
		var n uint32
		rem := len(b) - i
		n |= uint32(b[i]) << 16
		if rem > 1 {
			n |= uint32(b[i+1]) << 8
		}
		if rem > 2 {
			n |= uint32(b[i+2])
		}
		out.WriteByte(table[(n>>18)&63])
		out.WriteByte(table[(n>>12)&63])
		if rem > 1 {
			out.WriteByte(table[(n>>6)&63])
		} else {
			out.WriteByte('=')
		}
		if rem > 2 {
			out.WriteByte(table[n&63])
		} else {
			out.WriteByte('=')
		}
	}
	return out.String()
}

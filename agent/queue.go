package main

import (
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	_ "modernc.org/sqlite"
)

type JobStatus string

const (
	StatusQueued    JobStatus = "queued"
	StatusUploading JobStatus = "uploading"
	StatusPaused    JobStatus = "paused"
	StatusCompleted JobStatus = "completed"
	StatusFailed    JobStatus = "failed"
	StatusCancelled JobStatus = "cancelled"
)

type UploadJob struct {
	ID           string    `json:"id"`
	FilePath     string    `json:"filePath"`
	FileName     string    `json:"fileName"`
	FileSize     int64     `json:"fileSize"`
	ServerURL    string    `json:"serverUrl"`
	TusUploadURL string    `json:"tusUploadUrl,omitempty"`
	Status       JobStatus `json:"status"`
	Progress     float64   `json:"progress"`
	BytesUploaded int64    `json:"bytesUploaded"`
	Speed        float64   `json:"speed"`
	ErrorMessage string    `json:"errorMessage,omitempty"`
	CreatedAt    time.Time `json:"createdAt"`
	UpdatedAt    time.Time `json:"updatedAt"`
	CompletedAt  *time.Time `json:"completedAt,omitempty"`
	RetryCount   int       `json:"retryCount"`
}

type JobQueue struct {
	mu sync.RWMutex
	db *sql.DB
}

func NewJobQueue() (*JobQueue, error) {
	base, err := appDataDir()
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(base, 0o755); err != nil {
		return nil, err
	}
	dbPath := filepath.Join(base, "queue.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, err
	}
	q := &JobQueue{db: db}
	if err := q.init(); err != nil {
		return nil, err
	}
	return q, nil
}

func (q *JobQueue) init() error {
	query := `
	CREATE TABLE IF NOT EXISTS upload_jobs (
		id TEXT PRIMARY KEY,
		file_path TEXT NOT NULL,
		file_name TEXT NOT NULL,
		file_size INTEGER,
		server_url TEXT NOT NULL,
		tus_upload_url TEXT,
		status TEXT,
		progress REAL,
		bytes_uploaded INTEGER,
		error_message TEXT,
		created_at DATETIME,
		updated_at DATETIME,
		completed_at DATETIME,
		retry_count INTEGER DEFAULT 0
	);`
	_, err := q.db.Exec(query)
	return err
}

func (q *JobQueue) Close() error { return q.db.Close() }

func (q *JobQueue) Add(job UploadJob) error {
	q.mu.Lock()
	defer q.mu.Unlock()
	_, err := q.db.Exec(`INSERT INTO upload_jobs (id,file_path,file_name,file_size,server_url,tus_upload_url,status,progress,bytes_uploaded,error_message,created_at,updated_at,completed_at,retry_count)
	VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
		job.ID, job.FilePath, job.FileName, job.FileSize, job.ServerURL, job.TusUploadURL, string(job.Status), job.Progress, job.BytesUploaded, job.ErrorMessage, job.CreatedAt, job.UpdatedAt, job.CompletedAt, job.RetryCount)
	return err
}

func (q *JobQueue) Get(id string) (*UploadJob, error) {
	q.mu.RLock()
	defer q.mu.RUnlock()
	row := q.db.QueryRow(`SELECT id,file_path,file_name,file_size,server_url,tus_upload_url,status,progress,bytes_uploaded,error_message,created_at,updated_at,completed_at,retry_count FROM upload_jobs WHERE id = ?`, id)
	return scanJob(row)
}

func (q *JobQueue) List() ([]UploadJob, error) {
	q.mu.RLock()
	defer q.mu.RUnlock()
	rows, err := q.db.Query(`SELECT id,file_path,file_name,file_size,server_url,tus_upload_url,status,progress,bytes_uploaded,error_message,created_at,updated_at,completed_at,retry_count FROM upload_jobs ORDER BY created_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	jobs := make([]UploadJob, 0)
	for rows.Next() {
		j, err := scanJob(rows)
		if err != nil {
			return nil, err
		}
		jobs = append(jobs, *j)
	}
	return jobs, rows.Err()
}

func (q *JobQueue) ListByStatus(statuses ...JobStatus) ([]UploadJob, error) {
	if len(statuses) == 0 {
		return nil, errors.New("no statuses provided")
	}
	q.mu.RLock()
	defer q.mu.RUnlock()
	ph := "?"
	args := []any{string(statuses[0])}
	for i := 1; i < len(statuses); i++ {
		ph += ",?"
		args = append(args, string(statuses[i]))
	}
	rows, err := q.db.Query(fmt.Sprintf(`SELECT id,file_path,file_name,file_size,server_url,tus_upload_url,status,progress,bytes_uploaded,error_message,created_at,updated_at,completed_at,retry_count FROM upload_jobs WHERE status IN (%s) ORDER BY created_at ASC`, ph), args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var jobs []UploadJob
	for rows.Next() {
		j, err := scanJob(rows)
		if err != nil {
			return nil, err
		}
		jobs = append(jobs, *j)
	}
	return jobs, rows.Err()
}

func (q *JobQueue) UpdateProgress(id string, progress float64, bytesUploaded int64, speed float64) error {
	q.mu.Lock()
	defer q.mu.Unlock()
	_, err := q.db.Exec(`UPDATE upload_jobs SET progress=?, bytes_uploaded=?, updated_at=? WHERE id=?`, progress, bytesUploaded, time.Now().UTC(), id)
	_ = speed
	return err
}

func (q *JobQueue) UpdateTusUploadURL(id, uploadURL string) error {
	q.mu.Lock()
	defer q.mu.Unlock()
	_, err := q.db.Exec(`UPDATE upload_jobs SET tus_upload_url=?, updated_at=? WHERE id=?`, uploadURL, time.Now().UTC(), id)
	return err
}

func (q *JobQueue) UpdateStatus(id string, status JobStatus, errMsg string) error {
	q.mu.Lock()
	defer q.mu.Unlock()
	var completedAt any
	if status == StatusCompleted {
		t := time.Now().UTC()
		completedAt = t
	}
	_, err := q.db.Exec(`UPDATE upload_jobs SET status=?, error_message=?, updated_at=?, completed_at=? WHERE id=?`, string(status), errMsg, time.Now().UTC(), completedAt, id)
	return err
}

func (q *JobQueue) IncrementRetry(id string) error {
	q.mu.Lock()
	defer q.mu.Unlock()
	_, err := q.db.Exec(`UPDATE upload_jobs SET retry_count=retry_count+1, updated_at=? WHERE id=?`, time.Now().UTC(), id)
	return err
}

func scanJob(scanner interface{ Scan(dest ...any) error }) (*UploadJob, error) {
	var j UploadJob
	var status string
	var completedAt sql.NullTime
	if err := scanner.Scan(&j.ID, &j.FilePath, &j.FileName, &j.FileSize, &j.ServerURL, &j.TusUploadURL, &status, &j.Progress, &j.BytesUploaded, &j.ErrorMessage, &j.CreatedAt, &j.UpdatedAt, &completedAt, &j.RetryCount); err != nil {
		return nil, err
	}
	j.Status = JobStatus(status)
	if completedAt.Valid {
		j.CompletedAt = &completedAt.Time
	}
	return &j, nil
}

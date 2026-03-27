package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

type APIServer struct {
	cfg     *ConfigStore
	queue   *JobQueue
	uploader *Uploader
	network *NetworkMonitor
}

func NewAPIServer(cfg *ConfigStore, queue *JobQueue, uploader *Uploader, network *NetworkMonitor) *APIServer {
	return &APIServer{cfg: cfg, queue: queue, uploader: uploader, network: network}
}

func (s *APIServer) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/enqueue", s.handleEnqueue)
	mux.HandleFunc("/api/status", s.handleStatus)
	mux.HandleFunc("/api/job/", s.handleJobAction)
	mux.HandleFunc("/api/pause-all", s.handlePauseAll)
	mux.HandleFunc("/api/resume-all", s.handleResumeAll)
	mux.HandleFunc("/api/config", s.handleConfig)
	mux.HandleFunc("/api/health", s.handleHealth)
	return mux
}

func (s *APIServer) handleEnqueue(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		FilePath  string `json:"filePath"`
		ServerURL string `json:"serverUrl"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if req.ServerURL == "" {
		req.ServerURL = s.cfg.Get().ServerURL
	}
	job, err := s.uploader.Enqueue(req.FilePath, req.ServerURL)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	writeJSON(w, map[string]any{"jobId": job.ID, "status": "queued"})
}

func (s *APIServer) handleStatus(w http.ResponseWriter, r *http.Request) {
	jobs, err := s.queue.List()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	var uploading, queued, completed int
	for i := range jobs {
		if jobs[i].Status == StatusUploading {
			uploading++
			jobs[i].Speed = s.uploader.Speed(jobs[i].ID)
		}
		if jobs[i].Status == StatusQueued {
			queued++
		}
		if jobs[i].Status == StatusCompleted {
			completed++
		}
	}
	writeJSON(w, map[string]any{"jobs": jobs, "uploading": uploading, "queued": queued, "completed": completed})
}

func (s *APIServer) handleJobAction(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/job/")
	parts := strings.Split(path, "/")
	if len(parts) == 0 || parts[0] == "" {
		http.Error(w, "job id required", http.StatusBadRequest)
		return
	}
	id := parts[0]
	if len(parts) == 1 {
		job, err := s.queue.Get(id)
		if err != nil {
			http.Error(w, err.Error(), http.StatusNotFound)
			return
		}
		job.Speed = s.uploader.Speed(id)
		writeJSON(w, job)
		return
	}
	action := parts[1]
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	switch action {
	case "pause":
		s.uploader.Pause(id)
	case "resume":
		s.uploader.Resume(id)
	case "cancel":
		s.uploader.Cancel(id)
	default:
		http.Error(w, "unknown action", http.StatusNotFound)
		return
	}
	writeJSON(w, map[string]string{"status": "ok"})
}

func (s *APIServer) handlePauseAll(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	s.uploader.PauseAll()
	writeJSON(w, map[string]string{"status": "ok"})
}

func (s *APIServer) handleResumeAll(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	s.uploader.ResumeAll()
	writeJSON(w, map[string]string{"status": "ok"})
}

func (s *APIServer) handleConfig(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, s.cfg.Get())
	case http.MethodPut:
		cfg := s.cfg.Get()
		if err := json.NewDecoder(r.Body).Decode(&cfg); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if err := s.cfg.Save(cfg); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		writeJSON(w, cfg)
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func (s *APIServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]any{"status": "ok", "version": "0.1.0", "networkOnline": s.network.IsOnline()})
}

func writeJSON(w http.ResponseWriter, data any) {
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(data); err != nil {
		http.Error(w, fmt.Sprintf("json encode: %v", err), http.StatusInternalServerError)
	}
}

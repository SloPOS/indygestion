# Indygestion Agent

Indygestion Agent is a lightweight desktop tray app that takes upload jobs from the web app over localhost, then performs resumable tus uploads in the background. Uploads survive browser close, app restart, and short network interruptions by persisting job state in SQLite and resuming from stored tus upload URLs.

## Build

```bash
go build -o indygestion-agent .
```

Cross-compile helpers:

```bash
./build/build-windows.sh
./build/build-mac.sh
./build/build-linux.sh
```

## Run

```bash
./indygestion-agent
```

The agent starts:
- System tray icon
- Localhost HTTP API on `127.0.0.1:4709` (configurable)
- Upload scheduler
- Network monitor

## API Reference

### POST `/api/enqueue`
Request:
```json
{ "filePath": "/path/to/video.mov", "serverUrl": "http://192.168.86.85/files/" }
```
Response:
```json
{ "jobId": "uuid", "status": "queued" }
```

### GET `/api/status`
Response:
```json
{
  "jobs": [],
  "uploading": 0,
  "queued": 0,
  "completed": 0
}
```

### GET `/api/job/:id`
Response includes job fields including `progress`, `status`, and `speed`.

### POST `/api/job/:id/pause`
### POST `/api/job/:id/resume`
### POST `/api/job/:id/cancel`

### POST `/api/pause-all`
### POST `/api/resume-all`

### GET `/api/config`
Returns current JSON config.

### PUT `/api/config`
Request body supports:
```json
{ "chunkSizeMb": 50, "maxConcurrent": 2, "autoRetry": true, "retryDelaySeconds": 30 }
```

### GET `/api/health`
Response:
```json
{ "status": "ok", "version": "0.1.0", "networkOnline": true }
```

## Configuration

Config file location (same folder as DB):
- Windows: `%APPDATA%/indygestion-agent/config.json`
- macOS: `~/Library/Application Support/indygestion-agent/config.json`
- Linux: `~/.local/share/indygestion-agent/config.json`

Default config:

```json
{
  "serverUrl": "http://127.0.0.1:1080/files/",
  "listenPort": 4709,
  "chunkSizeMb": 50,
  "maxConcurrent": 2,
  "autoRetry": true,
  "maxRetries": 10,
  "retryDelaySeconds": 30,
  "networkCheckIntervalSeconds": 10,
  "autoStartOnBoot": false
}
```

Queue DB location:
- Windows: `%APPDATA%/indygestion-agent/queue.db`
- macOS: `~/Library/Application Support/indygestion-agent/queue.db`
- Linux: `~/.local/share/indygestion-agent/queue.db`

## Webapp Integration Flow

1. Browser posts `filePath` and `serverUrl` to `POST /api/enqueue`.
2. Agent stores job in SQLite (`queued`).
3. Scheduler starts tus upload with chunked PATCH requests.
4. Agent persists `tus_upload_url` and byte/progress updates continuously.
5. On disconnect, active uploads are paused; on reconnect, paused jobs resume.
6. On completion/failure, the agent updates status and shows OS notifications.

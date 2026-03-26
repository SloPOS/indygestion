# Indygestion — Video Asset Management Platform

> *A play on "indigestion" — because we're swallowing all your footage whole.* 🎬

## Overview

A self-hosted, Dockerized web application for ingesting, organizing, proxying, and archiving video footage for YouTube production workflows. Runs on Unraid.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Docker Compose                  │
├──────────┬──────────┬───────────┬───────────────┤
│ Frontend │ Backend  │ Workers   │ Infrastructure│
│ (React)  │ (FastAPI)│ (Celery)  │               │
│ :3000    │ :8000    │           │ PostgreSQL    │
│          │          │           │ Redis         │
└──────────┴──────────┴───────────┴───────────────┘
```

### Stack

| Layer | Tech | Why |
|-------|------|-----|
| Frontend | React + TypeScript | Modern, fast, good upload libraries |
| Backend API | Python / FastAPI | Async, great FFmpeg/Whisper ecosystem |
| Task Queue | Celery + Redis | Background jobs (transcription, encoding, archival) |
| Database | PostgreSQL + pgvector | Relational data, full-text search, embeddings |
| Storage | Mounted Unraid shares | Direct access to array/cache drives |
| Transcoding | FFmpeg w/ QSV (Intel Quick Sync) | Hardware-accelerated encoding via i7-8700K iGPU |
| Transcription | faster-whisper (small/base model) | CPU-friendly, good enough for topic clustering |

### Hardware Target

- **CPU:** Intel i7-8700K (Coffee Lake, 6C/12T)
- **GPU:** Intel UHD 630 iGPU — Quick Sync Video for H.264/H.265 encode/decode
- **Network:** 10GbE primary, must degrade gracefully to 1GbE
- **Platform:** Unraid

---

## Feature 1: Resumable Web Upload

### Problem
Large ProRes files (10-100+ GB) over network = dropped connections = wasted time.

### Solution
**tus protocol** — an open standard for resumable uploads.

- Frontend uses **Uppy** (tus-compatible upload widget with drag-and-drop, progress bars, pause/resume)
- Backend runs a **tusd** sidecar container that handles chunked uploads
- If connection drops, the client automatically resumes from the last successful chunk on reconnect
- Chunk size configurable (default 50MB) — balances resume granularity vs overhead
- Upload targets a staging area; on completion, triggers the ingest pipeline

### Network Adaptivity

- **Settings page** exposes network speed configuration (1GbE / 2.5GbE / 5GbE / 10GbE / custom)
- Chunk size auto-adjusts based on configured speed:
  - 1GbE → 25MB chunks (more resume points)
  - 10GbE → 100MB chunks (less overhead)
- Concurrent upload slots adjustable (default: 2 for 1GbE, 4 for 10GbE)
- Real-time throughput display in UI with estimated time remaining
- Option to throttle uploads to avoid saturating the network

### Flow
```
Browser → Uppy (tus client) → tusd container → /staging/{upload_id}/
                                                      │
                                              on_complete webhook
                                                      │
                                              Backend → Celery task
```

---

## Feature 2: Smart Organization via Transcription + Clustering

### Problem
Clips from multiple shoots need to be grouped into projects/topics. Complication: shoots happen on different days, ingested at different times, and topics often overlap.

### Solution
**Whisper transcription → text embeddings → similarity clustering** with heavy emphasis on **user review and manual override**.

### Pipeline

1. **Transcribe** — `faster-whisper` with `small` model (CPU-friendly on 8700K, ~5-8x realtime). Precision isn't critical — we need topic gist, not perfect captions.
2. **Embed** — `all-MiniLM-L6-v2` (sentence-transformers, local, free, ~80MB). Store in pgvector.
3. **Suggest Groupings** — Compare new clips against ALL existing projects + ungrouped clips using cosine similarity.
4. **Present to User** — Show proposed groupings in a review UI with:
   - Similarity scores (percentage match)
   - Transcript snippets showing *why* clips matched
   - Existing projects that new clips might belong to
   - Clear "this is a new shoot for an existing project" detection
5. **User Decides** — Approve, reassign, merge, or create new project. Nothing moves without confirmation.

### Cross-Session Shoot Detection

Since Jacob shoots 3-5 clips per session but may ingest across multiple days:

- When new clips arrive, check similarity against **recent ungrouped clips** (last 30 days)
- If match confidence > threshold → prompt: *"These 3 clips look related to 2 clips you uploaded on March 20th about [topic]. Combine into one project?"*
- Track **ingest sessions** (batch of clips uploaded together) as a unit, but allow splitting across projects
- Show timeline view: clips grouped by upload date with proposed project assignments

### Handling Similar Subject Matter

- **Similarity threshold is tunable** in settings (default: 0.75 = pretty confident match)
- Below threshold → flag as "possible match" (shown but not pre-assigned)
- UI clearly shows: "We think this goes here, but you shoot a lot about [topic] — double check"
- **Project tags** (user-defined) help disambiguate: e.g., "unraid tutorial" vs "unraid troubleshooting"

### Folder Structure (generated after user approval)
```
/media/indygestion/
├── projects/
│   ├── 2026-03-26_unraid-setup-guide/
│   │   ├── originals/
│   │   │   ├── clip_001.mov        ← original ProRes, untouched
│   │   │   └── clip_002.mov
│   │   ├── proxies/
│   │   │   ├── clip_001_proxy.mp4
│   │   │   └── clip_002_proxy.mp4
│   │   ├── transcripts/
│   │   │   ├── clip_001.json       ← timestamped transcript
│   │   │   └── clip_002.json
│   │   └── project.json            ← metadata, status, tags, notes
│   └── 2026-03-28_docker-tutorial/
│       └── ...
├── staging/                         ← uploads land here first
├── archive/                         ← finished + compressed projects
└── _review/                         ← clips awaiting user assignment
```

### File Movement Transparency

- **Activity log** in UI: every file move/copy is logged with source → destination
- **Undo** support: moves within the last 24h can be reversed
- **Dry run mode**: show what *would* happen before committing
- Notifications for all automated file operations

---

## Feature 3: Proxy Generation + Archive Compression

### Proxy Generation (automatic on ingest)

- **Input:** ProRes / high-bitrate source files
- **Output:** Low-res H.264 proxy for editing
- **Encoder:** FFmpeg with **Intel QSV** (Quick Sync on i7-8700K UHD 630)
  - H.264 QSV encode is well-supported on Coffee Lake
  - Offloads CPU for Whisper to run simultaneously
- **Proxy preset:** 1080p, H.264, ~8Mbps, same framerate as source
- **Naming:** `{original_name}_proxy.mp4`
- Generated automatically after ingest, stored alongside originals

### Archive Compression (on "Finish Project")

When a project is marked **finished** in the UI:

1. **Choose codec** — User selects from presets (see below), with **estimated output size per file and total**
2. **Compress** — FFmpeg encodes originals using QSV acceleration where available
3. **Verify** — Compare frame count, duration, checksum spot-checks
4. **Move to archive** — Transfer compressed files to archive share
5. **Clean up** — Remove proxies and originals from active storage (with confirmation + grace period)
6. **Update metadata** — Mark project as archived, store archive location + compression details

### Encoding Presets (user-selectable per project)

| Preset | Codec | Quality | Est. Size vs ProRes | Best For |
|--------|-------|---------|---------------------|----------|
| Archive (default) | H.265 (HEVC) | CRF 18 | ~25-35% of original | Long-term storage, near-lossless |
| Archive (compact) | H.265 (HEVC) | CRF 22 | ~15-20% of original | Space savings, still great quality |
| Production archive | DNxHR HQ | ~145Mbps | ~50-60% of original | Re-editable intermediate |
| Custom | Configurable | User-set | Estimated live | Power users |

### Size Estimation

Before encoding starts, the UI shows:
```
Project: Unraid Setup Guide (4 clips, 47.2 GB total)

┌──────────────────┬──────────┬──────────────┬─────────────┐
│ Preset           │ Est Size │ Space Saved  │ Quality     │
├──────────────────┼──────────┼──────────────┼─────────────┤
│ H.265 CRF 18    │ ~14.2 GB │ 33.0 GB (70%)│ ★★★★★       │
│ H.265 CRF 22    │ ~8.5 GB  │ 38.7 GB (82%)│ ★★★★☆       │
│ DNxHR HQ         │ ~26.8 GB │ 20.4 GB (43%)│ ★★★★★ (edit)│
└──────────────────┴──────────┴──────────────┴─────────────┘
```

Estimates based on a quick probe of source files (resolution, bitrate, duration) + historical compression ratios.

### QSV Encoding Notes

- i7-8700K supports QSV for H.264 and **H.265 (8-bit only)**
- H.265 QSV encoding is faster than software but slightly lower quality at same CRF — we compensate by targeting a slightly lower CRF
- DNxHR has no QSV path — runs on CPU (still fine for archive, not time-critical)
- Docker container needs `/dev/dri` device passthrough for QSV access

---

## Feature 4: USB/SD Card Auto-Ingest

### Problem
Plugging in a camera card and manually copying files is tedious. Want automatic detection and ingest.

### Solution
A watcher service that detects new block devices, mounts them, and triggers the ingest pipeline.

### How It Works

1. **Device detection** — `udev` rules + watcher daemon
2. **Auto-mount** — Mount the device read-only to a temp path
3. **Scan** — Find video files (`.mov`, `.mp4`, `.mxf`, `.avi`, `.braw`, etc.)
4. **Notify** — UI toast: *"SanDisk 128GB detected — 5 video files (28.4 GB). Ingest now?"*
5. **Copy** — rsync with checksums from device to staging area (resumable if interrupted)
6. **Verify** — SHA-256 comparison, source vs destination
7. **Safe eject** — Unmount + UI confirmation: *"Safe to remove device"*
8. **Ingest** — Same pipeline as web uploads (transcribe → cluster → review → proxy)

### Configuration

- **Auto-ingest toggle**: Off by default (confirmation required). Can enable for hands-free operation.
- **File type filter**: Configurable list of extensions to look for
- **Minimum file size**: Skip thumbnails and small files (default: >10MB)

### Docker Requirements

- Container needs `/dev/dri` (QSV) and device access for USB
- Mount `/run/udev` from host for device events
- Unraid Docker extra parameters: `--device /dev/dri:/dev/dri --privileged` (or fine-grained device list)

---

## Data Model

```
Project
├── id, name, description, status (active|review|finished|archiving|archived)
├── created_at, updated_at, archived_at
├── folder_path, archive_path
├── tags[], notes
├── archive_preset (codec, crf, etc.)
├── estimated_archive_size
└── clips[]

Clip
├── id, project_id (nullable — unassigned clips), filename, original_path
├── file_size, duration, resolution, codec, fps, bitrate
├── proxy_path, proxy_status (pending|processing|ready|failed)
├── transcript_text, transcript_json_path
├── embedding (pgvector, 384-dim)
├── checksum_sha256
├── source (web_upload|usb_ingest|sd_ingest)
├── source_device (device label/serial for USB/SD)
├── ingest_session_id (batch grouping)
├── ingest_status (uploading|staged|transcribing|reviewing|assigned|archived)
├── similarity_matches[] (clip_id, score — for review UI)
└── created_at, updated_at

IngestSession
├── id, source (web|usb|sd), device_info
├── clip_count, total_size
├── started_at, completed_at
└── status (active|complete)

IngestJob
├── id, clip_id, job_type (proxy|transcribe|embed|archive)
├── status (queued|running|completed|failed|cancelled)
├── progress (0-100), error_message
├── started_at, completed_at
└── worker_id

FileOperation
├── id, clip_id, operation (move|copy|delete|archive)
├── source_path, dest_path
├── performed_at, reversible_until
└── undone (boolean)
```

---

## Web UI Pages

1. **Dashboard** — Active projects, recent ingests, queue status, storage usage breakdown
2. **Upload** — Drag-and-drop zone (Uppy), active upload progress, network speed indicator
3. **Review Queue** — **Key page**: newly ingested clips with proposed groupings, similarity scores, transcript snippets, drag-and-drop assignment, approve/reassign/create-new actions
4. **Projects** — List/grid of projects, filter by status/date/tag, quick actions
5. **Project Detail** — Clips in project, inline playback, transcript view, proxy download, finish/archive controls with size estimates
6. **Devices** — Connected USB/SD status, ingest history, auto-ingest toggle
7. **Activity Log** — All file operations with undo capability, job history
8. **Settings** — Network speed, encoding presets, storage paths, Whisper model, similarity threshold, auto-ingest config, file type filters

---

## Docker Compose Services

| Service | Image | Purpose |
|---------|-------|---------|
| `frontend` | Custom (Node/React) | Web UI |
| `backend` | Custom (Python/FastAPI) | API server |
| `tusd` | `tusproject/tusd` | Resumable upload server |
| `worker` | Custom (Celery) | Background processing (proxy, archive) |
| `whisper` | Custom (faster-whisper) | Transcription (CPU, small model) |
| `postgres` | `postgres:16` + pgvector | Database + embeddings |
| `redis` | `redis:7` | Task queue broker |
| `device-watcher` | Custom (lightweight) | USB/SD detection |

### Key Docker Flags (Unraid)
```
--device /dev/dri:/dev/dri          # Intel QSV access
--privileged                         # USB device detection (or fine-grained)
-v /mnt/user/indygestion:/media/indygestion  # Unraid share
-v /run/udev:/run/udev:ro           # Device events
```

---

## Settings Page

| Setting | Default | Description |
|---------|---------|-------------|
| Network Speed | 10GbE | Adjusts chunk size, concurrency, throughput estimates |
| Upload Chunk Size | Auto (based on network) | Override: 10MB - 500MB |
| Max Concurrent Uploads | Auto | Override: 1-8 |
| Whisper Model | `small` | Options: tiny, base, small, medium |
| Similarity Threshold | 0.75 | How confident before auto-suggesting groupings |
| Cross-Session Window | 30 days | How far back to look for related ungrouped clips |
| Default Archive Preset | H.265 CRF 18 | Per-project override available |
| Auto-Ingest (USB/SD) | Off | Enable for hands-free device ingest |
| Video Extensions | .mov,.mp4,.mxf,.avi,.braw | File types to scan for |
| Min File Size | 10 MB | Skip small files on device scan |
| Storage: Active | /media/indygestion/projects | Active project root |
| Storage: Archive | /media/indygestion/archive | Compressed archive root |
| Storage: Staging | /media/indygestion/staging | Upload staging area |

---

## Non-Goals (for now)

- Cloud sync / remote access (LAN-only first)
- Multi-user / auth (single-user initially)
- Video editing within the app
- Direct YouTube upload (future feature)
- Real-time collaboration
- 10-bit HEVC encoding (8700K QSV only supports 8-bit H.265)

---

## Development Phases

| Phase | Scope | Est. Effort |
|-------|-------|-------------|
| 1 | Project scaffolding, Docker Compose, DB schema, basic API | 1-2 days |
| 2 | Resumable upload (tusd + Uppy integration) | 2-3 days |
| 3 | Transcription pipeline (faster-whisper) + embeddings | 2-3 days |
| 4 | Smart grouping UI + review queue | 2-3 days |
| 5 | Proxy generation (QSV) + archive workflow + size estimation | 2-3 days |
| 6 | USB/SD auto-ingest | 1-2 days |
| 7 | Settings, activity log, polish | 1-2 days |
| 8 | Unraid template + documentation | 1 day |

**Total: ~12-19 days of dev work**

---

*Spec v0.2 — 2026-03-26 — Renamed to Indygestion, incorporated hardware details and workflow refinements*

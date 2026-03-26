import axios from 'axios';
import type { AppSettings, Clip, CodecEstimate, Device, FileOperation, IngestJob, Project, ReviewGroup, StorageStats } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({ baseURL: API_BASE_URL, timeout: 15000 });

export const formatBytes = (bytes: number) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / 1024 ** i).toFixed(1)} ${units[i]}`;
};

const mockClips: Clip[] = Array.from({ length: 8 }).map((_, i) => ({
  id: `clip-${i + 1}`,
  filename: `A_roll_${String(i + 1).padStart(3, '0')}.mov`,
  originalPath: `/media/indygestion/staging/A_roll_${i + 1}.mov`,
  fileSize: (5 + i) * 1024 ** 3,
  duration: 90 + i * 13,
  resolution: '3840x2160',
  codec: 'ProRes 422',
  fps: 29.97,
  bitrate: 220,
  proxyPath: `/api/proxy/clip-${i + 1}.mp4`,
  proxyStatus: 'ready',
  transcriptText: 'Today we are deep-diving into Docker workflows, NAS strategy, and practical troubleshooting from the latest shoot.',
  source: i % 2 ? 'web_upload' : 'sd_ingest',
  sourceDevice: i % 2 ? undefined : 'SanDisk 128GB',
  ingestStatus: 'reviewing',
  createdAt: new Date(Date.now() - i * 86_400_000).toISOString(),
  updatedAt: new Date().toISOString(),
  similarityMatches: [{ clipId: 'project-1', score: 0.91 - i * 0.03, reason: 'Repeated terms: “Unraid parity”, “cache pool”, “Docker compose”' }],
}));

const mockProjects: Project[] = [
  { id: 'project-1', name: 'Unraid Setup Guide', description: 'Primary tutorial series buildout', status: 'active', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), folderPath: '/media/indygestion/projects/2026-03-26_unraid-setup-guide', tags: ['unraid', 'tutorial'], clipCount: 7, totalSize: 47.2 * 1024 ** 3 },
  { id: 'project-2', name: 'Docker Troubleshooting', description: 'Troubleshooting & diagnostics series', status: 'review', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), folderPath: '/media/indygestion/projects/2026-03-28_docker-troubleshooting', tags: ['docker', 'debugging'], clipCount: 4, totalSize: 21.3 * 1024 ** 3 },
];

const mockJobs: IngestJob[] = [
  { id: 'job-1', clipId: 'clip-1', jobType: 'transcribe', status: 'running', progress: 61 },
  { id: 'job-2', clipId: 'clip-2', jobType: 'proxy', status: 'queued', progress: 10 },
  { id: 'job-3', clipId: 'clip-3', jobType: 'embed', status: 'completed', progress: 100 },
];

const mockSettings: AppSettings = {
  networkSpeed: '10GbE', uploadChunkSizeMb: 100, maxConcurrentUploads: 4, whisperModel: 'small', similarityThreshold: 0.75, crossSessionWindowDays: 30,
  defaultArchivePreset: 'H.265 CRF 18', autoIngest: false, videoExtensions: '.mov,.mp4,.mxf,.avi,.braw', minFileSizeMb: 10,
  storageActive: '/media/indygestion/projects', storageArchive: '/media/indygestion/archive', storageStaging: '/media/indygestion/staging', uploadThrottleMbps: 0,
};

const mockDevices: Device[] = [
  { id: 'device-1', label: 'SanDisk Extreme 128GB', serial: 'SDX-78A2', capacityBytes: 119 * 1024 ** 3, usedBytes: 34 * 1024 ** 3, detectedAt: new Date().toISOString(), status: 'ready', fileCount: 12, totalVideoBytes: 28.4 * 1024 ** 3 },
  { id: 'device-2', label: 'Sony A7S Card', serial: 'SONY-11FA', capacityBytes: 238 * 1024 ** 3, usedBytes: 103 * 1024 ** 3, detectedAt: new Date().toISOString(), status: 'ingesting', fileCount: 8, totalVideoBytes: 42.8 * 1024 ** 3 },
];

const mockOperations: FileOperation[] = Array.from({ length: 7 }).map((_, i) => ({
  id: `op-${i + 1}`,
  operation: i % 3 === 0 ? 'move' : i % 3 === 1 ? 'copy' : 'archive',
  sourcePath: `/media/indygestion/staging/clip_${i + 1}.mov`,
  destPath: `/media/indygestion/projects/2026-03-26_unraid/clip_${i + 1}.mov`,
  performedAt: new Date(Date.now() - i * 3_600_000).toISOString(),
  reversibleUntil: new Date(Date.now() + (24 - i) * 3_600_000).toISOString(),
  undone: false,
}));

const mockStorage: StorageStats = { totalBytes: 4 * 1024 ** 4, activeBytes: 1.2 * 1024 ** 4, archiveBytes: 2.4 * 1024 ** 4, stagingBytes: 0.14 * 1024 ** 4 };

const mockReviewGroups: ReviewGroup[] = [
  { id: 'group-1', title: 'Likely: Unraid Setup Guide', confidence: 0.91, why: 'Strong overlap in transcript keywords and pacing patterns from March 20 ingest.', targetProjectId: 'project-1', clips: mockClips.slice(0, 3) },
  { id: 'group-2', title: 'Possible: Docker Troubleshooting', confidence: 0.78, why: 'Related issue-triage terminology, but weaker narrative continuity.', targetProjectId: 'project-2', clips: mockClips.slice(3, 6) },
  { id: 'group-3', title: 'New Project Candidate', confidence: 0.66, why: 'Topic drift into camera workflow and behind-the-scenes operation.', clips: mockClips.slice(6, 8) },
];

const mockEstimates: CodecEstimate[] = [
  { preset: 'Archive (default)', codec: 'H.265', quality: 'CRF 18', estimatedSize: 14.2 * 1024 ** 3, spaceSaved: 0.70, rating: 5 },
  { preset: 'Archive (compact)', codec: 'H.265', quality: 'CRF 22', estimatedSize: 8.5 * 1024 ** 3, spaceSaved: 0.82, rating: 4 },
  { preset: 'Production archive', codec: 'DNxHR HQ', quality: '~145Mbps', estimatedSize: 26.8 * 1024 ** 3, spaceSaved: 0.43, rating: 5 },
];

const fromApi = async <T>(path: string, fallback: T): Promise<T> => {
  try { const { data } = await api.get<T>(path); return data; } catch { return fallback; }
};

export const getProjects = () => fromApi('/projects', mockProjects);
export const getProject = async (id: string) => (await getProjects()).find((p) => p.id === id) ?? mockProjects[0];
export const getClips = () => fromApi('/clips', mockClips);
export const getJobs = () => fromApi('/jobs', mockJobs);
export const getSettings = () => fromApi('/settings', mockSettings);
export const saveSettings = async (settings: AppSettings) => { try { await api.put('/settings', settings); } catch {} return settings; };
export const getDevices = () => fromApi('/devices', mockDevices);
export const getStorageStats = () => fromApi('/dashboard/storage', mockStorage);
export const getFileOperations = () => fromApi('/activity', mockOperations);
export const undoOperation = async (id: string) => { try { await api.post(`/activity/${id}/undo`); } catch {} return { success: true }; };
export const getReviewGroups = () => fromApi('/review/groups', mockReviewGroups);
export const getArchiveEstimates = (projectId: string) => fromApi(`/projects/${projectId}/archive-estimates`, mockEstimates);

export const triggerDeviceIngest = async (deviceId: string) => {
  try { await api.post(`/devices/${deviceId}/ingest`); } catch {}
  return { success: true };
};

export const approveReviewGroup = async (groupId: string, projectId?: string) => {
  try { await api.post(`/review/groups/${groupId}/approve`, { projectId }); } catch {}
  return { success: true };
};

export const rejectReviewGroup = async (groupId: string) => {
  try { await api.post(`/review/groups/${groupId}/reject`); } catch {}
  return { success: true };
};

import { useEffect, useState } from 'react';
import type { AppSettings } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';

export function SettingsForm({ settings, onSave }: { settings: AppSettings; onSave: (value: AppSettings) => void }) {
  const [form, setForm] = useState(settings);
  useEffect(() => setForm(settings), [settings]);
  const setField = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => setForm((prev) => ({ ...prev, [key]: value }));

  return <Card><form className="grid md:grid-cols-2 gap-4" onSubmit={(e) => { e.preventDefault(); onSave(form); }}>
    <label className="field">Network Speed<select value={form.networkSpeed} onChange={(e) => setField('networkSpeed', e.target.value as AppSettings['networkSpeed'])}><option>1GbE</option><option>2.5GbE</option><option>5GbE</option><option>10GbE</option><option>custom</option></select></label>
    <label className="field">Upload Chunk Size (MB)<input type="number" value={form.uploadChunkSizeMb} onChange={(e) => setField('uploadChunkSizeMb', Number(e.target.value))} /></label>
    <label className="field">Max Concurrent Uploads<input type="number" min={1} max={8} value={form.maxConcurrentUploads} onChange={(e) => setField('maxConcurrentUploads', Number(e.target.value))} /></label>
    <label className="field">Whisper Model<select value={form.whisperModel} onChange={(e) => setField('whisperModel', e.target.value as AppSettings['whisperModel'])}><option>tiny</option><option>base</option><option>small</option><option>medium</option></select></label>
    <label className="field">Similarity Threshold<input type="number" step="0.01" min={0} max={1} value={form.similarityThreshold} onChange={(e) => setField('similarityThreshold', Number(e.target.value))} /></label>
    <label className="field">Cross-Session Window (days)<input type="number" value={form.crossSessionWindowDays} onChange={(e) => setField('crossSessionWindowDays', Number(e.target.value))} /></label>
    <label className="field">Default Archive Preset<input value={form.defaultArchivePreset} onChange={(e) => setField('defaultArchivePreset', e.target.value)} /></label>
    <label className="field">Upload Throttle Mbps (0=off)<input type="number" value={form.uploadThrottleMbps} onChange={(e) => setField('uploadThrottleMbps', Number(e.target.value))} /></label>
    <label className="field md:col-span-2">Video Extensions<input value={form.videoExtensions} onChange={(e) => setField('videoExtensions', e.target.value)} /></label>
    <label className="field">Min File Size (MB)<input type="number" value={form.minFileSizeMb} onChange={(e) => setField('minFileSizeMb', Number(e.target.value))} /></label>
    <label className="field">Auto-Ingest<input type="checkbox" checked={form.autoIngest} onChange={(e) => setField('autoIngest', e.target.checked)} /></label>
    <label className="field md:col-span-2">Storage Active<input value={form.storageActive} onChange={(e) => setField('storageActive', e.target.value)} /></label>
    <label className="field md:col-span-2">Storage Archive<input value={form.storageArchive} onChange={(e) => setField('storageArchive', e.target.value)} /></label>
    <label className="field md:col-span-2">Storage Staging<input value={form.storageStaging} onChange={(e) => setField('storageStaging', e.target.value)} /></label>
    <div className="md:col-span-2"><Button type="submit">Save Settings</Button></div>
  </form></Card>;
}

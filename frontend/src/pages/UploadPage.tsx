import { UploadZone } from '../components/upload/UploadZone';
import { Card } from '../components/common/Card';

export function UploadPage() {
  return <div className="space-y-4"><h1 className="text-2xl font-bold">Upload</h1><Card><p className="text-sm text-slate-300 mb-3">Resumable ingest via tus. Network profile and chunk sizing come from settings.</p><UploadZone /></Card></div>;
}

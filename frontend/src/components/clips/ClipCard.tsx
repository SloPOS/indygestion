import { FileVideo } from 'lucide-react';
import { formatBytes } from '../../api/client';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import type { Clip } from '../../types';

export function ClipCard({ clip }: { clip: Clip }) {
  return <Card className="space-y-3"><div className="h-32 rounded-lg bg-gradient-to-br from-[#0f3460] to-[#16213e] flex items-center justify-center"><FileVideo /></div><div><h4 className="font-medium truncate">{clip.filename}</h4><p className="text-xs text-slate-400">{clip.resolution} • {clip.codec} • {Math.round(clip.duration)}s</p></div><p className="text-xs text-slate-300 line-clamp-2">{clip.transcriptText}</p><div className="flex justify-between items-center"><Badge>{formatBytes(clip.fileSize)}</Badge><Badge tone={clip.proxyStatus === 'ready' ? 'success' : 'warning'}>{clip.proxyStatus}</Badge></div></Card>;
}

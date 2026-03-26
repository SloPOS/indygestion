import { Link } from 'react-router-dom';
import { formatBytes } from '../../api/client';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import type { Project } from '../../types';

export function ProjectCard({ project }: { project: Project }) {
  return <Card><div className="flex justify-between"><div><h3 className="font-semibold">{project.name}</h3><p className="text-xs text-slate-400">{project.description}</p></div><Badge>{project.status}</Badge></div><div className="mt-3 text-sm text-slate-300">{project.clipCount} clips • {formatBytes(project.totalSize)}</div><div className="mt-3 flex gap-2 flex-wrap">{project.tags.map((t) => <Badge key={t}>{t}</Badge>)}</div><Link className="mt-4 inline-block text-[#7fb3ff] text-sm" to={`/projects/${project.id}`}>Open Project →</Link></Card>;
}

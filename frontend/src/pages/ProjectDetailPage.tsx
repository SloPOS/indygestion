import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ClipPlayer } from '../components/clips/ClipPlayer';
import { ArchiveDialog } from '../components/projects/ArchiveDialog';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { useClips } from '../hooks/useClips';
import { useArchiveEstimates, useProject, useStartArchive } from '../hooks/useProjects';

export function ProjectDetailPage() {
  const { id = '' } = useParams();
  const [open, setOpen] = useState(false);
  const { data: project } = useProject(id);
  const { data: clips = [] } = useClips();
  const { data: estimates = [] } = useArchiveEstimates(id);
  const startArchive = useStartArchive();
  const projectClips = useMemo(() => clips.slice(0, 4), [clips]);
  if (!project) return null;
  return <div className="space-y-4"><div className="flex justify-between"><h1 className="text-2xl font-bold">{project.name}</h1><Button onClick={() => setOpen(true)}>Archive Project</Button></div><Card><p className="text-slate-300">{project.description}</p></Card><div className="space-y-4">{projectClips.map((clip) => <Card key={clip.id}><div className="grid lg:grid-cols-2 gap-4"><ClipPlayer clip={clip} /><div><h3 className="font-semibold">{clip.filename}</h3><p className="text-xs text-slate-400">{clip.resolution} • {clip.codec}</p><details className="mt-3"><summary className="cursor-pointer text-[#7fb3ff]">Transcript</summary><p className="text-sm text-slate-300 mt-2">{clip.transcriptText}</p></details></div></div></Card>)}</div><ArchiveDialog open={open} onClose={() => setOpen(false)} estimates={estimates} onArchive={(preset) => { startArchive.mutate({ projectId: id, preset }); setOpen(false); }} /></div>;
}

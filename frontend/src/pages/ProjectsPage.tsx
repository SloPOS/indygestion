import { ProjectGrid } from '../components/projects/ProjectGrid';
import { useProjects } from '../hooks/useProjects';

export function ProjectsPage() {
  const { data: projects = [] } = useProjects();
  return <div className="space-y-4"><h1 className="text-2xl font-bold">Projects</h1><ProjectGrid projects={projects} /></div>;
}

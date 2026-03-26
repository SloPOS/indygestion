import type { Project } from '../../types';
import { ProjectCard } from './ProjectCard';

export function ProjectGrid({ projects }: { projects: Project[] }) {
  return <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">{projects.map((project) => <ProjectCard key={project.id} project={project} />)}</div>;
}

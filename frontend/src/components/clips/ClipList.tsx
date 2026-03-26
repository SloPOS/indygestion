import { DndContext, type DragEndEvent } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { Clip } from '../../types';
import { ClipCard } from './ClipCard';

function Item({ clip }: { clip: Clip }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: clip.id });
  return <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} {...attributes} {...listeners}><ClipCard clip={clip} /></div>;
}

export function ClipList({ clips, onReorder }: { clips: Clip[]; onReorder?: (items: Clip[]) => void }) {
  const onDragEnd = (event: DragEndEvent) => {
    if (!onReorder || !event.over || event.over.id === event.active.id) return;
    const oldIndex = clips.findIndex((c) => c.id === event.active.id);
    const newIndex = clips.findIndex((c) => c.id === event.over?.id);
    const items = [...clips];
    const [moved] = items.splice(oldIndex, 1); items.splice(newIndex, 0, moved); onReorder(items);
  };
  return <DndContext onDragEnd={onDragEnd}><SortableContext items={clips.map((c) => c.id)} strategy={verticalListSortingStrategy}><div className="space-y-3">{clips.map((clip) => <Item key={clip.id} clip={clip} />)}</div></SortableContext></DndContext>;
}

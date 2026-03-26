import { formatBytes } from '../../api/client';
import type { CodecEstimate } from '../../types';
import { Button } from '../common/Button';
import { Dialog } from '../common/Dialog';
import { Table, Td, Th } from '../common/Table';

export function ArchiveDialog({ open, onClose, estimates, onArchive }: { open: boolean; onClose: () => void; estimates: CodecEstimate[]; onArchive: (preset: string) => void }) {
  return <Dialog open={open} onClose={onClose} title="Archive Preset Selection"><Table><thead><tr><Th>Preset</Th><Th>Codec</Th><Th>Est. Size</Th><Th>Space Saved</Th><Th>Quality</Th><Th /></tr></thead><tbody>{estimates.map((e) => <tr key={e.preset}><Td>{e.preset}</Td><Td>{e.codec} {e.quality}</Td><Td>{formatBytes(e.estimatedSize)}</Td><Td>{Math.round(e.spaceSaved * 100)}%</Td><Td>{'★'.repeat(e.rating)}{'☆'.repeat(5 - e.rating)}</Td><Td className="text-right"><Button onClick={() => onArchive(e.preset)}>Use</Button></Td></tr>)}</tbody></Table></Dialog>;
}

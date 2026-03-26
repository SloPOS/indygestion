import { Badge } from '../common/Badge';

export function SimilarityBadge({ score, why }: { score: number; why: string }) {
  const tone = score > 0.85 ? 'success' : score > 0.7 ? 'warning' : 'danger';
  return <div title={why}><Badge tone={tone}>{Math.round(score * 100)}% match</Badge></div>;
}

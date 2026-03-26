import type { Clip } from '../../types';

export function ClipPlayer({ clip }: { clip: Clip }) {
  return <video controls className="w-full rounded-lg border border-[#2b3a61] bg-black" src={clip.proxyPath || ''}><track kind="captions" /></video>;
}

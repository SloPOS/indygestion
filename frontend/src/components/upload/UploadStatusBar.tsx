import { useMemo, useState } from 'react';
import { ChevronUp, Pause, Play } from 'lucide-react';
import { useUploadContext } from '../../contexts/UploadContext';

const formatBytesPerSecond = (value: number) => {
  if (value <= 0) return '0 B/s';
  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
  let speed = value;
  let unitIndex = 0;
  while (speed >= 1024 && unitIndex < units.length - 1) {
    speed /= 1024;
    unitIndex += 1;
  }
  return `${speed.toFixed(speed >= 10 ? 0 : 1)} ${units[unitIndex]}`;
};

export function UploadStatusBar() {
  const { files, activeUploads, totalProgress, uploadSpeedBps, isPaused, pauseAll, resumeAll } = useUploadContext();
  const [expanded, setExpanded] = useState(false);

  const activeFiles = useMemo(
    () => files.filter((file) => file.progress < 100),
    [files],
  );

  if (activeUploads <= 0 || activeFiles.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[70] w-[min(24rem,calc(100vw-2rem))]">
      <div className="rounded-2xl border border-slate-700 bg-[#111827]/95 backdrop-blur-md shadow-2xl shadow-black/50 overflow-hidden transition-all duration-300">
        <button
          type="button"
          className="w-full px-4 py-3 text-left hover:bg-white/5 transition-colors"
          onClick={() => setExpanded((prev) => !prev)}
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-100">{activeUploads} active upload{activeUploads > 1 ? 's' : ''}</p>
              <p className="text-xs text-slate-400">{Math.round(totalProgress)}% • {formatBytesPerSecond(uploadSpeedBps)}</p>
            </div>
            <ChevronUp className={`h-4 w-4 text-slate-300 transition-transform duration-300 ${expanded ? 'rotate-0' : 'rotate-180'}`} />
          </div>
          <div className="mt-3 h-1.5 rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-[#0f3460] transition-all duration-300 ease-out"
              style={{ width: `${Math.max(2, totalProgress)}%` }}
            />
          </div>
        </button>

        <div className={`grid transition-all duration-300 ${expanded ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}>
          <div className="overflow-hidden">
            <div className="border-t border-slate-800 px-4 py-3 space-y-3">
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={pauseAll}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 transition-colors"
                >
                  <Pause className="h-3.5 w-3.5" />
                  Pause All
                </button>
                <button
                  type="button"
                  onClick={resumeAll}
                  className="inline-flex items-center gap-1 rounded-lg border border-[#0f3460] bg-[#0f3460] px-2.5 py-1.5 text-xs font-medium text-slate-100 hover:bg-[#154778] transition-colors"
                >
                  <Play className="h-3.5 w-3.5" />
                  {isPaused ? 'Resume All' : 'Resume'}
                </button>
              </div>

              <ul className="space-y-2 max-h-56 overflow-auto pr-1">
                {activeFiles.map((file) => (
                  <li key={file.id} className="rounded-lg border border-slate-800 bg-slate-900/80 p-2.5">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="truncate text-xs font-medium text-slate-200">{file.name}</span>
                      <span className="text-[11px] text-slate-400">{Math.round(file.progress)}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-[#e94560] transition-all duration-300 ease-out"
                        style={{ width: `${Math.max(2, file.progress)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

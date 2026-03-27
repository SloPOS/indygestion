import Uppy, { type UppyFile } from '@uppy/core';
import GoldenRetriever from '@uppy/golden-retriever';
import Tus from '@uppy/tus';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

type Meta = Record<string, unknown>;
type Body = Record<string, unknown>;

type UploadSnapshotFile = {
  id: string;
  name: string;
  size: number;
  progress: number;
  uploadURL?: string;
  isPaused: boolean;
};

type UploadSnapshot = {
  files: UploadSnapshotFile[];
  updatedAt: number;
};

type UploadContextValue = {
  uppy: Uppy<Meta, Body>;
  files: UploadSnapshotFile[];
  activeUploads: number;
  totalProgress: number;
  isPaused: boolean;
  uploadSpeedBps: number;
  resumeAll: () => void;
  pauseAll: () => void;
};

const STORAGE_KEY = 'indygestion-uploads';

const UploadContext = createContext<UploadContextValue | null>(null);

const resolveTusEndpoint = () => `${window.location.origin}/files/`;

const fileProgressPercent = (file: UppyFile<Meta, Body>): number => {
  if (typeof file.progress?.percentage === 'number') {
    return Math.max(0, Math.min(100, file.progress.percentage));
  }

  const bytesTotal = typeof file.progress?.bytesTotal === 'number' ? file.progress.bytesTotal : file.size ?? 0;
  const bytesUploaded = typeof file.progress?.bytesUploaded === 'number' ? file.progress.bytesUploaded : 0;
  if (!bytesTotal || bytesTotal <= 0) return 0;
  return Math.max(0, Math.min(100, (bytesUploaded / bytesTotal) * 100));
};

const toSnapshotFiles = (files: UppyFile<Meta, Body>[]): UploadSnapshotFile[] =>
  files.map((file) => ({
    id: file.id,
    name: file.name ?? 'Unnamed file',
    size: file.size ?? 0,
    progress: fileProgressPercent(file),
    uploadURL: (file as UppyFile<Meta, Body> & { tus?: { uploadUrl?: string } }).tus?.uploadUrl,
    isPaused: !!file.isPaused,
  }));

export function UploadProvider({ children }: { children: ReactNode }) {
  const [uppy] = useState(
    () =>
      new Uppy<Meta, Body>({
        autoProceed: false,
        restrictions: { minFileSize: 10 * 1024 * 1024 },
      })
        .use(Tus, {
          endpoint: resolveTusEndpoint(),
          retryDelays: [0, 3000, 5000, 10000],
          chunkSize: 100 * 1024 * 1024,
          removeFingerprintOnSuccess: true,
        })
        .use(GoldenRetriever, {
          serviceWorker: false,
        }),
  );

  const [files, setFiles] = useState<UploadSnapshotFile[]>([]);
  const [totalProgress, setTotalProgress] = useState(0);
  const [activeUploads, setActiveUploads] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [uploadSpeedBps, setUploadSpeedBps] = useState(0);

  useEffect(() => {
    const syncFromState = () => {
      const state = uppy.getState();
      const uppyFiles = uppy.getFiles();
      const inFlight = uppyFiles.filter((file) => !file.progress?.uploadComplete && !file.error);
      const allPaused = inFlight.length > 0 && inFlight.every((file) => !!file.isPaused);

      setFiles(toSnapshotFiles(uppyFiles));
      setTotalProgress(typeof state.totalProgress === 'number' ? state.totalProgress : 0);
      setActiveUploads(inFlight.length);
      setIsPaused(allPaused);
    };

    let lastTotalUploaded = 0;
    let lastTick = Date.now();

    const persistState = () => {
      const snapshot: UploadSnapshot = {
        files: toSnapshotFiles(uppy.getFiles()),
        updatedAt: Date.now(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
      syncFromState();
    };

    const updateSpeed = () => {
      const now = Date.now();
      const elapsed = (now - lastTick) / 1000;
      if (elapsed <= 0) return;

      const currentTotal = uppy.getFiles().reduce((sum, file) => {
        const uploaded = typeof file.progress?.bytesUploaded === 'number' ? file.progress.bytesUploaded : 0;
        return sum + uploaded;
      }, 0);
      const delta = Math.max(0, currentTotal - lastTotalUploaded);
      setUploadSpeedBps(delta / elapsed);

      lastTotalUploaded = currentTotal;
      lastTick = now;
      syncFromState();
    };

    const handleComplete = () => {
      setUploadSpeedBps(0);
      persistState();
    };

    syncFromState();

    uppy.on('file-added', persistState);
    uppy.on('file-removed', persistState);
    uppy.on('upload', persistState);
    uppy.on('upload-progress', updateSpeed);
    uppy.on('upload-success', persistState);
    uppy.on('upload-error', persistState);
    uppy.on('complete', handleComplete);
    uppy.on('state-update', syncFromState);

    return () => {
      uppy.off('file-added', persistState);
      uppy.off('file-removed', persistState);
      uppy.off('upload', persistState);
      uppy.off('upload-progress', updateSpeed);
      uppy.off('upload-success', persistState);
      uppy.off('upload-error', persistState);
      uppy.off('complete', handleComplete);
      uppy.off('state-update', syncFromState);
      uppy.destroy();
    };
  }, [uppy]);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;

    try {
      const snapshot = JSON.parse(raw) as UploadSnapshot;
      const interrupted = snapshot.files.filter((file) => file.progress < 100);
      if (!interrupted.length) return;

      const shouldResume = window.confirm(`${interrupted.length} interrupted uploads found. Resume?`);
      if (!shouldResume) return;

      setTimeout(() => {
        uppy.resumeAll();
      }, 0);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [uppy]);

  const resumeAll = useCallback(() => {
    uppy.resumeAll();
  }, [uppy]);

  const pauseAll = useCallback(() => {
    uppy.pauseAll();
  }, [uppy]);

  const value = useMemo<UploadContextValue>(
    () => ({
      uppy,
      files,
      activeUploads,
      totalProgress,
      isPaused,
      uploadSpeedBps,
      resumeAll,
      pauseAll,
    }),
    [uppy, files, activeUploads, totalProgress, isPaused, uploadSpeedBps, resumeAll, pauseAll],
  );

  return <UploadContext.Provider value={value}>{children}</UploadContext.Provider>;
}

export function useUploadContext() {
  const context = useContext(UploadContext);
  if (!context) {
    throw new Error('useUploadContext must be used within an UploadProvider');
  }
  return context;
}

import { useEffect, useMemo } from 'react';
import Uppy from '@uppy/core';
import Dashboard from '@uppy/dashboard';
import Tus from '@uppy/tus';
import '@uppy/core/css/style.min.css';
import '@uppy/dashboard/css/style.min.css';

const resolveTusEndpoint = () => {
  // Force same-origin uploads by default to avoid Unraid login redirects on :80.
  // This ensures uploads hit the same host+port as the UI (e.g. :4708/files/).
  const configured = import.meta.env.VITE_TUSD_ENDPOINT as string | undefined;
  if (configured && configured.trim().length > 0) {
    if (configured.startsWith('/')) {
      return `${window.location.origin}${configured}`;
    }
    return configured;
  }
  return `${window.location.origin}/files/`;
};

export function UploadZone() {
  const uppy = useMemo(
    () =>
      new Uppy({ autoProceed: false, restrictions: { minFileSize: 10 * 1024 * 1024 } }).use(Tus, {
        endpoint: resolveTusEndpoint(),
        retryDelays: [0, 3000, 5000, 10000],
        chunkSize: 100 * 1024 * 1024,
      }),
    [],
  );

  useEffect(() => {
    uppy.use(Dashboard, {
      inline: true,
      target: '#uppy-dashboard',
      height: 420,
      theme: 'dark',
      proudlyDisplayPoweredByUppy: false,
      note: 'Resumable uploads via tusd endpoint /files',
    });
    return () => uppy.destroy();
  }, [uppy]);

  return <div id="uppy-dashboard" />;
}

import { useEffect, useId } from 'react';
import Dashboard from '@uppy/dashboard';
import '@uppy/core/css/style.min.css';
import '@uppy/dashboard/css/style.min.css';
import { useUploadContext } from '../../contexts/UploadContext';

export function UploadZone() {
  const { uppy } = useUploadContext();
  const dashboardId = useId().replace(/:/g, '-');

  useEffect(() => {
    const pluginId = `upload-dashboard-${dashboardId}`;

    uppy.use(Dashboard, {
      id: pluginId,
      inline: true,
      target: `#${dashboardId}`,
      height: 420,
      theme: 'dark',
      proudlyDisplayPoweredByUppy: false,
      note: 'Resumable uploads via tusd endpoint /files',
    });

    return () => {
      const plugin = uppy.getPlugin(pluginId);
      if (plugin) {
        uppy.removePlugin(plugin);
      }
    };
  }, [dashboardId, uppy]);

  return <div id={dashboardId} />;
}

import { useState } from 'react';
import { DeviceStatus } from '../components/devices/DeviceStatus';
import { Card } from '../components/common/Card';
import { useDevices, useTriggerIngest } from '../hooks/useDevices';

export function DevicesPage() {
  const { data: devices = [] } = useDevices();
  const ingest = useTriggerIngest();
  const [autoIngest, setAutoIngest] = useState(false);
  return <div className="space-y-4"><div className="flex justify-between"><h1 className="text-2xl font-bold">Devices</h1><label className="text-sm flex items-center gap-2">Auto-Ingest <input type="checkbox" checked={autoIngest} onChange={(e) => setAutoIngest(e.target.checked)} /></label></div><Card><p className="text-sm text-slate-300">USB/SD watcher status: ready. Detected devices are listed below with ingest controls.</p></Card><DeviceStatus devices={devices} onIngest={(id) => ingest.mutate(id)} /></div>;
}

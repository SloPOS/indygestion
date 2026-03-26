import type { Device } from '../../types';
import { formatBytes } from '../../api/client';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { Card } from '../common/Card';

export function DeviceStatus({ devices, onIngest }: { devices: Device[]; onIngest: (deviceId: string) => void }) {
  return <div className="grid lg:grid-cols-2 gap-4">{devices.map((device) => <Card key={device.id}><div className="flex justify-between"><h3 className="font-semibold">{device.label}</h3><Badge tone={device.status === 'ingesting' ? 'warning' : 'success'}>{device.status}</Badge></div><p className="text-xs text-slate-400 mt-1">{device.serial}</p><div className="text-sm mt-3 text-slate-300">{device.fileCount} files • {formatBytes(device.totalVideoBytes)}</div><div className="w-full h-2 rounded bg-[#0f1a35] mt-2"><div className="h-full bg-[#0f3460] rounded" style={{ width: `${(device.usedBytes / device.capacityBytes) * 100}%` }} /></div><div className="mt-3"><Button onClick={() => onIngest(device.id)}>Ingest Now</Button></div></Card>)}</div>;
}

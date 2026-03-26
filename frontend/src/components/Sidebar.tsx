import { Activity, FolderKanban, HardDrive, Home, Settings, Upload, Usb, WandSparkles } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const items = [
  { to: '/', icon: Home, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/review', icon: WandSparkles, label: 'Review Queue' },
  { to: '/projects', icon: FolderKanban, label: 'Projects' },
  { to: '/devices', icon: Usb, label: 'Devices' },
  { to: '/activity', icon: Activity, label: 'Activity Log' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-[#111a33] border-r border-[#23345d] p-4">
      <div className="mb-6 flex items-center gap-2 text-[#e94560] font-bold text-xl"><HardDrive className="h-5"/> Indygestion</div>
      <nav className="space-y-1">
        {items.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-lg transition ${isActive ? 'bg-[#0f3460] text-white' : 'text-slate-300 hover:bg-[#1d2a4a]'}`}>
            <Icon className="h-4 w-4" /> {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

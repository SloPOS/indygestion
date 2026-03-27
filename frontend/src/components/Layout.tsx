import { Outlet } from 'react-router-dom';
import { UploadStatusBar } from './upload/UploadStatusBar';
import { Sidebar } from './Sidebar';

export function Layout() {
  return (
    <div className="min-h-screen bg-[#1a1a2e] text-slate-100 flex">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto"><Outlet /></main>
      <UploadStatusBar />
    </div>
  );
}

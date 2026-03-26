import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ActivityPage } from './pages/ActivityPage';
import { DashboardPage } from './pages/DashboardPage';
import { DevicesPage } from './pages/DevicesPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ReviewPage } from './pages/ReviewPage';
import { SettingsPage } from './pages/SettingsPage';
import { UploadPage } from './pages/UploadPage';

const router = createBrowserRouter([
  { path: '/', element: <Layout />, children: [
    { index: true, element: <DashboardPage /> },
    { path: 'upload', element: <UploadPage /> },
    { path: 'review', element: <ReviewPage /> },
    { path: 'projects', element: <ProjectsPage /> },
    { path: 'projects/:id', element: <ProjectDetailPage /> },
    { path: 'devices', element: <DevicesPage /> },
    { path: 'activity', element: <ActivityPage /> },
    { path: 'settings', element: <SettingsPage /> },
  ] },
]);

export default function App() { return <RouterProvider router={router} />; }

import { SettingsForm } from '../components/settings/SettingsForm';
import { useSaveSettings, useSettings } from '../hooks/useSettings';

export function SettingsPage() {
  const { data } = useSettings();
  const save = useSaveSettings();
  if (!data) return null;
  return <div className="space-y-4"><h1 className="text-2xl font-bold">Settings</h1><SettingsForm settings={data} onSave={(value) => save.mutate(value)} /></div>;
}

import { useOllamaStatus } from '../hooks/useOllamaStatus';
import type { WorkspacePageProps } from '../types/pages';
import { EmptyState, Panel, Badge } from '../ui/primitives';

export function OllamaPage(_props: WorkspacePageProps) {
  const { isConnected, isLoading } = useOllamaStatus();

  return (
    <div className="fedda-page">
      <Panel
        title="Ollama Models"
        subtitle="Local text and vision models."
        actions={
          <Badge tone={isConnected ? 'success' : 'warn'}>
            {isLoading ? 'Checking…' : isConnected ? 'Online' : 'Offline'}
          </Badge>
        }
      >
        <EmptyState
          title="Ollama manager shell ready"
          description="Model download and removal UI will live here. Ollama starts automatically from run.bat when available."
        />
      </Panel>
    </div>
  );
}
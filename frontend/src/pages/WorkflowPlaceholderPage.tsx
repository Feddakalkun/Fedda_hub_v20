import { PAGE_META } from '../modules/registry';
import type { WorkspacePageProps } from '../types/pages';
import { EmptyState, Panel } from '../ui/primitives';

export function WorkflowPlaceholderPage({ activeTab }: WorkspacePageProps) {
  const meta = PAGE_META[activeTab] ?? { title: activeTab, subtitle: 'Workflow page' };

  return (
    <div className="fedda-page">
      <Panel title={meta.title} subtitle={meta.subtitle}>
        <EmptyState
          title="Workflow page not wired yet"
          description="Add a Page component to this tab in registry.ts, or register a workflow in workflow_api.json."
        />
      </Panel>
    </div>
  );
}
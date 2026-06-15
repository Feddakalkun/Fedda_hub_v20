import type { WorkspacePageProps } from '../types/pages';
import { EmptyState, Panel } from '../ui/primitives';

export function LibraryPage(_props: WorkspacePageProps) {
  return (
    <div className="fedda-page">
      <Panel title="LoRA Library" subtitle="Install and manage LoRA packs for active workflows.">
        <EmptyState
          title="Library shell ready"
          description="Connect LoRA APIs when you add your first image workflow module."
        />
      </Panel>
    </div>
  );
}
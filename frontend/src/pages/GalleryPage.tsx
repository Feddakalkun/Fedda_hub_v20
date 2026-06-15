import type { WorkspacePageProps } from '../types/pages';
import { EmptyState, Panel } from '../ui/primitives';

export function GalleryPage(_props: WorkspacePageProps) {
  return (
    <div className="fedda-page">
      <Panel title="Gallery" subtitle="Unified output browser for images and video.">
        <EmptyState
          title="Gallery shell ready"
          description="Wire this page to /api/files/list when your first workflow is live."
        />
      </Panel>
    </div>
  );
}
import { workflowModulesForArea } from '../../modules/registry';
import { EmptyState } from '../../ui/primitives';
import { WorkflowCard } from '../cards/WorkflowCard';
import { CardGrid } from './CardGrid';

interface SectionViewProps {
  area: 'image' | 'video';
  onOpenTab: (tab: string) => void;
}

export function SectionView({ area, onOpenTab }: SectionViewProps) {
  const modules = workflowModulesForArea(area);
  const title = area === 'image' ? 'Image workflows' : 'Video workflows';

  if (!modules.length) {
    return (
      <div className="fedda-page">
        <EmptyState
          title={`No ${title.toLowerCase()} yet`}
          description="Register a workflow module in config/modules.json, workflow_api.json, and frontend/src/modules/registry.ts. Each workflow gets one card here."
        />
      </div>
    );
  }

  return (
    <div className="fedda-page">
      <header className="fedda-page-hero compact">
        <h1>{title}</h1>
      </header>
      <CardGrid>
        {modules.map((module) => (
          <WorkflowCard
            key={module.id}
            module={module}
            onOpen={() => onOpenTab(module.defaultTab)}
          />
        ))}
      </CardGrid>
    </div>
  );
}
import { ENABLED_MODULES } from '../../modules/registry';
import { WorkflowCard } from '../cards/WorkflowCard';
import { CardGrid } from './CardGrid';

interface HomeViewProps {
  onOpenTab: (tab: string) => void;
}

export function HomeView({ onOpenTab }: HomeViewProps) {
  const homeModules = ENABLED_MODULES.filter((module) => module.area === 'home' || module.area === 'system');

  return (
    <div className="fedda-page">
      <header className="fedda-page-hero">
        <p className="fedda-eyebrow">FEDDA Hub v20</p>
        <h1>Creative studio, rebuilt clean</h1>
        <p>Cards and workflows start empty. Add modules in registry.ts and config as you go.</p>
      </header>
      <CardGrid>
        {homeModules.map((module) => (
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
import { motion } from 'framer-motion';
import type { FeddaModule } from '../../modules/registry';
import { Badge } from '../../ui/primitives';

interface WorkflowCardProps {
  module: FeddaModule;
  onOpen: () => void;
}

export function WorkflowCard({ module, onOpen }: WorkflowCardProps) {
  const Icon = module.Icon;
  const poster = module.card?.poster ?? '/cards/placeholders/default.svg';

  return (
    <motion.button
      type="button"
      className="fedda-workflow-card"
      onClick={onOpen}
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 420, damping: 28 }}
    >
      <div className="fedda-workflow-card-media">
        <img src={poster} alt="" loading="lazy" />
        {module.card?.video && (
          <video
            src={module.card.video}
            muted
            loop
            playsInline
            onMouseEnter={(event) => void event.currentTarget.play()}
            onMouseLeave={(event) => {
              event.currentTarget.pause();
              event.currentTarget.currentTime = 0;
            }}
          />
        )}
        <div className="fedda-workflow-card-scrim" />
        <div className="fedda-workflow-card-icon">
          <Icon size={18} />
        </div>
      </div>
      <div className="fedda-workflow-card-copy">
        <div className="fedda-workflow-card-top">
          <h3>{module.label}</h3>
          {module.status && (
            <Badge tone={module.status === 'verified' ? 'success' : module.status === 'lab' ? 'lab' : 'neutral'}>
              {module.statusLabel ?? module.status}
            </Badge>
          )}
        </div>
        <p>{module.description}</p>
      </div>
    </motion.button>
  );
}
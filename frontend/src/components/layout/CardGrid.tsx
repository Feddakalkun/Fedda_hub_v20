import type { ReactNode } from 'react';

export function CardGrid({ children }: { children: ReactNode }) {
  return <div className="fedda-card-grid">{children}</div>;
}
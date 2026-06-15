import { ChevronRight } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
}

interface BreadcrumbTrailProps {
  items: BreadcrumbItem[];
}

export function BreadcrumbTrail({ items }: BreadcrumbTrailProps) {
  if (!items.length) return null;

  return (
    <nav className="fedda-breadcrumbs" aria-label="Breadcrumb">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`} className="fedda-breadcrumb-item">
            {item.onClick && !isLast ? (
              <button type="button" onClick={item.onClick}>
                {item.label}
              </button>
            ) : (
              <span className={isLast ? 'fedda-breadcrumb-current' : undefined}>{item.label}</span>
            )}
            {!isLast && <ChevronRight size={14} aria-hidden />}
          </span>
        );
      })}
    </nav>
  );
}
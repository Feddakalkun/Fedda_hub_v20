import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

const buttonClass: Record<ButtonVariant, string> = {
  primary: 'fedda-btn fedda-btn-primary',
  secondary: 'fedda-btn fedda-btn-secondary',
  ghost: 'fedda-btn fedda-btn-ghost',
  danger: 'fedda-btn fedda-btn-danger',
};

export function Button({ variant = 'secondary', className = '', children, ...props }: ButtonProps) {
  return (
    <button type="button" className={`${buttonClass[variant]} ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}

interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function Panel({ title, subtitle, actions, children, className = '', ...props }: PanelProps) {
  return (
    <section className={`fedda-panel ${className}`.trim()} {...props}>
      {(title || actions) && (
        <header className="fedda-panel-header">
          <div>
            {title && <h2 className="fedda-panel-title">{title}</h2>}
            {subtitle && <p className="fedda-panel-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="fedda-panel-actions">{actions}</div>}
        </header>
      )}
      <div className="fedda-panel-body">{children}</div>
    </section>
  );
}

interface BadgeProps {
  tone?: 'neutral' | 'success' | 'warn' | 'info' | 'lab';
  children: ReactNode;
}

export function Badge({ tone = 'neutral', children }: BadgeProps) {
  return <span className={`fedda-badge fedda-badge-${tone}`}>{children}</span>;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="fedda-empty">
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
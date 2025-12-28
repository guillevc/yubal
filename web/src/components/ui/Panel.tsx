import { forwardRef } from "react";
import type { ReactNode, HTMLAttributes } from "react";

export interface PanelProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
}

export const Panel = forwardRef<HTMLElement, PanelProps>(
  ({ children, className = "", ...props }, ref) => {
    return (
      <section
        ref={ref}
        className={`border-divider bg-content1 rounded-large border-small flex flex-col overflow-hidden ${className}`}
        {...props}
      >
        {children}
      </section>
    );
  }
);
Panel.displayName = "Panel";

export interface PanelHeaderProps extends HTMLAttributes<HTMLElement> {
  leadingIcon?: ReactNode;
  badge?: ReactNode;
  trailingIcon?: ReactNode;
  children: ReactNode;
}

export const PanelHeader = forwardRef<HTMLElement, PanelHeaderProps>(
  ({ leadingIcon, badge, trailingIcon, children, className = "", ...props }, ref) => {
    return (
      <header
        ref={ref}
        className={`shrink-0 px-4 py-3 ${className}`}
        {...props}
      >
        <div
          className={`flex items-center gap-2 ${className}`}
          {...props}
        >
          {leadingIcon && (
            <span className="text-foreground-500">
              {leadingIcon}
            </span>
          )}
          <span className="text-foreground-500 font-mono text-xs tracking-wider uppercase">
            {children}
          </span>
          {badge}
          {trailingIcon && (
            <span className="ml-auto text-foreground-500">{trailingIcon}</span>
          )}
        </div>
      </header>
    );
  }
);
PanelHeader.displayName = "PanelHeader";

export interface PanelContentProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export const PanelContent = forwardRef<HTMLDivElement, PanelContentProps>(
  ({ children, className = "", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`border-divider border-t-small h-72 overflow-y-auto p-3 ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);
PanelContent.displayName = "PanelContent";

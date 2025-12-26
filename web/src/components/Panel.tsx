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
  children: ReactNode;
}

export const PanelHeader = forwardRef<HTMLElement, PanelHeaderProps>(
  ({ children, className = "", ...props }, ref) => {
    return (
      <header
        ref={ref}
        className={`border-divider border-b-small shrink-0 px-4 py-3 ${className}`}
        {...props}
      >
        {children}
      </header>
    );
  }
);
PanelHeader.displayName = "PanelHeader";

export interface PanelTitleProps extends HTMLAttributes<HTMLDivElement> {
  icon?: ReactNode;
  children: ReactNode;
  badge?: ReactNode;
}

export const PanelTitle = forwardRef<HTMLDivElement, PanelTitleProps>(
  ({ icon, children, badge, className = "", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex items-center gap-2 ${className}`}
        {...props}
      >
        {icon && (
          <span className="text-foreground-400 [&>svg]:h-4 [&>svg]:w-4">
            {icon}
          </span>
        )}
        <span className="text-foreground-400 font-mono text-xs tracking-wider uppercase">
          {children}
        </span>
        {badge}
      </div>
    );
  }
);
PanelTitle.displayName = "PanelTitle";

export interface PanelContentProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export const PanelContent = forwardRef<HTMLDivElement, PanelContentProps>(
  ({ children, className = "", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`h-72 overflow-y-auto p-3 ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);
PanelContent.displayName = "PanelContent";

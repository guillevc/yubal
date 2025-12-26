import { forwardRef } from "react";
import type { ReactNode, HTMLAttributes } from "react";

export interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export const Panel = forwardRef<HTMLDivElement, PanelProps>(
  ({ children, className = "", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`border-default-200 rounded-large border-medium flex flex-col overflow-hidden ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Panel.displayName = "Panel";

export interface PanelHeaderProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export const PanelHeader = forwardRef<HTMLDivElement, PanelHeaderProps>(
  ({ children, className = "", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`border-default-200 border-b-medium shrink-0 px-4 py-3 ${className}`}
        {...props}
      >
        {children}
      </div>
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
          <span className="text-default-500 [&>svg]:h-4 [&>svg]:w-4">
            {icon}
          </span>
        )}
        <span className="text-default-500 font-mono text-xs tracking-wider uppercase">
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

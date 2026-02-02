import { Card, CardBody, CardHeader, ScrollShadow } from "@heroui/react";
import type { HTMLAttributes, ReactNode } from "react";
import { forwardRef } from "react";

export interface PanelProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
}

export const Panel = forwardRef<HTMLElement, PanelProps>(
  ({ children, className = "" }) => {
    return (
      <Card
        className={className}
        classNames={{
          body: "px-0",
        }}
      >
        {children}
      </Card>
    );
  },
);
Panel.displayName = "Panel";

export interface PanelHeaderProps extends HTMLAttributes<HTMLElement> {
  leadingIcon?: ReactNode;
  badge?: ReactNode;
  trailingIcon?: ReactNode;
  children: ReactNode;
}

export const PanelHeader = forwardRef<HTMLElement, PanelHeaderProps>(
  ({
    leadingIcon,
    badge,
    trailingIcon,
    children,
    className = "",
    ...props
  }) => {
    return (
      <CardHeader className={`shrink-0 px-4 py-3 ${className}`} {...props}>
        <div
          className={`text-foreground-500 flex w-full items-center gap-2 ${className}`}
          {...props}
        >
          {leadingIcon && <span>{leadingIcon}</span>}
          <span className="text-xs tracking-wider uppercase">{children}</span>
          {badge}
          {trailingIcon && <span className="ml-auto">{trailingIcon}</span>}
        </div>
      </CardHeader>
    );
  },
);
PanelHeader.displayName = "PanelHeader";

export interface PanelContentProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  height?: string;
}

export const PanelContent = forwardRef<HTMLDivElement, PanelContentProps>(
  ({ children, className = "", height = "h-72", ...props }, ref) => {
    return (
      <CardBody className="pt-0">
        <ScrollShadow
          ref={ref}
          className={`${height} px-4 py-4 ${className}`}
          offset={2}
          {...props}
        >
          {children}
        </ScrollShadow>
      </CardBody>
    );
  },
);
PanelContent.displayName = "PanelContent";

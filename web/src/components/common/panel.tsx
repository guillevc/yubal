import { Card, CardBody, CardHeader, ScrollShadow } from "@heroui/react";
import type { HTMLAttributes, ReactNode, Ref } from "react";

type Props = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
};

export function Panel({ children, className = "" }: Props) {
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
}

type HeaderProps = {
  leadingIcon?: ReactNode;
  badge?: ReactNode;
  trailingIcon?: ReactNode;
  children: ReactNode;
  className?: string;
  onClick?: () => void;
};

export function PanelHeader({
  leadingIcon,
  badge,
  trailingIcon,
  children,
  className = "",
  onClick,
  ...props
}: HeaderProps) {
  return (
    <CardHeader
      className={`shrink-0 px-4 py-3 ${className}`}
      {...props}
      onClick={onClick}
    >
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
}

type ContentProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  height?: string;
  ref?: Ref<HTMLDivElement>;
};

export function PanelContent({
  children,
  className = "",
  height = "h-72",
  ref,
  ...props
}: ContentProps) {
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
}

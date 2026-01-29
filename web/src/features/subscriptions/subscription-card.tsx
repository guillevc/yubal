import { Button, Switch, Tooltip } from "@heroui/react";
import { ExternalLink, RefreshCw, Trash2 } from "lucide-react";
import type { Subscription } from "@/api/subscriptions";
import { HoverFade } from "@/components/common/hover-fade";
import { useHover } from "@/hooks/use-hover";

interface SubscriptionCardProps {
  subscription: Subscription;
  onToggleEnabled: (id: string, enabled: boolean) => void;
  onSync: (id: string) => void;
  onDelete: (id: string) => void;
}

function formatTimeAgo(dateString: string | null | undefined): string {
  if (!dateString) return "Never";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function SubscriptionCard({
  subscription,
  onToggleEnabled,
  onSync,
  onDelete,
}: SubscriptionCardProps) {
  const [isHovered, hoverHandlers] = useHover();

  return (
    <div
      className={`bg-content2 shadow-small rounded-large overflow-hidden px-3 py-2.5 transition-opacity ${
        !subscription.enabled ? "opacity-60" : ""
      }`}
      {...hoverHandlers}
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div className="bg-content3 flex h-12 w-12 shrink-0 items-center justify-center rounded">
          <RefreshCw className="text-foreground-400 h-4 w-4" />
        </div>

        {/* Info */}
        <div className="min-w-0 flex-1 font-mono">
          <p className="text-foreground truncate text-sm">
            {subscription.name}
          </p>
          <p className="text-foreground-500 text-xs">
            Synced {formatTimeAgo(subscription.last_synced_at)}
          </p>
        </div>

        {/* Enable toggle */}
        <Tooltip
          content={
            subscription.enabled ? "Disable auto-sync" : "Enable auto-sync"
          }
        >
          <div>
            <Switch
              size="sm"
              isSelected={subscription.enabled}
              onValueChange={(enabled) =>
                onToggleEnabled(subscription.id, enabled)
              }
              aria-label="Toggle auto-sync"
            />
          </div>
        </Tooltip>

        {/* Sync button */}
        <Tooltip content="Sync now">
          <Button
            variant="light"
            size="sm"
            isIconOnly
            className="text-foreground-500 hover:text-primary h-7 w-7 shrink-0"
            onPress={() => onSync(subscription.id)}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </Tooltip>

        {/* External link */}
        <HoverFade show={isHovered}>
          <Button
            as="a"
            href={subscription.url}
            target="_blank"
            rel="noopener noreferrer"
            variant="light"
            size="sm"
            isIconOnly
            className="text-foreground-500 hover:text-primary h-7 w-7 shrink-0"
          >
            <ExternalLink className="h-4 w-4" />
          </Button>
        </HoverFade>

        {/* Delete button */}
        <HoverFade show={isHovered}>
          <Button
            variant="light"
            size="sm"
            isIconOnly
            className="text-foreground-500 hover:text-danger h-7 w-7 shrink-0"
            onPress={() => onDelete(subscription.id)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </HoverFade>
      </div>
    </div>
  );
}

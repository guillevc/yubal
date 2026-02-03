import type { Subscription } from "@/api/subscriptions";
import { EmptyState } from "@/components/common/empty-state";
import { formatTimeAgo } from "@/lib/format";
import {
  Button,
  Image,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow,
} from "@heroui/react";
import {
  InboxIcon,
  ListMusicIcon,
  RefreshCwIcon,
  Trash2Icon,
} from "lucide-react";
import { useCallback } from "react";

type ColumnKey = "name" | "lastSynced" | "limit" | "enabled" | "actions";

const columns: { name: string; key: ColumnKey }[] = [
  { name: "PLAYLIST", key: "name" },
  { name: "LAST SYNCED", key: "lastSynced" },
  { name: "LIMIT", key: "limit" },
  { name: "ENABLED", key: "enabled" },
  { name: "ACTIONS", key: "actions" },
];

type SubscriptionsTableProps = {
  subscriptions: Subscription[];
  isLoading?: boolean;
  isSchedulerEnabled?: boolean;
  onToggleEnabled: (id: string, enabled: boolean) => void;
  onSync: (id: string) => void;
  onDelete: (id: string) => void;
};

export function SubscriptionsTable({
  subscriptions,
  isLoading,
  isSchedulerEnabled,
  onToggleEnabled,
  onSync,
  onDelete,
}: SubscriptionsTableProps) {
  const renderCell = useCallback(
    (
      subscription: Subscription,
      isSchedulerEnabled: boolean,
      columnKey: ColumnKey,
    ) => {
      switch (columnKey) {
        case "name": {
          const size = 40;
          return (
            <div className="flex items-center gap-4">
              {subscription.thumbnail_url ? (
                <Image
                  alt="Playlist thumbnail"
                  src={subscription.thumbnail_url}
                  width={size}
                  height={size}
                  radius="md"
                  fallbackSrc=""
                />
              ) : (
                <div className="bg-content3 flex h-8 w-8 shrink-0 items-center justify-center rounded">
                  <ListMusicIcon
                    width={size}
                    height={size}
                    className="text-foreground-400"
                  />
                </div>
              )}
              <span className="font-mono text-sm">{subscription.name}</span>
            </div>
          );
        }
        case "lastSynced":
          return (
            <span className="text-foreground-500 font-mono text-sm">
              {formatTimeAgo(subscription.last_synced_at)}
            </span>
          );
        case "limit":
          return (
            <span className="text-foreground-500 font-mono text-sm">
              {subscription.max_items ?? "∞"}
            </span>
          );
        case "enabled":
          return (
            <Switch
              size="sm"
              isDisabled={!isSchedulerEnabled}
              isSelected={subscription.enabled}
              onValueChange={(enabled) =>
                onToggleEnabled(subscription.id, enabled)
              }
              aria-label="Toggle auto-sync"
            />
          );
        case "actions":
          return (
            <div className="flex items-center justify-center gap-1">
              <Button
                variant="light"
                size="sm"
                isIconOnly
                className="text-foreground-500 hover:text-primary"
                onPress={() => onSync(subscription.id)}
              >
                <RefreshCwIcon className="h-4 w-4" />
              </Button>
              <Button
                variant="light"
                size="sm"
                isIconOnly
                className="text-foreground-500 hover:text-danger"
                onPress={() => onDelete(subscription.id)}
              >
                <Trash2Icon className="h-4 w-4" />
              </Button>
            </div>
          );
      }
    },
    [onToggleEnabled, onSync, onDelete],
  );

  return (
    <Table>
      <TableHeader columns={columns}>
        {(column) => (
          <TableColumn
            key={column.key}
            align={
              column.key === "actions" || column.key == "enabled"
                ? "center"
                : "start"
            }
          >
            {column.name}
          </TableColumn>
        )}
      </TableHeader>
      <TableBody
        items={subscriptions}
        loadingState={isLoading ? "loading" : "idle"}
        loadingContent=<span className="text-foreground-400 text-small font-mono">
          Loading...
        </span>
        emptyContent={
          <EmptyState icon={InboxIcon} title="No playlists registered" />
        }
      >
        {(subscription) => (
          <TableRow key={subscription.id}>
            {(columnKey) => (
              <TableCell>
                {renderCell(
                  subscription,
                  !!isSchedulerEnabled,
                  columnKey as ColumnKey,
                )}
              </TableCell>
            )}
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

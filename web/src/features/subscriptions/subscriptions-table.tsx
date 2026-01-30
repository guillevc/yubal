import type { Subscription } from "@/api/subscriptions";
import { EmptyState } from "@/components/common/empty-state";
import { formatTimeAgo } from "@/lib/format";
import {
  Button,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow
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

interface SubscriptionsTableProps {
  subscriptions: Subscription[];
  onToggleEnabled: (id: string, enabled: boolean) => void;
  onSync: (id: string) => void;
  onDelete: (id: string) => void;
}

export function SubscriptionsTable({
  subscriptions,
  onToggleEnabled,
  onSync,
  onDelete,
}: SubscriptionsTableProps) {
  const renderCell = useCallback(
    (subscription: Subscription, columnKey: ColumnKey) => {
      switch (columnKey) {
        case "name":
          return (
            <div className="flex items-center gap-3">
              <div className="bg-content3 flex h-8 w-8 shrink-0 items-center justify-center rounded">
                <ListMusicIcon className="text-foreground-400 h-4 w-4" />
              </div>
              <span className="font-mono text-sm">{subscription.name}</span>
            </div>
          );
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
            align={column.key === "actions" ? "center" : "start"}
          >
            {column.name}
          </TableColumn>
        )}
      </TableHeader>
      <TableBody
        items={subscriptions}
        emptyContent={
          <EmptyState icon={InboxIcon} title="No playlists registered" />
        }
      >
        {(subscription) => (
          <TableRow key={subscription.id}>
            {(columnKey) => (
              <TableCell>
                {renderCell(subscription, columnKey as ColumnKey)}
              </TableCell>
            )}
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

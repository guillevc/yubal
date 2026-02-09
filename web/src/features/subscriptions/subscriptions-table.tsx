import type { Subscription } from "@/api/subscriptions";
import { EmptyState } from "@/components/common/empty-state";
import { useTimeAgo } from "@/hooks/use-time-ago";
import {
  Button,
  Image,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
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
  PencilIcon,
  RefreshCwIcon,
  Trash2Icon,
} from "lucide-react";
import { useCallback, useState } from "react";

type ColumnKey = "name" | "lastSynced" | "limit" | "enabled" | "actions";

function TimeAgo({ dateString }: { dateString: string | null | undefined }) {
  const timeAgo = useTimeAgo(dateString);
  return (
    <span className="text-foreground-500 font-mono text-sm">{timeAgo}</span>
  );
}

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
  onUpdateLimit: (id: string, maxItems: number | null) => Promise<void>;
  onSync: (id: string) => void;
  onDelete: (id: string) => void;
};

export function SubscriptionsTable({
  subscriptions,
  isLoading,
  isSchedulerEnabled,
  onToggleEnabled,
  onUpdateLimit,
  onSync,
  onDelete,
}: SubscriptionsTableProps) {
  const [editingLimitId, setEditingLimitId] = useState<string | null>(null);
  const [limitDraft, setLimitDraft] = useState("");
  const [isSavingLimit, setIsSavingLimit] = useState(false);

  const beginLimitEdit = useCallback((subscription: Subscription) => {
    setEditingLimitId(subscription.id);
    setLimitDraft(subscription.max_items?.toString() ?? "");
  }, []);

  const cancelLimitEdit = useCallback(() => {
    setEditingLimitId(null);
    setLimitDraft("");
  }, []);

  const saveLimitEdit = useCallback(async (subscriptionId: string) => {
    const trimmed = limitDraft.trim();
    const parsed = trimmed === "" ? null : Number.parseInt(trimmed, 10);
    const isValidParsed = parsed === null || (!Number.isNaN(parsed) && parsed >= 1);

    if (!isValidParsed) {
      return;
    }

    setIsSavingLimit(true);
    try {
      await onUpdateLimit(subscriptionId, parsed);
      cancelLimitEdit();
    } finally {
      setIsSavingLimit(false);
    }
  }, [cancelLimitEdit, limitDraft, onUpdateLimit]);

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
            <div className="flex items-center gap-4 max-md:gap-0">
              {subscription.thumbnail_url ? (
                <Image
                  alt="Playlist thumbnail"
                  src={subscription.thumbnail_url}
                  width={size}
                  height={size}
                  radius="md"
                  fallbackSrc=""
                  className="max-md:hidden"
                />
              ) : (
                <div className="bg-content3 flex h-8 w-8 shrink-0 items-center justify-center rounded">
                  <ListMusicIcon
                    width={size}
                    height={size}
                    className="text-foreground-400 max-md:hidden"
                  />
                </div>
              )}
              <span className="font-mono text-sm">{subscription.name}</span>
            </div>
          );
        }
        case "lastSynced":
          return <TimeAgo dateString={subscription.last_synced_at} />;
        case "limit":
          return (
            <Button
              variant="light"
              size="sm"
              onPress={() => beginLimitEdit(subscription)}
              aria-label={`Edit sync limit for ${subscription.name}`}
              className="group/limit h-auto min-h-0 gap-1 rounded-sm px-1 py-0.5 data-[hover=true]:bg-transparent"
            >
              <span className="text-foreground-500 font-mono text-sm">
                {subscription.max_items ?? "∞"}
              </span>
              <PencilIcon className="text-foreground-400 h-3.5 w-3.5 opacity-0 transition-opacity group-hover/limit:opacity-100 group-focus-visible/limit:opacity-100" />
            </Button>
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
                aria-label={`Sync ${subscription.name}`}
              >
                <RefreshCwIcon className="h-4 w-4" />
              </Button>
              <Button
                variant="light"
                size="sm"
                isIconOnly
                className="text-foreground-500 hover:text-danger"
                onPress={() => onDelete(subscription.id)}
                aria-label={`Delete ${subscription.name}`}
              >
                <Trash2Icon className="h-4 w-4" />
              </Button>
            </div>
          );
      }
    },
    [
      beginLimitEdit,
      cancelLimitEdit,
      editingLimitId,
      isSavingLimit,
      limitDraft,
      onToggleEnabled,
      onSync,
      onDelete,
      saveLimitEdit,
    ],
  );

  return (
    <>
      <Table aria-label="Subscriptions table" selectionMode="none">
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
      <Modal
        isOpen={editingLimitId !== null}
        onOpenChange={(open) => {
          if (!open) cancelLimitEdit();
        }}
      >
        <ModalContent>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (editingLimitId) {
                void saveLimitEdit(editingLimitId);
              }
            }}
          >
            <ModalHeader>Edit sync limit</ModalHeader>
            <ModalBody>
              <input
                type="number"
                min={1}
                max={10000}
                autoFocus
                value={limitDraft}
                onChange={(e) => setLimitDraft(e.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    event.preventDefault();
                    cancelLimitEdit();
                  }
                }}
                placeholder="Leave empty for unlimited"
                className="bg-default-100 border-default-200 focus:border-primary h-10 w-full rounded-md border px-3 font-mono text-sm outline-none"
                aria-label="Limit value"
              />
            </ModalBody>
            <ModalFooter>
              <Button
                variant="light"
                onPress={cancelLimitEdit}
                isDisabled={isSavingLimit}
              >
                Cancel
              </Button>
              <Button color="primary" type="submit" isLoading={isSavingLimit}>
                Save
              </Button>
            </ModalFooter>
          </form>
        </ModalContent>
      </Modal>
    </>
  );
}

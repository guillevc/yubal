import { UrlInput } from "@/components/common/url-input";
import { SubscriptionCard } from "@/features/subscriptions/subscription-card";
import { SubscriptionsTable } from "@/features/subscriptions/subscriptions-table";
import { useSubscriptions } from "@/features/subscriptions/use-subscriptions";
import { useCountdown } from "@/hooks/use-countdown";
import { isValidUrl } from "@/lib/url";
import {
  Alert,
  Button,
  Card,
  CardBody,
  NumberInput,
  Tooltip,
} from "@heroui/react";
import {
  CircleQuestionMarkIcon,
  ClockIcon,
  HashIcon,
  ListMusicIcon,
  RefreshCw,
  ZapIcon,
  ZapOffIcon,
} from "lucide-react";
import { useState } from "react";

const DEFAULT_MAX_ITEMS = 100;

export function SubscriptionsPage() {
  const [url, setUrl] = useState("");
  const [maxItems, setMaxItems] = useState(DEFAULT_MAX_ITEMS);
  const [isAdding, setIsAdding] = useState(false);
  const {
    subscriptions,
    schedulerStatus,
    isLoading,
    addSubscription,
    updateSubscription,
    deleteSubscription,
    syncSubscription,
    syncAll,
    refresh,
  } = useSubscriptions();
  const [isSyncing, setIsSyncing] = useState(false);

  const canAdd = isValidUrl(url);
  const isEmpty = subscriptions.length == 0;
  const canSyncAll = !isEmpty && !isSyncing && !isLoading;

  const handleAdd = async () => {
    if (!canAdd) return;
    setIsAdding(true);
    const success = await addSubscription(url.trim(), maxItems);
    if (success) {
      setUrl("");
    }
    setIsAdding(false);
  };

  const handleToggleEnabled = async (id: string, enabled: boolean) => {
    await updateSubscription(id, { enabled });
  };

  const handleSyncAll = async () => {
    setIsSyncing(true);
    await syncAll();
    setIsSyncing(false);
  };

  const nextSyncTime = schedulerStatus?.next_run_at
    ? new Date(schedulerStatus.next_run_at)
    : null;
  const countdown = useCountdown(nextSyncTime, refresh);
  const enabledCount = subscriptions.filter((s) => s.enabled).length;
  const totalCount = subscriptions.length;

  return (
    <>
      {/* Page Title */}
      <h1 className="text-foreground mb-6 text-2xl font-bold">My playlists</h1>

      {/* URL Input Section */}
      <section className="mb-8 flex gap-2">
        <div className="flex-1">
          <UrlInput
            value={url}
            onChange={setUrl}
            disabled={isAdding}
            placeholder="Playlist URL to sync automatically"
          />
        </div>
        <Tooltip content="Max tracks to sync per run" offset={14}>
          <NumberInput
            hideStepper
            value={maxItems}
            onValueChange={setMaxItems}
            minValue={1}
            maxValue={10000}
            radius="lg"
            fullWidth={false}
            formatOptions={{
              useGrouping: false,
            }}
            placeholder="Max"
            startContent={<HashIcon className="text-foreground-400 h-4 w-4" />}
            className="w-20 font-mono"
          />
        </Tooltip>
        <Button
          color="primary"
          radius="lg"
          variant={canAdd ? "shadow" : "solid"}
          className="shadow-primary-100/50"
          onPress={handleAdd}
          isDisabled={!canAdd}
          isLoading={isAdding}
          startContent={!isAdding && <ZapIcon className="h-4 w-4" />}
        >
          Subscribe
        </Button>
      </section>

      {/* Stats Cards */}
      <div className="mb-6 grid w-full grid-cols-1 gap-4 md:grid-cols-3">
        {/* Active playlists */}
        <SubscriptionCard isDisabled={!schedulerStatus?.enabled}>
          <SubscriptionCard.Header title="Active">
            <SubscriptionCard.Value suffix={`of ${totalCount}`}>
              <span className="font-mono">{enabledCount}</span>
            </SubscriptionCard.Value>
          </SubscriptionCard.Header>
          <SubscriptionCard.Icon className="text-success bg-success/10">
            <ListMusicIcon />
          </SubscriptionCard.Icon>
        </SubscriptionCard>
        {/* Next sync */}
        <SubscriptionCard isDisabled={!schedulerStatus?.enabled}>
          <SubscriptionCard.Header title="Next sync">
            <SubscriptionCard.Value suffix="remaining">
              <span className="font-mono">{countdown}</span>
            </SubscriptionCard.Value>
          </SubscriptionCard.Header>
          <SubscriptionCard.Icon>
            <ClockIcon />
          </SubscriptionCard.Icon>
        </SubscriptionCard>
        {/* Sync all button */}
        <Card
          isHoverable={canSyncAll}
          isPressable={canSyncAll}
          isDisabled={!canSyncAll}
          onPress={handleSyncAll}
          classNames={{
            base: "group",
            body: "flex flex-1 flex-col items-center justify-center gap-2",
          }}
        >
          <CardBody>
            <RefreshCw
              size={24}
              className={`mb-1 ${isSyncing ? "text-success-400 animate-spin" : "transition-transform duration-500 group-data-[hover=true]:rotate-180"}`}
            />
            <span className="text-small font-medium">
              {isSyncing ? "Synchronizing..." : "Sync all now"}
            </span>
          </CardBody>
        </Card>
      </div>
      {/* Scheduler disabled alert */}
      <div className="mb-6 flex w-full items-center justify-center">
        <Alert
          icon={<ZapOffIcon size={18} />}
          endContent={
            <a
              target="_blank"
              rel="noopener noreferrer"
              href="https://github.com/guillevc/yubal?tab=readme-ov-file#%EF%B8%8F-configuration"
            >
              <CircleQuestionMarkIcon size={20} className="mr-2" />
            </a>
          }
          color="warning"
          title="Scheduler is disabled."
          description="You can still add playlists and sync them manually."
        />
      </div>
      {/* Subscriptions Table */}
      <SubscriptionsTable
        subscriptions={subscriptions}
        isLoading={isLoading}
        isSchedulerEnabled={schedulerStatus?.enabled}
        onToggleEnabled={handleToggleEnabled}
        onSync={syncSubscription}
        onDelete={deleteSubscription}
      />
    </>
  );
}

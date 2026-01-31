import { UrlInput } from "@/components/common/url-input";
import { SubscriptionsTable } from "@/features/subscriptions/subscriptions-table";
import { useSubscriptions } from "@/features/subscriptions/use-subscriptions";
import { isValidUrl } from "@/lib/url";
import { Button, NumberInput, Spacer, Tooltip } from "@heroui/react";
import { HashIcon, RefreshCwIcon, RssIcon } from "lucide-react";
import { useState } from "react";

const DEFAULT_MAX_ITEMS = 100;

export function SubscriptionsPage() {
  const [url, setUrl] = useState("");
  const [maxItems, setMaxItems] = useState(DEFAULT_MAX_ITEMS);
  const [isAdding, setIsAdding] = useState(false);
  const {
    subscriptions,
    isLoading,
    addSubscription,
    updateSubscription,
    deleteSubscription,
    syncSubscription,
    syncAll,
  } = useSubscriptions();

  const canAdd = isValidUrl(url);
  const isEmpty = subscriptions.length == 0;

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

  return (
    <>
      {/* Page Title */}
      <h1 className="text-foreground mb-5 text-2xl font-bold">My playlists</h1>

      {/* URL Input Section */}
      <section className="mb-6 flex gap-2">
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
            variant="faded"
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
          startContent={!isAdding && <RssIcon className="h-4 w-4" />}
        >
          Subscribe
        </Button>
      </section>

      {/* Subscriptions Table */}
      <section>
        <div className="mb-2 flex items-center justify-between">
          {!isEmpty && (
            <span className="text-foreground-400 text-small font-mono">
              {subscriptions.filter((s) => s.enabled).length}/
              {subscriptions.length} enabled
            </span>
          )}
          <Spacer />
          <Button
            variant="light"
            size="sm"
            radius="lg"
            className="text-foreground-500 hover:text-primary text-small"
            onPress={syncAll}
            isDisabled={isEmpty}
            startContent={<RefreshCwIcon className="h-3.5 w-3.5" />}
          >
            Sync All
          </Button>
        </div>
        <SubscriptionsTable
          subscriptions={subscriptions}
          isLoading={isLoading}
          onToggleEnabled={handleToggleEnabled}
          onSync={syncSubscription}
          onDelete={deleteSubscription}
        />
      </section>
    </>
  );
}

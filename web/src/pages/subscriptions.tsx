import { UrlInput } from "@/components/common/url-input";
import { getCookiesStatus } from "@/api/cookies";
import { SubscriptionCard } from "@/features/subscriptions/subscription-card";
import { SubscriptionsTable } from "@/features/subscriptions/subscriptions-table";
import { useSubscriptions } from "@/features/subscriptions/use-subscriptions";
import { useScheduleCountdown } from "@/hooks/use-schedule-countdown";
import { showErrorToast } from "@/lib/toast";
import { isValidUrl } from "@/lib/url";
import {
  Alert,
  Button,
  Card,
  CardBody,
  Checkbox,
  Input,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  Spinner,
  Tooltip,
} from "@heroui/react";
import {
  AlertCircleIcon,
  CircleQuestionMarkIcon,
  ClockIcon,
  HashIcon,
  ImportIcon,
  ListMusicIcon,
  RefreshCw,
  ZapIcon,
  ZapOffIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const DEFAULT_MAX_ITEMS = 100;

export function SubscriptionsPage() {
  const [url, setUrl] = useState("");
  const [maxItems, setMaxItems] = useState(DEFAULT_MAX_ITEMS);
  const [isAdding, setIsAdding] = useState(false);
  const [cookiesConfigured, setCookiesConfigured] = useState(false);
  const [isCheckingCookies, setIsCheckingCookies] = useState(true);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [selectedLibraryPlaylistUrls, setSelectedLibraryPlaylistUrls] = useState<
    Set<string>
  >(new Set<string>());
  const {
    subscriptions,
    schedulerStatus,
    libraryPlaylists,
    isLibraryPlaylistsLoading,
    isLibraryPlaylistsAuthError,
    libraryPlaylistsError,
    isLoading,
    isImportingLibraryPlaylists,
    addSubscription,
    loadLibraryPlaylists,
    importLibraryPlaylists,
    updateSubscription,
    deleteSubscription,
    syncSubscription,
    syncAll,
  } = useSubscriptions();
  const [isSyncing, setIsSyncing] = useState(false);

  const canAdd = isValidUrl(url);
  const isEmpty = subscriptions.length == 0;
  const canSyncAll = !isEmpty && !isSyncing && !isLoading;
  const subscribedUrls = useMemo(
    () => new Set(subscriptions.map((subscription) => subscription.url)),
    [subscriptions],
  );
  const selectedImportCount = selectedLibraryPlaylistUrls.size;

  useEffect(() => {
    let isMounted = true;

    const refreshCookiesStatus = async () => {
      try {
        const configured = await getCookiesStatus();
        if (isMounted) {
          setCookiesConfigured(configured);
        }
      } finally {
        if (isMounted) {
          setIsCheckingCookies(false);
        }
      }
    };

    refreshCookiesStatus();
    window.addEventListener("focus", refreshCookiesStatus);

    return () => {
      isMounted = false;
      window.removeEventListener("focus", refreshCookiesStatus);
    };
  }, []);

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

  const handleOpenImportModal = async () => {
    const result = await loadLibraryPlaylists();
    if (!result.success) {
      if (result.authRequired) {
        showErrorToast(
          "Valid cookies required",
          "Upload valid YouTube cookies before importing playlists",
        );
      } else {
        showErrorToast("Import unavailable", result.error);
      }
      return;
    }

    setSelectedLibraryPlaylistUrls(new Set<string>());
    setIsImportModalOpen(true);
  };

  const handleSelectLibraryPlaylist = (url: string, selected: boolean) => {
    setSelectedLibraryPlaylistUrls((previous) => {
      const next = new Set(previous);
      if (selected) {
        next.add(url);
      } else {
        next.delete(url);
      }
      return next;
    });
  };

  const handleImportSelected = async () => {
    const importUrls = Array.from(selectedLibraryPlaylistUrls).filter(
      (playlistUrl) => !subscribedUrls.has(playlistUrl),
    );
    const result = await importLibraryPlaylists(importUrls, maxItems);
    if (result.added > 0 && result.failed === 0) {
      setIsImportModalOpen(false);
      setSelectedLibraryPlaylistUrls(new Set<string>());
    }
  };

  const handleSyncAll = async () => {
    setIsSyncing(true);
    await syncAll();
    setIsSyncing(false);
  };

  const countdown = useScheduleCountdown(
    schedulerStatus?.cron_expression,
    schedulerStatus?.timezone,
  );
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
          <Input
            type="number"
            value={String(maxItems)}
            onChange={(e) => {
              const value = parseInt(e.target.value, 10);
              if (!Number.isNaN(value) && value >= 1) setMaxItems(value);
            }}
            min={1}
            max={10000}
            radius="lg"
            placeholder="Max"
            startContent={<HashIcon className="text-foreground-400 h-4 w-4" />}
            classNames={{
              base: "w-24",
              input: "font-mono",
            }}
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
        <Button
          variant="flat"
          radius="lg"
          onPress={handleOpenImportModal}
          startContent={<ImportIcon className="h-4 w-4" />}
          isDisabled={
            isCheckingCookies || !cookiesConfigured || isLibraryPlaylistsLoading
          }
        >
          Import
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
      {schedulerStatus?.enabled === false && (
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
      )}
      {/* Subscriptions Table */}
      <SubscriptionsTable
        subscriptions={subscriptions}
        isLoading={isLoading}
        isSchedulerEnabled={schedulerStatus?.enabled}
        onToggleEnabled={handleToggleEnabled}
        onSync={syncSubscription}
        onDelete={deleteSubscription}
      />

      <Modal
        isOpen={isImportModalOpen}
        onOpenChange={setIsImportModalOpen}
        scrollBehavior="inside"
        size="2xl"
      >
        <ModalContent>
          <ModalHeader className="flex flex-col gap-1">
            Import account playlists
          </ModalHeader>
          <ModalBody>
            {isLibraryPlaylistsLoading && (
              <div className="flex min-h-48 items-center justify-center">
                <Spinner label="Loading account playlists..." color="primary" />
              </div>
            )}

            {!isLibraryPlaylistsLoading && isLibraryPlaylistsAuthError && (
              <Alert
                color="warning"
                title="Authentication required"
                description="Upload cookies to access your YouTube Music account playlists."
                icon={<AlertCircleIcon className="h-4 w-4" />}
              />
            )}

            {!isLibraryPlaylistsLoading &&
              !isLibraryPlaylistsAuthError &&
              libraryPlaylistsError && (
                <Alert
                  color="danger"
                  title="Could not load playlists"
                  description={libraryPlaylistsError}
                  icon={<AlertCircleIcon className="h-4 w-4" />}
                />
              )}

            {!isLibraryPlaylistsLoading &&
              !isLibraryPlaylistsAuthError &&
              !libraryPlaylistsError &&
              libraryPlaylists.length === 0 && (
                <p className="text-foreground-500 py-8 text-center text-sm">
                  No playlists found in your account library.
                </p>
              )}

            {!isLibraryPlaylistsLoading &&
              !isLibraryPlaylistsAuthError &&
              !libraryPlaylistsError &&
              libraryPlaylists.length > 0 && (
                <div className="flex flex-col gap-2">
                  {libraryPlaylists.map((playlist) => {
                    const isSubscribed = subscribedUrls.has(playlist.url);
                    const isSelected = selectedLibraryPlaylistUrls.has(playlist.url);

                    return (
                      <label
                        key={playlist.id}
                        className="hover:bg-default-100 border-default-200 flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors"
                      >
                        <Checkbox
                          isSelected={isSelected}
                          isDisabled={isSubscribed}
                          onValueChange={(checked) =>
                            handleSelectLibraryPlaylist(
                              playlist.url,
                              checked,
                            )
                          }
                          aria-label={`Select ${playlist.name}`}
                        />
                        {playlist.thumbnailUrl && (
                          <img
                            src={playlist.thumbnailUrl}
                            alt={playlist.name}
                            className="h-12 w-12 rounded-md object-cover"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium">{playlist.name}</p>
                          {typeof playlist.trackCount === "number" && (
                            <p className="text-foreground-500 text-xs">
                              {playlist.trackCount} track
                              {playlist.trackCount === 1 ? "" : "s"}
                            </p>
                          )}
                          <p className="text-foreground-500 truncate text-xs">
                            {playlist.url}
                          </p>
                        </div>
                        {isSubscribed && (
                          <span className="text-success text-xs font-medium">
                            Already subscribed
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
              )}
          </ModalBody>
          <ModalFooter>
            <Button variant="light" onPress={() => setIsImportModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="primary"
              onPress={handleImportSelected}
              isDisabled={selectedImportCount === 0 || isLibraryPlaylistsLoading}
              isLoading={isImportingLibraryPlaylists}
            >
              Import selected ({selectedImportCount})
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
}

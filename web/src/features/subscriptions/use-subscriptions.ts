import {
  addSubscription as addSubscriptionApi,
  deleteSubscription as deleteSubscriptionApi,
  getStatus,
  listLibraryPlaylists as listLibraryPlaylistsApi,
  listSubscriptions,
  syncAll as syncAllApi,
  syncSubscription as syncSubscriptionApi,
  updateSubscription as updateSubscriptionApi,
  type LibraryPlaylist,
  type LibraryPlaylistsResult,
  type SchedulerStatus,
  type Subscription,
} from "@/api/subscriptions";
import { showErrorToast, showSuccessToast } from "@/lib/toast";
import { useCallback, useEffect, useState } from "react";

export type {
  LibraryPlaylist,
  SchedulerStatus,
  Subscription,
} from "@/api/subscriptions";

export interface UseSubscriptionsResult {
  subscriptions: Subscription[];
  schedulerStatus: SchedulerStatus | null;
  libraryPlaylists: LibraryPlaylist[];
  isLibraryPlaylistsLoading: boolean;
  isLibraryPlaylistsAuthError: boolean;
  libraryPlaylistsError: string | null;
  isLoading: boolean;
  isImportingLibraryPlaylists: boolean;
  addSubscription: (url: string, maxItems?: number) => Promise<boolean>;
  loadLibraryPlaylists: () => Promise<LibraryPlaylistsResult>;
  importLibraryPlaylists: (
    urls: string[],
    maxItems?: number,
  ) => Promise<{ added: number; failed: number; skipped: number }>;
  updateSubscription: (
    id: string,
    updates: { enabled?: boolean; max_items?: number | null },
  ) => Promise<void>;
  deleteSubscription: (id: string) => Promise<void>;
  syncSubscription: (id: string) => Promise<void>;
  syncAll: () => Promise<void>;
}

export function useSubscriptions(): UseSubscriptionsResult {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [schedulerStatus, setSchedulerStatus] =
    useState<SchedulerStatus | null>(null);
  const [libraryPlaylists, setLibraryPlaylists] = useState<LibraryPlaylist[]>([]);
  const [isLibraryPlaylistsLoading, setIsLibraryPlaylistsLoading] =
    useState(false);
  const [isLibraryPlaylistsAuthError, setIsLibraryPlaylistsAuthError] =
    useState(false);
  const [libraryPlaylistsError, setLibraryPlaylistsError] = useState<string | null>(
    null,
  );
  const [isImportingLibraryPlaylists, setIsImportingLibraryPlaylists] =
    useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const fetchSubscriptions = useCallback(async () => {
    const data = await listSubscriptions();
    setSubscriptions(data);
  }, []);

  const addSubscription = useCallback(
    async (url: string, maxItems?: number): Promise<boolean> => {
      const result = await addSubscriptionApi(url, maxItems);
      if (!result.success) {
        showErrorToast("Failed to add subscription", result.error);
        return false;
      }
      await fetchSubscriptions();
      return true;
    },
    [fetchSubscriptions],
  );

  const loadLibraryPlaylists = useCallback(async () => {
    setIsLibraryPlaylistsLoading(true);
    setIsLibraryPlaylistsAuthError(false);
    setLibraryPlaylistsError(null);

    try {
      const result = await listLibraryPlaylistsApi();
      if (!result.success) {
        setLibraryPlaylists([]);
        setIsLibraryPlaylistsAuthError(result.authRequired);
        setLibraryPlaylistsError(result.error);
        return result;
      }

      setLibraryPlaylists(result.playlists);
      return result;
    } catch {
      setLibraryPlaylists([]);
      setLibraryPlaylistsError("Failed to load account playlists");
      return {
        success: false,
        error: "Failed to load account playlists",
        authRequired: false,
      } as const;
    } finally {
      setIsLibraryPlaylistsLoading(false);
    }
  }, []);

  const importLibraryPlaylists = useCallback(
    async (
      urls: string[],
      maxItems?: number,
    ): Promise<{ added: number; failed: number; skipped: number }> => {
      if (urls.length === 0) {
        return { added: 0, failed: 0, skipped: 0 };
      }

      setIsImportingLibraryPlaylists(true);
      try {
        let added = 0;
        let failed = 0;
        let skipped = 0;

        for (const url of urls) {
          const result = await addSubscriptionApi(url, maxItems);
          if (result.success) {
            added += 1;
            continue;
          }

          if (result.error === "Subscription already exists") {
            skipped += 1;
            continue;
          }

          failed += 1;
        }

        if (added > 0) {
          await fetchSubscriptions();
          showSuccessToast(
            "Playlists imported",
            `${added} playlist${added === 1 ? "" : "s"} added to sync list`,
          );
        }

        if (failed > 0) {
          showErrorToast(
            "Import incomplete",
            `${failed} playlist${failed === 1 ? "" : "s"} could not be imported`,
          );
        }

        if (added === 0 && skipped > 0 && failed === 0) {
          showErrorToast(
            "Nothing to import",
            "Selected playlists are already synced",
          );
        }

        return { added, failed, skipped };
      } finally {
        setIsImportingLibraryPlaylists(false);
      }
    },
    [fetchSubscriptions],
  );

  const updateSubscription = useCallback(
    async (id: string, updates: { enabled?: boolean; max_items?: number | null }) => {
      const result = await updateSubscriptionApi(id, updates);
      if (result === null) {
        showErrorToast("Update failed", "Could not update subscription");
        return;
      }
      await fetchSubscriptions();
    },
    [fetchSubscriptions],
  );

  const deleteSubscription = useCallback(
    async (id: string) => {
      const success = await deleteSubscriptionApi(id);
      if (!success) {
        showErrorToast("Delete failed", "Could not delete subscription");
        return;
      }
      await fetchSubscriptions();
    },
    [fetchSubscriptions],
  );

  const syncSubscription = useCallback(
    async (id: string) => {
      const result = await syncSubscriptionApi(id);
      if (!result.success) {
        showErrorToast("Sync failed", result.error);
        return;
      }
      await fetchSubscriptions();
      showSuccessToast("Sync queued", "Subscription will sync shortly");
    },
    [fetchSubscriptions],
  );

  const syncAll = useCallback(async () => {
    const result = await syncAllApi();
    if (!result.success) {
      showErrorToast("Sync failed", result.error);
      return;
    }
    await fetchSubscriptions();
    showSuccessToast("Sync queued", "All subscriptions will sync shortly");
  }, [fetchSubscriptions]);

  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        const [subscriptionsData, statusData] = await Promise.all([
          listSubscriptions(),
          getStatus(),
        ]);
        if (mounted) {
          setSubscriptions(subscriptionsData);
          setSchedulerStatus(statusData);
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, []);

  return {
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
  };
}

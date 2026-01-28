import { useCallback, useEffect, useState } from "react";
import {
  addSubscription as addSubscriptionApi,
  deleteSubscription as deleteSubscriptionApi,
  getStatus,
  listSubscriptions,
  syncAll as syncAllApi,
  syncSubscription as syncSubscriptionApi,
  updateSubscription as updateSubscriptionApi,
  type SchedulerStatus,
  type Subscription,
} from "../api/subscriptions";
import { showErrorToast } from "../lib/toast";

export type { SchedulerStatus, Subscription } from "../api/subscriptions";

export interface UseSubscriptionsResult {
  subscriptions: Subscription[];
  schedulerStatus: SchedulerStatus | null;
  isLoading: boolean;
  addSubscription: (url: string, name: string) => Promise<boolean>;
  updateSubscription: (
    id: string,
    updates: { name?: string; enabled?: boolean },
  ) => Promise<void>;
  deleteSubscription: (id: string) => Promise<void>;
  syncSubscription: (id: string) => Promise<void>;
  syncAll: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useSubscriptions(): UseSubscriptionsResult {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [schedulerStatus, setSchedulerStatus] =
    useState<SchedulerStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const [subscriptionsData, statusData] = await Promise.all([
      listSubscriptions(),
      getStatus(),
    ]);
    setSubscriptions(subscriptionsData);
    setSchedulerStatus(statusData);
  }, []);

  const refresh = useCallback(async () => {
    await fetchData();
  }, [fetchData]);

  const addSubscription = useCallback(
    async (url: string, name: string): Promise<boolean> => {
      const result = await addSubscriptionApi(url, name);
      if (!result.success) {
        showErrorToast("Failed to add subscription", result.error);
        return false;
      }
      await fetchData();
      return true;
    },
    [fetchData],
  );

  const updateSubscription = useCallback(
    async (id: string, updates: { name?: string; enabled?: boolean }) => {
      const result = await updateSubscriptionApi(id, updates);
      if (result === null) {
        showErrorToast("Update failed", "Could not update subscription");
        return;
      }
      await fetchData();
    },
    [fetchData],
  );

  const deleteSubscription = useCallback(
    async (id: string) => {
      const success = await deleteSubscriptionApi(id);
      if (!success) {
        showErrorToast("Delete failed", "Could not delete subscription");
        return;
      }
      await fetchData();
    },
    [fetchData],
  );

  const syncSubscription = useCallback(
    async (id: string) => {
      const result = await syncSubscriptionApi(id);
      if (!result.success) {
        showErrorToast("Sync failed", result.error);
        return;
      }
      await fetchData();
    },
    [fetchData],
  );

  const syncAll = useCallback(async () => {
    const result = await syncAllApi();
    if (!result.success) {
      showErrorToast("Sync failed", result.error);
      return;
    }
    await fetchData();
  }, [fetchData]);

  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        await fetchData();
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, [fetchData]);

  return {
    subscriptions,
    schedulerStatus,
    isLoading,
    addSubscription,
    updateSubscription,
    deleteSubscription,
    syncSubscription,
    syncAll,
    refresh,
  };
}

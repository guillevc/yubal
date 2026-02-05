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
} from "@/api/subscriptions";
import { showErrorToast, showSuccessToast } from "@/lib/toast";
import { useCallback, useEffect, useState } from "react";

export type { SchedulerStatus, Subscription } from "@/api/subscriptions";

export interface UseSubscriptionsResult {
  subscriptions: Subscription[];
  schedulerStatus: SchedulerStatus | null;
  isLoading: boolean;
  addSubscription: (url: string, maxItems?: number) => Promise<boolean>;
  updateSubscription: (
    id: string,
    updates: { enabled?: boolean },
  ) => Promise<void>;
  deleteSubscription: (id: string) => Promise<void>;
  syncSubscription: (id: string) => Promise<void>;
  syncAll: () => Promise<void>;
}

export function useSubscriptions(): UseSubscriptionsResult {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [schedulerStatus, setSchedulerStatus] =
    useState<SchedulerStatus | null>(null);
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

  const updateSubscription = useCallback(
    async (id: string, updates: { enabled?: boolean }) => {
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
    isLoading,
    addSubscription,
    updateSubscription,
    deleteSubscription,
    syncSubscription,
    syncAll,
  };
}

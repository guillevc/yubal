import { api } from "./client";
import type { components } from "./schema";

export type Subscription = components["schemas"]["SubscriptionResponse"];
export type SchedulerStatus = components["schemas"]["SchedulerStatus"];

export type AddSubscriptionResult =
  | { success: true; id: string }
  | { success: false; error: string };

export type SyncResult =
  | { success: true; jobIds: string[] }
  | { success: false; error: string };

// --- Subscriptions ---

export async function listSubscriptions(): Promise<Subscription[]> {
  const { data, error } = await api.GET("/subscriptions");
  if (error) return [];
  return data.items;
}

export async function addSubscription(
  url: string,
  name: string,
): Promise<AddSubscriptionResult> {
  const { data, error, response } = await api.POST("/subscriptions", {
    body: { url, name, type: "playlist", enabled: true },
  });

  if (error) {
    if (response.status === 409) {
      return { success: false, error: "Subscription already exists" };
    }
    if (response.status === 422) {
      const validation = error as unknown as {
        detail?: { msg: string }[];
      };
      return {
        success: false,
        error: validation.detail?.[0]?.msg ?? "Invalid input",
      };
    }
    return { success: false, error: "Failed to add subscription" };
  }

  return { success: true, id: data.id };
}

export async function getSubscription(
  id: string,
): Promise<Subscription | null> {
  const { data, error } = await api.GET("/subscriptions/{subscription_id}", {
    params: { path: { subscription_id: id } },
  });
  if (error) return null;
  return data;
}

export async function updateSubscription(
  id: string,
  updates: { name?: string; enabled?: boolean },
): Promise<Subscription | null> {
  const { data, error } = await api.PATCH("/subscriptions/{subscription_id}", {
    params: { path: { subscription_id: id } },
    body: updates,
  });
  if (error) return null;
  return data;
}

export async function deleteSubscription(id: string): Promise<boolean> {
  const { error } = await api.DELETE("/subscriptions/{subscription_id}", {
    params: { path: { subscription_id: id } },
  });
  return !error;
}

// --- Sync Jobs ---

export async function syncSubscription(id: string): Promise<SyncResult> {
  const { data, error, response } = await api.POST(
    "/subscriptions/{subscription_id}/sync",
    {
      params: { path: { subscription_id: id } },
    },
  );

  if (error) {
    if (response.status === 404) {
      return { success: false, error: "Subscription not found" };
    }
    if (response.status === 409) {
      return { success: false, error: "Job queue is full" };
    }
    return { success: false, error: "Failed to create sync job" };
  }

  return { success: true, jobIds: data.job_ids };
}

export async function syncAll(): Promise<SyncResult> {
  const { data, error } = await api.POST("/subscriptions/sync");

  if (error) {
    return { success: false, error: "Failed to create sync jobs" };
  }

  return { success: true, jobIds: data.job_ids };
}

// --- Status ---

export async function getStatus(): Promise<SchedulerStatus | null> {
  const { data, error } = await api.GET("/scheduler");
  if (error) return null;
  return data;
}

import { api } from "./client";
import type { components } from "./schema";

export type Subscription = components["schemas"]["SubscriptionResponse"];
export type SchedulerStatus = components["schemas"]["SchedulerStatus"];
export interface LibraryPlaylist {
  id: string;
  name: string;
  url: string;
  thumbnailUrl?: string | null;
  trackCount?: number | null;
}

export type LibraryPlaylistsResult =
  | { success: true; playlists: LibraryPlaylist[] }
  | { success: false; error: string; authRequired: boolean };

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

export async function listLibraryPlaylists(): Promise<LibraryPlaylistsResult> {
  const { data, error, response } = await (
    api as unknown as {
      GET: (
        path: "/subscriptions/library-playlists",
      ) => Promise<{ data?: unknown; error?: unknown; response: Response }>;
    }
  ).GET("/subscriptions/library-playlists");

  if (error) {
    const authRequired = response.status === 401 || response.status === 403;
    return {
      success: false,
      authRequired,
      error: authRequired
        ? "Authentication required to list account playlists"
        : "Failed to load account playlists",
    };
  }

  const items = Array.isArray(data)
    ? data
    : typeof data === "object" && data !== null && "items" in data
      ? (data.items as unknown[])
      : [];

  const playlists = items
    .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
    .map((item) => {
      const id = String(item.id ?? item.playlist_id ?? item.url ?? "");
      const name = String(item.name ?? item.title ?? "Untitled playlist");
      const url = String(item.url ?? "");
      const thumbnailUrl =
        typeof item.thumbnail_url === "string" ? item.thumbnail_url : null;
      const rawTrackCount =
        typeof item.track_count === "number"
          ? item.track_count
          : typeof item.count === "number"
            ? item.count
            : null;
      return { id, name, url, thumbnailUrl, trackCount: rawTrackCount };
    })
    .filter((item) => item.id.length > 0 && item.url.length > 0);

  return { success: true, playlists };
}

export async function addSubscription(
  url: string,
  maxItems?: number,
): Promise<AddSubscriptionResult> {
  const { data, error, response } = await api.POST("/subscriptions", {
    body: { url, max_items: maxItems },
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

export async function updateSubscription(
  id: string,
  updates: { enabled?: boolean; max_items?: number | null },
): Promise<Subscription | null> {
  const { data, error } = await api.PATCH("/subscriptions/{subscription_id}", {
    params: { path: { subscription_id: id } },
    body: updates as never,
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

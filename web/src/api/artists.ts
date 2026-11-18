import { api } from "./client";
import type { components } from "./schema";

export type ArtistSummary = components["schemas"]["ArtistSummary"];
export type ArtistRelease = components["schemas"]["ArtistRelease"];
export type ArtistReleases = components["schemas"]["ArtistReleasesResponse"];

type ApiError = { error?: string; message?: string };

function errorMessage(error: unknown, fallback: string): string {
  const e = error as ApiError | undefined;
  return e?.message ?? fallback;
}

export async function searchArtists(query: string): Promise<ArtistSummary[]> {
  const { data, error, response } = await api.GET("/artists/search", {
    params: { query: { q: query } },
  });

  if (error) {
    if (response.status === 404) return [];
    throw new Error(errorMessage(error, "Artist search failed"));
  }

  return data.artists;
}

export async function getArtistReleases(
  channelId: string,
): Promise<ArtistReleases> {
  const { data, error } = await api.GET("/artists/{channel_id}/releases", {
    params: { path: { channel_id: channelId } },
  });

  if (error) throw new Error(errorMessage(error, "Failed to load releases"));

  return data;
}

type QueueReleasesResult =
  | { success: true; queued: number; skipped: number }
  | { success: false; error: string };

export async function queueArtistReleases(
  urls: string[],
): Promise<QueueReleasesResult> {
  const { data, error } = await api.POST("/artists/jobs", {
    body: { urls },
  });

  if (error) {
    return {
      success: false,
      error: errorMessage(error, "Failed to queue downloads"),
    };
  }

  return { success: true, queued: data.job_ids.length, skipped: data.skipped };
}

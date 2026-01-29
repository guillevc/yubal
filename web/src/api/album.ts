export interface AlbumArtist {
  name: string;
  id?: string;
}

export interface AlbumThumbnail {
  url: string;
  width?: number;
  height?: number;
}

export interface AlbumTrack {
  videoId?: string;
  title: string;
  artists?: AlbumArtist[];
  trackNumber?: number;
  duration_seconds?: number;
  duration?: string;
}

export interface AlbumResponse {
  title: string;
  type?: string;
  thumbnails?: AlbumThumbnail[];
  description?: string;
  artists?: AlbumArtist[];
  year?: string;
  trackCount?: number;
  duration?: string;
  audioPlaylistId?: string;
  tracks?: AlbumTrack[];
  duration_seconds?: number;
}

export async function fetchAlbum(browseId: string): Promise<AlbumResponse> {
  const response = await fetch(`/api/albums/${browseId}`);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to fetch album");
  }

  return response.json() as Promise<AlbumResponse>;
}

export function getAlbumThumbnail(album: AlbumResponse | null): string | null {
  const thumbnails = album?.thumbnails;
  if (!thumbnails || thumbnails.length === 0) return null;

  const sorted = [...thumbnails].sort((a, b) => {
    const aSize = (a.width ?? 0) * (a.height ?? 0);
    const bSize = (b.width ?? 0) * (b.height ?? 0);
    return bSize - aSize;
  });

  return sorted[0]?.url ?? null;
}

export function getTrackMeta(track: AlbumTrack): string | null {
  const duration = track.duration ?? null;
  return duration ?? null;
}

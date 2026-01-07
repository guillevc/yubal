export const YOUTUBE_MUSIC_URL_PATTERN =
  /^https?:\/\/(music\.)?youtube\.com\/(playlist\?list=|watch\?v=|browse\/VL)/;

export enum UrlType {
  ALBUM = "album",
  PLAYLIST = "playlist",
}

export function isValidUrl(url: string): boolean {
  return YOUTUBE_MUSIC_URL_PATTERN.test(url);
}

/**
 * Detect URL type based on playlist ID prefix.
 * Albums have playlist IDs starting with OLAK5uy_
 *
 * @returns UrlType or null if URL doesn't contain a playlist ID
 */
export function getUrlType(url: string): UrlType | null {
  const match = url.match(/list=([^&]+)/);
  const playlistId = match?.[1];
  if (!playlistId) return null;

  return playlistId.startsWith("OLAK5uy_") ? UrlType.ALBUM : UrlType.PLAYLIST;
}

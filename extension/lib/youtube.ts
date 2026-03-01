const SUPPORTED_HOSTS = new Set([
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "youtube-nocookie.com",
  "www.youtube-nocookie.com",
]);

export function isYouTubeUrl(url: string): boolean {
  try {
    return SUPPORTED_HOSTS.has(new URL(url).hostname);
  } catch {
    return false;
  }
}

export function getContentType(url: string): "track" | "playlist" | null {
  try {
    const u = new URL(url);
    const params = u.searchParams;
    if (params.has("list") || u.pathname.startsWith("/browse/")) {
      return "playlist";
    }
    if (params.has("v")) {
      return "track";
    }
    return null;
  } catch {
    return null;
  }
}

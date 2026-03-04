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

/** Returns true if the URL points to a YouTube page with extractable media. */
export function isYouTubeMediaUrl(url: string): boolean {
  try {
    const u = new URL(url);
    if (!SUPPORTED_HOSTS.has(u.hostname)) return false;
    return (
      u.pathname.startsWith("/watch") || u.pathname.startsWith("/playlist")
    );
  } catch {
    return false;
  }
}

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

export type TrackInfo = {
  title: string | null;
  artist: string | null;
};

/** Extract the track title and artist from the active tab's DOM. */
export async function extractTrackInfo(tabId: number): Promise<TrackInfo> {
  try {
    const [result] = await browser.scripting.executeScript({
      target: { tabId },
      func: (): TrackInfo => {
        let title: string | null = null;
        let artist: string | null = null;

        // YouTube Music
        const ytmTitle = document.querySelector<HTMLElement>(
          "ytmusic-player-bar .title",
        );
        if (ytmTitle?.textContent) {
          title = ytmTitle.textContent.trim();
          // Byline contains "Artist1, Artist2 • 3m views • 62k likes"
          const byline = document.querySelector<HTMLElement>(
            "ytmusic-player-bar .byline",
          );
          if (byline?.textContent) {
            artist = byline.textContent.split("•")[0].trim() || null;
          }
          return { title, artist };
        }

        // Regular YouTube
        const ytTitle = document.querySelector<HTMLElement>(
          "ytd-watch-metadata h1, #above-the-fold #title h1",
        );
        if (ytTitle?.textContent) {
          title = ytTitle.textContent.trim();
          const channel = document.querySelector<HTMLElement>(
            "ytd-watch-metadata ytd-channel-name a, #owner #channel-name a",
          );
          if (channel?.textContent) {
            artist = channel.textContent.trim() || null;
          }
        }

        return { title, artist };
      },
    });
    return (result?.result as TrackInfo) ?? { title: null, artist: null };
  } catch {
    return { title: null, artist: null };
  }
}

export type PlaylistInfo = {
  title: string | null;
};

/** Extract the playlist title from the active tab's DOM. */
export async function extractPlaylistInfo(
  tabId: number,
): Promise<PlaylistInfo> {
  try {
    const [result] = await browser.scripting.executeScript({
      target: { tabId },
      func: (): PlaylistInfo => {
        // Playlist page header
        const header = document.querySelector<HTMLElement>(
          [
            "ytmusic-immersive-header-renderer .title",
            "ytmusic-detail-header-renderer .title",
            "ytmusic-responsive-header-renderer .title",
          ].join(", "),
        );
        if (header?.textContent) {
          return { title: header.textContent.trim() };
        }
        // Watch page queue panel — subtitle shows the playlist name
        const queueSubtitle = document.querySelector<HTMLElement>(
          "ytmusic-queue-header-renderer .subtitle",
        );
        if (queueSubtitle?.textContent) {
          return { title: queueSubtitle.textContent.trim() };
        }
        return { title: null };
      },
    });
    return (result?.result as PlaylistInfo) ?? { title: null };
  } catch {
    return { title: null };
  }
}

export type ContentType = "track" | "playlist";

export function getContentType(url: string): ContentType | null {
  try {
    const u = new URL(url);
    const params = u.searchParams;
    if (u.pathname === "/playlist" && params.has("list")) {
      return "playlist";
    }
    if (u.pathname === "/watch" && params.has("v")) {
      return params.has("list") ? "playlist" : "track";
    }
    return null;
  } catch {
    return null;
  }
}

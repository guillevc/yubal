import { isYouTubeUrl } from "@/lib/youtube";

const ICON_SIZES = [16, 32, 48, 128] as const;
const COLORED_PATHS = Object.fromEntries(
  ICON_SIZES.map((s) => [String(s), `icons/${s}.png`]),
);

let inactiveCache: Record<string, ImageData> | null = null;

async function getInactiveIcons(): Promise<Record<string, ImageData>> {
  if (inactiveCache) return inactiveCache;

  const entries = await Promise.all(
    ICON_SIZES.map(async (size) => {
      const resp = await fetch(browser.runtime.getURL(`/icons/${size}.png`));
      const blob = await resp.blob();
      const bmp = await createImageBitmap(blob);
      const canvas = new OffscreenCanvas(size, size);
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(bmp, 0, 0);
      const img = ctx.getImageData(0, 0, size, size);
      const d = img.data;
      for (let i = 0; i < d.length; i += 4) {
        const gray = Math.round(
          0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2],
        );
        d[i] = gray;
        d[i + 1] = gray;
        d[i + 2] = gray;
        d[i + 3] = Math.round(d[i + 3] * 0.6);
      }
      return [String(size), img] as const;
    }),
  );

  inactiveCache = Object.fromEntries(entries);
  return inactiveCache;
}

async function updateIcon(tabId: number): Promise<void> {
  try {
    const tab = await browser.tabs.get(tabId);
    const active = tab.url ? isYouTubeUrl(tab.url) : false;

    if (active) {
      await browser.action.setIcon({ tabId, path: COLORED_PATHS });
    } else {
      const icons = await getInactiveIcons();
      await browser.action.setIcon({
        tabId,
        imageData: icons as unknown as Record<string, ImageData>,
      });
    }
  } catch {
    // Tab may have been closed
  }
}

export default defineBackground(() => {
  browser.runtime.onInstalled.addListener(({ reason }) => {
    console.log("Yubal extension installed:", reason);
  });

  browser.tabs.onActivated.addListener(({ tabId }) => {
    updateIcon(tabId);
  });

  browser.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url || changeInfo.status === "complete") {
      updateIcon(tabId);
    }
  });
});

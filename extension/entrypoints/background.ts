import { isYouTubeMediaUrl } from "@/lib/youtube";

const SIZES = [16, 32, 48, 128] as const;

// MV3 (Chrome) uses `action`, MV2 (Firefox) uses `browserAction`
const actionApi = browser.action ?? browser.browserAction;

const activeTabs = new Set<number>();

async function buildGrayscaleIcons(): Promise<Record<string, ImageData>> {
  const entries = await Promise.all(
    SIZES.map(async (size) => {
      const url = browser.runtime.getURL(`/icons/${size}.png`);
      const resp = await fetch(url);
      const bitmap = await createImageBitmap(await resp.blob());
      const canvas = new OffscreenCanvas(size, size);
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(bitmap, 0, 0, size, size);
      const imageData = ctx.getImageData(0, 0, size, size);

      const { data } = imageData;
      for (let i = 0; i < data.length; i += 4) {
        const gray = Math.round(
          0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2],
        );
        data[i] = gray;
        data[i + 1] = gray;
        data[i + 2] = gray;
      }

      return [String(size), imageData] as const;
    }),
  );

  return Object.fromEntries(entries);
}

function activeIconPaths(): Record<string, string> {
  return Object.fromEntries(SIZES.map((s) => [String(s), `icons/${s}.png`]));
}

async function updateIcon(tabId: number): Promise<void> {
  try {
    const tab = await browser.tabs.get(tabId);
    const isActive = tab.url ? isYouTubeMediaUrl(tab.url) : false;

    if (isActive) {
      activeTabs.add(tabId);
      await actionApi.setIcon({ tabId, path: activeIconPaths() });
    } else {
      activeTabs.delete(tabId);
      // Clear per-tab override so global grayscale default takes effect
      await actionApi.setIcon({ tabId, path: {} });
    }
  } catch (err) {
    console.error("updateIcon failed:", err);
  }
}

export default defineBackground(() => {
  // Set grayscale as the global default icon so new/navigating tabs
  // never flash the colored icon before our handler runs
  buildGrayscaleIcons().then((imageData) => {
    actionApi.setIcon({ imageData });
  });

  browser.runtime.onInstalled.addListener(({ reason }) => {
    console.log("yubal extension installed:", reason);
  });

  browser.tabs.onRemoved.addListener((tabId) => {
    activeTabs.delete(tabId);
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

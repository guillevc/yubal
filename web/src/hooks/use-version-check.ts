import { useEffect, useState } from "react";

const CACHE_KEY = "yubal-version-check";
const CACHE_DURATION_MS = 6 * 60 * 60 * 1000; // 6 hours

interface VersionInfo {
  latestVersion: string;
  updateAvailable: boolean;
  releaseUrl: string;
}

interface CachedData {
  latestVersion: string;
  releaseUrl: string;
  checkedVersion: string;
  timestamp: number;
}

interface GitHubRelease {
  tag_name: string;
  html_url: string;
}

function compareVersions(current: string, latest: string): boolean {
  const normalize = (v: string) => v.replace(/^v/, "");
  const currentParts = normalize(current).split(".").map(Number);
  const latestParts = normalize(latest).split(".").map(Number);

  for (let i = 0; i < Math.max(currentParts.length, latestParts.length); i++) {
    const currentPart = currentParts[i] || 0;
    const latestPart = latestParts[i] || 0;
    if (latestPart > currentPart) return true;
    if (currentPart > latestPart) return false;
  }
  return false;
}

function getCachedVersionInfo(): VersionInfo | null {
  if (!__IS_RELEASE__) {
    return null;
  }

  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      const parsed: CachedData = JSON.parse(cached);
      const isFresh = Date.now() - parsed.timestamp < CACHE_DURATION_MS;
      const sameVersion = parsed.checkedVersion === __VERSION__;

      if (isFresh && sameVersion) {
        return {
          latestVersion: parsed.latestVersion,
          releaseUrl: parsed.releaseUrl,
          updateAvailable: compareVersions(__VERSION__, parsed.latestVersion),
        };
      }
    }
  } catch {
    // Ignore cache errors
  }

  return null;
}

export function useVersionCheck(): { data: VersionInfo | null } {
  const [data, setData] = useState<VersionInfo | null>(getCachedVersionInfo);

  useEffect(() => {
    if (!__IS_RELEASE__ || data !== null) {
      return;
    }

    const controller = new AbortController();

    fetch("https://api.github.com/repos/guillevc/yubal/releases/latest", {
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch");
        return res.json() as Promise<GitHubRelease>;
      })
      .then((release) => {
        const latestVersion = release.tag_name;
        const releaseUrl = release.html_url;

        const cacheData: CachedData = {
          latestVersion,
          releaseUrl,
          checkedVersion: __VERSION__,
          timestamp: Date.now(),
        };

        try {
          localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
        } catch {
          // Storage full or unavailable
        }

        setData({
          latestVersion,
          releaseUrl,
          updateAvailable: compareVersions(__VERSION__, latestVersion),
        });
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          // Fail silently for network errors
        }
      });

    return () => controller.abort();
  }, [data]);

  return { data };
}

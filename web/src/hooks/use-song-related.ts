import { useEffect, useState } from "react";
import { fetchSongRelated, type RelatedSection } from "../api/song-related";
import { showErrorToast } from "../lib/toast";

const relatedCache = new Map<string, RelatedSection[]>();

export function useSongRelated(videoId: string | null) {
  const [sections, setSections] = useState<RelatedSection[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!videoId) {
      setSections([]);
      setIsLoading(false);
      return;
    }

    const cached = relatedCache.get(videoId);
    if (cached) {
      setSections(cached);
      setIsLoading(false);
      return;
    }

    let active = true;
    setIsLoading(true);

    fetchSongRelated(videoId)
      .then((data) => {
        if (active) {
          relatedCache.set(videoId, data);
          setSections(data);
        }
      })
      .catch((error) => {
        const message =
          error instanceof Error ? error.message : "Unable to load related";
        showErrorToast("Related content failed", message);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [videoId]);

  return { sections, isLoading };
}

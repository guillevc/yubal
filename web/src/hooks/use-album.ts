import { useEffect, useState } from "react";
import { fetchAlbum, type AlbumResponse } from "../api/album";
import { showErrorToast } from "../lib/toast";

export function useAlbum(browseId: string | null) {
  const [album, setAlbum] = useState<AlbumResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!browseId) {
      setAlbum(null);
      setIsLoading(false);
      return;
    }

    let isActive = true;
    setIsLoading(true);

    fetchAlbum(browseId)
      .then((data) => {
        if (isActive) setAlbum(data);
      })
      .catch((error) => {
        const message =
          error instanceof Error ? error.message : "Unable to load album";
        showErrorToast("Album load failed", message);
      })
      .finally(() => {
        if (isActive) setIsLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [browseId]);

  return { album, isLoading };
}

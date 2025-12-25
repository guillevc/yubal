import { useState, useEffect, useRef } from "react";
import { Button } from "@heroui/react";
import { Download, X, Music2 } from "lucide-react";
import { AnimatePresence } from "framer-motion";
import { UrlInput } from "./components/UrlInput";
import { isValidUrl } from "./utils/url";
import { ConsoleOutput } from "./components/ConsoleOutput";
import { AlbumInfoCard, type TrackInfo } from "./components/AlbumInfoCard";
import {
  DownloadHistory,
  type DownloadedAlbum,
} from "./components/DownloadHistory";
import { useSync } from "./hooks/useSync";

export default function App() {
  const [url, setUrl] = useState("");
  const { status, progress, logs, result, startSync, cancelSync, clearLogs } =
    useSync();
  const [downloadHistory, setDownloadHistory] = useState<DownloadedAlbum[]>([]);
  const lastCompletedRef = useRef<string | null>(null);

  const isSyncing =
    status !== "idle" && status !== "complete" && status !== "error";
  const canSync = isValidUrl(url) && !isSyncing;
  const showAlbumCard = isSyncing || status === "complete";

  // TODO: Wire to backend when album metadata is available in SSE events
  // For now, extract from result when complete, otherwise show skeleton
  const trackInfo: TrackInfo | null =
    result?.album && status === "complete"
      ? {
          title: result.album.title,
          artist: result.album.artist,
          album: result.album.title,
        }
      : null;

  const handleSync = () => {
    if (canSync) {
      startSync(url);
    }
  };

  const handleClear = () => {
    clearLogs();
    setUrl("");
  };

  // Add to history when sync completes successfully
  // This effect reacts to external async completion and is a valid use case
  useEffect(() => {
    if (
      status === "complete" &&
      result?.success &&
      result.album &&
      lastCompletedRef.current !== result.album.title
    ) {
      lastCompletedRef.current = result.album.title;
      const newAlbum: DownloadedAlbum = {
        id: Date.now().toString(),
        title: result.album.title,
        artist: result.album.artist,
        album: result.album.title,
        downloadedAt: new Date().toISOString(),
        trackCount: result.track_count,
        size: "-- MB", // TODO: Get real size from backend
      };
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Reacting to async completion
      setDownloadHistory((prev) => [newAlbum, ...prev]);
    }
  }, [status, result]);

  const removeFromHistory = (id: string) => {
    setDownloadHistory((prev) => prev.filter((album) => album.id !== id));
  };

  return (
    <div className="bg-background flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <main className="w-full max-w-xl">
        {/* Header - v0 style with YouTube icon and version */}
        <div className="mb-6 flex items-center gap-2">
          <div className="bg-primary/10 rounded-lg p-2">
            <Music2 className="text-primary h-5 w-5" />
          </div>
          <div>
            <h1 className="text-foreground font-mono text-lg font-semibold">
              yubal
            </h1>
            <p className="text-default-500 font-mono text-xs">v0.1.0</p>
          </div>
        </div>

        {/* URL Input Section */}
        <div className="mb-6 flex gap-2">
          <div className="flex-1">
            <UrlInput value={url} onChange={setUrl} disabled={isSyncing} />
          </div>
          <Button
            color="primary"
            isIconOnly
            onPress={handleSync}
            isLoading={isSyncing}
            isDisabled={!canSync}
          >
            {!isSyncing && <Download className="h-4 w-4" />}
          </Button>
          {isSyncing && (
            <Button color="danger" isIconOnly onPress={cancelSync}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Album Info Card */}
        <AnimatePresence>
          {showAlbumCard && (
            <AlbumInfoCard
              trackInfo={trackInfo}
              progress={progress}
              status={status}
            />
          )}
        </AnimatePresence>

        {/* Console Output */}
        <ConsoleOutput logs={logs} status={status} />

        {/* Clear Button */}
        {(status === "complete" || status === "error") && (
          <div className="mt-4">
            <Button
              color="default"
              variant="flat"
              onPress={handleClear}
              fullWidth
            >
              Clear
            </Button>
          </div>
        )}

        {/* Download History */}
        <DownloadHistory
          history={downloadHistory}
          onRemove={removeFromHistory}
        />

        {/* Footer */}
        <p className="text-default-500 mt-6 text-center font-mono text-xs">
          For educational purposes only
        </p>
      </main>
    </div>
  );
}

import { Button } from "@heroui/react";
import { Clock, Music, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export interface DownloadedAlbum {
  id: string;
  title: string;
  artist: string;
  album: string;
  downloadedAt: string;
  trackCount: number;
  size: string;
}

interface DownloadHistoryProps {
  history: DownloadedAlbum[];
  onRemove: (id: string) => void;
}

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateString;
  }
}

export function DownloadHistory({ history, onRemove }: DownloadHistoryProps) {
  if (history.length === 0) return null;

  return (
    <div className="mt-6">
      <div className="mb-3 flex items-center gap-2">
        <Clock className="text-default-500 h-4 w-4" />
        <span className="text-foreground font-mono text-sm font-medium">
          Download History
        </span>
        <span className="text-default-500 font-mono text-xs">
          ({history.length})
        </span>
      </div>
      <div className="max-h-64 space-y-2 overflow-y-auto">
        <AnimatePresence initial={false}>
          {history.map((album) => (
            <motion.div
              key={album.id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="group bg-default-50 flex items-center gap-3 rounded-lg border border-white/10 p-3"
            >
              <div className="bg-default-100 flex h-10 w-10 shrink-0 items-center justify-center rounded">
                <Music className="text-default-400 h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-foreground truncate font-mono text-sm font-medium">
                  {album.album}
                </p>
                <p className="text-default-500 truncate font-mono text-xs">
                  {album.artist}
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-default-400 font-mono text-xs">
                    {album.trackCount} tracks
                  </span>
                  <span className="text-default-300 text-xs">&#8226;</span>
                  <span className="text-default-400 font-mono text-xs">
                    {album.size}
                  </span>
                  <span className="text-default-300 text-xs">&#8226;</span>
                  <span className="text-default-400 font-mono text-xs">
                    {formatDate(album.downloadedAt)}
                  </span>
                </div>
              </div>
              <Button
                isIconOnly
                variant="light"
                size="sm"
                onPress={() => onRemove(album.id)}
              >
                <Trash2 className="text-default-400 h-3.5 w-3.5" />
              </Button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

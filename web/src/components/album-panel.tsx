import { Button } from "@heroui/react";
import { ArrowLeft, Disc3, Download } from "lucide-react";
import type { AlbumResponse } from "../api/album";
import { getAlbumThumbnail, getTrackMeta } from "../api/album";
import { EmptyState } from "./common/empty-state";
import { DownloadStatusIcon, type DownloadStatus } from "./common/download-indicator";
import { Panel, PanelContent, PanelHeader } from "./common/panel";

interface AlbumPanelProps {
  album: AlbumResponse | null;
  isLoading: boolean;
  onBack: () => void;
  onDownloadAlbum?: () => void;
  onDownloadTrack?: (videoId: string) => void;
  onViewSong?: (videoId: string) => void;
  albumStatus?: { status: DownloadStatus; progress: number | null };
  trackStatuses?: Record<string, { status: DownloadStatus; progress: number | null }>;
}

export function AlbumPanel({
  album,
  isLoading,
  onBack,
  onDownloadAlbum,
  onDownloadTrack,
  onViewSong,
  albumStatus = { status: "idle", progress: null },
  trackStatuses = {},
}: AlbumPanelProps) {
  const thumbnail = getAlbumThumbnail(album);
  const tracks = album?.tracks ?? [];
  const hasTracks = tracks.length > 0;

  return (
    <Panel>
      <PanelHeader
        leadingIcon={<Disc3 size={18} />}
        trailingIcon={
          <div className="flex items-center gap-2">
            {onDownloadAlbum && hasTracks && (
              <Button
                size="sm"
                variant="flat"
                onPress={onDownloadAlbum}
                isDisabled={
                  albumStatus.status === "queued" ||
                  albumStatus.status === "downloading"
                }
                isIconOnly
                aria-label="Download album"
                startContent={
                  albumStatus.status === "idle" ? (
                    <Download className="h-4 w-4" />
                  ) : (
                    <DownloadStatusIcon
                      status={albumStatus.status}
                      progress={albumStatus.progress}
                    />
                  )
                }
              />
            )}
            <Button
              variant="light"
              size="sm"
              startContent={<ArrowLeft className="h-4 w-4" />}
              onPress={onBack}
            >
              Back to results
            </Button>
          </div>
        }
      >
        Album
      </PanelHeader>
      <PanelContent height="h-[520px]" className="space-y-4">
        {isLoading ? (
          <EmptyState icon={Disc3} title="Loading album..." />
        ) : !album ? (
          <EmptyState icon={Disc3} title="Album not found" />
        ) : (
          <>
            <div className="flex flex-wrap gap-4">
              {thumbnail && (
                <img
                  src={thumbnail}
                  alt={album.title}
                  className="h-24 w-24 rounded-xl object-cover"
                  loading="lazy"
                />
              )}
              <div className="min-w-0 flex-1">
                <div className="text-foreground-600 truncate text-lg font-semibold">
                  {album.title}
                </div>
                <div className="text-foreground-400 text-xs uppercase tracking-wider">
                  {(album.artists ?? [])
                    .map((artist) => artist.name)
                    .filter(Boolean)
                    .join(", ") || "Unknown artist"}
                </div>
                <div className="text-foreground-400 mt-1 text-xs">
                  {[album.year, album.trackCount && `${album.trackCount} tracks`, album.duration]
                    .filter(Boolean)
                    .join(" • ")}
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-foreground-400 text-xs uppercase tracking-wider">
                Tracks
              </div>
              {tracks.length === 0 ? (
                <EmptyState icon={Disc3} title="No tracks available" />
              ) : (
                <div className="space-y-2">
                  {tracks.map((track, index) => (
                    <div
                      key={`${track.videoId ?? "track"}-${index}`}
                      onClick={() => {
                        if (track.videoId) onViewSong?.(track.videoId);
                      }}
                      className={`bg-content2/60 flex items-center gap-3 rounded-xl px-3 py-2 ${
                        track.videoId ? "cursor-pointer hover:bg-content2" : ""
                      }`}
                    >
                      <div className="text-foreground-400 w-6 text-xs">
                        {track.trackNumber ?? index + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-foreground-600 truncate text-sm font-medium">
                          {track.title}
                        </div>
                        {getTrackMeta(track) && (
                          <div className="text-foreground-400 truncate text-xs">
                            {getTrackMeta(track)}
                          </div>
                        )}
                      </div>
                      {track.videoId && onDownloadTrack && (
                        <Button
                          size="sm"
                          variant="flat"
                          onPress={() => onDownloadTrack(track.videoId!)}
                          onClick={(event) => event.stopPropagation()}
                          isDisabled={
                            trackStatuses[track.videoId]?.status === "queued" ||
                            trackStatuses[track.videoId]?.status === "downloading"
                          }
                          isIconOnly
                          aria-label={`Download ${track.title}`}
                          startContent={
                            trackStatuses[track.videoId]?.status === "idle" ? (
                              <Download className="h-4 w-4" />
                            ) : (
                              <DownloadStatusIcon
                                status={
                                  trackStatuses[track.videoId]?.status ?? "idle"
                                }
                                progress={
                                  trackStatuses[track.videoId]?.progress ?? null
                                }
                              />
                            )
                          }
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </PanelContent>
    </Panel>
  );
}

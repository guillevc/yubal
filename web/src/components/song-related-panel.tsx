import { Button } from "@heroui/react";
import { ArrowLeft, Download, Music2 } from "lucide-react";
import type { RelatedItem, RelatedSection } from "../api/song-related";
import { EmptyState } from "./common/empty-state";
import { DownloadStatusIcon, type DownloadStatus } from "./common/download-indicator";
import { Panel, PanelContent, PanelHeader } from "./common/panel";

interface SongRelatedPanelProps {
  sections: RelatedSection[];
  isLoading: boolean;
  onQueueUrl: (url: string) => void;
  downloadStatuses: Record<string, { status: DownloadStatus; progress: number | null }>;
  onViewSong: (videoId: string) => void;
  onBack: () => void;
}

function getTitle(item: RelatedItem): string {
  return item.title || item.name || "Untitled";
}

function getSubtitle(item: RelatedItem): string | null {
  const artists = item.artists?.map((artist) => artist.name).filter(Boolean) ?? [];
  if (artists.length > 0) return artists.join(", ");
  return item.subscribers || item.description || null;
}

function getThumbnailUrl(item: RelatedItem): string | null {
  const thumbnails = item.thumbnails;
  if (!thumbnails || thumbnails.length === 0) return null;

  const sorted = [...thumbnails].sort((a, b) => {
    const aSize = (a.width ?? 0) * (a.height ?? 0);
    const bSize = (b.width ?? 0) * (b.height ?? 0);
    return bSize - aSize;
  });

  return sorted[0]?.url ?? null;
}

function getSongUrl(item: RelatedItem): string | null {
  if (item.videoId) {
    return `https://music.youtube.com/watch?v=${item.videoId}`;
  }
  return null;
}

export function SongRelatedPanel({
  sections,
  isLoading,
  onQueueUrl,
  downloadStatuses,
  onViewSong,
  onBack,
}: SongRelatedPanelProps) {
  return (
    <Panel>
      <PanelHeader
        leadingIcon={<Music2 size={18} />}
        trailingIcon={
          <Button
            variant="light"
            size="sm"
            startContent={<ArrowLeft className="h-4 w-4" />}
            onPress={onBack}
          >
            Back to results
          </Button>
        }
      >
        Related
      </PanelHeader>
      <PanelContent height="h-[520px]" className="space-y-4">
        {isLoading ? (
          <EmptyState icon={Music2} title="Loading related..." />
        ) : sections.length === 0 ? (
          <EmptyState icon={Music2} title="No related content" />
        ) : (
          <div className="space-y-6">
            {sections.map((section, sectionIndex) => (
              <section key={`${section.title ?? "section"}-${sectionIndex}`}>
                {section.title && (
                  <div className="text-foreground-400 mb-2 text-xs uppercase tracking-wider">
                    {section.title}
                  </div>
                )}
                {typeof section.contents === "string" ? (
                  <div className="text-foreground-500 text-sm leading-relaxed">
                    {section.contents}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {(section.contents ?? []).map((item, index) => {
                      const title = getTitle(item);
                      const subtitle = getSubtitle(item);
                      const thumbnailUrl = getThumbnailUrl(item);
                      const url = getSongUrl(item);
                      const canView = Boolean(item.videoId);
                      const status: {
                        status: DownloadStatus;
                        progress: number | null;
                      } = url
                        ? downloadStatuses[url] ?? { status: "idle", progress: null }
                        : { status: "idle", progress: null };
                      const meta = [item.year, item.duration, item.itemCount]
                        .filter(Boolean)
                        .join(" • ");

                      return (
                        <div
                          key={`${title}-${index}`}
                          onClick={() => {
                            if (item.videoId) onViewSong(item.videoId);
                          }}
                          className={`bg-content2/60 flex items-center gap-3 rounded-xl px-3 py-2 ${
                            canView ? "cursor-pointer hover:bg-content2" : ""
                          }`}
                        >
                          {thumbnailUrl && (
                            <img
                              src={thumbnailUrl}
                              alt={title}
                              className="h-10 w-10 rounded-lg object-cover"
                              loading="lazy"
                            />
                          )}
                          <div className="min-w-0 flex-1">
                            <div className="text-foreground-600 truncate text-sm font-medium">
                              {title}
                            </div>
                            {subtitle && (
                              <div className="text-foreground-400 truncate text-xs">
                                {subtitle}
                              </div>
                            )}
                            {meta && (
                              <div className="text-foreground-400 text-xs">
                                {meta}
                              </div>
                            )}
                          </div>
                          {url && (
                            <Button
                              size="sm"
                              variant="flat"
                              onPress={() => onQueueUrl(url)}
                              onClick={(event) => event.stopPropagation()}
                              isDisabled={
                                status.status === "queued" ||
                                status.status === "downloading"
                              }
                              isIconOnly
                              aria-label={`Download ${title}`}
                              startContent={
                                status.status === "idle" ? (
                                  <Download className="h-4 w-4" />
                                ) : (
                                  <DownloadStatusIcon
                                    status={status.status}
                                    progress={status.progress}
                                  />
                                )
                              }
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            ))}
          </div>
        )}
      </PanelContent>
    </Panel>
  );
}

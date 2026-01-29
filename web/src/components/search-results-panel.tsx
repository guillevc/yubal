import { Button } from "@heroui/react";
import { ArrowLeft, Download, ExternalLink, Search } from "lucide-react";
import type { SearchResult } from "../api/search";
import { EmptyState } from "./common/empty-state";
import { DownloadStatusIcon, type DownloadStatus } from "./common/download-indicator";
import { Panel, PanelContent, PanelHeader } from "./common/panel";

interface SearchResultsPanelProps {
  results: SearchResult[];
  query: string;
  isSearching: boolean;
  onQueueUrl: (url: string) => void;
  onViewAlbum: (browseId: string) => void;
  onViewSong: (videoId: string) => void;
  downloadStatuses: Record<string, { status: DownloadStatus; progress: number | null }>;
  onBack: () => void;
}

function getTitle(result: SearchResult): string {
  const primaryArtist = result.artists?.[0]?.name;
  return (
    result.title ||
    result.name ||
    primaryArtist ||
    result.artist ||
    result.author ||
    "Untitled"
  );
}

function getSubtitle(result: SearchResult): string | null {
  const artists =
    result.artists?.map((artist) => artist.name).filter(Boolean) ?? [];
  if (artists.length > 0) return artists.join(", ");
  if (result.artist) return result.artist;
  if (result.author) return result.author;
  return null;
}

function formatTypeLabel(value: string | undefined): string | null {
  if (!value) return null;
  const text = value.replace(/[_-]+/g, " ").toLowerCase();
  return text.replace(/\b\w/g, (char) => char.toUpperCase());
}

function getInfoLine(result: SearchResult): string | null {
  const subtitle = getSubtitle(result);
  const category = result.category?.toLowerCase();
  const isListenAgain = category === "listen again";
  const isSong =
    result.resultType === "song" || category === "songs" || isListenAgain;
  const duration = isSong ? result.duration ?? null : null;
  const typeLabel = isListenAgain
    ? null
    : formatTypeLabel(result.resultType ?? result.category);

  const parts = [typeLabel, subtitle, duration].filter(Boolean) as string[];
  if (parts.length === 0) return null;
  return parts.join(" • ");
}

function getResultUrl(result: SearchResult): string | null {
  if (result.playlistId) {
    return `https://music.youtube.com/playlist?list=${result.playlistId}`;
  }
  if (result.browseId) {
    return `https://music.youtube.com/browse/${result.browseId}`;
  }
  if (result.videoId) {
    return `https://music.youtube.com/watch?v=${result.videoId}`;
  }
  return null;
}

function getThumbnailUrl(result: SearchResult): string | null {
  const thumbnails = result.thumbnails;
  if (!thumbnails || thumbnails.length === 0) return null;

  const sorted = [...thumbnails].sort((a, b) => {
    const aSize = (a.width ?? 0) * (a.height ?? 0);
    const bSize = (b.width ?? 0) * (b.height ?? 0);
    return bSize - aSize;
  });

  return sorted[0]?.url ?? null;
}

export function SearchResultsPanel({
  results,
  query,
  isSearching,
  onQueueUrl,
  onViewAlbum,
  onViewSong,
  downloadStatuses,
  onBack,
}: SearchResultsPanelProps) {
  const topArtistIndex = results.findIndex(
    (item) =>
      item.category?.toLowerCase() === "top result" &&
      item.resultType === "artist",
  );
  const topArtist = topArtistIndex >= 0 ? results[topArtistIndex] : null;
  const usedIndexes = new Set<number>();

  const topItems: SearchResult[] = [];

  if (topArtist) {
    const artistName =
      topArtist.artists?.[0]?.name || topArtist.name || topArtist.artist || null;

    usedIndexes.add(topArtistIndex);

    for (let i = topArtistIndex + 1; i < results.length; i += 1) {
      const item = results[i];
      if (!item) continue;
      if (topItems.length >= 3) break;

      const itemArtists =
        item.artists?.map((artist) => artist.name).filter(Boolean) ?? [];
      const isFromArtist = artistName
        ? itemArtists.includes(artistName) ||
          item.artist === artistName ||
          item.author === artistName
        : false;

      if (!isFromArtist) continue;

      topItems.push(item);
      usedIndexes.add(i);
    }
  }

  const filteredResults = results.filter((_, index) => !usedIndexes.has(index));
  const grouped = filteredResults.reduce<Record<string, SearchResult[]>>(
    (acc, item) => {
      const key = item.category || item.resultType || "Results";
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    },
    {},
  );

  const hasResults = results.length > 0;
  const topArtistThumbnail = topArtist ? getThumbnailUrl(topArtist) : null;
  const topArtistUrl = topArtist ? getResultUrl(topArtist) : null;
  const topArtistStatus: { status: DownloadStatus; progress: number | null } =
    topArtistUrl
      ? downloadStatuses[topArtistUrl] ?? { status: "idle", progress: null }
      : { status: "idle", progress: null };

  return (
    <Panel>
      <PanelHeader
        leadingIcon={<Search size={18} />}
        trailingIcon={
          <Button
            variant="light"
            size="sm"
            startContent={<ArrowLeft className="h-4 w-4" />}
            onPress={onBack}
          >
            Back to downloads
          </Button>
        }
        badge={
          query && (
            <span className="text-foreground-400 font-mono text-xs">
              ({results.length})
            </span>
          )
        }
      >
        Search results
      </PanelHeader>
      <PanelContent height="h-[520px]">
        {isSearching ? (
          <EmptyState icon={Search} title="Searching..." />
        ) : !hasResults ? (
          <EmptyState
            icon={Search}
            title="No results"
            description={
              query
                ? `No results found for "${query}".`
                : "Search for artists, songs, albums, or playlists."
            }
          />
        ) : (
          <div className="space-y-6">
            {topArtist && (
              <section className="space-y-3">
                <div className="text-foreground-400 text-xs uppercase tracking-wider">
                  Top result
                </div>
                <div className="bg-content2/70 border-content3/40 relative overflow-hidden rounded-2xl border p-4">
                  {topArtistThumbnail && (
                    <div
                      className="absolute inset-0 bg-cover bg-center blur-2xl scale-110 opacity-20"
                      style={{ backgroundImage: `url(${topArtistThumbnail})` }}
                    />
                  )}
                  <div className="relative z-10 space-y-4">
                    <div className="flex flex-wrap items-center gap-4">
                      {topArtistThumbnail && (
                        <img
                          src={topArtistThumbnail}
                          alt={getTitle(topArtist)}
                          className="h-16 w-16 rounded-full object-cover"
                          loading="lazy"
                        />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="text-foreground-600 truncate text-lg font-semibold">
                          {getTitle(topArtist)}
                        </div>
                        <div className="text-foreground-400 text-xs uppercase tracking-wider">
                          Artist
                        </div>
                      </div>
                      {topArtistUrl && (
                        <Button
                          size="sm"
                          variant="flat"
                          onPress={() => onQueueUrl(topArtistUrl)}
                          isDisabled={
                            topArtistStatus.status === "queued" ||
                            topArtistStatus.status === "downloading"
                          }
                          isIconOnly
                          aria-label="Download top result"
                          startContent={
                            topArtistStatus.status === "idle" ? (
                              <Download className="h-4 w-4" />
                            ) : (
                              <DownloadStatusIcon
                                status={topArtistStatus.status}
                                progress={topArtistStatus.progress}
                              />
                            )
                          }
                        />
                      )}
                    </div>
                    {topItems.length > 0 && (
                      <div className="space-y-2">
                        {topItems.map((item, index) => {
                          const title = getTitle(item);
                          const infoLine = getInfoLine(item);
                          const url = getResultUrl(item);
                          const browseId = item.browseId;
                          const isAlbum =
                            item.resultType === "album" || item.category === "Albums";
                          const isSong =
                            item.resultType === "song" ||
                            item.category?.toLowerCase() === "songs" ||
                            item.category?.toLowerCase() === "listen again";
                          const thumbnailUrl = getThumbnailUrl(item);
                          const status: {
                            status: DownloadStatus;
                            progress: number | null;
                          } = url
                            ? downloadStatuses[url] ?? { status: "idle", progress: null }
                            : { status: "idle", progress: null };
                          const meta = infoLine;

                          return (
                            <div
                              key={`top-item-${index}-${title}`}
                              onClick={() => {
                                if (isAlbum && browseId) onViewAlbum(browseId);
                                if (isSong && item.videoId) onViewSong(item.videoId);
                              }}
                              className={`bg-content1/60 flex items-center gap-3 rounded-xl px-3 py-2 ${
                                isAlbum || (isSong && item.videoId)
                                  ? "cursor-pointer hover:bg-content1"
                                  : ""
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
                  </div>
                </div>
              </section>
            )}
            {Object.entries(grouped).map(([category, items]) => (
              <section key={category} className="space-y-2">
                <div className="text-foreground-400 text-xs uppercase tracking-wider">
                  {category}
                </div>
                <div className="space-y-2">
                  {items.map((item, index) => {
                    const title = getTitle(item);
                    const infoLine = getInfoLine(item);
                    const url = getResultUrl(item);
                    const browseId = item.browseId;
                    const isAlbum =
                      item.resultType === "album" || item.category === "Albums";
                    const isSong =
                      item.resultType === "song" ||
                      item.category?.toLowerCase() === "songs" ||
                      item.category?.toLowerCase() === "listen again";
                    const thumbnailUrl = getThumbnailUrl(item);
                    const status: {
                      status: DownloadStatus;
                      progress: number | null;
                    } = url
                      ? downloadStatuses[url] ?? { status: "idle", progress: null }
                      : { status: "idle", progress: null };
                    const meta = infoLine;
                    const canQueue = Boolean(url);

                    return (
                      <div
                        key={`${category}-${index}-${title}`}
                        onClick={() => {
                          if (isAlbum && browseId) onViewAlbum(browseId);
                          if (isSong && item.videoId) onViewSong(item.videoId);
                        }}
                        className={`bg-content2/60 flex items-center gap-3 rounded-xl px-3 py-2 ${
                          canQueue ? "transition" : "opacity-80"
                        } ${
                          isAlbum || (isSong && item.videoId)
                            ? "cursor-pointer hover:bg-content2"
                            : ""
                        }`}
                      >
                        {thumbnailUrl && (
                          <img
                            src={thumbnailUrl}
                            alt={title}
                            className="h-12 w-12 rounded-lg object-cover"
                            loading="lazy"
                          />
                        )}
                        <div className="flex min-w-0 flex-1 flex-col">
                          <div className="flex items-center gap-2">
                            <span className="text-foreground-600 truncate text-sm font-medium">
                              {title}
                            </span>
                          </div>
                          {meta && (
                            <span className="text-foreground-400 text-xs">
                              {meta}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
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
                          {url && (
                            <Button
                              size="sm"
                              variant="light"
                              as="a"
                              href={url}
                              target="_blank"
                              rel="noreferrer"
                              isIconOnly
                              onClick={(event) => event.stopPropagation()}
                            >
                              <ExternalLink className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )}
      </PanelContent>
    </Panel>
  );
}

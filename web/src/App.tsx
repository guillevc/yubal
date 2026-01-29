import { Button, NumberInput, Tooltip } from "@heroui/react";
import { Download, Hash, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ConsolePanel } from "./components/console-panel";
import { DownloadsPanel } from "./components/downloads-panel";
import { AlbumPanel } from "./components/album-panel";
import { Footer } from "./components/layout/footer";
import { Header } from "./components/layout/header";
import { BlurFade } from "./components/magicui/blur-fade";
import { SearchResultsPanel } from "./components/search-results-panel";
import { SongRelatedPanel } from "./components/song-related-panel";
import { UrlInput } from "./components/url-input";
import { useAlbum } from "./hooks/use-album";
import { useJobs } from "./hooks/use-jobs";
import { useSearch } from "./hooks/use-search";
import { useSearchSuggestions } from "./hooks/use-search-suggestions";
import { useSongRelated } from "./hooks/use-song-related";
import { isValidUrl } from "./lib/url";
import { isActive } from "./lib/job-status";
import { showErrorToast } from "./lib/toast";

const DEFAULT_MAX_ITEMS = 50;

type DownloadStatus =
  | "idle"
  | "queued"
  | "downloading"
  | "completed"
  | "failed";

interface DownloadState {
  status: DownloadStatus;
  progress: number | null;
}

function normalizeProgress(progress: number | null | undefined): number | null {
  if (progress === null || progress === undefined) return null;
  if (Number.isNaN(progress)) return null;
  if (progress <= 1) return Math.round(progress * 100);
  return Math.round(progress);
}

function deriveDownloadState(
  job: { status: string; progress?: number } | undefined,
  isPending: boolean,
): DownloadState {
  if (job) {
    if (job.status === "completed") {
      return { status: "completed", progress: 100 };
    }
    if (job.status === "failed" || job.status === "cancelled") {
      return { status: "failed", progress: null };
    }

    if (job.status === "pending" || job.status === "fetching_info") {
      return { status: "queued", progress: null };
    }

    if (isActive(job.status as never)) {
      return { status: "downloading", progress: normalizeProgress(job.progress) };
    }

    return { status: "queued", progress: null };
  }
  return { status: isPending ? "queued" : "idle", progress: null };
}

export default function App() {
  const [url, setUrl] = useState("");
  const [maxItems, setMaxItems] = useState(DEFAULT_MAX_ITEMS);
  const [view, setView] = useState<"downloads" | "search" | "album" | "related">(
    "downloads",
  );
  const [albumBrowseId, setAlbumBrowseId] = useState<string | null>(null);
  const [relatedVideoId, setRelatedVideoId] = useState<string | null>(null);
  const [, setRelatedHistory] = useState<string[]>([]);
  const [relatedSourceView, setRelatedSourceView] = useState<"search" | "album">(
    "search",
  );
  const [pendingAlbum, setPendingAlbum] = useState(false);
  const [pendingTrackIds, setPendingTrackIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [pendingSearchUrls, setPendingSearchUrls] = useState<Set<string>>(
    () => new Set(),
  );
  const [pendingRelatedUrls, setPendingRelatedUrls] = useState<Set<string>>(
    () => new Set(),
  );
  const { jobs, startJob, cancelJob, deleteJob } = useJobs();
  const { results, query, isSearching, search, clear } = useSearch();
  const { album, isLoading: isAlbumLoading } = useAlbum(albumBrowseId);
  const { sections, isLoading: isRelatedLoading } = useSongRelated(relatedVideoId);
  const albumUrl = album?.audioPlaylistId
    ? `https://music.youtube.com/playlist?list=${album.audioPlaylistId}`
    : albumBrowseId
      ? `https://music.youtube.com/browse/${albumBrowseId}`
      : null;
  const albumJob = albumUrl
    ? jobs.find((job) => job.url === albumUrl)
    : undefined;

  const trackStatuses = useMemo(() => {
    const statusMap: Record<string, DownloadState> = {};
    const albumFallback = deriveDownloadState(albumJob, pendingAlbum);

    const trackList = album?.tracks ?? [];
    for (const track of trackList) {
      if (!track.videoId) continue;
      const url = `https://music.youtube.com/watch?v=${track.videoId}`;
      const job = jobs.find((candidate) => candidate.url === url);
      const directState = deriveDownloadState(
        job,
        pendingTrackIds.has(track.videoId),
      );

      statusMap[track.videoId] =
        directState.status === "idle" && albumFallback.status !== "idle"
          ? albumFallback
          : directState;
    }

    return statusMap;
  }, [album, albumJob, jobs, pendingAlbum, pendingTrackIds]);

  const albumStatus = deriveDownloadState(albumJob, pendingAlbum);

  const searchDownloadStatuses = useMemo(() => {
    const statusMap: Record<string, DownloadState> = {};

    for (const item of results) {
      const url = item.playlistId
        ? `https://music.youtube.com/playlist?list=${item.playlistId}`
        : item.browseId
          ? `https://music.youtube.com/browse/${item.browseId}`
          : item.videoId
            ? `https://music.youtube.com/watch?v=${item.videoId}`
            : null;

      if (!url) continue;
      const job = jobs.find((candidate) => candidate.url === url);
      statusMap[url] = deriveDownloadState(job, pendingSearchUrls.has(url));
    }

    return statusMap;
  }, [jobs, pendingSearchUrls, results]);

  const relatedDownloadStatuses = useMemo(() => {
    const statusMap: Record<string, DownloadState> = {};

    for (const section of sections) {
      if (!Array.isArray(section.contents)) continue;
      for (const item of section.contents) {
        if (!item.videoId) continue;
        const url = `https://music.youtube.com/watch?v=${item.videoId}`;
        const job = jobs.find((candidate) => candidate.url === url);
        statusMap[url] = deriveDownloadState(job, pendingRelatedUrls.has(url));
      }
    }

    return statusMap;
  }, [jobs, pendingRelatedUrls, sections]);


  const isUrl = isValidUrl(url);
  const isUrlLike = url.startsWith("http://") || url.startsWith("https://");
  const isSearchable = url.trim().length > 0 && !isUrlLike;
  const canSubmit = isUrl || isSearchable;
  const { suggestions } = useSearchSuggestions(url, {
    enabled: false,
  });

  const handleSubmit = async () => {
    if (isUrl) {
      await startJob(url, maxItems);
      setUrl("");
      setView("downloads");
      setAlbumBrowseId(null);
      setRelatedVideoId(null);
      setRelatedHistory([]);
      return;
    }

    if (isSearchable) {
      await search(url);
      setView("search");
      setAlbumBrowseId(null);
      setRelatedVideoId(null);
      setRelatedHistory([]);
    }
  };

  const handleDelete = async (jobId: string) => {
    await deleteJob(jobId);
  };

  useEffect(() => {
    setPendingAlbum(false);
  }, [albumBrowseId]);

  useEffect(() => {
    if (pendingAlbum && albumJob) {
      setPendingAlbum(false);
    }
  }, [pendingAlbum, albumJob]);

  useEffect(() => {
    if (pendingTrackIds.size === 0) return;

    setPendingTrackIds((prev) => {
      let changed = false;
      const next = new Set(prev);
      for (const videoId of prev) {
        const url = `https://music.youtube.com/watch?v=${videoId}`;
        if (jobs.some((job) => job.url === url)) {
          next.delete(videoId);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [jobs, pendingTrackIds]);

  useEffect(() => {
    if (pendingSearchUrls.size === 0) return;

    setPendingSearchUrls((prev) => {
      let changed = false;
      const next = new Set(prev);
      for (const url of prev) {
        if (jobs.some((job) => job.url === url)) {
          next.delete(url);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [jobs, pendingSearchUrls]);

  useEffect(() => {
    if (pendingRelatedUrls.size === 0) return;

    setPendingRelatedUrls((prev) => {
      let changed = false;
      const next = new Set(prev);
      for (const url of prev) {
        if (jobs.some((job) => job.url === url)) {
          next.delete(url);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [jobs, pendingRelatedUrls]);

  return (
    <div className="relative flex min-h-screen flex-col">
      <Header />

      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8">
        {/* URL Input Section */}
        <BlurFade delay={0.05} direction="up" className="relative z-40">
          <section className="mb-6 flex gap-2">
            <div className="flex-1">
              <UrlInput
                value={url}
                onChange={setUrl}
                onSubmit={handleSubmit}
                suggestions={suggestions}
                onSuggestionSelect={async (suggestion) => {
                  setUrl(suggestion);
                  await search(suggestion);
                  setView("search");
                }}
              />
            </div>
            {isUrl && (
              <Tooltip content="Max number of tracks to download" offset={14}>
                <NumberInput
                  hideStepper
                  variant="faded"
                  value={maxItems}
                  onValueChange={setMaxItems}
                  minValue={1}
                  maxValue={10000}
                  radius="lg"
                  fullWidth={false}
                  startContent={<Hash className="text-foreground-400 h-4 w-4" />}
                  className="w-24 font-mono"
                />
              </Tooltip>
            )}
            <Button
              color="primary"
              radius="lg"
              variant={canSubmit ? "shadow" : "solid"}
              className="shadow-primary-100/50"
              onPress={handleSubmit}
              isDisabled={!canSubmit}
              startContent={
                isUrl ? (
                  <Download className="h-4 w-4" />
                ) : (
                  <Search className="h-4 w-4" />
                )
              }
            >
              {isUrl ? "Download" : "Search"}
            </Button>
          </section>
        </BlurFade>

        {/* Stacked Panels */}
        <BlurFade delay={0.1} direction="up">
          <section className="mb-6 flex flex-col gap-4">
            {view === "related" ? (
              <>
                <SongRelatedPanel
                  sections={sections}
                  isLoading={isRelatedLoading}
                  downloadStatuses={relatedDownloadStatuses}
                  onQueueUrl={async (nextUrl) => {
                    if (pendingRelatedUrls.has(nextUrl)) return;
                    setPendingRelatedUrls((prev) => {
                      const next = new Set(prev);
                      next.add(nextUrl);
                      return next;
                    });
                    const success = await startJob(nextUrl, maxItems);
                    if (!success) {
                      setPendingRelatedUrls((prev) => {
                        const next = new Set(prev);
                        next.delete(nextUrl);
                        return next;
                      });
                    }
                  }}
                  onViewSong={(videoId) => {
                    setRelatedHistory((prev) => [...prev, videoId]);
                    setRelatedVideoId(videoId);
                    setView("related");
                  }}
                  onBack={() => {
                    setRelatedHistory((prev) => {
                      if (prev.length <= 1) {
                        setView(relatedSourceView);
                        setRelatedVideoId(null);
                        return [];
                      }
                      const next = prev.slice(0, -1);
                      const nextVideoId = next[next.length - 1] ?? null;
                      setRelatedVideoId(nextVideoId);
                      setView("related");
                      return next;
                    });
                  }}
                />
                <ConsolePanel jobs={jobs} />
              </>
            ) : view === "album" ? (
              <>
                <AlbumPanel
                  album={album}
                  isLoading={isAlbumLoading}
                  onBack={() => {
                    setView("search");
                    setAlbumBrowseId(null);
                    setRelatedHistory([]);
                  }}
                  onViewSong={(videoId) => {
                    setRelatedSourceView("album");
                    setRelatedHistory([videoId]);
                    setRelatedVideoId(videoId);
                    setView("related");
                  }}
                  onDownloadAlbum={
                    albumBrowseId
                      ? async () => {
                          if (pendingAlbum) return;
                          const audioPlaylistId = album?.audioPlaylistId;
                          if (!audioPlaylistId) {
                            showErrorToast(
                              "Download failed",
                              "Album playlist ID not available.",
                            );
                            return;
                          }
                          setPendingAlbum(true);
                          const url = `https://music.youtube.com/playlist?list=${audioPlaylistId}`;
                          const success = await startJob(url, maxItems);
                          if (!success) {
                            setPendingAlbum(false);
                          }
                        }
                      : undefined
                  }
                  onDownloadTrack={async (videoId) => {
                    if (pendingTrackIds.has(videoId)) return;
                    setPendingTrackIds((prev) => {
                      const next = new Set(prev);
                      next.add(videoId);
                      return next;
                    });
                    const url = `https://music.youtube.com/watch?v=${videoId}`;
                    const success = await startJob(url, maxItems);
                    if (!success) {
                      setPendingTrackIds((prev) => {
                        const next = new Set(prev);
                        next.delete(videoId);
                        return next;
                      });
                    }
                  }}
                  albumStatus={albumStatus}
                  trackStatuses={trackStatuses}
                />
                <ConsolePanel jobs={jobs} />
              </>
            ) : view === "search" ? (
              <>
                <SearchResultsPanel
                  results={results}
                  query={query}
                  isSearching={isSearching}
                  onQueueUrl={async (nextUrl) => {
                    if (pendingSearchUrls.has(nextUrl)) return;
                    setPendingSearchUrls((prev) => {
                      const next = new Set(prev);
                      next.add(nextUrl);
                      return next;
                    });
                    const success = await startJob(nextUrl, maxItems);
                    if (!success) {
                      setPendingSearchUrls((prev) => {
                        const next = new Set(prev);
                        next.delete(nextUrl);
                        return next;
                      });
                    }
                  }}
                  downloadStatuses={searchDownloadStatuses}
                  onViewSong={(videoId) => {
                    setRelatedSourceView("search");
                    setRelatedHistory([videoId]);
                    setRelatedVideoId(videoId);
                    setView("related");
                  }}
                  onViewAlbum={(browseId) => {
                    setAlbumBrowseId(browseId);
                    setView("album");
                  }}
                  onBack={() => {
                    setView("downloads");
                    clear();
                    setAlbumBrowseId(null);
                    setRelatedVideoId(null);
                    setRelatedHistory([]);
                  }}
                />
                <ConsolePanel jobs={jobs} />
              </>
            ) : (
              <>
                <DownloadsPanel
                  jobs={jobs}
                  onCancel={cancelJob}
                  onDelete={handleDelete}
                />
                <ConsolePanel jobs={jobs} />
              </>
            )}
          </section>
        </BlurFade>
      </main>

      <BlurFade delay={0.15} direction="up">
        <Footer />
      </BlurFade>
    </div>
  );
}

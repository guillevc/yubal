import {
  getArtistReleases,
  queueArtistReleases,
  searchArtists,
  type ArtistRelease,
  type ArtistReleases,
  type ArtistSummary,
} from "@/api/artists";
import { showErrorToast, showSuccessToast } from "@/lib/toast";
import {
  Button,
  Card,
  Checkbox,
  CloseButton,
  cn,
  InputGroup,
  Label,
  Spinner,
  TextField,
} from "@heroui/react";
import { ArrowLeftIcon, DownloadIcon, SearchIcon, UserIcon } from "lucide-react";
import { useState } from "react";

function Thumbnail({
  src,
  alt,
  rounded,
}: {
  src?: string | null;
  alt: string;
  rounded?: boolean;
}) {
  const shape = rounded ? "rounded-full" : "rounded-md";
  if (!src) {
    return (
      <div
        className={cn(
          "bg-default flex h-10 w-10 shrink-0 items-center justify-center",
          shape,
        )}
      >
        <UserIcon className="text-muted h-4 w-4" />
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      referrerPolicy="no-referrer"
      className={cn("h-10 w-10 shrink-0 object-cover", shape)}
    />
  );
}

type ReleaseGroupProps = {
  title: string;
  releases: ArtistRelease[];
  selected: Set<string>;
  onToggle: (url: string, selected: boolean) => void;
  onToggleAll: (urls: string[], selected: boolean) => void;
};

function ReleaseGroup({
  title,
  releases,
  selected,
  onToggle,
  onToggleAll,
}: ReleaseGroupProps) {
  if (releases.length === 0) return null;

  const urls = releases.map((r) => r.url);
  const selectedCount = urls.filter((u) => selected.has(u)).length;
  const allSelected = selectedCount === urls.length;

  return (
    <div className="flex flex-col gap-1">
      <Checkbox
        isSelected={allSelected}
        isIndeterminate={selectedCount > 0 && !allSelected}
        onChange={(value) => onToggleAll(urls, value)}
      >
        <Checkbox.Content>
          <Checkbox.Control>
            <Checkbox.Indicator />
          </Checkbox.Control>
          <Label className="text-muted text-xs tracking-wider uppercase">
            {title} ({selectedCount}/{urls.length})
          </Label>
        </Checkbox.Content>
      </Checkbox>
      <ul className="flex flex-col">
        {releases.map((release) => (
          <li key={release.url}>
            <Checkbox
              className="w-full py-1"
              isSelected={selected.has(release.url)}
              onChange={(value) => onToggle(release.url, value)}
            >
              <Checkbox.Content className="w-full min-w-0">
                <Checkbox.Control>
                  <Checkbox.Indicator />
                </Checkbox.Control>
                <Thumbnail src={release.thumbnail_url} alt="" />
                <Label className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate">{release.title}</span>
                  <span className="text-muted text-xs">
                    {[release.type, release.year].filter(Boolean).join(" · ")}
                  </span>
                </Label>
              </Checkbox.Content>
            </Checkbox>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ArtistSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ArtistSummary[] | null>(null);
  const [artist, setArtist] = useState<ArtistReleases | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState<"search" | "releases" | null>(null);
  const [queueing, setQueueing] = useState(false);

  const handleSearch = async () => {
    const q = query.trim();
    if (!q || loading) return;
    setLoading("search");
    setArtist(null);
    try {
      setResults(await searchArtists(q));
    } catch (e) {
      showErrorToast("Search failed", (e as Error).message);
    } finally {
      setLoading(null);
    }
  };

  const handlePickArtist = async (match: ArtistSummary) => {
    setLoading("releases");
    try {
      const releases = await getArtistReleases(match.channel_id);
      setArtist(releases);
      setSelected(
        new Set([...releases.albums, ...releases.singles].map((r) => r.url)),
      );
    } catch (e) {
      showErrorToast("Failed to load releases", (e as Error).message);
    } finally {
      setLoading(null);
    }
  };

  const toggle = (url: string, value: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (value) next.add(url);
      else next.delete(url);
      return next;
    });
  };

  const toggleAll = (urls: string[], value: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const url of urls) {
        if (value) next.add(url);
        else next.delete(url);
      }
      return next;
    });
  };

  const handleDownload = async () => {
    if (!artist || selected.size === 0) return;
    // Keep artist page order (albums first, then singles)
    const urls = [...artist.albums, ...artist.singles]
      .map((r) => r.url)
      .filter((u) => selected.has(u));

    setQueueing(true);
    const result = await queueArtistReleases(urls);
    setQueueing(false);

    if (!result.success) {
      showErrorToast("Failed to queue downloads", result.error);
      return;
    }
    const skipped =
      result.skipped > 0 ? ` (${result.skipped} skipped: queue full)` : "";
    showSuccessToast(
      `Queued ${result.queued} releases`,
      `${artist.name}${skipped}`,
    );
    setArtist(null);
  };

  return (
    <section className="mb-8 flex flex-col gap-4">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSearch();
        }}
      >
        <TextField
          value={query}
          onChange={setQuery}
          fullWidth
          aria-label="Artist name"
          className="min-w-0 flex-1"
        >
          <InputGroup className="min-w-0">
            <InputGroup.Prefix>
              <SearchIcon className="text-muted h-4 w-4" />
            </InputGroup.Prefix>
            <InputGroup.Input
              className="w-full min-w-0"
              placeholder="Artist name"
            />
            {query !== "" && (
              <InputGroup.Suffix>
                <CloseButton aria-label="Clear" onPress={() => setQuery("")} />
              </InputGroup.Suffix>
            )}
          </InputGroup>
        </TextField>
        <Button
          type="submit"
          variant="primary"
          className="shrink-0"
          isDisabled={!query.trim() || loading !== null}
        >
          {loading === "search" ? (
            <Spinner size="sm" color="current" />
          ) : (
            <SearchIcon className="h-4 w-4" />
          )}
          Search
        </Button>
      </form>

      {loading === "releases" && (
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      )}

      {!artist && loading !== "releases" && results !== null && (
        <Card>
          <Card.Content>
            {results.length === 0 ? (
              <p className="text-muted py-2 text-sm">No artists found.</p>
            ) : (
              <ul className="flex flex-col">
                {results.map((match) => (
                  <li key={match.channel_id}>
                    <button
                      type="button"
                      onClick={() => void handlePickArtist(match)}
                      className="hover:bg-default flex w-full items-center gap-3 rounded-lg p-2 text-left transition-colors"
                    >
                      <Thumbnail src={match.thumbnail_url} alt="" rounded />
                      <span className="truncate font-medium">{match.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card.Content>
        </Card>
      )}

      {artist && (
        <Card>
          <Card.Header>
            <div className="flex w-full items-center gap-3">
              <Button
                isIconOnly
                size="sm"
                variant="ghost"
                aria-label="Back to results"
                onPress={() => setArtist(null)}
              >
                <ArrowLeftIcon className="h-4 w-4" />
              </Button>
              <Thumbnail src={artist.thumbnail_url} alt="" rounded />
              <span className="min-w-0 flex-1 truncate text-lg font-semibold">
                {artist.name}
              </span>
              <Button
                variant="primary"
                className="shrink-0"
                onPress={() => void handleDownload()}
                isDisabled={selected.size === 0 || queueing}
              >
                {queueing ? (
                  <Spinner size="sm" color="current" />
                ) : (
                  <DownloadIcon className="h-4 w-4" />
                )}
                Download {selected.size}
              </Button>
            </div>
          </Card.Header>
          <Card.Content className="flex flex-col gap-4">
            {artist.albums.length + artist.singles.length === 0 ? (
              <p className="text-muted text-sm">No releases found.</p>
            ) : (
              <>
                <ReleaseGroup
                  title="Albums"
                  releases={artist.albums}
                  selected={selected}
                  onToggle={toggle}
                  onToggleAll={toggleAll}
                />
                <ReleaseGroup
                  title="Singles & EPs"
                  releases={artist.singles}
                  selected={selected}
                  onToggle={toggle}
                  onToggleAll={toggleAll}
                />
              </>
            )}
          </Card.Content>
        </Card>
      )}
    </section>
  );
}

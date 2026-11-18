import { UrlInput } from "@/components/common/url-input";
import { ArtistSearch } from "@/features/artists/artist-search";
import { LogsPanel } from "@/features/logs/logs-panel";
import { JobsPanel } from "@/features/jobs/jobs-panel";
import { useJobs } from "@/features/jobs/jobs-context";
import { isValidUrl } from "@/lib/url";
import { Button, InputGroup, NumberField, Tabs } from "@heroui/react";
import { DownloadIcon, HashIcon } from "lucide-react";
import { memo, useState } from "react";

const DEFAULT_MAX_ITEMS = 100;

interface DownloadFormProps {
  onDownload: (url: string, maxItems: number) => Promise<void>;
}

const DownloadForm = memo(function DownloadForm({
  onDownload,
}: DownloadFormProps) {
  const [url, setUrl] = useState("");
  const [maxItems, setMaxItems] = useState(DEFAULT_MAX_ITEMS);

  const canDownload = isValidUrl(url);

  const handleDownload = async () => {
    if (canDownload) {
      await onDownload(url, maxItems);
      setUrl("");
    }
  };

  return (
    <section className="mb-8 flex gap-2">
      <div className="min-w-0 flex-1">
        <UrlInput value={url} onChange={setUrl} />
      </div>
      <NumberField
        className="w-24"
        aria-label="Max number of tracks to download"
        value={maxItems}
        onChange={(value) => {
          if (!Number.isNaN(value) && value >= 1) setMaxItems(value);
        }}
        minValue={1}
        maxValue={10000}
      >
        <InputGroup>
          <InputGroup.Prefix>
            <HashIcon className="text-muted h-4 w-4" />
          </InputGroup.Prefix>
          <InputGroup.Input
            placeholder="Max"
            className="w-full min-w-0 font-mono"
          />
        </InputGroup>
      </NumberField>
      <Button
        variant="primary"
        className="shrink-0"
        onPress={handleDownload}
        isDisabled={!canDownload}
      >
        <DownloadIcon className="h-4 w-4" />
        Download
      </Button>
    </section>
  );
});

export function JobsPage() {
  const { jobs, isLoading, startJob, cancelJob, deleteJob } = useJobs();

  const handleDeleteJob = async (jobId: string) => {
    await deleteJob(jobId);
  };

  return (
    <>
      {/* Page Title */}
      <h1 className="text-foreground mb-6 text-2xl font-bold">Downloads</h1>

      {/* Download by URL or by artist */}
      <Tabs defaultSelectedKey="url">
        <Tabs.ListContainer className="mb-4">
          <Tabs.List aria-label="Download source">
            <Tabs.Tab id="url">
              URL
              <Tabs.Indicator />
            </Tabs.Tab>
            <Tabs.Tab id="artist">
              Artist
              <Tabs.Indicator />
            </Tabs.Tab>
          </Tabs.List>
        </Tabs.ListContainer>
        <Tabs.Panel id="url">
          <DownloadForm onDownload={startJob} />
        </Tabs.Panel>
        <Tabs.Panel id="artist">
          <ArtistSearch />
        </Tabs.Panel>
      </Tabs>

      {/* Downloads Panels */}
      <section className="flex flex-col gap-6">
        <JobsPanel
          jobs={jobs}
          isLoading={isLoading}
          onCancel={cancelJob}
          onDelete={handleDeleteJob}
        />
        <LogsPanel jobs={jobs} />
      </section>
    </>
  );
}

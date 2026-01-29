import { ConsolePanel } from "@/features/console/console-panel";
import { DownloadsPanel } from "@/features/downloads/downloads-panel";
import { UrlInput } from "@/features/downloads/url-input";
import { useJobs } from "@/features/downloads/use-jobs";
import { isValidUrl } from "@/lib/url";
import { Button, NumberInput, Tooltip } from "@heroui/react";
import { Download, Hash } from "lucide-react";
import { useState } from "react";

const DEFAULT_MAX_ITEMS = 100;

export function DownloadsPage() {
  const [url, setUrl] = useState("");
  const [maxItems, setMaxItems] = useState(DEFAULT_MAX_ITEMS);
  const { jobs, startJob, cancelJob, deleteJob } = useJobs();

  const canDownload = isValidUrl(url);

  const handleDownload = async () => {
    if (canDownload) {
      await startJob(url, maxItems);
      setUrl("");
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    await deleteJob(jobId);
  };

  return (
    <>
      {/* Page Title */}
      <h1 className="text-foreground mb-5 text-2xl font-bold">Downloads</h1>

      {/* URL Input Section */}
      <section className="mb-6 flex gap-2">
        <div className="flex-1">
          <UrlInput value={url} onChange={setUrl} />
        </div>
        <Tooltip content="Max number of tracks to download" offset={14}>
          <NumberInput
            hideStepper
            variant="faded"
            value={maxItems}
            onValueChange={setMaxItems}
            minValue={1}
            maxValue={1000}
            radius="lg"
            fullWidth={false}
            formatOptions={{
              useGrouping: false,
            }}
            placeholder="Max"
            startContent={<Hash className="text-foreground-400 h-4 w-4" />}
            className="w-20 font-mono"
          />
        </Tooltip>
        <Button
          color="primary"
          radius="lg"
          variant={canDownload ? "shadow" : "solid"}
          className="shadow-primary-100/50"
          onPress={handleDownload}
          isDisabled={!canDownload}
          startContent={<Download className="h-4 w-4" />}
        >
          Download
        </Button>
      </section>

      {/* Downloads Panels */}
      <section className="mb-6 flex flex-col gap-4">
        <DownloadsPanel
          jobs={jobs}
          onCancel={cancelJob}
          onDelete={handleDeleteJob}
        />
        <ConsolePanel jobs={jobs} />
      </section>
    </>
  );
}

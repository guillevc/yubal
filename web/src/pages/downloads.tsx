import { Button, NumberInput, Tooltip } from "@heroui/react";
import { Download, Hash } from "lucide-react";
import { useState } from "react";
import { ConsolePanel } from "../components/console-panel";
import { DownloadsPanel } from "../components/downloads-panel";
import { BlurFade } from "../components/magicui/blur-fade";
import { UrlInput } from "../components/url-input";
import { useJobs } from "../hooks/use-jobs";
import { isValidUrl } from "../lib/url";

const DEFAULT_MAX_ITEMS = 50;

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
      <BlurFade delay={0.025} direction="up">
        <h1 className="text-foreground mb-6 text-2xl font-bold">Downloads</h1>
      </BlurFade>

      {/* URL Input Section */}
      <BlurFade delay={0.05} direction="up">
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
              maxValue={10000}
              radius="lg"
              fullWidth={false}
              startContent={<Hash className="text-foreground-400 h-4 w-4" />}
              className="w-24 font-mono"
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
      </BlurFade>

      {/* Downloads Panels */}
      <BlurFade delay={0.1} direction="up">
        <section className="mb-6 flex flex-col gap-4">
          <DownloadsPanel
            jobs={jobs}
            onCancel={cancelJob}
            onDelete={handleDeleteJob}
          />
          <ConsolePanel jobs={jobs} />
        </section>
      </BlurFade>
    </>
  );
}

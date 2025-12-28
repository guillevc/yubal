import { useState } from "react";
import { Button } from "@heroui/react";
import { Download } from "lucide-react";
import { UrlInput } from "./components/UrlInput";
import { isValidUrl } from "./utils/url";
import { ConsolePanel } from "./components/ConsolePanel";
import { DownloadsPanel } from "./components/DownloadsPanel";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { useJobs } from "./hooks/useJobs";

export default function App() {
  const [url, setUrl] = useState("");
  const { jobs, logs, startJob, cancelJob, deleteJob } = useJobs();

  const canSync = isValidUrl(url);

  const handleSync = async () => {
    if (canSync) {
      await startJob(url);
      setUrl("");
    }
  };

  const handleDelete = async (jobId: string) => {
    await deleteJob(jobId);
  };

  return (
    <div className="bg-background flex min-h-screen flex-col justify-center px-4 py-6">
      <main className="mx-auto w-full max-w-2xl">
        <Header />

        {/* URL Input Section */}
        <section className="mb-6 flex gap-2">
          <div className="flex-1">
            <UrlInput value={url} onChange={setUrl} />
          </div>
          <Button
            color="primary"
            size="md"
            onPress={handleSync}
            isDisabled={!canSync}
            startContent={<Download className="h-4 w-4" />}
          >
            Download
          </Button>
        </section>

        {/* Stacked Panels */}
        <section className="mb-6 flex flex-col gap-4">
          <DownloadsPanel
            jobs={jobs}
            onCancel={cancelJob}
            onDelete={handleDelete}
          />
          <ConsolePanel logs={logs} jobs={jobs} />
        </section>

        <Footer />
      </main>
    </div>
  );
}

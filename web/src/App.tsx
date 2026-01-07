import { Button } from "@heroui/react";
import { Download } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { ConsolePanel } from "./components/console-panel";
import { DownloadsPanel } from "./components/downloads-panel";
import { Footer } from "./components/layout/footer";
import { Header } from "./components/layout/header";
import { UrlInput } from "./components/url-input";
import { useJobs } from "./hooks/use-jobs";
import { isValidUrl } from "./lib/url";

// Shared spring transition for appearance animations
const appearTransition = {
  type: "spring" as const,
  bounce: 0.15,
  duration: 0.5,
};

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
      <div className="mx-auto w-full max-w-2xl">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={appearTransition}
        >
          <Header />
        </motion.div>

        {/* URL Input Section */}
        <motion.section
          className="mb-6 flex gap-2"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...appearTransition, delay: 0.05 }}
        >
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
        </motion.section>

        {/* Stacked Panels */}
        <motion.section
          className="mb-6 flex flex-col gap-4"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...appearTransition, delay: 0.1 }}
        >
          <DownloadsPanel
            jobs={jobs}
            onCancel={cancelJob}
            onDelete={handleDelete}
          />
          <ConsolePanel logs={logs} jobs={jobs} />
        </motion.section>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ ...appearTransition, delay: 0.15 }}
        >
          <Footer />
        </motion.div>
      </div>
    </div>
  );
}

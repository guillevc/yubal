import { Download } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import type { Job } from "../api/jobs";
import { JobCard } from "./JobCard";
import { Panel, PanelHeader, PanelContent } from "./ui/Panel";

interface DownloadsPanelProps {
  jobs: Job[];
  onCancel: (jobId: string) => void;
  onDelete: (jobId: string) => void;
}

export function DownloadsPanel({
  jobs,
  onCancel,
  onDelete,
}: DownloadsPanelProps) {
  const isActive = (status: string) =>
    ["pending", "fetching_info", "downloading", "importing"].includes(status);

  return (
    <Panel>
      <PanelHeader
        leadingIcon={<Download size={18} />}
        badge={
          jobs.length > 0 && (
            <span className="text-foreground-400 font-mono text-xs">
              {jobs.length}
            </span>
          )
        }>
        Downloads
      </PanelHeader>
      <PanelContent className="space-y-2">
        {jobs.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-foreground-400 font-mono text-xs">
              No downloads yet
            </p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {jobs.map((job) => (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                transition={{ duration: 0.2 }}
              >
                <JobCard
                  job={job}
                  onCancel={isActive(job.status) ? onCancel : undefined}
                  onDelete={!isActive(job.status) ? onDelete : undefined}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </PanelContent>
    </Panel>
  );
}

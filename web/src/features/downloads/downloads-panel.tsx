import { Download, Inbox } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { Job } from "@/api/jobs";
import { EmptyState } from "@/components/common/empty-state";
import { Panel, PanelContent, PanelHeader } from "@/components/common/panel";
import { isActive } from "@/lib/job-status";
import { JobCard } from "./job-card";

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
  return (
    <Panel>
      <PanelHeader
        leadingIcon={<Download size={18} />}
        badge={
          jobs.length > 0 && (
            <span className="text-foreground-400 font-mono text-xs">
              ({jobs.length})
            </span>
          )
        }
      >
        Downloads
      </PanelHeader>
      <PanelContent height="h-[400px]" className="space-y-2">
        {jobs.length === 0 ? (
          <EmptyState icon={Inbox} title="No downloads yet" />
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

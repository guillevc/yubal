import { ChevronDown, Terminal } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import type { Job, JobLog } from "../hooks/useJobs";
import { useLocalStorage } from "../hooks/useLocalStorage";
import { isActive } from "../lib/job-status";
import { Panel, PanelContent, PanelHeader } from "./common/Panel";

interface ConsolePanelProps {
  logs: JobLog[];
  jobs: Job[];
}

function StatusIndicator({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-foreground-500",
    fetching_info: "bg-foreground",
    downloading: "bg-primary",
    importing: "bg-secondary",
    completed: "bg-success",
    failed: "bg-danger",
    cancelled: "bg-warning",
  };
  const color = colors[status] ?? "bg-foreground-500";
  return (
    <span
      className={`inline-flex h-2 w-2 animate-pulse rounded-full ${color}`}
    />
  );
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function getTimestamp(): string {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, "0");
  const m = String(now.getMinutes()).padStart(2, "0");
  const s = String(now.getSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

export function ConsolePanel({ logs, jobs }: ConsolePanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const currentJob = jobs.find((j) => isActive(j.status));
  const hasActiveJobs = !!currentJob;
  const [currentTime, setCurrentTime] = useState(getTimestamp());
  const [isExpanded, setIsExpanded] = useLocalStorage(
    "yubal-console-expanded",
    false,
  );

  const statusColors: Record<string, string> = {
    pending: "text-foreground-500",
    fetching_info: "text-foreground",
    downloading: "text-primary",
    importing: "text-secondary",
    completed: "text-success",
    failed: "text-danger",
    cancelled: "text-warning",
  };

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  // Update blinking cursor timestamp
  useEffect(() => {
    if (hasActiveJobs) {
      const interval = setInterval(() => {
        setCurrentTime(getTimestamp());
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [hasActiveJobs]);

  const panelHeader = (
    <PanelHeader
      className="hover:bg-content2 cursor-pointer select-none"
      onClick={() => setIsExpanded(!isExpanded)}
      leadingIcon={<Terminal size={18} />}
      badge={currentJob && <StatusIndicator status={currentJob.status} />}
      trailingIcon={
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="flex items-center justify-center"
        >
          <ChevronDown size={18} />
        </motion.div>
      }
    >
      console
    </PanelHeader>
  );

  const panelContent = (
    <PanelContent
      ref={containerRef}
      className="space-y-1 p-4 font-mono text-xs"
    >
      {logs.length === 0 ? (
        <div className="flex h-full items-center justify-center">
          <span className="text-foreground-400">Awaiting YouTube URL...</span>
        </div>
      ) : (
        <AnimatePresence initial={false}>
          {logs.map((log, idx) => (
            <motion.div
              key={`${log.timestamp}-${idx}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-2"
            >
              <span className="text-foreground-400 shrink-0">
                [{formatTime(log.timestamp)}]
              </span>
              <span className={statusColors[log.status] ?? "text-foreground"}>
                {log.message}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      )}
      {/* Blinking cursor when active */}
      {hasActiveJobs && (
        <div className="flex gap-2">
          <span className="text-foreground-400">[{currentTime}]</span>
          <span className="text-foreground-500 animate-pulse">&#9608;</span>
        </div>
      )}
    </PanelContent>
  );

  return (
    <Panel>
      {panelHeader}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            {panelContent}
          </motion.div>
        )}
      </AnimatePresence>
    </Panel>
  );
}

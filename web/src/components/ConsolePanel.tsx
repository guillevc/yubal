import { useEffect, useRef, useState } from "react";
import { Terminal } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { LogEntry, ProgressStep } from "../hooks/useJobs";
import { Panel, PanelHeader, PanelTitle, PanelContent } from "./Panel";

interface ConsolePanelProps {
  logs: LogEntry[];
  status: ProgressStep;
}

const stepColors: Record<ProgressStep, string> = {
  idle: "text-foreground-400",
  pending: "text-foreground-500",
  fetching_info: "text-foreground-500",
  downloading: "text-primary",
  importing: "text-secondary",
  complete: "text-success",
  error: "text-danger",
  cancelled: "text-warning",
};

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
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

export function ConsolePanel({ logs, status }: ConsolePanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isActive =
    status !== "idle" &&
    status !== "complete" &&
    status !== "error" &&
    status !== "cancelled";
  const [currentTime, setCurrentTime] = useState(getTimestamp());

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  // Update blinking cursor timestamp
  useEffect(() => {
    if (isActive) {
      const interval = setInterval(() => {
        setCurrentTime(getTimestamp());
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isActive]);

  return (
    <Panel>
      <PanelHeader>
        <PanelTitle icon={<Terminal />}>console</PanelTitle>
      </PanelHeader>
      <PanelContent
        ref={containerRef}
        className="space-y-1 p-4 font-mono text-xs"
      >
        {logs.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <span className="text-foreground-400/50">
              Awaiting YouTube URL...
            </span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {logs.map((log) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-2"
              >
                <span className="text-foreground-400/50 shrink-0">
                  [{formatTime(log.timestamp)}]
                </span>
                <span className={stepColors[log.step]}>{log.message}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
        {/* Blinking cursor when active */}
        {isActive && (
          <div className="flex gap-2">
            <span className="text-foreground-400/50">[{currentTime}]</span>
            <span className="text-foreground-500 animate-pulse">&#9608;</span>
          </div>
        )}
      </PanelContent>
    </Panel>
  );
}

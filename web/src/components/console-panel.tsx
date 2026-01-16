import { ChevronDown, Terminal } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef } from "react";
import type { components } from "../api/schema";
import { useLocalStorage } from "../hooks/use-local-storage";
import { useLogs } from "../hooks/use-logs";
import { Panel, PanelContent, PanelHeader } from "./common/panel";

type LogEntry = components["schemas"]["LogEntry"];

/** Status icons for result messages */
const STATUS_ICONS = {
  success: "✓",
  skipped: "○",
  failed: "✗",
} as const satisfies Record<NonNullable<LogEntry["status"]>, string>;

/** Status colors using Tailwind classes */
const STATUS_COLORS = {
  success: "text-success",
  skipped: "text-warning",
  failed: "text-danger",
} as const satisfies Record<NonNullable<LogEntry["status"]>, string>;

/**
 * Renders a single log entry with appropriate styling based on entry_type.
 * Uses discriminated union pattern matching for exhaustive type safety.
 */
function LogLine({ entry }: { entry: LogEntry }) {
  switch (entry.entry_type) {
    case "header":
      // Section header - prominent visual separator
      return (
        <div className="mt-2 first:mt-0">
          <span className="text-secondary font-bold">
            {"═".repeat(15)} {entry.header} {"═".repeat(15)}
          </span>
        </div>
      );

    case "phase":
      // Phase headers - cyan/primary bold with separator
      return (
        <div>
          <span className="text-primary font-bold">
            ━━ Phase {entry.phase_num}: {entry.phase} {"━".repeat(20)}
          </span>
        </div>
      );

    case "stats": {
      // Stats summary - colored counts (mutually exclusive: download vs extraction)
      const { stats } = entry;
      if (!stats) return <div>{entry.message}</div>;

      // Extraction stats (has 'extracted' field)
      if (stats.extracted !== undefined) {
        return (
          <div>
            <span className="text-success">✓ </span>
            <span className="text-success">{stats.extracted} extracted</span>
            <span>, </span>
            <span className="text-warning">{stats.skipped ?? 0} skipped</span>
            <span>, </span>
            <span className="text-foreground-400">
              {stats.unavailable ?? 0} unavailable
            </span>
          </div>
        );
      }

      // Download stats (has 'success' field)
      return (
        <div>
          <span className="text-success">✓ </span>
          <span className="text-success">{stats.success ?? 0} success</span>
          <span>, </span>
          <span className="text-warning">{stats.skipped ?? 0} skipped</span>
          <span>, </span>
          <span className="text-danger">{stats.failed ?? 0} failed</span>
        </div>
      );
    }

    case "progress":
      // Progress tracking - dimmed counter with optional download icon
      return (
        <div>
          {entry.event_type === "track_download" && (
            <span className="text-primary">↓ </span>
          )}
          <span className="text-foreground-400">
            [{entry.current}/{entry.total}]{" "}
          </span>
          <span>{entry.message}</span>
        </div>
      );

    case "status": {
      // Status messages - icon prefix with appropriate color
      const status = entry.status;
      if (!status) return <div>{entry.message}</div>;
      return (
        <div>
          <span className={STATUS_COLORS[status]}>{STATUS_ICONS[status]} </span>
          <span>{entry.message}</span>
        </div>
      );
    }

    case "file":
      // File operations - dimmed
      return <div className="text-foreground-400">{entry.message}</div>;

    case "default":
    default:
      // Default - plain text
      return <div>{entry.message}</div>;
  }
}

export function ConsolePanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { lines, isConnected } = useLogs();
  const [isExpanded, setIsExpanded] = useLocalStorage(
    "yubal-console-expanded",
    false,
  );

  // Auto-scroll to bottom when new lines arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [lines]);

  const panelHeader = (
    <PanelHeader
      className="hover:bg-content2 cursor-pointer select-none"
      onClick={() => setIsExpanded(!isExpanded)}
      leadingIcon={<Terminal size={18} />}
      badge={
        !isConnected && (
          <span className="text-warning text-xs">disconnected</span>
        )
      }
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
      className="console-logs space-y-0.5 p-4 font-mono text-xs"
    >
      {lines.length === 0 ? (
        <div className="flex h-full items-center justify-center">
          <span className="text-foreground-400">Awaiting YouTube URL...</span>
        </div>
      ) : (
        <AnimatePresence initial={false}>
          {lines.map((line, idx) => {
            try {
              const entry: LogEntry = JSON.parse(line);
              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <LogLine entry={entry} />
                </motion.div>
              );
            } catch {
              // Fallback for non-JSON lines (startup logs, errors, etc.)
              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-foreground-400"
                >
                  {line}
                </motion.div>
              );
            }
          })}
        </AnimatePresence>
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

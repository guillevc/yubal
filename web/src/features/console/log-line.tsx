import type { components } from "@/api/schema";
import { AlertTriangle, ArrowDown, Check, Circle, X } from "lucide-react";

type LogEntry = components["schemas"]["LogEntry"];
type LogStatus = NonNullable<LogEntry["status"]>;
type SkippedByReason = NonNullable<
  components["schemas"]["LogStats"]["skipped_by_reason"]
>;

/** Common icon size class for consistency */
const ICON_CLASS = "h-4 w-4 shrink-0";

/** Status icon configuration mapping status to icon component and color */
const STATUS_CONFIG: Record<LogStatus, { icon: typeof Check; color: string }> =
  {
    success: { icon: Check, color: "text-success" },
    skipped: { icon: Circle, color: "text-warning" },
    failed: { icon: X, color: "text-danger" },
  };

/** Header log - prominent visual separator */
function HeaderLog({ header }: { header: string }) {
  return (
    <div className="mt-2 first:mt-0">
      <span className="text-secondary font-bold">
        {"═".repeat(15)} {header} {"═".repeat(15)}
      </span>
    </div>
  );
}

/** Phase log - cyan/primary bold with separator */
function PhaseLog({ phaseNum, phase }: { phaseNum: number; phase: string }) {
  return (
    <div>
      <span className="text-primary font-bold">
        ━━ Phase {phaseNum}: {phase} {"━".repeat(20)}
      </span>
    </div>
  );
}

/** Human-readable labels for skip reasons */
const SKIP_REASON_LABELS: Record<string, string> = {
  file_exists: "file exists",
  unsupported_video_type: "unsupported",
  no_video_id: "unavailable",
};

/** Format skip reasons into a human-readable summary string */
function formatSkippedMessage(skippedByReason: SkippedByReason): string {
  const total = Object.values(skippedByReason).reduce((a, b) => a + b, 0);
  if (total === 0) return "0 skipped";

  const breakdown = Object.entries(skippedByReason)
    .filter(([, count]) => count > 0)
    .map(
      ([reason, count]) =>
        `${count} ${SKIP_REASON_LABELS[reason] || reason.replace(/_/g, " ")}`,
    )
    .join(", ");

  return breakdown ? `${total} skipped (${breakdown})` : `${total} skipped`;
}

/** Extraction stats display */
function ExtractionStatsLog({
  success,
  skippedByReason,
}: {
  success: number;
  skippedByReason: SkippedByReason;
}) {
  // Extraction-specific: show unsupported and unavailable separately
  const skipped = skippedByReason.unsupported_video_type ?? 0;
  const unavailable = skippedByReason.no_video_id ?? 0;

  return (
    <div className="flex items-center gap-1">
      <Check className={`${ICON_CLASS} text-success`} />
      <span className="text-success">{success} extracted</span>
      <span>,</span>
      <span className="text-warning">{skipped} skipped</span>
      <span>,</span>
      <span className="text-foreground-400">{unavailable} unavailable</span>
    </div>
  );
}

/** Download stats display */
function DownloadStatsLog({
  success,
  failed,
  skippedByReason,
}: {
  success: number;
  failed: number;
  skippedByReason: SkippedByReason;
}) {
  // Show warning icon if any tracks failed
  const hasIssues = failed > 0;
  const Icon = hasIssues ? AlertTriangle : Check;
  const iconColor = hasIssues ? "text-warning" : "text-success";

  return (
    <div className="flex items-center gap-1">
      <Icon className={`${ICON_CLASS} ${iconColor}`} />
      <span className="text-success">{success} success</span>
      <span>,</span>
      <span className="text-warning">
        {formatSkippedMessage(skippedByReason)}
      </span>
      <span>,</span>
      <span className="text-danger">{failed} failed</span>
    </div>
  );
}

/** Progress tracking display */
function ProgressLog({
  current,
  total,
  message,
  isDownload,
}: {
  current: number;
  total: number;
  message: string;
  isDownload: boolean;
}) {
  return (
    <div className="flex items-center gap-1">
      {isDownload && <ArrowDown className={`${ICON_CLASS} text-primary`} />}
      <span className="text-foreground-400">
        [{current}/{total}]
      </span>
      <span>{message}</span>
    </div>
  );
}

/** Status message display */
function StatusLog({
  status,
  message,
}: {
  status: LogStatus;
  message: string;
}) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  return (
    <div className="flex items-center gap-1">
      <Icon className={`${ICON_CLASS} ${config.color}`} />
      <span>{message}</span>
    </div>
  );
}

/** File operation display */
function FileLog({ message }: { message: string }) {
  return <div className="text-foreground-400">{message}</div>;
}

/** Level-based color mapping */
const LEVEL_COLORS: Record<string, string> = {
  WARNING: "text-warning",
  ERROR: "text-danger",
  CRITICAL: "text-danger",
};

/** Default/plain text display with level-based coloring */
function DefaultLog({ message, level }: { message: string; level?: string }) {
  const colorClass = level ? LEVEL_COLORS[level] : undefined;
  return <div className={colorClass}>{message}</div>;
}

/**
 * Renders a single log entry with appropriate styling based on entry_type.
 * Uses discriminated union pattern matching for exhaustive type safety.
 */
export function LogLine({ entry }: { entry: LogEntry }) {
  switch (entry.entry_type) {
    case "header":
      return <HeaderLog header={entry.header ?? ""} />;

    case "phase":
      return (
        <PhaseLog phaseNum={entry.phase_num ?? 0} phase={entry.phase ?? ""} />
      );

    case "stats": {
      const { stats } = entry;
      if (!stats) return <DefaultLog message={entry.message} />;

      const skippedByReason = stats.skipped_by_reason ?? {};

      // Use stats_type discriminator for clean type narrowing
      if (stats.stats_type === "extraction") {
        return (
          <ExtractionStatsLog
            success={stats.success ?? 0}
            skippedByReason={skippedByReason}
          />
        );
      }

      // Default to download stats (stats_type === "download")
      return (
        <DownloadStatsLog
          success={stats.success ?? 0}
          failed={stats.failed ?? 0}
          skippedByReason={skippedByReason}
        />
      );
    }

    case "progress":
      return (
        <ProgressLog
          current={entry.current ?? 0}
          total={entry.total ?? 0}
          message={entry.message}
          isDownload={entry.event_type === "track_download"}
        />
      );

    case "status": {
      const status = entry.status;
      if (!status) return <DefaultLog message={entry.message} />;
      return <StatusLog status={status} message={entry.message} />;
    }

    case "file":
      return <FileLog message={entry.message} />;

    case "default":
    default:
      return <DefaultLog message={entry.message} level={entry.level} />;
  }
}

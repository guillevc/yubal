import { ArrowDown, Check, Circle, X } from "lucide-react";
import type { components } from "../../api/schema";

type LogEntry = components["schemas"]["LogEntry"];
type LogStatus = NonNullable<LogEntry["status"]>;

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
export function HeaderLog({ header }: { header: string }) {
  return (
    <div className="mt-2 first:mt-0">
      <span className="text-secondary font-bold">
        {"═".repeat(15)} {header} {"═".repeat(15)}
      </span>
    </div>
  );
}

/** Phase log - cyan/primary bold with separator */
export function PhaseLog({
  phaseNum,
  phase,
}: {
  phaseNum: number;
  phase: string;
}) {
  return (
    <div>
      <span className="text-primary font-bold">
        ━━ Phase {phaseNum}: {phase} {"━".repeat(20)}
      </span>
    </div>
  );
}

/** Extraction stats display */
export function ExtractionStatsLog({
  extracted,
  skipped,
  unavailable,
}: {
  extracted: number;
  skipped: number;
  unavailable: number;
}) {
  return (
    <div className="flex items-center gap-1">
      <Check className={`${ICON_CLASS} text-success`} />
      <span className="text-success">{extracted} extracted</span>
      <span>,</span>
      <span className="text-warning">{skipped} skipped</span>
      <span>,</span>
      <span className="text-foreground-400">{unavailable} unavailable</span>
    </div>
  );
}

/** Download stats display */
export function DownloadStatsLog({
  success,
  skipped,
  failed,
}: {
  success: number;
  skipped: number;
  failed: number;
}) {
  return (
    <div className="flex items-center gap-1">
      <Check className={`${ICON_CLASS} text-success`} />
      <span className="text-success">{success} success</span>
      <span>,</span>
      <span className="text-warning">{skipped} skipped</span>
      <span>,</span>
      <span className="text-danger">{failed} failed</span>
    </div>
  );
}

/** Progress tracking display */
export function ProgressLog({
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
export function StatusLog({
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
export function FileLog({ message }: { message: string }) {
  return <div className="text-foreground-400">{message}</div>;
}

/** Default/plain text display */
export function DefaultLog({ message }: { message: string }) {
  return <div>{message}</div>;
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

      if (typeof stats.extracted === "number") {
        return (
          <ExtractionStatsLog
            extracted={stats.extracted}
            skipped={stats.skipped ?? 0}
            unavailable={stats.unavailable ?? 0}
          />
        );
      }

      return (
        <DownloadStatsLog
          success={stats.success ?? 0}
          skipped={stats.skipped ?? 0}
          failed={stats.failed ?? 0}
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
      return <DefaultLog message={entry.message} />;
  }
}

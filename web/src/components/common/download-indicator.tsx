import type { ReactElement } from "react";
import { CheckCircle2, XCircle } from "lucide-react";

export type DownloadStatus =
  | "idle"
  | "queued"
  | "downloading"
  | "completed"
  | "failed";

export function Spinner(): ReactElement {
  return (
    <span className="border-foreground-400/60 h-4 w-4 animate-spin rounded-full border-2 border-t-transparent" />
  );
}

export function ProgressRing({ progress }: { progress: number | null }): ReactElement {
  const size = 18;
  const stroke = 2.5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(100, progress ?? 0));
  const offset = circumference - (pct / 100) * circumference;

  return (
    <svg width={size} height={size} className="text-primary">
      <circle
        stroke="currentColor"
        strokeOpacity="0.2"
        strokeWidth={stroke}
        fill="transparent"
        r={radius}
        cx={size / 2}
        cy={size / 2}
      />
      <circle
        stroke="currentColor"
        strokeWidth={stroke}
        strokeLinecap="round"
        fill="transparent"
        r={radius}
        cx={size / 2}
        cy={size / 2}
        strokeDasharray={`${circumference} ${circumference}`}
        strokeDashoffset={offset}
      />
    </svg>
  );
}

export function DownloadStatusIcon({
  status,
  progress,
}: {
  status: DownloadStatus;
  progress: number | null;
}): ReactElement | null {
  if (status === "failed") {
    return <XCircle className="text-danger h-4 w-4" />;
  }
  if (status === "completed") {
    return <CheckCircle2 className="text-success h-4 w-4" />;
  }
  if (status === "downloading") {
    return <ProgressRing progress={progress} />;
  }
  if (status === "queued") {
    return <Spinner />;
  }
  return null;
}

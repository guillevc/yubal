import { Button, Chip, Progress } from "@heroui/react";
import { CheckCircle, Clock, Loader2, Trash2, X, XCircle } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import type { Job, JobStatus } from "../../api/jobs";
import { isActive, isFinished } from "../../lib/job-status";

interface JobCardProps {
  job: Job;
  onCancel?: (jobId: string) => void;
  onDelete?: (jobId: string) => void;
}

const STATUS_ICON_CLASS = "h-4 w-4";
const STATUS_CONFIG: Record<
  JobStatus,
  { icon: typeof Clock; color: string; spin?: boolean }
> = {
  pending: { icon: Clock, color: "text-foreground-400" },
  fetching_info: { icon: Loader2, color: "text-foreground-500", spin: true },
  downloading: { icon: Loader2, color: "text-primary", spin: true },
  importing: { icon: Loader2, color: "text-secondary", spin: true },
  completed: { icon: CheckCircle, color: "text-success" },
  failed: { icon: XCircle, color: "text-danger" },
  cancelled: { icon: X, color: "text-warning" },
};

const PROGRESS_COLORS: Record<
  JobStatus,
  "default" | "primary" | "secondary" | "success" | "warning" | "danger"
> = {
  pending: "default",
  fetching_info: "default",
  downloading: "primary",
  importing: "secondary",
  completed: "success",
  failed: "danger",
  cancelled: "warning",
};

function StatusIcon({ status }: { status: JobStatus }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <Icon
      className={`${STATUS_ICON_CLASS} ${config.color} ${config.spin ? "animate-spin" : ""}`}
    />
  );
}

function MetadataChip({ children }: { children: React.ReactNode }) {
  return (
    <Chip size="sm" variant="faded" className="text-foreground-500">
      {children}
    </Chip>
  );
}

function Thumbnail({ url, status }: { url: string | null; status: JobStatus }) {
  if (url) {
    return (
      <div className="relative shrink-0">
        <img src={url} alt="" className="h-16 w-16 rounded object-cover" />
        <div className="bg-content2/80 absolute right-0.5 bottom-0.5 rounded-full p-0.5">
          <StatusIcon status={status} />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-content3 flex h-16 w-16 shrink-0 items-center justify-center rounded">
      <StatusIcon status={status} />
    </div>
  );
}

function AlbumInfo({
  title,
  artist,
  year,
  trackCount,
  audioCodec,
  audioBitrate,
  showBitrate,
}: {
  title: string;
  artist: string | null;
  year: number | null;
  trackCount: number | null;
  audioCodec: string | null;
  audioBitrate: number | null;
  showBitrate: boolean;
}) {
  return (
    <>
      <div className="flex min-w-0 items-baseline gap-1 text-sm">
        <span className="text-foreground truncate">{title}</span>
        {year && <span className="text-foreground-500 shrink-0">({year})</span>}
      </div>
      <p className="text-foreground-500 mb-1 min-w-0 truncate text-xs">
        {artist}
      </p>
      <div className="flex items-center gap-1">
        {trackCount && <MetadataChip>{trackCount} tracks</MetadataChip>}
        {audioCodec && (
          <MetadataChip>
            <span className="uppercase">{audioCodec}</span>
          </MetadataChip>
        )}
        {showBitrate && audioBitrate && (
          <MetadataChip>{audioBitrate}kbps</MetadataChip>
        )}
      </div>
    </>
  );
}

export function JobCard({ job, onCancel, onDelete }: JobCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const isRunning = isActive(job.status);
  const isJobFinished = isFinished(job.status);

  const { album_info } = job;

  return (
    <div
      className={`bg-content2 rounded-lg border px-3 py-2.5 transition-colors ${
        job.status === "cancelled"
          ? "border-divider opacity-50"
          : "border-divider"
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex items-center gap-3">
        <Thumbnail
          url={album_info?.thumbnail_url ?? null}
          status={job.status}
        />

        <div className="min-w-0 flex-1 font-mono">
          {album_info?.title ? (
            <AlbumInfo
              title={album_info.title}
              artist={album_info.artist ?? null}
              year={album_info.year ?? null}
              trackCount={album_info.track_count ?? null}
              audioCodec={album_info.audio_codec ?? null}
              audioBitrate={album_info.audio_bitrate ?? null}
              showBitrate={isJobFinished}
            />
          ) : (
            <p className="text-foreground-500 truncate text-xs">{job.url}</p>
          )}
        </div>

        {isRunning && onCancel && (
          <Button
            variant="light"
            size="sm"
            isIconOnly
            className="text-foreground-500 hover:text-danger h-7 w-7 shrink-0"
            onPress={() => onCancel(job.id)}
          >
            <X className="h-4 w-4" />
          </Button>
        )}

        {isJobFinished && onDelete && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{
              opacity: isHovered ? 1 : 0,
              scale: isHovered ? 1 : 0.8,
            }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
          >
            <Button
              variant="light"
              size="sm"
              isIconOnly
              className="text-foreground-500 hover:text-danger h-7 w-7 shrink-0"
              onPress={() => onDelete(job.id)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </motion.div>
        )}
      </div>

      {isRunning && (
        <div className="mt-2 flex items-center gap-2">
          <Progress
            value={job.progress}
            size="sm"
            color={PROGRESS_COLORS[job.status]}
            className="flex-1"
            classNames={{
              indicator: "transition-all duration-500 ease-out",
            }}
            aria-label="Job progress"
          />
          <span className="text-foreground-500 w-8 text-right font-mono text-xs">
            {Math.round(job.progress)}%
          </span>
        </div>
      )}
    </div>
  );
}

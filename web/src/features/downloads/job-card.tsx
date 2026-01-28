import { Button, Chip, Image, Progress } from "@heroui/react";
import {
  CheckCircle,
  CircleAlert,
  Clock,
  ExternalLink,
  Loader2,
  Trash2,
  X,
  XCircle,
} from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import type { Job, JobStatus } from "@/api/jobs";
import { isActive, isFinished } from "@/lib/job-status";

interface JobCardProps {
  job: Job;
  onCancel?: (jobId: string) => void;
  onDelete?: (jobId: string) => void;
}

type ProgressColor =
  | "default"
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "danger";

const STATUS_CONFIG: Record<
  JobStatus,
  {
    icon: typeof Clock;
    color: string;
    progressColor: ProgressColor;
    spin?: boolean;
  }
> = {
  pending: {
    icon: Clock,
    color: "text-foreground-400",
    progressColor: "default",
  },
  fetching_info: {
    icon: Loader2,
    color: "text-foreground-500",
    progressColor: "default",
    spin: true,
  },
  downloading: {
    icon: Loader2,
    color: "text-primary",
    progressColor: "primary",
    spin: true,
  },
  importing: {
    icon: Loader2,
    color: "text-secondary",
    progressColor: "secondary",
    spin: true,
  },
  completed: {
    icon: CheckCircle,
    color: "text-success",
    progressColor: "success",
  },
  failed: { icon: XCircle, color: "text-danger", progressColor: "danger" },
  cancelled: { icon: X, color: "text-warning", progressColor: "warning" },
};

const ICON_CLASS = "h-4 w-4";

function StatusIcon({
  status,
  hasPartialFailures,
}: {
  status: JobStatus;
  hasPartialFailures?: boolean;
}) {
  if (status === "completed" && hasPartialFailures) {
    return <CircleAlert className={`${ICON_CLASS} text-warning`} />;
  }

  const { icon: Icon, color, spin } = STATUS_CONFIG[status];
  return (
    <Icon className={`${ICON_CLASS} ${color} ${spin ? "animate-spin" : ""}`} />
  );
}

function Thumbnail({
  url,
  status,
  hasPartialFailures,
}: {
  url: string | null;
  status: JobStatus;
  hasPartialFailures?: boolean;
}) {
  const statusIcon = (
    <StatusIcon status={status} hasPartialFailures={hasPartialFailures} />
  );

  if (!url) {
    return (
      <div className="bg-content3 flex h-16 w-16 shrink-0 items-center justify-center rounded">
        {statusIcon}
      </div>
    );
  }

  return (
    <div className="relative h-16 w-16 shrink-0">
      <Image
        src={url}
        alt=""
        radius="sm"
        isBlurred
        className="h-16 w-16 object-cover"
      />
      <div className="bg-content2/80 absolute right-0.5 bottom-0.5 z-10 grid h-5 w-5 place-items-center rounded-full">
        {statusIcon}
      </div>
    </div>
  );
}

function MetadataChip({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Chip
      size="sm"
      variant="flat"
      className={`text-foreground-500 ${className ?? ""}`}
    >
      {children}
    </Chip>
  );
}

function ContentInfo({
  title,
  artist,
  year,
  trackCount,
  audioCodec,
  audioBitrate,
  showBitrate,
  kind,
}: {
  title: string;
  artist: string | null;
  year: number | null;
  trackCount: number | null;
  audioCodec: string | null;
  audioBitrate: number | null;
  showBitrate: boolean;
  kind: string | null;
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
        {kind && <MetadataChip className="capitalize">{kind}</MetadataChip>}
        {trackCount && kind !== "track" && (
          <MetadataChip>
            {trackCount} {trackCount === 1 ? "track" : "tracks"}
          </MetadataChip>
        )}
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
  const { content_info, download_stats } = job;
  const hasPartialFailures =
    job.status === "completed" && (download_stats?.failed ?? 0) > 0;

  return (
    <div
      className={`bg-content2 shadow-small rounded-large overflow-hidden px-3 py-2.5 transition-colors ${
        job.status === "cancelled" ? "opacity-50" : ""
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex items-center gap-3">
        <Thumbnail
          url={content_info?.thumbnail_url ?? null}
          status={job.status}
          hasPartialFailures={hasPartialFailures}
        />

        <div className="min-w-0 flex-1 font-mono">
          {content_info?.title ? (
            <ContentInfo
              title={content_info.title}
              artist={content_info.artist ?? null}
              year={content_info.year ?? null}
              trackCount={content_info.track_count ?? null}
              audioCodec={content_info.audio_codec ?? null}
              audioBitrate={content_info.audio_bitrate ?? null}
              showBitrate={isJobFinished}
              kind={content_info.kind ?? null}
            />
          ) : (
            <p className="text-foreground-500 truncate text-xs">{job.url}</p>
          )}
        </div>

        <motion.div
          initial={{ opacity: isRunning ? 1 : 0, scale: isRunning ? 1 : 0.8 }}
          animate={{
            opacity: isRunning || isHovered ? 1 : 0,
            scale: isRunning || isHovered ? 1 : 0.8,
          }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
          <Button
            as="a"
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            variant="light"
            size="sm"
            isIconOnly
            className="text-foreground-500 hover:text-primary h-7 w-7 shrink-0"
          >
            <ExternalLink className="h-4 w-4" />
          </Button>
        </motion.div>

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
            color={STATUS_CONFIG[job.status].progressColor}
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

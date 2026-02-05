import type { Job, JobStatus } from "@/api/jobs";
import { formatDateTime } from "@/lib/format";
import { isActive, isFinished, isRunning } from "@/lib/job-status";
import {
  Button,
  Card,
  CardBody,
  CardFooter,
  Chip,
  Image,
  Progress,
  Tooltip,
} from "@heroui/react";
import {
  CheckCircleIcon,
  CircleAlertIcon,
  ClockIcon,
  ExternalLinkIcon,
  Loader2,
  Loader2Icon,
  Trash2Icon,
  XCircleIcon,
  XIcon,
  ZapIcon,
} from "lucide-react";
import { JobChip } from "./job-chip";

type Props = {
  job: Job;
  onCancel?: (jobId: string) => void;
  onDelete?: (jobId: string) => void;
};

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
    icon: typeof ClockIcon;
    color: string;
    progressColor: ProgressColor;
    spin?: boolean;
  }
> = {
  pending: {
    icon: ClockIcon,
    color: "text-foreground-400",
    progressColor: "default",
  },
  fetching_info: {
    icon: Loader2Icon,
    color: "text-foreground-500",
    progressColor: "default",
    spin: true,
  },
  downloading: {
    icon: Loader2Icon,
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
    icon: CheckCircleIcon,
    color: "text-success",
    progressColor: "success",
  },
  failed: { icon: XCircleIcon, color: "text-danger", progressColor: "danger" },
  cancelled: { icon: XIcon, color: "text-warning", progressColor: "warning" },
};

function StatusIcon({
  status,
  hasPartialFailures,
}: {
  status: JobStatus;
  hasPartialFailures?: boolean;
}) {
  const sizeClass = "h-4 w-4";

  if (status === "completed" && hasPartialFailures) {
    return <CircleAlertIcon className={`${sizeClass} text-warning`} />;
  }

  const { icon: Icon, color, spin } = STATUS_CONFIG[status];
  return (
    <Icon className={`${sizeClass} ${color} ${spin ? "animate-spin" : ""}`} />
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

  return (
    <div className="relative h-18 w-18 shrink-0">
      {url ? (
        <Image src={url} radius="sm" isBlurred />
      ) : (
        <div className="bg-content3 rounded-small flex h-full w-full shrink-0 items-center justify-center"></div>
      )}
      <div className="bg-content2/80 absolute right-0.5 bottom-0.5 z-10 grid h-6 w-6 place-items-center rounded-full">
        {statusIcon}
      </div>
    </div>
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
  source,
  createdAt,
}: {
  title: string;
  artist: string | null;
  year: number | null;
  trackCount: number | null;
  audioCodec: string | null;
  audioBitrate: number | null;
  showBitrate: boolean;
  kind: "playlist" | "album" | "track" | null;
  source: "manual" | "scheduler";
  createdAt: string | undefined;
}) {
  return (
    <div className="min-w-0">
      <div className="flex flex-col gap-1">
        <div className="text-small flex min-w-0 items-baseline gap-2 font-mono">
          <span className="text-foreground truncate">{title}</span>
          {year && (
            <span className="text-foreground-500 shrink-0">({year})</span>
          )}
        </div>
        <p className="text-foreground-500 text-small mb-1 min-w-0 truncate">
          {artist}
        </p>
      </div>
      <div className="flex items-center gap-2">
        {source === "scheduler" && (
          <Tooltip
            content={
              createdAt
                ? `Synced @ ${formatDateTime(createdAt)}`
                : "Synced by the scheduler"
            }
            closeDelay={0}
          >
            <Chip
              size="sm"
              variant="flat"
              startContent={<ZapIcon size={14} className="mx-1" />}
              className="bg-sky-500/15 font-mono text-sky-600 dark:bg-sky-500/20 dark:text-sky-300"
            >
              Auto
            </Chip>
          </Tooltip>
        )}
        {kind && (
          <JobChip variant={kind}>
            <span className="capitalize">{kind}</span>
          </JobChip>
        )}
        {audioCodec && (
          <JobChip variant="flat" className="max-md:hidden">
            {`${audioCodec} ${showBitrate && audioBitrate ? `@ ${audioBitrate}kbps` : ""}`}
          </JobChip>
        )}
        {trackCount && kind !== "track" && (
          <JobChip variant="flat" className="max-md:hidden">
            {trackCount} {trackCount === 1 ? "track" : "tracks"}
          </JobChip>
        )}
      </div>
    </div>
  );
}

export function JobCard({ job, onCancel, onDelete }: Props) {
  const isJobActive = isActive(job.status);
  const isJobRunning = isRunning(job.status);
  const isJobFinished = isFinished(job.status);
  const { content_info, download_stats } = job;
  const hasPartialFailures =
    job.status === "completed" && (download_stats?.failed ?? 0) > 0;
  const opacity = `${job.status === "cancelled" ? "opacity - 50" : ""}`;

  return (
    <Card className={`group bg-content2 transition-colors ${opacity}`}>
      <CardBody className="flex flex-row items-center gap-3">
        <Thumbnail
          url={content_info?.thumbnail_url ?? null}
          status={job.status}
          hasPartialFailures={hasPartialFailures}
        />

        <div className="min-w-0 flex-1">
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
              source={job.source}
              createdAt={job.created_at}
            />
          ) : (
            <p className="text-foreground-500 truncate font-mono text-xs">
              {job.url}
            </p>
          )}
        </div>

        <Button
          as="a"
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          variant="light"
          size="sm"
          isIconOnly
          className="text-foreground-500 hover:text-primary h-7 w-7 shrink-0 md:not-group-hover:hidden"
        >
          <ExternalLinkIcon className="h-4 w-4" />
        </Button>

        {isJobActive && onCancel && (
          <Button
            variant="light"
            size="sm"
            isIconOnly
            className="text-foreground-500 hover:text-danger h-7 w-7 shrink-0 md:not-group-hover:hidden"
            onPress={() => onCancel(job.id)}
          >
            <XIcon className="h-4 w-4" />
          </Button>
        )}

        {isJobFinished && onDelete && (
          <Button
            variant="light"
            size="sm"
            isIconOnly
            className="text-foreground-500 hover:text-danger h-7 w-7 shrink-0 not-group-hover:hidden max-md:hidden"
            onPress={() => onDelete(job.id)}
          >
            <Trash2Icon className="h-4 w-4" />
          </Button>
        )}
      </CardBody>

      {isJobRunning && (
        <CardFooter className="flex items-center gap-2 pt-0">
          <Progress
            value={job.progress}
            size="md"
            color={STATUS_CONFIG[job.status].progressColor}
            className="flex-1"
            classNames={{
              indicator: "transition-all duration-500 ease-out",
            }}
            aria-label="Job progress"
          />
          <span className="text-foreground-500 text-small w-8 text-right font-mono">
            {Math.round(job.progress)}%
          </span>
        </CardFooter>
      )}
    </Card>
  );
}

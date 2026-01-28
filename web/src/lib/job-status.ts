import type { JobStatus } from "@/api/jobs";

/** Active states that indicate job is in progress */
const ACTIVE_STATUSES = new Set<JobStatus>([
  "pending",
  "fetching_info",
  "downloading",
  "importing",
]);

/** Check if a job status indicates the job is active (not finished) */
export function isActive(status: JobStatus): boolean {
  return ACTIVE_STATUSES.has(status);
}

/** Check if a job status indicates the job is finished */
export function isFinished(status: JobStatus): boolean {
  return !ACTIVE_STATUSES.has(status);
}

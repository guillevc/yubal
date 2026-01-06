import type { JobStatus } from "../api/jobs";

/** Terminal states that indicate job is finished */
export const FINISHED_STATUSES: readonly JobStatus[] = [
  "completed",
  "failed",
  "cancelled",
] as const;

/** Check if a job status indicates the job is finished */
export function isFinished(status: JobStatus): boolean {
  return (FINISHED_STATUSES as readonly string[]).includes(status);
}

/** Check if a job status indicates the job is active (not finished) */
export function isActive(status: JobStatus): boolean {
  return !isFinished(status);
}

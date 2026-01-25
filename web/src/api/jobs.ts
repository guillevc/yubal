import { api } from "./client";
import type { components } from "./schema";

// Re-export types from schema
export type AlbumInfo = components["schemas"]["AlbumInfo"];
export type ContentKind = components["schemas"]["ContentKind"];

export type JobStatus =
  | "pending"
  | "fetching_info"
  | "downloading"
  | "importing"
  | "completed"
  | "failed"
  | "cancelled";

// Override status field to use JobStatus instead of string
export type Job = Omit<components["schemas"]["Job"], "status"> & {
  status: JobStatus;
};

export type CreateJobResult =
  | {
      success: true;
      jobId: string;
    }
  | {
      success: false;
      error: string;
      activeJobId?: string;
    };

export async function createJob(
  url: string,
  maxItems?: number,
): Promise<CreateJobResult> {
  const { data, error, response } = await api.POST("/jobs", {
    body: { url, max_items: maxItems },
  });

  if (error) {
    if (response.status === 409) {
      // Job conflict - another job is running
      const conflict = error as { error: string; active_job_id?: string };
      return {
        success: false,
        error: conflict.error,
        activeJobId: conflict.active_job_id,
      };
    }
    if (response.status === 422) {
      // Validation error - extract message from detail
      const validation = error as { detail?: { msg: string }[] };
      const message = validation.detail?.[0]?.msg ?? "Invalid URL";
      return { success: false, error: message };
    }
    return { success: false, error: "Failed to create job" };
  }

  return { success: true, jobId: data.id };
}

export async function listJobs(): Promise<{ jobs: Job[] }> {
  const { data, error } = await api.GET("/jobs");

  if (error) return { jobs: [] };
  return { jobs: data.jobs as Job[] };
}

export async function deleteJob(jobId: string): Promise<void> {
  const { error } = await api.DELETE("/jobs/{job_id}", {
    params: { path: { job_id: jobId } },
  });

  if (error) throw new Error("Failed to delete job");
}

export async function cancelJob(jobId: string): Promise<void> {
  const { error } = await api.POST("/jobs/{job_id}/cancel", {
    params: { path: { job_id: jobId } },
  });

  if (error) throw new Error("Failed to cancel job");
}

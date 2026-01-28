import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelJob as cancelJobApi,
  createJob,
  deleteJob as deleteJobApi,
  listJobs,
  type Job,
} from "@/api/jobs";
import { isActive } from "@/lib/job-status";
import { showErrorToast } from "@/lib/toast";

export type { Job } from "@/api/jobs";

export interface UseJobsResult {
  jobs: Job[];
  startJob: (url: string, maxItems?: number) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  deleteJob: (jobId: string) => Promise<void>;
  refreshJobs: () => Promise<void>;
}

const POLL_INTERVAL = 2000;

export function useJobs(): UseJobsResult {
  const [jobs, setJobs] = useState<Job[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const fetchJobs = useCallback(async (): Promise<Job[]> => {
    const { jobs: jobList } = await listJobs();
    const reversed = [...jobList].reverse(); // Newest first
    setJobs(reversed);
    return jobList;
  }, []);

  const startPolling = useCallback(() => {
    // Already polling
    if (intervalRef.current) return;

    intervalRef.current = setInterval(async () => {
      try {
        const jobList = await fetchJobs();
        // Stop polling when no active jobs
        if (!jobList.some((j) => isActive(j.status))) {
          stopPolling();
        }
      } catch (error) {
        console.error("Failed to fetch jobs:", error);
      }
    }, POLL_INTERVAL);
  }, [fetchJobs, stopPolling]);

  const startJob = useCallback(
    async (url: string, maxItems?: number) => {
      const result = await createJob(url, maxItems);

      if (!result.success) {
        showErrorToast("Download failed", result.error);
        await fetchJobs();
        return;
      }

      await fetchJobs();
      startPolling();
    },
    [fetchJobs, startPolling],
  );

  const cancelJob = useCallback(
    async (jobId: string) => {
      try {
        await cancelJobApi(jobId);
      } catch (error) {
        console.error("Failed to cancel job:", error);
      }
      await fetchJobs();
    },
    [fetchJobs],
  );

  const deleteJob = useCallback(
    async (jobId: string) => {
      try {
        await deleteJobApi(jobId);
      } catch (error) {
        console.error("Failed to delete job:", error);
      }
      await fetchJobs();
    },
    [fetchJobs],
  );

  const refreshJobs = useCallback(async () => {
    const jobList = await fetchJobs();
    if (jobList.some((j) => isActive(j.status))) {
      startPolling();
    }
  }, [fetchJobs, startPolling]);

  // Initial fetch on mount
  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        const { jobs: jobList } = await listJobs();
        if (!mounted) return;

        const reversed = [...jobList].reverse();
        setJobs(reversed);

        // Start polling if there are active jobs
        if (jobList.some((j) => isActive(j.status))) {
          startPolling();
        }
      } catch (error) {
        console.error("Failed to fetch jobs:", error);
      }
    }

    init();

    return () => {
      mounted = false;
      stopPolling();
    };
  }, [startPolling, stopPolling]);

  return {
    jobs,
    startJob,
    cancelJob,
    deleteJob,
    refreshJobs,
  };
}

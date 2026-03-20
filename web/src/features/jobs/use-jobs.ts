import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelJob as cancelJobApi,
  createJob,
  deleteJob as deleteJobApi,
  type Job,
  type JobEvent,
} from "@/api/jobs";
import { basePath } from "@/lib/base-path";
import { isActive } from "@/lib/job-status";
import { showErrorToast } from "@/lib/toast";

const SSE_URL = `${basePath}/api/jobs/sse`;
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000] as const;

export function useJobsState() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  useEffect(() => {
    let mounted = true;

    function connect() {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const eventSource = new EventSource(SSE_URL);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        if (!mounted) return;
        setIsOffline(false);
        reconnectAttemptRef.current = 0;
      };

      eventSource.onmessage = (event) => {
        if (!mounted) return;
        const data = JSON.parse(event.data) as JobEvent;

        switch (data.type) {
          case "snapshot":
            setJobs([...data.jobs].reverse());
            setIsLoading(false);
            break;
          case "created":
          case "updated":
            setJobs((prev) => {
              const exists = prev.some((j) => j.id === data.job.id);
              if (exists) {
                return prev.map((j) => (j.id === data.job.id ? data.job : j));
              }
              return [data.job, ...prev];
            });
            break;
          case "deleted":
            setJobs((prev) => prev.filter((j) => j.id !== data.jobId));
            break;
          case "cleared":
            setJobs((prev) => prev.filter((j) => isActive(j.status)));
            break;
        }
      };

      eventSource.onerror = () => {
        if (!mounted) return;
        setIsOffline(true);
        eventSource.close();

        const delayIndex = Math.min(
          reconnectAttemptRef.current,
          RECONNECT_DELAYS.length - 1,
        );
        const delay = RECONNECT_DELAYS[delayIndex] ?? RECONNECT_DELAYS[0];
        const jitter = Math.random() * (delay * 0.5);
        reconnectAttemptRef.current++;

        reconnectTimeoutRef.current = setTimeout(connect, delay + jitter);
      };
    }

    connect();

    return () => {
      mounted = false;
      if (reconnectTimeoutRef.current)
        clearTimeout(reconnectTimeoutRef.current);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  const startJob = useCallback(async (url: string, maxItems?: number) => {
    const result = await createJob(url, maxItems);
    if (!result.success) {
      showErrorToast("Download failed", result.error);
    }
  }, []);

  const cancelJob = useCallback(async (jobId: string) => {
    try {
      await cancelJobApi(jobId);
    } catch (error) {
      console.error("Failed to cancel job:", error);
    }
  }, []);

  const deleteJob = useCallback(async (jobId: string) => {
    try {
      await deleteJobApi(jobId);
    } catch (error) {
      console.error("Failed to delete job:", error);
    }
  }, []);

  const hasActiveJobs = jobs.some((j) => isActive(j.status));

  return {
    jobs,
    hasActiveJobs,
    isLoading,
    isOffline,
    startJob,
    cancelJob,
    deleteJob,
  };
}

export type UseJobsResult = ReturnType<typeof useJobsState>;

/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, type ReactNode } from "react";
import { useJobsState, type UseJobsResult } from "./use-jobs";

const JobsContext = createContext<UseJobsResult | null>(null);

export function JobsProvider({ children }: { children: ReactNode }) {
  const jobs = useJobsState();
  return <JobsContext.Provider value={jobs}>{children}</JobsContext.Provider>;
}

export function useJobs(): UseJobsResult {
  const context = useContext(JobsContext);
  if (!context) {
    throw new Error("useJobs must be used within a JobsProvider");
  }
  return context;
}

import { formatCountdown } from "@/lib/format";
import { CronExpressionParser } from "cron-parser";
import { useEffect, useState } from "react";

function computeNextRun(
  cronExpression: string | null | undefined,
  timezone: string | null | undefined,
): Date | null {
  if (!cronExpression || !timezone) return null;

  try {
    const interval = CronExpressionParser.parse(cronExpression, {
      tz: timezone,
      currentDate: new Date(),
    });
    return interval.next().toDate();
  } catch {
    return null;
  }
}

/**
 * Hook that computes the next run time from a cron expression and returns
 * a formatted countdown string that updates every second.
 */
export function useScheduleCountdown(
  cronExpression: string | null | undefined,
  timezone: string | null | undefined,
): string {
  const [nextRun, setNextRun] = useState<Date | null>(() =>
    computeNextRun(cronExpression, timezone),
  );
  const [tick, setTick] = useState(0);

  // Recompute when inputs change
  useEffect(() => {
    setNextRun(computeNextRun(cronExpression, timezone));
  }, [cronExpression, timezone]);

  // Schedule recomputation when next run time passes
  useEffect(() => {
    if (!nextRun) return;

    const ms = nextRun.getTime() - Date.now();
    if (ms <= 0) {
      // Already passed, schedule immediate recompute
      const timeout = setTimeout(() => {
        setNextRun(computeNextRun(cronExpression, timezone));
      }, 0);
      return () => clearTimeout(timeout);
    }

    // Schedule recomputation when next run time passes
    const timeout = setTimeout(() => {
      setNextRun(computeNextRun(cronExpression, timezone));
    }, ms + 100); // Small buffer to ensure cron-parser moves to next interval

    return () => clearTimeout(timeout);
  }, [nextRun, cronExpression, timezone]);

  // Tick every second for countdown display
  useEffect(() => {
    if (!nextRun) return;

    const interval = setInterval(() => {
      setTick((t) => t + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [nextRun]);

  void tick;
  return formatCountdown(nextRun);
}

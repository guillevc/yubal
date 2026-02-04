import { useEffect, useRef, useState } from "react";

function formatCountdown(targetDate: Date | null): string {
  if (!targetDate) return "—";

  const ms = targetDate.getTime() - Date.now();

  if (ms <= 0) return "Now";

  const totalSeconds = Math.floor(ms / 1000);
  const days = Math.floor(totalSeconds / 86400);

  if (days >= 1) {
    return `${days} day${days === 1 ? "" : "s"}`;
  }

  const hours = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  const pad = (n: number) => n.toString().padStart(2, "0");

  if (hours > 0) {
    return `${hours}:${pad(mins)}:${pad(secs)}`;
  }
  return `${mins}:${pad(secs)}`;
}

export function useCountdown(
  targetDate: Date | null,
  onComplete?: () => void,
): string {
  const [tick, setTick] = useState(0);
  const completedRef = useRef(false);

  useEffect(() => {
    if (!targetDate) return;
    completedRef.current = false;
  }, [targetDate]);

  useEffect(() => {
    if (!targetDate) return;

    const interval = setInterval(() => {
      const ms = targetDate.getTime() - Date.now();
      if (ms <= 0 && !completedRef.current) {
        completedRef.current = true;
        // Delay to allow backend to update next_run_at
        setTimeout(() => onComplete?.(), 1000);
      }
      setTick((t) => t + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [targetDate, onComplete]);

  void tick;
  return formatCountdown(targetDate);
}

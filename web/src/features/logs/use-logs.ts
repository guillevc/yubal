import { useEffect, useRef, useState } from "react";
import type { LogEntry, LogLine } from "@/api/logs";

export type { LogLine } from "@/api/logs";

const SSE_URL = "/api/logs/sse";
const MAX_LOG_LINES = 1000;
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000] as const;

export interface UseLogsResult {
  lines: LogLine[];
  isOffline: boolean;
}

/**
 * SSE log streaming hook with exponential backoff reconnection.
 *
 * Features:
 * - Automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, 16s max)
 * - Memory-bounded log buffer (MAX_LOG_LINES)
 * - Connection state tracking
 */
export function useLogs(): UseLogsResult {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [isOffline, setIsOffline] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  useEffect(() => {
    let mounted = true;

    function connect() {
      // Clean up existing connection
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
        const entry = JSON.parse(event.data) as LogEntry;
        const line: LogLine = { id: crypto.randomUUID(), entry };
        setLines((prev) => {
          const newLines = [...prev, line];
          return newLines.length > MAX_LOG_LINES
            ? newLines.slice(-MAX_LOG_LINES)
            : newLines;
        });
      };

      eventSource.onerror = () => {
        if (!mounted) return;
        setIsOffline(true);
        eventSource.close();

        // Schedule reconnection with exponential backoff
        const delayIndex = Math.min(
          reconnectAttemptRef.current,
          RECONNECT_DELAYS.length - 1,
        );
        const delay = RECONNECT_DELAYS[delayIndex];
        reconnectAttemptRef.current++;

        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      mounted = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  return { lines, isOffline };
}

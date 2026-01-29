import { useEffect, useRef, useState } from "react";
import { searchSuggestions } from "../api/search";

interface UseSearchSuggestionsOptions {
  enabled?: boolean;
  debounceMs?: number;
}

export function useSearchSuggestions(
  query: string,
  options: UseSearchSuggestionsOptions = {},
) {
  const { enabled = true, debounceMs = 200 } = options;
  const [suggestions, setSuggestions] = useState<
    Array<
      | string
      | {
          text: string;
          runs?: Array<{ text: string; bold?: boolean }>;
        }
    >
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const debounceRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) {
      setSuggestions([]);
      setIsLoading(false);
      return;
    }

    const trimmed = query.trim();
    if (trimmed.length < 1) {
      setSuggestions([]);
      setIsLoading(false);
      return;
    }

    if (debounceRef.current) {
      window.clearTimeout(debounceRef.current);
    }

    setIsLoading(true);
    debounceRef.current = window.setTimeout(async () => {
      try {
        const { suggestions: nextSuggestions } = await searchSuggestions(trimmed);
        setSuggestions(nextSuggestions);
      } catch {
        setSuggestions([]);
      } finally {
        setIsLoading(false);
      }
    }, debounceMs);

    return () => {
      if (debounceRef.current) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, [debounceMs, enabled, query]);

  return { suggestions, isLoading };
}

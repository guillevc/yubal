import { Input } from "@heroui/react";
import type { KeyboardEvent } from "react";
import { useEffect, useRef, useState } from "react";
import { Link, Search } from "lucide-react";
import { isValidUrl } from "../lib/url";

interface UrlInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  onSubmit?: () => void;
  suggestions?: Array<
    | string
    | {
        text: string;
        runs?: Array<{ text: string; bold?: boolean }>;
      }
  >;
  onSuggestionSelect?: (value: string) => void;
}

export function UrlInput({
  value,
  onChange,
  disabled,
  onSubmit,
  suggestions = [],
  onSuggestionSelect,
}: UrlInputProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isFocused, setIsFocused] = useState(false);
  const isUrlLike = value.startsWith("http://") || value.startsWith("https://");
  const isValid = value === "" || !isUrlLike || isValidUrl(value);
  const showSuggestions = !isUrlLike && suggestions.length > 0;
  const isOpen = isFocused && showSuggestions;

  const getSuggestionText = (
    suggestion:
      | string
      | {
          text: string;
          runs?: Array<{ text: string; bold?: boolean }>;
        },
  ) => (typeof suggestion === "string" ? suggestion : suggestion.text);

  useEffect(() => {
    const handleClickAway = (event: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        setIsFocused(false);
      }
    };

    const handleScroll = () => {
      setIsFocused(false);
    };

    window.addEventListener("mousedown", handleClickAway);
    window.addEventListener("scroll", handleScroll, true);
    return () => {
      window.removeEventListener("mousedown", handleClickAway);
      window.removeEventListener("scroll", handleScroll, true);
    };
  }, []);

  return (
    <div className="relative" ref={containerRef}>
      <Input
        isClearable
        variant="faded"
        type="url"
        placeholder="Album or playlist URL, or search terms"
        value={value}
        onValueChange={(nextValue: string) => onChange(nextValue.trim())}
        onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
          if (event.key === "Enter") {
            onSubmit?.();
            setIsFocused(false);
          }
        }}
        onClick={() => setIsFocused(true)}
        onFocus={() => setIsFocused(true)}
        isDisabled={disabled}
        isInvalid={!isValid}
        radius="lg"
        errorMessage={!isValid ? "Enter a valid YouTube URL" : undefined}
        // If isUrlLike, show link icon, else show search icon
        startContent={isUrlLike ? (
          <Link className="text-foreground-400 h-4 w-4" />
        ) : (
          <Search className="text-foreground-400 h-4 w-4" />
        )
      }
      />
      {isOpen && (
        <div className="bg-content1 border-content3 absolute z-50 mt-2 w-full rounded-xl border shadow-lg">
          <ul className="max-h-60 overflow-auto py-2 text-sm">
            {suggestions.map((suggestion, index) => (
              <li key={`${getSuggestionText(suggestion)}-${index}`}>
                <button
                  type="button"
                  className="hover:bg-content2 flex w-full items-center gap-2 px-3 py-2 text-left"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => {
                    onSuggestionSelect?.(getSuggestionText(suggestion));
                    setIsFocused(false);
                  }}
                >
                  {typeof suggestion === "string" ? (
                    suggestion
                  ) : suggestion.runs && suggestion.runs.length > 0 ? (
                    <span>
                      {suggestion.runs.map((run, runIndex) => (
                        <span
                          key={`${run.text}-${runIndex}`}
                          className={run.bold ? "font-semibold" : undefined}
                        >
                          {run.text}
                        </span>
                      ))}
                    </span>
                  ) : (
                    suggestion.text
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

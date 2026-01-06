import { Input } from "@heroui/react";
import { Link } from "lucide-react";
import { YOUTUBE_MUSIC_URL_PATTERN } from "../lib/url";

interface UrlInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function UrlInput({ value, onChange, disabled }: UrlInputProps) {
  const isValid = value === "" || YOUTUBE_MUSIC_URL_PATTERN.test(value);

  return (
    <Input
      size="md"
      classNames={{
        input: "text-foreground",
      }}
      type="url"
      placeholder="Paste album URL..."
      value={value}
      onValueChange={onChange}
      isDisabled={disabled}
      isInvalid={!isValid}
      errorMessage={!isValid ? "Enter a valid YouTube Music URL" : undefined}
      startContent={<Link className="text-foreground-400 h-4 w-4" />}
    />
  );
}

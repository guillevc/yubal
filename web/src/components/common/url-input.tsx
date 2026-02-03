import { YOUTUBE_MUSIC_URL_PATTERN } from "@/lib/url";
import { Input } from "@heroui/react";
import { LinkIcon } from "lucide-react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
};

export function UrlInput({
  value,
  onChange,
  disabled,
  placeholder = "Album or playlist URL",
}: Props) {
  const isValid = value === "" || YOUTUBE_MUSIC_URL_PATTERN.test(value);

  return (
    <Input
      isClearable
      type="url"
      placeholder={placeholder}
      value={value}
      onValueChange={(v) => onChange(v.trim())}
      isDisabled={disabled}
      isInvalid={!isValid}
      radius="lg"
      errorMessage={!isValid ? "Enter a valid YouTube URL" : undefined}
      startContent={<LinkIcon className="text-foreground-400 h-4 w-4" />}
    />
  );
}

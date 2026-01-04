import {
  addToast,
  Button,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Tooltip,
} from "@heroui/react";
import { Cookie, Disc3, Star, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { deleteCookies, getCookiesStatus, uploadCookies } from "../api/cookies";
import { AnimatedThemeToggler } from "./ui/AnimatedThemeToggler";

export function Header() {
  const [cookiesConfigured, setCookiesConfigured] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCookiesStatus().then(setCookiesConfigured);
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const content = await file.text();
      const success = await uploadCookies(content);

      if (success) {
        setCookiesConfigured(true);
        addToast({
          title: "Cookies uploaded",
          description: "YouTube cookies configured successfully",
          color: "success",
        });
      } else {
        addToast({
          title: "Upload failed",
          description: "Failed to upload cookies file",
          color: "danger",
        });
      }
    } catch {
      addToast({
        title: "Upload failed",
        description: "Could not read the file",
        color: "danger",
      });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const success = await deleteCookies();
      if (success) {
        setCookiesConfigured(false);
        addToast({
          title: "Cookies deleted",
          description: "YouTube cookies removed",
          color: "success",
        });
      } else {
        addToast({
          title: "Delete failed",
          description: "Failed to delete cookies",
          color: "danger",
        });
      }
    } catch {
      addToast({
        title: "Delete failed",
        description: "Could not delete cookies",
        color: "danger",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDropdownAction = (key: React.Key) => {
    if (key === "upload") {
      fileInputRef.current?.click();
    } else if (key === "delete") {
      handleDelete();
    }
  };

  return (
    <header className="mb-6 flex items-center gap-3">
      <div className="border-primary-200 bg-background rounded-lg border-1 p-1">
        <Disc3 className="text-primary h-7 w-7" />
      </div>
      <div className="flex-1">
        <h1 className="text-foreground font-mono text-xl font-semibold tracking-tight">
          yubal
        </h1>
        <p className="font-mono text-xs">
          <a
            href={`https://github.com/guillevc/yubal/${__IS_RELEASE__ ? `releases/tag/${__VERSION__}` : `commit/${__COMMIT_SHA__}`}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary/70 hover:text-primary underline-offset-2 transition-colors hover:underline"
          >
            {__VERSION__}
          </a>
        </p>
      </div>
      <Button
        as="a"
        href="https://github.com/guillevc/yubal"
        target="_blank"
        rel="noopener noreferrer"
        radius="full"
        size="sm"
        variant="ghost"
        startContent={
          <Star
            className="h-4 w-4 fill-amber-400 text-amber-400 dark:fill-amber-300 dark:text-amber-300"
            strokeWidth={1}
          />
        }
      >
        Star on GitHub
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt"
        onChange={handleFileSelect}
        className="hidden"
      />
      {cookiesConfigured ? (
        <Dropdown>
          <DropdownTrigger>
            <Button
              isIconOnly
              variant="light"
              aria-label="Cookie options"
              isLoading={isDeleting}
            >
              <Cookie className="text-success h-5 w-5" />
            </Button>
          </DropdownTrigger>
          <DropdownMenu
            aria-label="Cookie actions"
            onAction={handleDropdownAction}
          >
            <DropdownItem
              key="upload"
              startContent={<Upload className="h-4 w-4" />}
            >
              Upload new cookies
            </DropdownItem>
            <DropdownItem
              key="delete"
              color="danger"
              className="text-danger"
              startContent={<Trash2 className="h-4 w-4" />}
            >
              Delete cookies
            </DropdownItem>
          </DropdownMenu>
        </Dropdown>
      ) : (
        <Tooltip
          content="Upload cookies.txt for YouTube authentication"
          closeDelay={0}
        >
          <Button
            isIconOnly
            variant="light"
            aria-label="Upload cookies"
            isLoading={isUploading}
            onPress={() => fileInputRef.current?.click()}
          >
            <Cookie className="h-5 w-5" />
          </Button>
        </Tooltip>
      )}
      <AnimatedThemeToggler />
    </header>
  );
}

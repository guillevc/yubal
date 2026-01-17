import {
  Button,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Link,
  Tooltip,
} from "@heroui/react";
import { Cookie, Trash2, Upload } from "lucide-react";

interface CookieDropdownProps {
  cookiesConfigured: boolean;
  isUploading: boolean;
  isDeleting: boolean;
  onDropdownAction: (key: React.Key) => void;
  onUploadClick: () => void;
  variant: "desktop" | "mobile";
}

export function CookieDropdown({
  cookiesConfigured,
  isUploading,
  isDeleting,
  onDropdownAction,
  onUploadClick,
  variant,
}: CookieDropdownProps) {
  if (variant === "desktop") {
    return cookiesConfigured ? (
      <Dropdown>
        <DropdownTrigger>
          <Button
            isIconOnly
            variant="light"
            aria-label="Cookie options"
            isLoading={isDeleting}
          >
            <Cookie className="h-5 w-5 text-amber-500 dark:text-orange-300" />
          </Button>
        </DropdownTrigger>
        <CookieDropdownMenu onAction={onDropdownAction} />
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
          onPress={onUploadClick}
        >
          <Cookie className="h-5 w-5" />
        </Button>
      </Tooltip>
    );
  }

  // Mobile variant
  return cookiesConfigured ? (
    <Dropdown>
      <DropdownTrigger>
        <Link as="button" color="foreground" className="w-full gap-2" size="lg">
          <Cookie className="text-success h-4 w-4" />
          Cookies configured
        </Link>
      </DropdownTrigger>
      <CookieDropdownMenu onAction={onDropdownAction} />
    </Dropdown>
  ) : (
    <Link
      as="button"
      color="foreground"
      className="w-full cursor-pointer gap-2"
      size="lg"
      onPress={onUploadClick}
    >
      <Cookie className="h-4 w-4" />
      Upload cookies
    </Link>
  );
}

interface CookieDropdownMenuProps {
  onAction: (key: React.Key) => void;
}

function CookieDropdownMenu({ onAction }: CookieDropdownMenuProps) {
  return (
    <DropdownMenu aria-label="Cookie actions" onAction={onAction}>
      <DropdownItem key="upload" startContent={<Upload className="h-4 w-4" />}>
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
  );
}

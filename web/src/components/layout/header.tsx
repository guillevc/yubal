import {
  addToast,
  Button,
  Chip,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Link,
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  NavbarMenu,
  NavbarMenuItem,
  NavbarMenuToggle,
  Tooltip,
} from "@heroui/react";
import { Cookie, Disc3, Star, Trash2, Upload } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import {
  deleteCookies,
  getCookiesStatus,
  uploadCookies,
} from "../../api/cookies";
import { AnimatedThemeToggler } from "../magicui/animated-theme-toggler";

const MotionNavbarBrand = motion.create(NavbarBrand);
const MotionNavbarContent = motion.create(NavbarContent);

const blurFadeAnimation = {
  initial: { opacity: 0, y: -12, filter: "blur(8px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  transition: { duration: 0.4, ease: "easeOut" as const },
};

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
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
    <Navbar
      isBordered
      position="sticky"
      isMenuOpen={isMenuOpen}
      onMenuOpenChange={setIsMenuOpen}
      classNames={{
        wrapper: "max-w-4xl",
      }}
    >
      {/* Mobile menu toggle */}
      <NavbarContent className="sm:hidden" justify="start">
        <NavbarMenuToggle
          aria-label={isMenuOpen ? "Close menu" : "Open menu"}
        />
      </NavbarContent>

      {/* Brand - centered on mobile, left on desktop */}
      <NavbarContent className="sm:hidden pr-3" justify="center">
        <NavbarBrand className="gap-2">
          <Disc3 className="text-primary h-7 w-7" />
          <span className="text-foreground font-mono text-large font-bold">
            yubal
          </span>
        </NavbarBrand>
      </NavbarContent>

      {/* Desktop brand with version chip */}
      <MotionNavbarBrand className="hidden sm:flex gap-3" {...blurFadeAnimation}>
        <Disc3 className="text-primary h-8 w-8" />
        <span className="text-foreground font-mono text-large font-bold">
          yubal
        </span>
        <Chip
          as="a"
          href={`https://github.com/guillevc/yubal/${__IS_RELEASE__ ? `releases/tag/${__VERSION__}` : `commit/${__COMMIT_SHA__}`}`}
          target="_blank"
          rel="noopener noreferrer"
          size="sm"
          variant="flat"
          color="primary"
          classNames={{
            base: "cursor-pointer",
            content: "font-mono text-xs tracking-wider",
          }}
        >
          {__VERSION__}
        </Chip>
      </MotionNavbarBrand>

      {/* Desktop navigation items */}
      <MotionNavbarContent
        justify="end"
        className="hidden sm:flex gap-1"
        {...blurFadeAnimation}
      >
        <NavbarItem>
          <Button
            as="a"
            href="https://github.com/guillevc/yubal"
            target="_blank"
            rel="noopener noreferrer"
            radius="full"
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
        </NavbarItem>

        <input
          ref={fileInputRef}
          type="file"
          accept=".txt"
          onChange={handleFileSelect}
          className="hidden"
        />

        <NavbarItem>
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
        </NavbarItem>

        <NavbarItem>
          <AnimatedThemeToggler />
        </NavbarItem>
      </MotionNavbarContent>

      {/* Mobile: theme toggle always visible */}
      <NavbarContent className="sm:hidden" justify="end">
        <NavbarItem>
          <AnimatedThemeToggler />
        </NavbarItem>
      </NavbarContent>

      {/* Mobile menu */}
      <NavbarMenu>
        <NavbarMenuItem>
          <Link
            as="a"
            href="https://github.com/guillevc/yubal"
            target="_blank"
            rel="noopener noreferrer"
            color="foreground"
            className="w-full gap-2"
            size="lg"
          >
            <Star
              className="h-4 w-4 fill-amber-400 text-amber-400"
              strokeWidth={1}
            />
            Star on GitHub
          </Link>
        </NavbarMenuItem>
        <NavbarMenuItem>
          {cookiesConfigured ? (
            <Dropdown>
              <DropdownTrigger>
                <Link
                  as="button"
                  color="foreground"
                  className="w-full gap-2"
                  size="lg"
                >
                  <Cookie className="text-success h-4 w-4" />
                  Cookies configured
                </Link>
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
            <Link
              as="button"
              color="foreground"
              className="w-full gap-2"
              size="lg"
              onPress={() => fileInputRef.current?.click()}
            >
              <Cookie className="h-4 w-4" />
              Upload cookies
            </Link>
          )}
        </NavbarMenuItem>
        <NavbarMenuItem>
          <Link
            as="a"
            href={`https://github.com/guillevc/yubal/${__IS_RELEASE__ ? `releases/tag/${__VERSION__}` : `commit/${__COMMIT_SHA__}`}`}
            target="_blank"
            rel="noopener noreferrer"
            color="primary"
            className="w-full gap-2"
            size="lg"
          >
            Version {__VERSION__}
          </Link>
        </NavbarMenuItem>
      </NavbarMenu>
    </Navbar>
  );
}

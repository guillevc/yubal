import { listSubscriptions } from "@/api/subscriptions";
import { AnimatedThemeToggler } from "@/components/magicui/animated-theme-toggler";
import { CookieDropdown } from "@/features/cookies/cookie-dropdown";
import { useCookies } from "@/features/cookies/use-cookies";
import { useJobs } from "@/features/jobs/jobs-context";
import { useVersionCheck } from "@/hooks/use-version-check";
import {
  Button,
  Chip,
  Link,
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  NavbarMenu,
  NavbarMenuItem,
  NavbarMenuToggle,
} from "@heroui/react";
import { useRouterState } from "@tanstack/react-router";
import {
  Disc3Icon,
  DownloadIcon,
  ListMusicIcon,
  RocketIcon,
  StarIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

const navItems = [
  { label: "Downloads", startIcon: DownloadIcon, href: "/" },
  { label: "My playlists", startIcon: ListMusicIcon, href: "/playlists" },
];

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [subscriptionCount, setSubscriptionCount] = useState(0);
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const {
    cookiesConfigured,
    isUploading,
    isDeleting,
    fileInputRef,
    handleFileSelect,
    handleDropdownAction,
    triggerFileUpload,
  } = useCookies();
  const { data: versionInfo } = useVersionCheck();
  const { hasActiveJobs } = useJobs();

  useEffect(() => {
    listSubscriptions().then((subs) => setSubscriptionCount(subs.length));
  }, []);

  return (
    <Navbar
      isMenuOpen={isMenuOpen}
      onMenuOpenChange={setIsMenuOpen}
      classNames={{
        wrapper: "max-w-4xl",
        brand: "grow-0",
      }}
    >
      {/* Mobile menu toggle + Brand */}
      <NavbarContent className="sm:hidden" justify="start">
        <NavbarMenuToggle
          aria-label={isMenuOpen ? "Close menu" : "Open menu"}
        />
      </NavbarContent>

      <NavbarBrand className="mr-4">
        <Link href="/" className="flex items-center">
          <Disc3Icon
            className={`text-primary h-7 w-7 ${hasActiveJobs ? "animate-[spin_4s_linear_infinite] motion-reduce:animate-none" : ""}`}
          />
          <p className="text-foreground ml-2 text-xl font-bold">yubal</p>
        </Link>
      </NavbarBrand>

      {/* Desktop navigation */}
      <NavbarContent justify="start" className="hidden gap-2 sm:flex">
        {navItems.map((item) => (
          <NavbarItem
            key={item.href}
            className="group"
            isActive={currentPath === item.href}
          >
            <Button
              disableRipple
              variant="light"
              size="sm"
              as={Link}
              radius="lg"
              href={item.href}
              startContent={<item.startIcon className="h-4 w-4" />}
              endContent={
                item.href === "/playlists" &&
                subscriptionCount > 0 && (
                  <Chip
                    size="sm"
                    variant="flat"
                    radius="sm"
                    className="font-mono"
                    classNames={{
                      content:
                        "text-foreground-400 text-xs group-data-[active=true]:text-foreground",
                    }}
                  >
                    {subscriptionCount}
                  </Chip>
                )
              }
              className="text-foreground-400 text-small group-data-[active=true]:text-foreground flex items-center gap-2 font-medium"
            >
              {item.label}
            </Button>
          </NavbarItem>
        ))}
      </NavbarContent>

      {/* Actions */}
      <NavbarContent className="items-center gap-2" justify="end">
        {versionInfo?.updateAvailable && (
          <NavbarItem className="hidden sm:flex">
            <Button
              as="a"
              disableAnimation
              size="sm"
              href={versionInfo.releaseUrl}
              target="_blank"
              rel="noopener noreferrer"
              variant="flat"
              color="success"
              radius="lg"
              startContent={<RocketIcon className="h-4 w-4" />}
              className="text-small font-mono"
            >
              {versionInfo.latestVersion}
            </Button>
          </NavbarItem>
        )}
        <NavbarItem className="hidden sm:flex">
          <Button
            as="a"
            disableAnimation
            size="sm"
            href="https://github.com/guillevc/yubal"
            target="_blank"
            rel="noopener noreferrer"
            variant="light"
            radius="lg"
            startContent={
              <StarIcon
                className="h-4 w-4 fill-amber-400 text-amber-400 dark:fill-amber-300 dark:text-amber-300"
                strokeWidth={1}
              />
            }
            className="text-small"
          >
            Star on GitHub
          </Button>
        </NavbarItem>
        <NavbarItem className="hidden sm:flex">
          <CookieDropdown
            variant="desktop"
            cookiesConfigured={cookiesConfigured}
            isUploading={isUploading}
            isDeleting={isDeleting}
            onDropdownAction={handleDropdownAction}
            onUploadClick={triggerFileUpload}
          />
        </NavbarItem>
        <NavbarItem>
          <AnimatedThemeToggler />
        </NavbarItem>
      </NavbarContent>

      {/* Mobile menu */}
      <NavbarMenu>
        {navItems.map((item) => (
          <NavbarMenuItem key={item.href} isActive={currentPath === item.href}>
            <Link
              href={item.href}
              color={currentPath === item.href ? "primary" : "foreground"}
              className="flex w-full items-center gap-2"
              size="lg"
              onPress={() => setIsMenuOpen(false)}
            >
              {item.label}
              {item.href === "/playlists" && subscriptionCount > 0 && (
                <Chip size="sm" variant="flat" color="primary">
                  {subscriptionCount}
                </Chip>
              )}
            </Link>
          </NavbarMenuItem>
        ))}
        <NavbarMenuItem>
          <CookieDropdown
            variant="mobile"
            cookiesConfigured={cookiesConfigured}
            isUploading={isUploading}
            isDeleting={isDeleting}
            onDropdownAction={handleDropdownAction}
            onUploadClick={triggerFileUpload}
          />
        </NavbarMenuItem>
        <NavbarMenuItem>
          <Link
            href="https://github.com/guillevc/yubal"
            isExternal
            showAnchorIcon
            color="foreground"
            className="w-full"
            size="lg"
          >
            Star on GitHub
          </Link>
        </NavbarMenuItem>
      </NavbarMenu>

      {/* Hidden file input for cookie upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt"
        onChange={handleFileSelect}
        className="hidden"
      />
    </Navbar>
  );
}

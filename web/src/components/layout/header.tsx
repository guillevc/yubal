import {
  Button,
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
import { Disc3, Star } from "lucide-react";
import { useState } from "react";
import { useCookies } from "../../hooks/use-cookies";
import { CookieDropdown } from "../common/cookie-dropdown";
import { AnimatedThemeToggler } from "../magicui/animated-theme-toggler";

const navItems = [
  { label: "Downloads", href: "/" },
  { label: "Playlists", href: "/sync" },
];

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
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
          <Disc3 className="text-primary h-7 w-7" />
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
            <Link
              isBlock
              href={item.href}
              color="foreground"
              className="text-foreground-400 text-medium group-data-[active=true]:text-foreground px-3 py-2 font-medium"
            >
              {item.label}
            </Link>
          </NavbarItem>
        ))}
      </NavbarContent>

      {/* Actions */}
      <NavbarContent className="items-center gap-2" justify="end">
        <NavbarItem className="hidden sm:flex">
          <Button
            as="a"
            href="https://github.com/guillevc/yubal"
            target="_blank"
            rel="noopener noreferrer"
            variant="light"
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
              className="w-full"
              size="lg"
              onPress={() => setIsMenuOpen(false)}
            >
              {item.label}
            </Link>
          </NavbarMenuItem>
        ))}
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

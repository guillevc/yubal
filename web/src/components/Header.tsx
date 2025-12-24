import { Navbar, NavbarBrand, NavbarContent } from "@heroui/react";

export function Header() {
  return (
    <Navbar maxWidth="full" className="bg-content1">
      <NavbarBrand>
        <div className="flex items-center gap-2">
          <svg
            className="h-8 w-8"
            viewBox="0 0 100 100"
            xmlns="http://www.w3.org/2000/svg"
          >
            <rect width="100" height="100" rx="20" fill="#18181b" />
            <path d="M30 25 L70 50 L30 75 Z" fill="#ef4444" />
            <path d="M45 40 L60 50 L45 60 Z" fill="white" />
          </svg>
          <div className="flex flex-col">
            <span className="text-xl font-bold">yubal</span>
            <span className="text-tiny text-default-500">
              YouTube Album Downloader
            </span>
          </div>
        </div>
      </NavbarBrand>
      <NavbarContent justify="end">
        <span className="text-tiny text-default-400">Powered by beets</span>
      </NavbarContent>
    </Navbar>
  );
}

/* eslint-disable react-refresh/only-export-components */

import { HeroUIProvider, ToastProvider } from "@heroui/react";
import {
  createRootRoute,
  createRoute,
  createRouter,
  NavigateOptions,
  Outlet,
  ToOptions,
  useNavigate,
  useRouter,
} from "@tanstack/react-router";
import { useEffect } from "react";
import { Footer } from "./components/layout/footer";
import { Header } from "./components/layout/header";
import { BlurFade } from "./components/magicui/blur-fade";
import { DownloadsPage } from "./pages/downloads";
import { SyncPage } from "./pages/sync";

function RootLayout() {
  const router = useRouter();

  return (
    <HeroUIProvider
      navigate={(to, options) => router.navigate({ to, ...options })}
      useHref={(to) => router.buildLocation({ to }).href}
    >
      <ToastProvider />
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="m-auto w-full max-w-4xl flex-1 px-4 py-8">
          <Outlet />
        </main>
        <BlurFade delay={0.15} direction="up">
          <Footer />
        </BlurFade>
      </div>
    </HeroUIProvider>
  );
}

function NotFoundRedirect() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate({ to: "/" });
  }, [navigate]);
  return null;
}

const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: NotFoundRedirect,
});

const downloadsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DownloadsPage,
});

const syncRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sync",
  component: SyncPage,
});

const routeTree = rootRoute.addChildren([downloadsRoute, syncRoute]);

export const router = createRouter({ routeTree });

declare module "@react-types/shared" {
  interface RouterConfig {
    href: ToOptions["to"];
    routerOptions: Omit<NavigateOptions, keyof ToOptions>;
  }
}

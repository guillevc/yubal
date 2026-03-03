/* eslint-disable react-refresh/only-export-components */

import { Footer } from "@/components/layout/footer";
import { Header } from "@/components/layout/header";
import { JobsPage } from "@/pages/jobs";
import { SubscriptionsPage } from "@/pages/subscriptions";
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
        <main className="m-auto w-full max-w-5xl flex-1 px-4 py-6">
          <Outlet />
        </main>
        <Footer />
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

const jobsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: JobsPage,
});

const subscriptionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/playlists",
  component: SubscriptionsPage,
});

const routeTree = rootRoute.addChildren([jobsRoute, subscriptionsRoute]);

export const router = createRouter({ routeTree });

declare module "@react-types/shared" {
  interface RouterConfig {
    href: ToOptions["to"];
    routerOptions: Omit<NavigateOptions, keyof ToOptions>;
  }
}

import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ErrorBoundary } from "./components/common/error-boundary";
import { JobsProvider } from "./features/downloads/jobs-context";
import { ThemeProvider } from "./hooks/use-theme";
import "./index.css";
import { router } from "./router";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <JobsProvider>
          <main className="text-foreground">
            <RouterProvider router={router} />
          </main>
        </JobsProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </StrictMode>,
);

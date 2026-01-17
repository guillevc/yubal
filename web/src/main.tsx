import { HeroUIProvider, ToastProvider } from "@heroui/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ErrorBoundary } from "./components/common/error-boundary";
import { ThemeProvider } from "./hooks/use-theme";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <ToastProvider />
      <ErrorBoundary>
        <ThemeProvider>
          <main className="text-foreground">
            <App />
          </main>
        </ThemeProvider>
      </ErrorBoundary>
    </HeroUIProvider>
  </StrictMode>,
);

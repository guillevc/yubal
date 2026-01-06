import { HeroUIProvider, ToastProvider } from "@heroui/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ThemeProvider } from "./hooks/ThemeProvider";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <ToastProvider />
      <ThemeProvider>
        <main className="text-foreground bg-background">
          <App />
        </main>
      </ThemeProvider>
    </HeroUIProvider>
  </StrictMode>,
);

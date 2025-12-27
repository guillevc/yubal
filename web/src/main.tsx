import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App";
import { ThemeProvider } from "./hooks/useTheme";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </HeroUIProvider>
  </StrictMode>
);

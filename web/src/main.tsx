import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <main className="flexoki">
        <App />
      </main>
    </HeroUIProvider>
  </StrictMode>
);

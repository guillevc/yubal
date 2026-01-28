import { execSync } from "child_process";
import { resolve } from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

function getVersion(): string {
  if (process.env.VITE_VERSION) return process.env.VITE_VERSION;
  try {
    return execSync("git describe --tags --always", {
      encoding: "utf-8",
    }).trim();
  } catch {
    return "dev";
  }
}

function getCommitSha(): string {
  if (process.env.VITE_COMMIT_SHA) return process.env.VITE_COMMIT_SHA;
  try {
    return execSync("git rev-parse --short HEAD", {
      encoding: "utf-8",
    }).trim();
  } catch {
    return "dev";
  }
}

function isRelease(): boolean {
  if (process.env.VITE_IS_RELEASE !== undefined) {
    return process.env.VITE_IS_RELEASE === "true";
  }
  try {
    execSync("git describe --tags --exact-match HEAD", { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

export default defineConfig({
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  define: {
    __VERSION__: JSON.stringify(getVersion()),
    __COMMIT_SHA__: JSON.stringify(getCommitSha()),
    __IS_RELEASE__: isRelease(),
  },
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom"],
          "vendor-heroui": ["@heroui/react"],
          "vendor-icons": ["lucide-react"],
        },
      },
    },
  },
});

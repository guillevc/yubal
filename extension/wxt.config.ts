import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "wxt";

export default defineConfig({
  modules: ["@wxt-dev/auto-icons"],
  autoIcons: {
    baseIconPath: "assets/icon.svg",
    developmentIndicator: false,
  },
  manifest: {
    name: "Yubal",
    description: "Queue YouTube content to your yubal instance",
    permissions: ["storage", "activeTab", "tabs"],
    browser_specific_settings: {
      gecko: {
        id: "yubal@guillevc.xyz",
      },
    },
  },
  vite: () => ({
    plugins: [tailwindcss()],
  }),
});

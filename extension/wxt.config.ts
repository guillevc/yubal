import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "wxt";

export default defineConfig({
  zip: {
    name: "yubal-extension",
    artifactTemplate: "{{name}}-{{packageVersion}}-{{browser}}.zip",
    zipSources: false,
  },
  modules: ["@wxt-dev/auto-icons"],
  autoIcons: {
    baseIconPath: "assets/icon.svg",
    developmentIndicator: false,
  },
  manifest: {
    name: "yubal companion extension",
    short_name: "yubal",
    description: "Send YouTube URLs to your yubal instance",
    homepage_url: "https://yubal.guillevc.dev",
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

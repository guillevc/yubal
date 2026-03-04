import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "wxt";

export default defineConfig({
  zip: {
    name: "yubal-extension",
    artifactTemplate: "{{name}}-{{packageVersion}}-{{browser}}.zip",
    sourcesTemplate: "{{name}}-{{packageVersion}}-sources.zip",
    zipSources: true,
  },
  modules: ["@wxt-dev/auto-icons"],
  autoIcons: {
    baseIconPath: "assets/icon.svg",
    developmentIndicator: false,
  },
  manifest: {
    name: "yubal",
    description: "Send YouTube URLs to your yubal instance",
    homepage_url: "https://yubal.guillevc.dev",
    permissions: ["storage", "activeTab", "tabs"],
    browser_specific_settings: {
      gecko: {
        id: "yubal@guillevc.xyz",
        // @ts-expect-error -- not yet in WXT's type definitions
        data_collection_permissions: {
          required: ["none"],
          optional: [],
        },
      },
    },
  },
  vite: () => ({
    plugins: [tailwindcss()],
  }),
});

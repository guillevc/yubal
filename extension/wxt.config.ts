import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "wxt";

export default defineConfig({
  manifest: {
    name: "Yubal",
    description: "Queue YouTube content to your yubal instance",
    permissions: ["storage", "activeTab", "scripting"],
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

import { GLOBE_X_ICON, SETTINGS_ICON } from "@/lib/icons";
import { rawHtml } from "@/lib/raw-html";
import van from "vanjs-core";
import { Header } from "./header";

const { div, h1, p, button } = van.tags;

interface ConnectionErrorViewProps {
  onSettings: () => void;
}

export function ConnectionErrorView({ onSettings }: ConnectionErrorViewProps) {
  return div(
    Header({ onSettings }),
    div(
      { class: "p-4 flex flex-col gap-4" },
      div(
        { class: "flex flex-col items-center gap-1 px-4 py-2" },
        div(
          { class: "mb-2 text-mist-500 [&>svg]:size-10" },
          rawHtml(GLOBE_X_ICON),
        ),
        h1({ class: "text-base font-semibold" }, "Connection Failed"),
        p(
          { class: "text-center text-sm text-mist-400" },
          "Your server couldn't be reached. Check that it's running or update the URL in settings.",
        ),
      ),
      button(
        {
          class:
            "w-full flex items-center justify-center gap-2 rounded-lg border border-mist-700 bg-mist-800/50 px-4 py-2.5 text-sm font-semibold text-mist-200 transition-colors hover:border-mist-600 hover:bg-mist-800 [&>svg]:size-[18px] [&>svg]:shrink-0 [&>svg]:text-mist-400",
          onclick: onSettings,
        },
        rawHtml(SETTINGS_ICON),
        "Open Settings",
      ),
    ),
  );
}

import {
  EXTERNAL_LINK_ICON,
  HEADPHONE_OFF_ICON,
  HEADPHONES_ICON,
  PLAY_ICON,
} from "@/lib/icons";
import { rawHtml } from "@/lib/raw-html";
import van from "vanjs-core";
import { Header } from "./header";

const { div, h1, p, a, span } = van.tags;

interface UnsupportedUrlPageProps {
  onSettings: () => void;
}

export function UnsupportedUrlPage({ onSettings }: UnsupportedUrlPageProps) {
  const btnClass =
    "w-full flex items-center gap-2 rounded-lg border border-mist-700 bg-mist-800/50 px-4 py-2.5 text-sm font-semibold text-mist-200 transition-colors hover:border-mist-600 hover:bg-mist-800 [&>svg]:size-[18px] [&>svg]:shrink-0 [&>svg]:text-mist-400";

  return div(
    Header({ onSettings }),
    div(
      { class: "p-4 flex flex-col gap-4" },
      div(
        { class: "flex flex-col items-center gap-1 px-4 py-2" },
        div(
          { class: "mb-2 text-mist-500 [&>svg]:size-10" },
          rawHtml(HEADPHONE_OFF_ICON),
        ),
        h1({ class: "text-base font-semibold" }, "No Media Detected"),
        p(
          { class: "text-center text-sm text-mist-400" },
          "Open a track, playlist, or album on YouTube or YouTube Music to start downloading.",
        ),
      ),
      div(
        { class: "flex flex-col gap-2" },
        a(
          {
            href: "https://music.youtube.com",
            target: "_blank",
            class: btnClass,
          },
          rawHtml(HEADPHONES_ICON),
          "music.youtube.com",
          span(
            {
              class: "ml-auto self-center [&>svg]:size-3 [&>svg]:text-mist-500",
            },
            rawHtml(EXTERNAL_LINK_ICON),
          ),
        ),
        a(
          {
            href: "https://www.youtube.com",
            target: "_blank",
            class: btnClass,
          },
          rawHtml(PLAY_ICON),
          "youtube.com",
          span(
            {
              class: "ml-auto self-center [&>svg]:size-3 [&>svg]:text-mist-500",
            },
            rawHtml(EXTERNAL_LINK_ICON),
          ),
        ),
      ),
    ),
  );
}

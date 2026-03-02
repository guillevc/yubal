import van from "vanjs-core";
import { EXTERNAL_LINK_ICON } from "@/lib/icons";
import { rawHtml } from "@/lib/raw-html";
import { Header } from "./header";

const { div, p, a } = van.tags;

interface NotYouTubeViewProps {
  onSettings: () => void;
}

export function NotYouTubeView({ onSettings }: NotYouTubeViewProps) {
  const linkClass =
    "inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700 [&>svg]:size-3.5 [&>svg]:inline [&>svg]:align-[-1px]";

  return div(
    Header({ onSettings }),
    div(
      { class: "p-4 text-center" },
      p(
        { class: "text-sm text-mist-400" },
        "Navigate to a YouTube Music track or playlist.",
      ),
      div(
        { class: "mt-4 flex justify-center gap-4" },
        a(
          {
            href: "https://www.youtube.com",
            target: "_blank",
            class: linkClass,
          },
          "YouTube",
          rawHtml(EXTERNAL_LINK_ICON),
        ),
        a(
          {
            href: "https://music.youtube.com",
            target: "_blank",
            class: linkClass,
          },
          "YouTube Music",
          rawHtml(EXTERNAL_LINK_ICON),
        ),
      ),
    ),
  );
}

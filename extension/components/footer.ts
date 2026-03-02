import { GITHUB_ICON } from "@/lib/icons";
import { rawHtml } from "@/lib/raw-html";
import van, { type State } from "vanjs-core";

const { a, footer, div, span } = van.tags;

interface FooterProps {
  connected: State<boolean>;
}

export function Footer({ connected }: FooterProps) {
  const version = `v${browser.runtime.getManifest().version}`;

  return footer(
    {
      class:
        "flex items-center justify-between border-t border-mist-800 bg-mist-900 px-4 py-2.5",
    },
    () =>
      div(
        { class: "flex items-center gap-2" },
        span({
          class: `size-1.5 rounded-full ${connected.val ? "bg-green-500" : "bg-mist-600"}`,
        }),
        span(
          { class: "text-xs text-mist-500" },
          connected.val ? "Connected" : "Not Connected",
        ),
      ),
    a(
      {
        href: "https://yubal.guillevc.dev",
        target: "_blank",
        class:
          "flex items-center gap-1.5 font-semibold text-xs text-mist-500 hover:text-mist-300 transition-colors [&>svg]:size-3.5",
      },
      rawHtml(GITHUB_ICON),
      version,
    ),
  );
}

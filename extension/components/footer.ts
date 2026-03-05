import { GITHUB_ICON } from "@/lib/icons";
import { rawHtml } from "@/lib/raw-html";
import { yubalUrl } from "@/lib/storage";
import van, { type State } from "vanjs-core";

const { a, footer, div, span } = van.tags;

interface FooterProps {
  connected: State<boolean>;
}

export function Footer({ connected }: FooterProps) {
  const version = `v${browser.runtime.getManifest().version}`;
  const instanceUrl = van.state("");
  yubalUrl.getValue().then((url) => {
    if (url) instanceUrl.val = url;
  });

  return footer(
    {
      class:
        "flex items-center justify-between border-t border-mist-800 bg-mist-900 px-4 py-2.5",
    },
    () => {
      const dot = span({
        class: `size-1.5 rounded-full ${connected.val ? "bg-green-500" : "bg-mist-600"}`,
      });
      const label = span(
        { class: "text-xs" },
        connected.val ? "Connected" : "Not Connected",
      );
      const url = instanceUrl.val;
      if (url && connected.val) {
        return a(
          {
            href: url,
            target: "_blank",
            class:
              "flex items-center gap-2 text-mist-500 hover:text-mist-300 transition-colors",
          },
          dot,
          label,
        );
      }
      return div(
        { class: "flex items-center gap-2 text-mist-500" },
        dot,
        label,
      );
    },
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

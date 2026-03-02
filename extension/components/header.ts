import van from "vanjs-core";
import { ARROW_LEFT_ICON, SETTINGS_ICON, YUBAL_ICON } from "@/lib/icons";
import { rawHtml } from "@/lib/raw-html";

const { header, div, span, button } = van.tags;

interface HeaderProps {
  onBack?: () => void;
  onSettings?: () => void;
}

export function Header({ onBack, onSettings }: HeaderProps = {}) {
  const left = div(
    { class: "flex items-center gap-2.5" },
    ...(onBack
      ? [
          button(
            {
              type: "button",
              class:
                "flex items-center justify-center size-8 -ml-1 rounded-lg text-mist-400 hover:text-mist-200 hover:bg-mist-800 transition-colors [&>svg]:size-[18px]",
              onclick: onBack,
            },
            rawHtml(ARROW_LEFT_ICON),
          ),
        ]
      : []),
    div(
      {
        class:
          "flex items-center justify-center size-7 rounded-lg bg-primary-600/20 [&>svg]:size-5",
      },
      rawHtml(YUBAL_ICON),
    ),
    span({ class: "text-base font-bold text-mist-100" }, "yubal"),
  );

  return header(
    {
      class:
        "flex items-center justify-between border-b border-mist-800 bg-mist-900 px-4 py-3",
    },
    left,
    ...(onSettings
      ? [
          button(
            {
              type: "button",
              class:
                "flex items-center justify-center size-8 rounded-lg text-mist-400 hover:text-mist-200 hover:bg-mist-800 transition-colors [&>svg]:size-[18px]",
              onclick: onSettings,
            },
            rawHtml(SETTINGS_ICON),
          ),
        ]
      : []),
  );
}

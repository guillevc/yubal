import van from "vanjs-core";
import { rawHtml } from "@/lib/raw-html";

const { button, span: spanTag } = van.tags;

type ButtonPhase = "idle" | "loading" | "success" | "error";

type ClickResult = { status: "success"; text?: string } | { status: "error" };

interface ActionButtonProps {
  icon?: string;
  label: string;
  successText: string;
  errorText: string;
  style: string;
  onClick: () => Promise<ClickResult>;
}

export function ActionButton({
  icon,
  label,
  successText,
  errorText,
  style,
  onClick,
}: ActionButtonProps) {
  const phase = van.state<ButtonPhase>("idle");
  const overrideText = van.state<string | null>(null);

  let resetTimer: ReturnType<typeof setTimeout> | undefined;

  const text = van.derive(() => {
    switch (phase.val) {
      case "idle":
        return label;
      case "loading":
        return "";
      case "success":
        return overrideText.val ?? successText;
      case "error":
        return errorText;
    }
  });

  const cls = van.derive(() => {
    switch (phase.val) {
      case "success":
        return `${style} !border-green-500/30 !bg-green-500/10 !text-green-500`;
      case "error":
        return `${style} !border-red-400/30 !bg-red-400/10 !text-red-400`;
      default:
        return style;
    }
  });

  const disabled = van.derive(() => phase.val === "loading");

  async function handleClick() {
    if (phase.val === "loading") return;
    if (resetTimer) clearTimeout(resetTimer);
    phase.val = "loading";
    const result = await onClick();
    if (result.status === "success") {
      overrideText.val = result.text ?? null;
      phase.val = "success";
    } else {
      phase.val = "error";
    }
  }

  van.derive(() => {
    const p = phase.val;
    if (resetTimer) clearTimeout(resetTimer);
    if (p === "success") {
      resetTimer = setTimeout(() => {
        phase.val = "idle";
        overrideText.val = null;
      }, 2500);
    } else if (p === "error") {
      resetTimer = setTimeout(() => {
        phase.val = "idle";
      }, 3000);
    }
  });

  return button(
    {
      class: cls,
      disabled,
      onclick: handleClick,
    },
    () =>
      phase.val === "loading"
        ? spanTag({
            class:
              "inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent align-middle",
          })
        : icon
          ? spanTag(
              { class: "inline-flex items-center gap-2 [&>svg]:size-[18px]" },
              rawHtml(icon),
              text.val,
            )
          : text.val,
  );
}

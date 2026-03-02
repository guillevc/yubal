import van from "vanjs-core";
import { CIRCLE_CHECK_ICON, WIFI_ICON } from "@/lib/icons";
import { yubalUrl } from "@/lib/storage";
import { healthCheck } from "@/lib/api";
import { rawHtml } from "@/lib/raw-html";
import { Header } from "./header";

const { div, h1, p, input, button } = van.tags;

type TestPhase = "idle" | "loading" | "success" | "error";

interface SetupViewProps {
  showBack: boolean;
  onBack: () => void;
}

export function SetupView({ showBack, onBack }: SetupViewProps) {
  const statusText = van.state("");
  const statusClass = van.state("text-xs empty:hidden");
  const testPhase = van.state<TestPhase>("idle");
  const testErrorMsg = van.state("");

  const baseClass =
    "w-full flex items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-semibold transition-colors [&>svg]:size-[18px]";
  const defaultClass = `${baseClass} border-mist-700 bg-transparent text-mist-400 hover:border-mist-600 hover:text-mist-200`;
  const successClass = `${baseClass} border-green-500/30 bg-green-500/10 text-green-500`;
  const errorClass = `${baseClass} border-red-400/30 bg-red-400/10 text-red-400`;

  const testBtnClass = van.derive(() => {
    switch (testPhase.val) {
      case "success":
        return successClass;
      case "error":
        return errorClass;
      default:
        return defaultClass;
    }
  });

  const testDisabled = van.derive(() => testPhase.val === "loading");

  const urlInput = input({
    type: "url",
    class:
      "w-full rounded-lg border border-mist-700 bg-mist-900 px-3 py-2 font-mono text-sm text-mist-200 outline-none focus:border-primary-600",
    placeholder: "http://localhost:8642",
  });

  // Pre-fill if already configured
  yubalUrl.getValue().then((v: string | null) => {
    if (v) (urlInput as HTMLInputElement).value = v;
  });

  function getUrl() {
    return (urlInput as HTMLInputElement).value.trim().replace(/\/+$/, "");
  }

  const saveBtn = button(
    {
      type: "button",
      class:
        "w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-mist-950 transition-colors hover:bg-primary-700 [&>svg]:size-[18px]",
      onclick: async () => {
        const value = getUrl();
        if (!value) {
          statusText.val = "URL is required";
          statusClass.val = "text-xs text-red-400";
          return;
        }
        try {
          new URL(value);
        } catch {
          statusText.val = "Invalid URL format";
          statusClass.val = "text-xs text-red-400";
          return;
        }
        await yubalUrl.setValue(value);
        statusText.val = "Saved!";
        statusClass.val = "text-xs text-primary-600";
        onBack();
      },
    },
    rawHtml(CIRCLE_CHECK_ICON),
    " Save Configuration",
  );

  let resetTimer: ReturnType<typeof setTimeout> | undefined;

  const testBtn = button(
    {
      type: "button",
      class: testBtnClass,
      disabled: testDisabled,
      onclick: async () => {
        const value = getUrl();
        if (!value) {
          statusText.val = "Enter a URL first";
          statusClass.val = "text-xs text-red-400";
          return;
        }
        if (resetTimer) clearTimeout(resetTimer);
        testPhase.val = "loading";
        const res = await healthCheck(value);
        if (res.ok) {
          testPhase.val = "success";
          resetTimer = setTimeout(() => {
            testPhase.val = "idle";
          }, 2000);
        } else {
          testErrorMsg.val =
            res.error === "network_error"
              ? "Could not connect"
              : `Error: ${res.message}`;
          testPhase.val = "error";
        }
      },
    },
    () => {
      const row = "inline-flex items-center gap-2 [&>svg]:size-[18px]";
      switch (testPhase.val) {
        case "idle":
          return van.tags.span(
            { class: row },
            rawHtml(WIFI_ICON),
            " Test connection",
          );
        case "loading":
          return van.tags.span(
            { class: row },
            rawHtml(WIFI_ICON),
            " Connecting...",
          );
        case "success":
          return van.tags.span(
            { class: row },
            rawHtml(CIRCLE_CHECK_ICON),
            " Connected!",
          );
        case "error":
          return van.tags.span(
            { class: row },
            rawHtml(WIFI_ICON),
            ` ${testErrorMsg.val}`,
          );
      }
    },
  );

  return div(
    Header(showBack ? { onBack } : {}),
    div(
      { class: "p-4 flex flex-col gap-4" },
      div(
        { class: "flex flex-col gap-1" },
        h1({ class: "text-base font-semibold" }, "Connect to Server"),
        p(
          { class: "text-sm text-mist-400" },
          "Enter your self-hosted yubal server URL to start downloading tracks directly from your browser.",
        ),
      ),
      urlInput,
      () => p({ class: statusClass.val }, statusText.val),
      div({ class: "flex flex-col gap-2" }, saveBtn, testBtn),
    ),
  );
}

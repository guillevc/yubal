import { healthCheck } from "@/lib/api";
import { CIRCLE_CHECK_ICON, INFO_ICON, WIFI_ICON } from "@/lib/icons";
import { rawHtml } from "@/lib/raw-html";
import { yubalUrl, yubalUrlDraft } from "@/lib/storage";
import van from "vanjs-core";
import { Header } from "./header";

const { div, h1, p, label, span, input, button } = van.tags;

type TestPhase = "idle" | "loading" | "success" | "error";

interface SetupPageProps {
  showBack: boolean;
  onBack: () => void;
}

export function SetupPage({ showBack, onBack }: SetupPageProps) {
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
    oninput: () => {
      yubalUrlDraft.setValue((urlInput as HTMLInputElement).value);
    },
  });

  // Restore draft, then fall back to saved value
  yubalUrlDraft.getValue().then((draft) => {
    if (draft) {
      (urlInput as HTMLInputElement).value = draft;
    } else {
      yubalUrl.getValue().then((v: string | null) => {
        if (v) (urlInput as HTMLInputElement).value = v;
      });
    }
  });

  function getUrl() {
    return (urlInput as HTMLInputElement).value.trim().replace(/\/+$/, "");
  }

  const saveBtn = button(
    {
      type: "button",
      disabled: testDisabled,
      class:
        "w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-mist-950 transition-colors hover:bg-primary-700 disabled:opacity-50 [&>svg]:size-[18px]",
      onclick: async () => {
        const value = getUrl();
        if (!value) {
          statusText.val = "Enter a server URL";
          statusClass.val = "text-xs text-red-400";
          return;
        }
        try {
          new URL(value);
        } catch {
          statusText.val = "Not a valid URL";
          statusClass.val = "text-xs text-red-400";
          return;
        }
        const ok = await testConnection(value);
        if (!ok) return;
        await yubalUrl.setValue(value);
        await yubalUrlDraft.removeValue();
        onBack();
      },
    },
    rawHtml(CIRCLE_CHECK_ICON),
    " Save",
  );

  let resetTimer: ReturnType<typeof setTimeout> | undefined;

  async function testConnection(value: string): Promise<boolean> {
    if (resetTimer) clearTimeout(resetTimer);
    testPhase.val = "loading";
    const res = await healthCheck(value);
    if (res.ok) {
      testPhase.val = "success";
      resetTimer = setTimeout(() => {
        testPhase.val = "idle";
      }, 2000);
      return true;
    }
    testErrorMsg.val =
      res.error === "network_error"
        ? "Can't reach server"
        : `Error: ${res.message}`;
    testPhase.val = "error";
    return false;
  }

  const testBtn = button(
    {
      type: "button",
      class: testBtnClass,
      disabled: testDisabled,
      onclick: async () => {
        const value = getUrl();
        if (!value) {
          statusText.val = "Enter a server URL first";
          statusClass.val = "text-xs text-red-400";
          return;
        }
        await testConnection(value);
      },
    },
    () => {
      const row = "inline-flex items-center gap-2 [&>svg]:size-[18px]";
      switch (testPhase.val) {
        case "idle":
          return van.tags.span(
            { class: row },
            rawHtml(WIFI_ICON),
            " Test Connection",
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
        h1({ class: "text-base font-semibold" }, "Server Setup"),
        p(
          { class: "text-sm text-mist-400" },
          "Connect to your yubal server to start downloading tracks.",
        ),
      ),
      div(
        { class: "flex flex-col gap-1.5" },
        label({ class: "text-sm font-medium text-mist-200" }, "Server URL"),
        urlInput,
        span(
          {
            class:
              "inline-flex items-center gap-1 text-xs text-mist-500 [&>svg]:size-3 [&>svg]:shrink-0",
          },
          rawHtml(INFO_ICON),
          "Runs on port 8000 by default",
        ),
      ),
      () => p({ class: statusClass.val }, statusText.val),
      div({ class: "flex flex-col gap-2" }, saveBtn, testBtn),
    ),
  );
}

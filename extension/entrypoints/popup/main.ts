import "@/assets/index.css";
import { createJob, createSubscription, healthCheck } from "@/lib/api";
import {
  CIRCLE_CHECK_ICON,
  EXTERNAL_LINK_ICON,
  SETTINGS_ICON,
  WIFI_ICON,
  YUBAL_ICON,
} from "@/lib/icons";
import { yubalUrl } from "@/lib/storage";
import { el, setButtonState } from "@/lib/ui";
import { getContentType, isYouTubeUrl } from "@/lib/youtube";

const app = document.getElementById("app")!;

async function main() {
  app.innerHTML = "";

  const baseUrl = await yubalUrl.getValue();
  if (!baseUrl) {
    renderSetup();
    return;
  }

  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  const tabUrl = tab?.url ?? "";

  if (!isYouTubeUrl(tabUrl)) {
    renderNotYouTube();
    return;
  }

  renderYouTube(baseUrl, tab);
}

// --- Header ---

function renderHeader(onSettings?: () => void) {
  const header = el("header", {
    class:
      "flex items-center justify-between border-b border-mist-800 bg-mist-900 px-4 py-3",
  });

  const left = el("div", { class: "flex items-center gap-2.5" });

  const iconBox = el("div", {
    class:
      "flex items-center justify-center size-7 rounded-lg bg-primary-600/20 [&>svg]:size-5",
  });
  iconBox.innerHTML = YUBAL_ICON;

  const title = el(
    "span",
    { class: "text-base font-bold text-mist-100" },
    "yubal"
  );

  left.append(iconBox, title);
  header.append(left);

  if (onSettings) {
    const settingsBtn = el("button", {
      type: "button",
      class:
        "flex items-center justify-center size-8 rounded-lg text-mist-400 hover:text-mist-200 hover:bg-mist-800 transition-colors [&>svg]:size-[18px]",
    });
    settingsBtn.innerHTML = SETTINGS_ICON;
    settingsBtn.onclick = onSettings;
    header.append(settingsBtn);
  }

  return header;
}

// --- Setup View ---

function renderSetup(showBack = false) {
  app.innerHTML = "";

  app.append(renderHeader(showBack ? () => main() : undefined));

  const container = el("div", { class: "p-4 flex flex-col gap-4" });

  const heading = el(
    "h1",
    { class: "text-base font-semibold" },
    "Connect to Server"
  );

  const desc = el(
    "p",
    { class: "text-xs text-mist-400 leading-relaxed" },
    "Enter your self-hosted yubal server URL to start downloading tracks directly from your browser."
  );

  const input = el("input", {
    type: "url",
    class:
      "w-full rounded-lg border border-mist-700 bg-mist-900 px-3 py-2 font-mono text-sm text-mist-200 outline-none focus:border-primary-600",
    placeholder: "http://localhost:8642",
  }) as HTMLInputElement;

  const statusMsg = el("p", { class: "text-xs" });

  const saveBtn = el("button", {
    type: "button",
    class:
      "w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2 font-semibold text-mist-950 transition-colors hover:bg-primary-700 [&>svg]:size-[18px]",
  });
  saveBtn.innerHTML = `${CIRCLE_CHECK_ICON} Save Configuration`;

  const testBtn = el("button", {
    type: "button",
    class:
      "w-full flex items-center justify-center gap-2 rounded-lg border border-mist-700 bg-transparent px-4 py-2 text-sm text-mist-400 transition-colors hover:border-mist-600 hover:text-mist-200 [&>svg]:size-[18px]",
  });
  testBtn.innerHTML = `${WIFI_ICON} Test connection`;

  saveBtn.onclick = async () => {
    const value = input.value.trim().replace(/\/+$/, "");
    if (!value) {
      statusMsg.textContent = "URL is required";
      statusMsg.className = "text-xs text-red-400";
      return;
    }
    try {
      new URL(value);
    } catch {
      statusMsg.textContent = "Invalid URL format";
      statusMsg.className = "text-xs text-red-400";
      return;
    }
    await yubalUrl.setValue(value);
    statusMsg.textContent = "Saved!";
    statusMsg.className = "text-xs text-primary-600";
    await main();
  };

  testBtn.onclick = async () => {
    const value = input.value.trim().replace(/\/+$/, "");
    if (!value) {
      statusMsg.textContent = "Enter a URL first";
      statusMsg.className = "text-xs text-red-400";
      return;
    }
    statusMsg.textContent = "Connecting...";
    statusMsg.className = "text-xs text-mist-400";
    const res = await healthCheck(value);
    if (res.ok) {
      statusMsg.textContent = "Connected!";
      statusMsg.className = "text-xs text-primary-600";
    } else {
      statusMsg.textContent =
        res.error === "network_error"
          ? "Could not connect"
          : `Error: ${res.message}`;
      statusMsg.className = "text-xs text-red-400";
    }
  };

  // Pre-fill if already configured
  yubalUrl.getValue().then((v: string | null) => {
    if (v) input.value = v;
  });

  container.append(heading, desc, input, statusMsg, saveBtn, testBtn);
  app.append(container);
}

// --- Not YouTube View ---

function renderNotYouTube() {
  app.innerHTML = "";

  app.append(renderHeader(() => renderSetup(true)));

  const container = el("div", { class: "p-6 text-center" });

  const msg = el(
    "p",
    { class: "text-sm text-mist-400" },
    "Navigate to a YouTube Music track or playlist."
  );

  const links = el("div", { class: "mt-4 flex justify-center gap-4" });

  const ytLink = el(
    "a",
    {
      href: "https://www.youtube.com",
      target: "_blank",
      class:
        "inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700 [&>svg]:size-3.5 [&>svg]:inline [&>svg]:align-[-1px]",
    },
    "YouTube"
  );
  ytLink.insertAdjacentHTML("beforeend", EXTERNAL_LINK_ICON);

  const ytMusicLink = el(
    "a",
    {
      href: "https://music.youtube.com",
      target: "_blank",
      class:
        "inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700 [&>svg]:size-3.5 [&>svg]:inline [&>svg]:align-[-1px]",
    },
    "YouTube Music"
  );
  ytMusicLink.insertAdjacentHTML("beforeend", EXTERNAL_LINK_ICON);

  links.append(ytLink, ytMusicLink);
  container.append(msg, links);
  app.append(container);
}

// --- YouTube View ---

function renderYouTube(baseUrl: string, tab: Browser.tabs.Tab) {
  app.innerHTML = "";

  app.append(renderHeader(() => renderSetup(true)));

  const tabUrl = tab.url ?? "";
  const contentType = getContentType(tabUrl);

  // Title
  const title = el(
    "h2",
    { class: "px-4 pt-3 text-sm font-bold leading-snug line-clamp-2" },
    tab.title ?? "Untitled"
  );

  // Content type pill
  let pill: HTMLElement | null = null;
  if (contentType === "track") {
    pill = el(
      "span",
      {
        class:
          "mx-4 mt-2 inline-block rounded-full bg-primary-600/15 px-3 py-0.5 text-xs font-medium text-primary-600",
      },
      "Track"
    );
  } else if (contentType === "playlist") {
    pill = el(
      "span",
      {
        class:
          "mx-4 mt-2 inline-block rounded-full bg-secondary-700/15 px-3 py-0.5 text-xs font-medium text-secondary-700",
      },
      "Playlist / Album"
    );
  }

  // Buttons
  const buttons = el("div", { class: "flex flex-col gap-2 p-4" });

  const downloadBtn = el(
    "button",
    {
      type: "button",
      class:
        "w-full rounded-lg bg-primary-600 px-4 py-2.5 font-semibold text-mist-950 transition-colors hover:bg-primary-700 disabled:opacity-50",
    },
    "Download"
  );

  const downloadOpts = {
    idleText: "Download",
    successText: "Queued!",
    errorText: "Failed \u2014 tap to retry",
    onClick: async () => {
      const res = await createJob(baseUrl, tabUrl);
      if (res.ok) {
        setButtonState(downloadBtn, "success", downloadOpts);
      } else if (res.status === 409) {
        setButtonState(downloadBtn, "success", {
          ...downloadOpts,
          successText: "Already downloading",
        });
      } else {
        setButtonState(downloadBtn, "error", downloadOpts);
      }
    },
  };

  setButtonState(downloadBtn, "idle", downloadOpts);
  buttons.append(downloadBtn);

  if (contentType === "playlist") {
    const subBtn = el(
      "button",
      {
        type: "button",
        class:
          "w-full rounded-lg border border-mist-700 bg-mist-800 px-4 py-2.5 text-mist-200 transition-colors hover:border-mist-600 disabled:opacity-50",
      },
      "Subscribe"
    );

    const subOpts = {
      idleText: "Subscribe",
      successText: "Subscribed!",
      errorText: "Failed \u2014 tap to retry",
      onClick: async () => {
        const res = await createSubscription(baseUrl, tabUrl);
        if (res.ok) {
          setButtonState(subBtn, "success", subOpts);
        } else if (res.status === 409) {
          setButtonState(subBtn, "success", {
            ...subOpts,
            successText: "Already subscribed",
          });
        } else {
          setButtonState(subBtn, "error", subOpts);
        }
      },
    };

    setButtonState(subBtn, "idle", subOpts);
    buttons.append(subBtn);
  }

  // Assemble
  app.append(title);
  if (pill) app.append(pill);
  app.append(buttons);
}

main();

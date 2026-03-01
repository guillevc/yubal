import "@/assets/index.css";
import { createJob, createSubscription, healthCheck } from "@/lib/api";
import { EXTERNAL_LINK_ICON, GEAR_ICON, YUBAL_ICON } from "@/lib/icons";
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

// --- Setup View ---

function renderSetup(showBack = false) {
  app.innerHTML = "";

  const heading = el(
    "h1",
    { class: "text-lg font-semibold" },
    "Connect to yubal"
  );

  const input = el("input", {
    type: "url",
    class:
      "mt-3 w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 font-mono text-sm text-neutral-200 outline-none focus:border-primary-600",
    placeholder: "http://localhost:8642",
  }) as HTMLInputElement;

  const statusMsg = el("p", { class: "mt-2 text-xs" });

  const saveBtn = el(
    "button",
    {
      type: "button",
      class:
        "mt-3 w-full rounded-lg bg-primary-600 px-4 py-2 font-semibold text-black transition-colors hover:bg-primary-700",
    },
    "Save"
  );

  const testBtn = el(
    "button",
    {
      type: "button",
      class:
        "mt-2 w-full rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 text-sm text-neutral-300 transition-colors hover:border-neutral-600",
    },
    "Test connection"
  );

  saveBtn.onclick = async () => {
    const value = input.value.trim().replace(/\/+$/, "");
    if (!value) {
      statusMsg.textContent = "URL is required";
      statusMsg.className = "mt-2 text-xs text-red-400";
      return;
    }
    try {
      new URL(value);
    } catch {
      statusMsg.textContent = "Invalid URL format";
      statusMsg.className = "mt-2 text-xs text-red-400";
      return;
    }
    await yubalUrl.setValue(value);
    statusMsg.textContent = "Saved!";
    statusMsg.className = "mt-2 text-xs text-primary-600";
    await main();
  };

  testBtn.onclick = async () => {
    const value = input.value.trim().replace(/\/+$/, "");
    if (!value) {
      statusMsg.textContent = "Enter a URL first";
      statusMsg.className = "mt-2 text-xs text-red-400";
      return;
    }
    statusMsg.textContent = "Connecting...";
    statusMsg.className = "mt-2 text-xs text-neutral-400";
    const res = await healthCheck(value);
    if (res.ok) {
      statusMsg.textContent = "Connected!";
      statusMsg.className = "mt-2 text-xs text-primary-600";
    } else {
      statusMsg.textContent =
        res.error === "network_error"
          ? "Could not connect"
          : `Error: ${res.message}`;
      statusMsg.className = "mt-2 text-xs text-red-400";
    }
  };

  // Pre-fill if already configured
  yubalUrl.getValue().then((v: string | null) => {
    if (v) input.value = v;
  });

  const container = el("div", { class: "p-4" });

  if (showBack) {
    const backBtn = el(
      "button",
      {
        type: "button",
        class: "mb-3 text-sm text-neutral-400 hover:text-neutral-200",
      },
      "\u2190 Back"
    );
    backBtn.onclick = () => main();
    container.append(backBtn);
  }

  container.append(heading, input, statusMsg, saveBtn, testBtn);
  app.append(container);
}

// --- Not YouTube View ---

function renderNotYouTube() {
  app.innerHTML = "";

  const container = el("div", { class: "p-6 text-center" });

  const msg = el(
    "p",
    { class: "text-sm text-neutral-400" },
    "Navigate to a YouTube Music track or playlist."
  );

  const links = el("div", { class: "mt-4 flex justify-center gap-4" });

  const ytLink = el(
    "a",
    {
      href: "https://www.youtube.com",
      target: "_blank",
      class:
        "inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700",
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
        "inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700",
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

  const tabUrl = tab.url ?? "";
  const contentType = getContentType(tabUrl);

  // Header
  const header = el("div", {
    class: "flex items-center justify-between p-4 pb-0",
  });

  const iconContainer = el("div", null);
  iconContainer.innerHTML = YUBAL_ICON;

  const gearBtn = el("button", {
    type: "button",
    class: "text-neutral-400 hover:text-neutral-200 transition-colors",
  });
  gearBtn.innerHTML = GEAR_ICON;
  gearBtn.onclick = () => renderSetup(true);

  header.append(iconContainer, gearBtn);

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
        "w-full rounded-lg bg-primary-600 px-4 py-2.5 font-semibold text-black transition-colors hover:bg-primary-700 disabled:opacity-50",
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
          "w-full rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2.5 text-neutral-200 transition-colors hover:border-neutral-600 disabled:opacity-50",
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
  app.append(header, title);
  if (pill) app.append(pill);
  app.append(buttons);
}

main();

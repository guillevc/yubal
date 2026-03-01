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
import { extractTrackInfo, getContentType, isYouTubeUrl } from "@/lib/youtube";

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

  const hdr = el("div", { class: "flex flex-col gap-1" });
  hdr.append(
    el("h1", { class: "text-base font-semibold" }, "Connect to Server"),
    el(
      "p",
      { class: "text-xs text-mist-400 leading-relaxed" },
      "Enter your self-hosted yubal server URL to start downloading tracks directly from your browser."
    )
  );

  const input = el("input", {
    type: "url",
    class:
      "w-full rounded-lg border border-mist-700 bg-mist-900 px-3 py-2 font-mono text-sm text-mist-200 outline-none focus:border-primary-600",
    placeholder: "http://localhost:8642",
  }) as HTMLInputElement;

  const statusMsg = el("p", { class: "text-xs empty:hidden" });

  const saveBtn = el("button", {
    type: "button",
    class:
      "w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-mist-950 transition-colors hover:bg-primary-700 [&>svg]:size-[18px]",
  });
  saveBtn.innerHTML = `${CIRCLE_CHECK_ICON} Save Configuration`;

  const testBtn = el("button", {
    type: "button",
    class:
      "w-full flex items-center justify-center gap-2 rounded-lg border border-mist-700 bg-transparent px-4 py-2.5 text-sm font-semibold text-mist-400 transition-colors hover:border-mist-600 hover:text-mist-200 [&>svg]:size-[18px]",
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

  const testBaseClass =
    "w-full flex items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-semibold transition-colors [&>svg]:size-[18px]";
  const testDefaultClass = `${testBaseClass} border-mist-700 bg-transparent text-mist-400 hover:border-mist-600 hover:text-mist-200`;
  const testSuccessClass = `${testBaseClass} border-green-500/30 bg-green-500/10 text-green-500`;
  const testErrorClass = `${testBaseClass} border-red-400/30 bg-red-400/10 text-red-400`;
  const testDefaultHTML = `${WIFI_ICON} Test connection`;

  testBtn.onclick = async () => {
    const value = input.value.trim().replace(/\/+$/, "");
    if (!value) {
      statusMsg.textContent = "Enter a URL first";
      statusMsg.className = "text-xs text-red-400";
      return;
    }
    testBtn.innerHTML = `${WIFI_ICON} Connecting...`;
    testBtn.disabled = true;
    const res = await healthCheck(value);
    if (res.ok) {
      testBtn.innerHTML = `${CIRCLE_CHECK_ICON} Connected!`;
      testBtn.className = testSuccessClass;
      setTimeout(() => {
        testBtn.innerHTML = testDefaultHTML;
        testBtn.className = testDefaultClass;
        testBtn.disabled = false;
      }, 2000);
    } else {
      testBtn.innerHTML = `${WIFI_ICON} ${res.error === "network_error" ? "Could not connect" : `Error: ${res.message}`}`;
      testBtn.className = testErrorClass;
      testBtn.disabled = false;
    }
  };

  // Pre-fill if already configured
  yubalUrl.getValue().then((v: string | null) => {
    if (v) input.value = v;
  });

  const actions = el("div", { class: "flex flex-col gap-2" });
  actions.append(saveBtn, testBtn);
  container.append(hdr, input, statusMsg, actions);
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

async function renderYouTube(baseUrl: string, tab: Browser.tabs.Tab) {
  app.innerHTML = "";

  app.append(renderHeader(() => renderSetup(true)));

  const tabUrl = tab.url ?? "";
  const contentType = getContentType(tabUrl);

  // Title & artist — extract from page DOM, fall back to tab title
  const info =
    tab.id != null
      ? await extractTrackInfo(tab.id)
      : { title: null, artist: null };
  const title = el(
    "h2",
    { class: "px-4 pt-2 text-lg font-bold leading-snug line-clamp-2" },
    info.title ?? tab.title ?? "Untitled"
  );
  const artist = info.artist
    ? el(
        "p",
        { class: "px-4 pt-0.5 text-sm text-mist-400 line-clamp-2" },
        info.artist
      )
    : null;

  // Content type pill
  let pill: HTMLElement | null = null;
  if (contentType === "track") {
    pill = el(
      "span",
      {
        class:
          "mx-4 mt-3 inline-block rounded-full bg-primary-600/15 px-3 py-0.5 text-xs font-medium text-primary-600",
      },
      "Track"
    );
  } else if (contentType === "playlist") {
    pill = el(
      "span",
      {
        class:
          "mx-4 mt-3 inline-block rounded-full bg-secondary-700/15 px-3 py-0.5 text-xs font-medium text-secondary-700",
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
        "w-full rounded-lg text-sm bg-primary-600 px-4 py-2.5 font-semibold text-mist-950 transition-colors hover:bg-primary-700 disabled:opacity-50",
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
          "w-full text-sm rounded-lg border font-semibold border-mist-700 bg-mist-800 px-4 py-2.5 text-mist-200 transition-colors hover:border-mist-600 disabled:opacity-50",
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
  if (pill) app.append(pill);
  app.append(title);
  if (artist) app.append(artist);
  app.append(buttons);
}

main();

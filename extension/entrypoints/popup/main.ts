import "@/assets/index.css";
import van from "vanjs-core";
import { yubalUrl, yubalUrlDraft } from "@/lib/storage";
import { isYouTubeUrl } from "@/lib/youtube";
import { SetupPage } from "@/components/setup-page";
import { ConnectionErrorPage } from "@/components/connection-error-page";
import { UnsupportedUrlPage } from "@/components/unsupported-url-page";
import { LoadingPage } from "@/components/loading-page";
import { YouTubePage } from "@/components/youtube-page";
import { Footer } from "@/components/footer";
import { healthCheck, getContentInfo } from "@/lib/api";

const view = van.state<Element>(document.createElement("div"));
const connected = van.state(false);

const app = document.getElementById("app")!;
van.add(app, () => view.val, Footer({ connected }));

let navId = 0;

function goToSetup(showBack: boolean) {
  navId++;
  view.val = SetupPage({
    showBack,
    onBack: () => {
      yubalUrlDraft.removeValue();
      refresh();
    },
  });
}

async function refresh() {
  const id = ++navId;

  const baseUrl = await yubalUrl.getValue();
  if (id !== navId) return;

  if (!baseUrl) {
    connected.val = false;
    goToSetup(false);
    return;
  }

  const onSettings = () => goToSetup(true);

  const health = await healthCheck(baseUrl);
  if (id !== navId) return;

  if (!health.ok) {
    connected.val = false;
    view.val = ConnectionErrorPage({ onSettings });
    return;
  }

  connected.val = true;

  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  if (id !== navId) return;

  const tab = tabs[0];
  const tabUrl = tab?.url ?? "";

  if (!isYouTubeUrl(tabUrl)) {
    view.val = UnsupportedUrlPage({ instanceUrl: baseUrl, onSettings });
    return;
  }

  view.val = LoadingPage({ instanceUrl: baseUrl, onSettings });

  const info = await getContentInfo(baseUrl, tabUrl);
  if (id !== navId) return;

  if (!info.ok) {
    view.val = UnsupportedUrlPage({ instanceUrl: baseUrl, onSettings });
    return;
  }

  view.val = YouTubePage({
    baseUrl,
    tabUrl,
    contentInfo: info.data,
    onSettings,
  });
}

async function init() {
  const baseUrl = await yubalUrl.getValue();
  if (!baseUrl) {
    goToSetup(false);
    return;
  }

  const draft = await yubalUrlDraft.getValue();
  if (draft) {
    goToSetup(true);
    return;
  }

  refresh();
}

init();

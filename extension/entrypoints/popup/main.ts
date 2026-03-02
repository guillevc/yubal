import "@/assets/index.css";
import van from "vanjs-core";
import { yubalUrl, yubalUrlDraft } from "@/lib/storage";
import { isYouTubeUrl } from "@/lib/youtube";
import { SetupView } from "@/components/setup-view";
import { ConnectionErrorView } from "@/components/connection-error-view";
import { NotYouTubeView } from "@/components/not-youtube-view";
import { YouTubeView } from "@/components/youtube-view";
import { healthCheck } from "@/lib/api";

const view = van.state<Element>(document.createElement("div"));

const app = document.getElementById("app")!;
van.add(app, () => view.val);

let navId = 0;

function goToSetup(showBack: boolean) {
  view.val = SetupView({
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
    goToSetup(false);
    return;
  }

  const onSettings = () => goToSetup(true);

  const health = await healthCheck(baseUrl);
  if (id !== navId) return;

  if (!health.ok) {
    view.val = ConnectionErrorView({ onSettings });
    return;
  }

  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  if (id !== navId) return;

  const tab = tabs[0];
  const tabUrl = tab?.url ?? "";

  if (!isYouTubeUrl(tabUrl)) {
    view.val = NotYouTubeView({ onSettings });
    return;
  }

  const el = await YouTubeView({ baseUrl, tab, onSettings });
  if (id !== navId) return;

  view.val = el;
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

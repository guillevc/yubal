import "@/assets/index.css";
import van from "vanjs-core";
import { yubalUrl } from "@/lib/storage";
import { isYouTubeUrl } from "@/lib/youtube";
import { SetupView } from "@/components/setup-view";
import { NotYouTubeView } from "@/components/not-youtube-view";
import { YouTubeView } from "@/components/youtube-view";

const app = document.getElementById("app")!;

function navigate(view: Element) {
  app.innerHTML = "";
  van.add(app, view);
}

async function main() {
  const baseUrl = await yubalUrl.getValue();
  if (!baseUrl) {
    navigate(SetupView({ showBack: false, onBack: main }));
    return;
  }

  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  const tabUrl = tab?.url ?? "";

  if (!isYouTubeUrl(tabUrl)) {
    navigate(
      NotYouTubeView({
        onSettings: () => navigate(SetupView({ showBack: true, onBack: main })),
      }),
    );
    return;
  }

  navigate(
    await YouTubeView({
      baseUrl,
      tab,
      onSettings: () => navigate(SetupView({ showBack: true, onBack: main })),
    }),
  );
}

main();

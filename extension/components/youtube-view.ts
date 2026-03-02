import van from "vanjs-core";
import { createJob, createSubscription } from "@/lib/api";
import { DOWNLOAD_ICON } from "@/lib/icons";
import { extractTrackInfo } from "@/lib/youtube";
import { getContentType } from "@/lib/youtube";
import { Header } from "./header";
import { ActionButton } from "./action-button";

const { div, h2, p, span } = van.tags;

interface YouTubeViewProps {
  baseUrl: string;
  tab: Browser.tabs.Tab;
  onSettings: () => void;
}

export async function YouTubeView({
  baseUrl,
  tab,
  onSettings,
}: YouTubeViewProps) {
  const tabUrl = tab.url ?? "";
  const contentType = getContentType(tabUrl);

  const info =
    tab.id != null
      ? await extractTrackInfo(tab.id)
      : { title: null, artist: null };

  const title = h2(
    { class: "px-4 pt-2 text-lg font-bold leading-snug line-clamp-2" },
    info.title ?? tab.title ?? "Untitled",
  );

  const artistEl = info.artist
    ? p(
        { class: "px-4 pt-0.5 text-sm text-mist-400 line-clamp-2" },
        info.artist,
      )
    : null;

  let pill: Element | null = null;
  if (contentType === "track") {
    pill = span(
      {
        class:
          "mx-4 mt-3 inline-block rounded-full bg-primary-600/15 px-3 py-0.5 text-xs font-medium text-primary-600",
      },
      "Track",
    );
  } else if (contentType === "playlist") {
    pill = span(
      {
        class:
          "mx-4 mt-3 inline-block rounded-full bg-secondary-700/15 px-3 py-0.5 text-xs font-medium text-secondary-700",
      },
      "Playlist",
    );
  }

  const downloadBtn = ActionButton({
    icon: DOWNLOAD_ICON,
    label: "Download",
    successText: "Queued!",
    errorText: "Failed \u2014 try again",
    style:
      "w-full flex items-center justify-center gap-2 rounded-lg text-sm bg-primary-600 px-4 py-2.5 font-semibold text-mist-950 transition-colors hover:bg-primary-700 disabled:opacity-50",
    onClick: async () => {
      const res = await createJob(baseUrl, tabUrl);
      if (res.ok) return { status: "success" };
      if (res.status === 409)
        return { status: "success", text: "Already queued" };
      return { status: "error" };
    },
  });

  const buttons = [downloadBtn];

  if (contentType === "playlist") {
    const subBtn = ActionButton({
      label: "Subscribe",
      successText: "Subscribed!",
      errorText: "Failed \u2014 try again",
      style:
        "w-full flex items-center justify-center gap-2 text-sm rounded-lg border font-semibold border-mist-700 bg-mist-800 px-4 py-2.5 text-mist-200 transition-colors hover:border-mist-600 disabled:opacity-50",
      onClick: async () => {
        const res = await createSubscription(baseUrl, tabUrl);
        if (res.ok) return { status: "success" };
        if (res.status === 409)
          return { status: "success", text: "Already subscribed" };
        return { status: "error" };
      },
    });
    buttons.push(subBtn);
  }

  return div(
    Header({ onSettings }),
    ...(pill ? [pill] : []),
    title,
    ...(artistEl ? [artistEl] : []),
    div({ class: "flex flex-col gap-2 p-4" }, ...buttons),
  );
}

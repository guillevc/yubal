import { type ContentInfo, createJob, createSubscription } from "@/lib/api";
import { DOWNLOAD_ICON } from "@/lib/icons";
import van from "vanjs-core";
import { ActionButton } from "./action-button";
import { Header } from "./header";

const { div, h2, img, p, span } = van.tags;

const PILL_STYLES: Record<
  ContentInfo["kind"],
  { class: string; label: string }
> = {
  track: {
    class:
      "self-start rounded-full bg-primary-600/15 px-2.5 py-0.5 text-xs font-medium text-primary-600",
    label: "Track",
  },
  playlist: {
    class:
      "self-start rounded-full bg-secondary-700/15 px-2.5 py-0.5 text-xs font-medium text-secondary-700",
    label: "Playlist",
  },
  album: {
    class:
      "self-start rounded-full bg-secondary-700/15 px-2.5 py-0.5 text-xs font-medium text-secondary-700",
    label: "Album",
  },
};

interface YouTubePageProps {
  baseUrl: string;
  tabUrl: string;
  contentInfo: ContentInfo;
  onSettings: () => void;
}

export function YouTubePage({
  baseUrl,
  tabUrl,
  contentInfo,
  onSettings,
}: YouTubePageProps) {
  const { kind, title, artist, year, track_count, thumbnail_url } = contentInfo;

  const pillStyle = PILL_STYLES[kind];
  const pill = span({ class: pillStyle.class }, pillStyle.label);

  const titleSuffix = kind === "album" && year ? ` (${year})` : "";
  const titleEl = h2(
    { class: "text-sm font-bold leading-snug line-clamp-2" },
    title + titleSuffix,
  );

  const metaParts: string[] = [artist];
  if (kind !== "track" && track_count != null) {
    metaParts.push(`${track_count} tracks`);
  }
  const metaEl = p(
    { class: "text-xs text-mist-400 line-clamp-1" },
    metaParts.join(" \u00b7 "),
  );

  const infoSection = div(
    { class: "flex items-center gap-3.5 px-4 pt-3" },
    ...(thumbnail_url
      ? [
          img({
            src: thumbnail_url,
            alt: "",
            class: "size-16 shrink-0 rounded-lg object-cover",
          }),
        ]
      : []),
    div({ class: "flex min-w-0 flex-col gap-1" }, pill, titleEl, metaEl),
  );

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

  if (kind !== "track") {
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
    infoSection,
    div({ class: "flex flex-col gap-2 p-4" }, ...buttons),
  );
}

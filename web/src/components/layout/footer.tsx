import { GithubIcon, KofiIcon } from "@/components/icons";

export function Footer() {
  return (
    <footer className="mx-auto max-w-4xl px-4 py-6">
      <div className="flex flex-col items-center gap-2 text-center">
        <p className="text-foreground-500 font-mono text-xs">
          Made by{" "}
          <a
            href="https://github.com/guillevc"
            target="_blank"
            rel="noopener noreferrer"
            className="group text-primary hover:text-foreground"
          >
            <GithubIcon className="-mt-px inline h-4 w-4" />{" "}
            <span className="group-hover:underline">guillevc</span>
          </a>
          {" · Support via "}
          <a
            href="https://ko-fi.com/guillevc"
            target="_blank"
            rel="noopener noreferrer"
            className="group text-primary hover:text-[#FF5E5B]"
          >
            <KofiIcon className="-mt-px inline h-4 w-4" />{" "}
            <span className="group-hover:underline">Ko-fi</span>
          </a>
        </p>
        <p className="text-foreground-400 font-mono text-xs">
          Powered by{" "}
          <a
            href="https://github.com/yt-dlp/yt-dlp"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground hover:underline"
          >
            yt-dlp
          </a>
          {" & "}
          <a
            href="https://github.com/sigma67/ytmusicapi"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground hover:underline"
          >
            ytmusicapi
          </a>
          {" · "}
          <a
            href={`https://github.com/guillevc/yubal/${__IS_RELEASE__ ? `releases/tag/${__VERSION__}` : `commit/${__COMMIT_SHA__}`}`}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground hover:underline"
          >
            {__VERSION__}
          </a>
        </p>
      </div>
    </footer>
  );
}

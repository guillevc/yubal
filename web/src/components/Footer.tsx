export function Footer() {
  return (
    <footer className="mt-6 space-y-1 text-center">
      <p className="text-default-500/50 font-mono text-xs">
        For educational purposes only
      </p>
      <p className="text-default-500/50 font-mono text-xs">
        Made by{" "}
        <a
          href="https://github.com/guillevc"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary/70 hover:text-primary hover:underline"
        >
          guillevc
        </a>
        {" · Powered by "}
        <a
          href="https://github.com/yt-dlp/yt-dlp"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary/70 hover:text-primary hover:underline"
        >
          yt-dlp
        </a>
        {" & "}
        <a
          href="https://github.com/beetbox/beets"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary/70 hover:text-primary hover:underline"
        >
          beets
        </a>
      </p>
    </footer>
  );
}

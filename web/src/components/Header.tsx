import { Music2 } from "lucide-react";

export function Header() {
  return (
    <header className="mb-6 flex items-center gap-3">
      <div className="border-primary/20 bg-primary/10 rounded-lg border p-2.5">
        <Music2 className="text-primary h-5 w-5" />
      </div>
      <div>
        <h1 className="text-foreground font-mono text-xl font-semibold tracking-tight">
          yubal
        </h1>
        <p className="text-foreground-500 font-mono text-xs">v0.1.0</p>
      </div>
    </header>
  );
}

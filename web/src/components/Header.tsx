import { Button } from "@heroui/react";
import { Moon, Music2, Sun } from "lucide-react";
import { useTheme } from "../hooks/useTheme";

export function Header() {
  const { theme, toggle } = useTheme();

  return (
    <header className="mb-6 flex items-center gap-3">
      <div className="border-primary/20 bg-primary/10 rounded-lg border p-2.5">
        <Music2 className="text-primary h-5 w-5" />
      </div>
      <div className="flex-1">
        <h1 className="text-foreground font-mono text-xl font-semibold tracking-tight">
          yubal
        </h1>
        <p className="text-foreground-500 font-mono text-xs">v0.1.0</p>
      </div>
      <Button
        isIconOnly
        variant="light"
        aria-label="Toggle theme"
        onPress={toggle}
      >
        {theme === "dark" ? (
          <Moon className="h-5 w-5" />
        ) : (
          <Sun className="h-5 w-5" />
        )}
      </Button>
    </header>
  );
}

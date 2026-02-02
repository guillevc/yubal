import { Button } from "@heroui/react";
import { MoonIcon, SunIcon } from "lucide-react";
import { useCallback, useRef } from "react";
import { flushSync } from "react-dom";
import { useTheme } from "@/hooks/use-theme";

type Props = {
  duration?: number;
};

export function AnimatedThemeToggler({ duration = 400 }: Props) {
  const { theme, toggle } = useTheme();
  const buttonRef = useRef<HTMLButtonElement>(null);

  const handleToggle = useCallback(async () => {
    // Fallback for browsers that don't support View Transitions
    if (!document.startViewTransition) {
      toggle();
      return;
    }

    const button = buttonRef.current;
    if (!button) {
      toggle();
      return;
    }

    // Start the view transition
    const transition = document.startViewTransition(() => {
      flushSync(() => {
        toggle();
      });
    });

    // Wait for the transition to be ready
    await transition.ready;

    // Calculate the animation origin from button center
    const { top, left, width, height } = button.getBoundingClientRect();
    const x = left + width / 2;
    const y = top + height / 2;

    // Calculate max radius to cover the entire viewport
    const maxRadius = Math.hypot(
      Math.max(left, window.innerWidth - left),
      Math.max(top, window.innerHeight - top),
    );

    // Animate the new view with an expanding circle
    document.documentElement.animate(
      {
        clipPath: [
          `circle(0px at ${x}px ${y}px)`,
          `circle(${maxRadius}px at ${x}px ${y}px)`,
        ],
      },
      {
        duration,
        easing: "ease-out",
        pseudoElement: "::view-transition-new(root)",
      },
    );
  }, [toggle, duration]);

  return (
    <Button
      ref={buttonRef}
      isIconOnly
      size="sm"
      variant="light"
      aria-label="Toggle theme"
      onPress={handleToggle}
    >
      {theme === "dark" ? (
        <MoonIcon className="h-5 w-5" />
      ) : (
        <SunIcon className="h-5 w-5" />
      )}
    </Button>
  );
}

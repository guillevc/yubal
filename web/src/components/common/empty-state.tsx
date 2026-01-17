import type { LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  /** Lucide icon component to display */
  icon: LucideIcon;
  /** Main title text */
  title: string;
  /** Optional description below the title */
  description?: ReactNode;
  /** Additional CSS classes for the container */
  className?: string;
  /** Use monospace font (useful for console-style panels) */
  mono?: boolean;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  className = "",
  mono = false,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={`flex h-full flex-col items-center justify-center gap-3 py-8 ${className}`}
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.3, ease: "easeOut" }}
        className="bg-content2 rounded-xl p-3"
      >
        <Icon className="text-foreground-400 h-5 w-5" strokeWidth={1.5} />
      </motion.div>
      <div className="flex flex-col items-center gap-1">
        <p
          className={`text-foreground-500 text-sm ${mono ? "font-mono text-xs" : ""}`}
        >
          {title}
        </p>
        {description && (
          <p
            className={`text-foreground-400 max-w-xs text-center text-xs ${mono ? "font-mono" : ""}`}
          >
            {description}
          </p>
        )}
      </div>
    </motion.div>
  );
}

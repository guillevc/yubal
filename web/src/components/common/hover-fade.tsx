import { motion } from "motion/react";
import type { ReactNode } from "react";

interface HoverFadeProps {
  show: boolean;
  /** Skip initial animation (useful when element should be visible on mount) */
  initialShow?: boolean;
  children: ReactNode;
}

export function HoverFade({ show, initialShow, children }: HoverFadeProps) {
  const shouldShow = initialShow ?? false;
  return (
    <motion.div
      initial={{ opacity: shouldShow ? 1 : 0, scale: shouldShow ? 1 : 0.8 }}
      animate={{ opacity: show ? 1 : 0, scale: show ? 1 : 0.8 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
    >
      {children}
    </motion.div>
  );
}

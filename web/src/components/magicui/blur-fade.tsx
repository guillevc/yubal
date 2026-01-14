import { AnimatePresence, motion, Variants } from "motion/react";
import { useRef } from "react";
import { useInView } from "motion/react";

interface BlurFadeProps {
  children: React.ReactNode;
  className?: string;
  duration?: number;
  delay?: number;
  offset?: number;
  direction?: "up" | "down" | "left" | "right";
  inView?: boolean;
  inViewMargin?: string;
  blur?: string;
}

export function BlurFade({
  children,
  className,
  duration = 0.4,
  delay = 0,
  offset = 6,
  direction = "down",
  inView = false,
  inViewMargin = "-50px",
  blur = "6px",
}: BlurFadeProps) {
  const ref = useRef(null);
  const inViewResult = useInView(ref, {
    once: true,
    margin: inViewMargin as `${number}px`,
  });
  const isInView = !inView || inViewResult;

  const defaultVariants: Variants = {
    hidden: {
      ...(direction === "left" || direction === "right"
        ? { x: direction === "right" ? -offset : offset }
        : { y: direction === "down" ? -offset : offset }),
      opacity: 0,
      filter: `blur(${blur})`,
    },
    visible: {
      x: 0,
      y: 0,
      opacity: 1,
      filter: "blur(0px)",
    },
  };

  return (
    <AnimatePresence>
      <motion.div
        ref={ref}
        initial="hidden"
        animate={isInView ? "visible" : "hidden"}
        exit="hidden"
        variants={defaultVariants}
        transition={{
          delay: 0.04 + delay,
          duration,
          ease: "easeOut",
        }}
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

import { useState } from "react";

export function useHover() {
  const [isHovered, setIsHovered] = useState(false);
  const handlers = {
    onMouseEnter: () => setIsHovered(true),
    onMouseLeave: () => setIsHovered(false),
  };
  return [isHovered, handlers] as const;
}

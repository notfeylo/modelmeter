import { useEffect, useRef, useState, type SVGProps } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

let cachedPathLength = 0;

export function LoadingBreadcrumb({ text = "Loading", className }: { text?: string; className?: string }) {
  const pathRef = useRef<SVGPathElement>(null);
  const [pathLength, setPathLength] = useState(cachedPathLength);

  useEffect(() => {
    if (!cachedPathLength && pathRef.current) {
      cachedPathLength = pathRef.current.getTotalLength();
      setPathLength(cachedPathLength);
    }
  }, []);

  return <div className={cn("flex items-center gap-2 text-sm font-medium tracking-wide", className)}>
    <svg role="img" aria-label="Loading" viewBox="0 0 19 19" fill="none" width="18" height="18" className="text-primary">
      <path ref={pathRef} d="M4.43431 2.42415C-0.789139 6.90104 1.21472 15.2022 8.434 15.9242C15.5762 16.6384 18.8649 9.23035 15.9332 4.5183C14.1316 1.62255 8.43695 0.0528911 7.51841 3.33733C6.48107 7.04659 15.2699 15.0195 17.4343 16.9241" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className={pathLength ? "loading-path" : "opacity-0"} style={pathLength ? { strokeDasharray: pathLength, "--path-length": pathLength } as SVGProps<SVGPathElement>["style"] : undefined} />
    </svg>
    <span className="loading-shimmer">{text}</span>
    <ChevronRight size={16} className="text-muted-foreground" aria-hidden="true" />
  </div>;
}

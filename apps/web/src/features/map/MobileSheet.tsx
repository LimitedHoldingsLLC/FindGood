"use client";

import type { ReactNode } from "react";

type Height = "peek" | "half" | "expanded";

const HEIGHTS: Record<Height, string> = {
  peek: "32vh",
  half: "52vh",
  expanded: "82vh",
};

export function MobileSheet({
  height,
  onHeight,
  children,
}: {
  height: Height;
  onHeight: (next: Height) => void;
  children: ReactNode;
}) {
  function cycle() {
    onHeight(height === "peek" ? "half" : height === "half" ? "expanded" : "peek");
  }

  return (
    <section
      className="absolute inset-x-0 bottom-0 z-20 rounded-t-3xl border border-ink/10 bg-paper/95 shadow-card backdrop-blur md:hidden"
      style={{ height: HEIGHTS[height] }}
    >
      <button type="button" className="flex w-full justify-center py-3" onClick={cycle} aria-label="Resize results">
        <span className="h-1.5 w-12 rounded-full bg-ink/20" />
      </button>
      <div className="h-[calc(100%-2.5rem)] overflow-y-auto px-4 pb-6">{children}</div>
    </section>
  );
}

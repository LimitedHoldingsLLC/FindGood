import Link from "next/link";

import { BrandMark } from "@/components/layout/BrandMark";

export function SiteHeader({ compact = false }: { compact?: boolean }) {
  return (
    <header className="sticky top-0 z-30 border-b border-ink/10 bg-paper/85 backdrop-blur">
      <div className={`mx-auto flex items-center justify-between px-4 ${compact ? "max-w-none py-3" : "max-w-6xl py-4"}`}>
        <Link href="/" className="font-display text-2xl tracking-tight">
          <BrandMark />
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/map" className="text-muted hover:text-ink">
            Map
          </Link>
          <Link href="/los-angeles" className="text-muted hover:text-ink">
            Los Angeles
          </Link>
        </nav>
      </div>
    </header>
  );
}

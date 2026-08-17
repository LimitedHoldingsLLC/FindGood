import Link from "next/link";

import { BrandMark } from "@/components/layout/BrandMark";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-ink/10 bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href="/" className="font-display text-2xl tracking-tight">
          <BrandMark />
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/los-angeles" className="text-muted hover:text-ink">
            Los Angeles
          </Link>
        </nav>
      </div>
    </header>
  );
}

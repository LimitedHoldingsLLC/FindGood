import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-ink/10 bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href="/" className="font-display text-2xl tracking-tight">
          FindGood
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/los-angeles" className="text-muted hover:text-ink">
            Los Angeles
          </Link>
          <Link href="/admin" className="text-muted hover:text-ink">
            Admin
          </Link>
        </nav>
      </div>
    </header>
  );
}

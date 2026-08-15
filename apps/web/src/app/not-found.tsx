import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-20 text-center">
      <p className="text-sm uppercase tracking-[0.2em] text-terracotta">404</p>
      <h1 className="mt-3 font-display text-5xl">That table isn’t set</h1>
      <p className="mt-3 text-muted">The page you wanted isn’t on the menu.</p>
      <Link href="/" className="mt-6 inline-block rounded-full bg-ink px-5 py-2 text-paper">
        Back to deals
      </Link>
    </div>
  );
}

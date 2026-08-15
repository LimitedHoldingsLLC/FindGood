export function DealCardSkeleton() {
  return (
    <div className="animate-pulse rounded-3xl border border-ink/5 bg-card p-5 shadow-card">
      <div className="h-3 w-24 rounded bg-ink/10" />
      <div className="mt-4 h-7 w-3/4 rounded bg-ink/10" />
      <div className="mt-3 h-4 w-1/2 rounded bg-ink/10" />
      <div className="mt-8 h-6 w-20 rounded bg-ink/10" />
    </div>
  );
}

export function ErrorState({
  title = "We couldn’t load that just now",
  body = "The kitchen is still here. Try again in a moment.",
}: {
  title?: string;
  body?: string;
}) {
  return (
    <div className="rounded-3xl border border-terracotta/30 bg-card px-6 py-14 text-center shadow-card">
      <p className="text-sm uppercase tracking-[0.2em] text-terracotta">FindGood</p>
      <h2 className="mt-3 font-display text-3xl">{title}</h2>
      <p className="mx-auto mt-3 max-w-md text-muted">{body}</p>
    </div>
  );
}

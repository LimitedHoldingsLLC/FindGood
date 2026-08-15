import type { ReactNode } from "react";

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-ink/10 bg-card px-6 py-16 text-center shadow-card">
      <p className="font-display text-3xl">Nothing here yet</p>
      <h2 className="mt-3 text-lg font-medium">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-muted">{body}</p>
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}

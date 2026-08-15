import type { AvailabilityStatus } from "@/lib/api/types";

const STYLES: Record<AvailabilityStatus, string> = {
  active_now: "bg-forest text-paper",
  starts_soon: "bg-terracotta text-paper",
  active_later_today: "bg-gold/20 text-ink",
  ended_today: "bg-ink/10 text-muted",
  currently_unavailable: "bg-ink/5 text-muted",
};

export function StatusBadge({
  status,
  label,
}: {
  status: AvailabilityStatus;
  label: string;
}) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${STYLES[status]}`}>
      {label}
    </span>
  );
}

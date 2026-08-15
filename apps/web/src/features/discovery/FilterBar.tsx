import Link from "next/link";

import { NEIGHBORHOODS } from "@/lib/location";

type Props = {
  city: string;
  neighborhood?: string;
  activeNow?: boolean;
  offering?: string;
};

function href(next: Props) {
  const params = new URLSearchParams();
  if (next.neighborhood) params.set("neighborhood", next.neighborhood);
  if (next.activeNow) params.set("active_now", "1");
  if (next.offering) params.set("offering", next.offering);
  const query = params.toString();
  const base = next.city === "Los Angeles" ? "/" : `/${next.city.toLowerCase().replace(/\s+/g, "-")}`;
  return query ? `${base}?${query}` : base;
}

const chip = (on: boolean) =>
  `rounded-full px-3 py-1.5 text-sm ${on ? "bg-ink text-paper" : "bg-white/70 text-ink hover:bg-white"}`;

export function FilterBar({ city, neighborhood, activeNow, offering }: Props) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Link className={chip(Boolean(activeNow))} href={href({ city, neighborhood, activeNow: true, offering })}>
          Happening now
        </Link>
        <Link className={chip(offering === "food")} href={href({ city, neighborhood, activeNow, offering: "food" })}>
          Food
        </Link>
        <Link className={chip(offering === "drink")} href={href({ city, neighborhood, activeNow, offering: "drink" })}>
          Drinks
        </Link>
        <Link className={chip(!offering)} href={href({ city, neighborhood, activeNow })}>
          Both
        </Link>
      </div>
      <div className="flex flex-wrap gap-2">
        <Link className={chip(!neighborhood)} href={href({ city, activeNow, offering })}>
          All {city}
        </Link>
        {NEIGHBORHOODS.map((name) => (
          <Link
            key={name}
            className={chip(neighborhood === name)}
            href={href({ city, neighborhood: name, activeNow, offering })}
          >
            {name}
          </Link>
        ))}
      </div>
    </div>
  );
}

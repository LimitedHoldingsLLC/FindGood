"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";

import {
  CUISINES,
  DAYS,
  DEAL_TYPES,
  DRINKS,
  FEATURES,
  NEIGHBORHOOD_OPTIONS,
  PRICE_LEVELS,
  TIME_BUCKETS,
  filterHref,
  hasActiveFilters,
  labelFor,
  type FilterState,
} from "./filters";

type PanelId = "when" | "area" | "cuisine" | "price" | "drinks" | "reservations" | "more";

type Props = {
  city: string;
  state: FilterState;
};

const chip = (on: boolean) =>
  `rounded-full px-3 py-1.5 text-sm transition ${on ? "bg-ink text-paper" : "bg-white/70 text-ink hover:bg-white"}`;

export function FilterBar({ city, state }: Props) {
  const [open, setOpen] = useState<PanelId | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const searchId = useId();
  const router = useRouter();

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(null);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(null);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  function href(next: Partial<FilterState>) {
    return filterHref(city, { ...state, ...next });
  }

  function toggle(next: PanelId) {
    setOpen((current) => (current === next ? null : next));
  }

  function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const q = String(form.get("q") ?? "");
    router.push(filterHref(city, { ...state, q }));
  }

  const whenLabel = labelFor(TIME_BUCKETS, state.when) ?? labelFor(DAYS, state.day) ?? "When";
  const areaLabel = state.neighborhood ?? "Area";
  const cuisineLabel = labelFor(CUISINES, state.cuisine) ?? "Cuisine";
  const priceLabel = labelFor(PRICE_LEVELS, state.price) ?? "Price";
  const drinkLabel = labelFor(DRINKS, state.drink) ?? "Drink types";
  const reservationLabel = state.reservations ? "Takes reservations" : "Reservations";
  const moreLabel = labelFor(DEAL_TYPES, state.dealType) ?? labelFor(FEATURES, state.feature) ?? "More";

  return (
    <div ref={rootRef} className="space-y-3">
      <form onSubmit={onSearch} className="relative" action={filterHref(city, { ...state, q: undefined })}>
        <label htmlFor={searchId} className="sr-only">
          Search deals
        </label>
        <input
          id={searchId}
          name="q"
          type="search"
          defaultValue={state.q ?? ""}
          placeholder="Search restaurants, dishes, neighborhoods…"
          className="w-full rounded-full border border-ink/10 bg-white/80 px-5 py-3 text-sm outline-none ring-terracotta/30 placeholder:text-muted focus:border-terracotta/40 focus:ring-2"
        />
      </form>

      <div className="flex flex-wrap gap-2">
        <Chip href={href({ activeNow: !state.activeNow })} on={Boolean(state.activeNow)}>
          Happening now
        </Chip>
        <Chip href={href({ offering: "food" })} on={state.offering === "food"}>
          Food
        </Chip>
        <Chip href={href({ offering: "drink" })} on={state.offering === "drink"}>
          Drinks
        </Chip>
        <Chip href={href({ offering: undefined })} on={!state.offering}>
          Both
        </Chip>
      </div>

      <div className="flex flex-wrap gap-2">
        <Trigger label={whenLabel} open={open === "when"} active={Boolean(state.when || state.day)} onClick={() => toggle("when")} />
        <Trigger label={areaLabel} open={open === "area"} active={Boolean(state.neighborhood)} onClick={() => toggle("area")} />
        <Trigger label={cuisineLabel} open={open === "cuisine"} active={Boolean(state.cuisine)} onClick={() => toggle("cuisine")} />
        <Trigger label={priceLabel} open={open === "price"} active={Boolean(state.price)} onClick={() => toggle("price")} />
        <Trigger label={drinkLabel} open={open === "drinks"} active={Boolean(state.drink)} onClick={() => toggle("drinks")} />
        <Trigger
          label={reservationLabel}
          open={open === "reservations"}
          active={Boolean(state.reservations)}
          onClick={() => toggle("reservations")}
        />
        <Trigger label={moreLabel} open={open === "more"} active={Boolean(state.dealType || state.feature)} onClick={() => toggle("more")} />
        {hasActiveFilters(state) ? (
          <Link className="rounded-full px-3 py-1.5 text-sm text-muted underline-offset-4 hover:text-ink hover:underline" href={filterHref(city, {})}>
            Clear
          </Link>
        ) : null}
      </div>

      {open === "when" ? (
        <Panel title="When">
          {TIME_BUCKETS.map((option) => (
            <Chip key={option.value} href={href({ when: state.when === option.value ? undefined : option.value })} on={state.when === option.value}>
              {option.label}
            </Chip>
          ))}
          <span className="w-full" />
          {DAYS.map((option) => (
            <Chip key={option.value} href={href({ day: state.day === option.value ? undefined : option.value })} on={state.day === option.value}>
              {option.label}
            </Chip>
          ))}
        </Panel>
      ) : null}

      {open === "area" ? (
        <Panel title="Area">
          <Chip href={href({ neighborhood: undefined })} on={!state.neighborhood}>
            All {city}
          </Chip>
          {NEIGHBORHOOD_OPTIONS.map((option) => (
            <Chip
              key={option.value}
              href={href({ neighborhood: state.neighborhood === option.value ? undefined : option.value })}
              on={state.neighborhood === option.value}
            >
              {option.label}
            </Chip>
          ))}
        </Panel>
      ) : null}

      {open === "cuisine" ? (
        <Panel title="Cuisine">
          {CUISINES.map((option) => (
            <Chip key={option.value} href={href({ cuisine: state.cuisine === option.value ? undefined : option.value })} on={state.cuisine === option.value}>
              {option.label}
            </Chip>
          ))}
        </Panel>
      ) : null}

      {open === "price" ? (
        <Panel title="Price">
          {PRICE_LEVELS.map((option) => (
            <Chip key={option.value} href={href({ price: state.price === option.value ? undefined : option.value })} on={state.price === option.value}>
              {option.label}
            </Chip>
          ))}
        </Panel>
      ) : null}

      {open === "drinks" ? (
        <Panel title="Drinks">
          {DRINKS.map((option) => (
            <Chip key={option.value} href={href({ drink: state.drink === option.value ? undefined : option.value })} on={state.drink === option.value}>
              {option.label}
            </Chip>
          ))}
        </Panel>
      ) : null}

      {open === "reservations" ? (
        <Panel title="Reservations">
          <Chip href={href({ reservations: !state.reservations })} on={Boolean(state.reservations)}>
            Takes reservations
          </Chip>
          <Chip href={href({ feature: state.feature === "walk_in" ? undefined : "walk_in" })} on={state.feature === "walk_in"}>
            Walk-in friendly
          </Chip>
        </Panel>
      ) : null}

      {open === "more" ? (
        <Panel title="More">
          {DEAL_TYPES.map((option) => (
            <Chip
              key={option.value}
              href={href({ dealType: state.dealType === option.value ? undefined : option.value })}
              on={state.dealType === option.value}
            >
              {option.label}
            </Chip>
          ))}
          <span className="w-full" />
          {FEATURES.map((option) => (
            <Chip key={option.value} href={href({ feature: state.feature === option.value ? undefined : option.value })} on={state.feature === option.value}>
              {option.label}
            </Chip>
          ))}
        </Panel>
      ) : null}
    </div>
  );
}

function Trigger({
  label,
  open,
  active,
  onClick,
}: {
  label: string;
  open: boolean;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-expanded={open}
      onClick={onClick}
      className={`rounded-full px-3.5 py-1.5 text-sm transition ${
        open || active ? "bg-ink text-paper" : "bg-white/70 text-ink hover:bg-white"
      }`}
    >
      {label}
      <span className="ml-1.5 text-[0.7em] opacity-70" aria-hidden>
        {open ? "▴" : "▾"}
      </span>
    </button>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-ink/10 bg-white/70 p-4 shadow-card">
      <p className="mb-3 text-xs uppercase tracking-[0.18em] text-muted">{title}</p>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

function Chip({ href, on, children }: { href: string; on: boolean; children: ReactNode }) {
  return (
    <Link className={chip(on)} href={href}>
      {children}
    </Link>
  );
}

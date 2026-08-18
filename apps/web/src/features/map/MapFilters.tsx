"use client";

import type { FormEvent } from "react";

import type { MapFilters as Filters } from "./types";

const WHEN = [
  { value: "now", label: "Now" },
  { value: "tonight", label: "Tonight" },
  { value: "today", label: "Today" },
  { value: "weekend", label: "Weekend" },
];

const KINDS = [
  { value: "drink", label: "Drinks" },
  { value: "food", label: "Food" },
];

const DEALS = [
  { value: "happy_hour", label: "Happy hour" },
  { value: "brunch", label: "Brunch" },
  { value: "lunch", label: "Lunch" },
  { value: "late_night", label: "Late night" },
];

export function MapFilters({
  filters,
  onChange,
  onSearch,
}: {
  filters: Filters;
  onChange: (next: Partial<Filters>) => void;
  onSearch: (q: string) => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSearch(String(form.get("q") ?? ""));
  }

  return (
    <div className="space-y-2">
      <form onSubmit={submit}>
        <label className="sr-only" htmlFor="map-search">
          Search deals or neighborhoods
        </label>
        <input
          id="map-search"
          name="q"
          defaultValue={filters.q ?? ""}
          placeholder="Search tacos, martinis, Silver Lake…"
          className="w-full rounded-full border border-ink/10 bg-white/90 px-4 py-2.5 text-sm outline-none ring-terracotta/30 focus:ring-2"
        />
      </form>
      <div className="flex flex-wrap gap-2">
        {WHEN.map((option) => (
          <Chip
            key={option.value}
            on={filters.when === option.value}
            onClick={() => onChange({ when: filters.when === option.value ? undefined : option.value })}
          >
            {option.label}
          </Chip>
        ))}
        {KINDS.map((option) => (
          <Chip
            key={option.value}
            on={filters.offering === option.value}
            onClick={() => onChange({ offering: filters.offering === option.value ? undefined : option.value })}
          >
            {option.label}
          </Chip>
        ))}
        {DEALS.map((option) => (
          <Chip
            key={option.value}
            on={filters.dealType === option.value}
            onClick={() => onChange({ dealType: filters.dealType === option.value ? undefined : option.value })}
          >
            {option.label}
          </Chip>
        ))}
      </div>
    </div>
  );
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1.5 text-sm ${on ? "bg-ink text-paper" : "bg-white/80 text-ink hover:bg-white"}`}
    >
      {children}
    </button>
  );
}

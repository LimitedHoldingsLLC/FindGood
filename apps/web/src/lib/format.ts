import type { DealItem } from "./api/types";

export function formatMoney(value: string | null): string | null {
  if (value == null) return null;
  const amount = Number(value);
  if (Number.isNaN(amount)) return null;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
}

export function primaryPrice(items: DealItem[]): { deal: string | null; normal: string | null; savings: string | null } {
  const priced = items.find((item) => item.deal_price);
  if (!priced) return { deal: null, normal: null, savings: null };
  return {
    deal: formatMoney(priced.deal_price),
    normal: formatMoney(priced.normal_price),
    savings: priced.percent_savings ? `${Number(priced.percent_savings).toFixed(0)}% off` : null,
  };
}

export function citySlug(city: string): string {
  return city.toLowerCase().replace(/\s+/g, "-");
}

export function priceLevelLabel(level: number | null | undefined): string | null {
  if (level == null || level < 1 || level > 4) return null;
  return "$".repeat(level);
}

export function formatRating(value: string | null | undefined): string | null {
  if (value == null || value === "") return null;
  const amount = Number(value);
  if (Number.isNaN(amount)) return null;
  return amount.toFixed(1);
}

export function ratingSourceLabel(providers: string[] | undefined): string | null {
  if (!providers?.length) return null;
  const names = providers.map((provider) => {
    if (provider === "google_places") return "Google";
    if (provider === "yelp") return "Yelp";
    if (provider === "tripadvisor") return "Tripadvisor";
    return titleCaseKey(provider);
  });
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}

export function titleCaseKey(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function titleCaseSlug(slug: string): string {
  return slug
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

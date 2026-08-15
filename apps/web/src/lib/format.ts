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

export function titleCaseSlug(slug: string): string {
  return slug
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

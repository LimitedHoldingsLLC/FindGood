import { NEIGHBORHOODS } from "@/lib/location";

export type FilterState = {
  q?: string;
  neighborhood?: string;
  activeNow?: boolean;
  offering?: string;
  cuisine?: string;
  price?: string;
  drink?: string;
  reservations?: boolean;
  feature?: string;
  when?: string;
  day?: string;
  dealType?: string;
  minRating?: string;
};

export const CUISINES = [
  { value: "american", label: "American" },
  { value: "mexican", label: "Mexican" },
  { value: "japanese", label: "Japanese" },
  { value: "korean", label: "Korean" },
  { value: "chinese", label: "Chinese" },
  { value: "thai", label: "Thai" },
  { value: "vietnamese", label: "Vietnamese" },
  { value: "italian", label: "Italian" },
  { value: "french", label: "French" },
  { value: "mediterranean", label: "Mediterranean" },
  { value: "indian", label: "Indian" },
  { value: "seafood", label: "Seafood" },
  { value: "cafe", label: "Cafe" },
  { value: "bar", label: "Bar" },
  { value: "gastropub", label: "Gastropub" },
] as const;

export const DRINKS = [
  { value: "cocktails", label: "Cocktails" },
  { value: "beer", label: "Beer" },
  { value: "wine", label: "Wine" },
  { value: "natural_wine", label: "Natural wine" },
  { value: "sake", label: "Sake" },
  { value: "nonalcoholic", label: "Non-alcoholic" },
] as const;

export const TIME_BUCKETS = [
  { value: "lunch", label: "Lunch" },
  { value: "afternoon", label: "Afternoon" },
  { value: "evening", label: "Evening" },
  { value: "late_night", label: "Late night" },
] as const;

export const DAYS = [
  { value: "1", label: "Monday" },
  { value: "2", label: "Tuesday" },
  { value: "3", label: "Wednesday" },
  { value: "4", label: "Thursday" },
  { value: "5", label: "Friday" },
  { value: "6", label: "Saturday" },
  { value: "7", label: "Sunday" },
] as const;

export const PRICE_LEVELS = [
  { value: "1", label: "$" },
  { value: "2", label: "$$" },
  { value: "3", label: "$$$" },
  { value: "4", label: "$$$$" },
] as const;

export const FEATURES = [
  { value: "patio", label: "Patio" },
  { value: "rooftop", label: "Rooftop" },
  { value: "outdoor", label: "Outdoor seating" },
  { value: "late_night", label: "Open late" },
  { value: "good_for_groups", label: "Good for groups" },
  { value: "walk_in", label: "Walk-in friendly" },
] as const;

export const DEAL_TYPES = [
  { value: "happy_hour", label: "Happy hour" },
  { value: "food_special", label: "Food special" },
  { value: "drink_special", label: "Drink special" },
  { value: "prix_fixe", label: "Prix fixe" },
  { value: "brunch", label: "Brunch" },
  { value: "lunch", label: "Lunch" },
  { value: "late_night", label: "Late night" },
  { value: "oyster", label: "Oysters" },
  { value: "taco_night", label: "Taco night" },
] as const;

export const RATINGS = [
  { value: "3", label: "3+" },
  { value: "3.5", label: "3.5+" },
  { value: "4", label: "4+" },
  { value: "4.5", label: "4.5+" },
] as const;

export const NEIGHBORHOOD_OPTIONS = NEIGHBORHOODS.map((name) => ({ value: name, label: name }));

export function filterHref(city: string, next: FilterState): string {
  const params = new URLSearchParams();
  if (next.q?.trim()) params.set("q", next.q.trim());
  if (next.neighborhood) params.set("neighborhood", next.neighborhood);
  if (next.activeNow) params.set("active_now", "1");
  if (next.offering) params.set("offering", next.offering);
  if (next.cuisine) params.set("cuisine", next.cuisine);
  if (next.price) params.set("price", next.price);
  if (next.drink) params.set("drink", next.drink);
  if (next.reservations) params.set("reservations", "1");
  if (next.feature) params.set("feature", next.feature);
  if (next.when) params.set("when", next.when);
  if (next.day) params.set("day", next.day);
  if (next.dealType) params.set("deal_type", next.dealType);
  if (next.minRating) params.set("min_rating", next.minRating);
  const query = params.toString();
  const base = city === "Los Angeles" ? "/" : `/${city.toLowerCase().replace(/\s+/g, "-")}`;
  return query ? `${base}?${query}` : base;
}

export function hasActiveFilters(state: FilterState): boolean {
  return Boolean(
    state.q?.trim() ||
      state.neighborhood ||
      state.activeNow ||
      state.offering ||
      state.cuisine ||
      state.price ||
      state.drink ||
      state.reservations ||
      state.feature ||
      state.when ||
      state.day ||
      state.dealType ||
      state.minRating,
  );
}

export function labelFor(options: readonly { value: string; label: string }[], value?: string): string | undefined {
  return options.find((option) => option.value === value)?.label;
}

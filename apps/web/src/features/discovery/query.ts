import type { DealQuery, OfferingKind } from "@/lib/api/types";
import { FOOD_VERTICAL } from "@/lib/api/types";

import type { FilterState } from "./filters";

export type DiscoverySearch = {
  q?: string;
  neighborhood?: string;
  active_now?: string;
  offering?: string;
  cuisine?: string;
  price?: string;
  drink?: string;
  reservations?: string;
  feature?: string;
  when?: string;
  day?: string;
  deal_type?: string;
  min_rating?: string;
};

export function filterStateFromSearch(params: DiscoverySearch): FilterState {
  return {
    q: params.q,
    neighborhood: params.neighborhood,
    activeNow: params.active_now === "1",
    offering: params.offering,
    cuisine: params.cuisine,
    price: params.price,
    drink: params.drink,
    reservations: params.reservations === "1",
    feature: params.feature,
    when: params.when,
    day: params.day,
    dealType: params.deal_type,
    minRating: params.min_rating,
  };
}

export function dealQueryFromSearch(params: DiscoverySearch, city: string): DealQuery {
  return {
    city,
    q: params.q,
    neighborhood: params.neighborhood,
    food_or_drink: params.offering as OfferingKind | undefined,
    active_now: params.active_now === "1" || undefined,
    cuisine: params.cuisine,
    price_level: params.price,
    drink: params.drink,
    reservations: params.reservations === "1" || undefined,
    feature: params.feature,
    when: params.when,
    day: params.day,
    deal_type: params.deal_type,
    min_rating: params.min_rating,
    vertical: FOOD_VERTICAL,
  };
}

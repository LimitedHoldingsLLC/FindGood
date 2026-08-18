import { DEFAULT_CENTER, DEFAULT_ZOOM, LA_BOUNDS } from "./defaults";
import type { MapFilters, MapQuery, MapViewport } from "./types";

export type MapSearch = {
  lat?: string;
  lng?: string;
  zoom?: string;
  q?: string;
  when?: string;
  offering?: string;
  deal_type?: string;
  cuisine?: string;
  price?: string;
};

export function viewportFromSearch(params: MapSearch): MapViewport {
  const lat = Number(params.lat ?? DEFAULT_CENTER.lat);
  const lng = Number(params.lng ?? DEFAULT_CENTER.lng);
  const zoom = Number(params.zoom ?? DEFAULT_ZOOM);
  const span = spanForZoom(zoom);
  return {
    lat,
    lng,
    zoom,
    north: lat + span,
    south: lat - span,
    east: lng + span * 1.4,
    west: lng - span * 1.4,
  };
}

export function filtersFromSearch(params: MapSearch): MapFilters {
  return {
    q: params.q,
    when: params.when,
    offering: params.offering,
    dealType: params.deal_type,
    cuisine: params.cuisine,
    price: params.price,
  };
}

export function mapHref(viewport: Partial<MapViewport>, filters: MapFilters): string {
  const params = new URLSearchParams();
  if (viewport.lat != null) params.set("lat", viewport.lat.toFixed(4));
  if (viewport.lng != null) params.set("lng", viewport.lng.toFixed(4));
  if (viewport.zoom != null) params.set("zoom", String(Math.round(viewport.zoom)));
  if (filters.q?.trim()) params.set("q", filters.q.trim());
  if (filters.when) params.set("when", filters.when);
  if (filters.offering) params.set("offering", filters.offering);
  if (filters.dealType) params.set("deal_type", filters.dealType);
  if (filters.cuisine) params.set("cuisine", filters.cuisine);
  if (filters.price) params.set("price", filters.price);
  const query = params.toString();
  return query ? `/map?${query}` : "/map";
}

export function apiQueryFromState(viewport: MapViewport, filters: MapFilters): Record<string, string | undefined> {
  return {
    north: String(viewport.north),
    south: String(viewport.south),
    east: String(viewport.east),
    west: String(viewport.west),
    zoom: String(Math.round(viewport.zoom)),
    q: filters.q,
    when: filters.when,
    food_or_drink: filters.offering,
    deal_type: filters.dealType,
    cuisine: filters.cuisine,
    price_level: filters.price,
  };
}

export function hasActiveMapFilters(filters: MapFilters): boolean {
  return Boolean(filters.q?.trim() || filters.when || filters.offering || filters.dealType || filters.cuisine || filters.price);
}

export function spanForZoom(zoom: number): number {
  if (zoom >= 15) return 0.03;
  if (zoom >= 13) return 0.06;
  if (zoom >= 11) return 0.12;
  return 0.25;
}

export function defaultViewport(): MapViewport {
  return {
    ...DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
    ...LA_BOUNDS,
  };
}

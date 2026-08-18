import { describe, expect, it } from "vitest";

import { clusterPins } from "@/features/map/cluster";
import { hasActiveMapFilters, mapHref, viewportFromSearch } from "@/features/map/query";
import type { MapPin } from "@/features/map/types";

describe("mapHref", () => {
  it("keeps shareable viewport and filters out of hover state", () => {
    const href = mapHref({ lat: 34.092, lng: -118.328, zoom: 14 }, { when: "now", offering: "drink" });
    expect(href).toContain("/map?");
    expect(href).toContain("lat=34.0920");
    expect(href).toContain("when=now");
    expect(href).toContain("offering=drink");
  });
});

describe("viewportFromSearch", () => {
  it("defaults to Los Angeles when the URL is empty", () => {
    const viewport = viewportFromSearch({});
    expect(viewport.lat).toBeCloseTo(34.0522);
    expect(viewport.zoom).toBe(12);
  });
});

describe("hasActiveMapFilters", () => {
  it("ignores empty search", () => {
    expect(hasActiveMapFilters({})).toBe(false);
    expect(hasActiveMapFilters({ q: "  " })).toBe(false);
    expect(hasActiveMapFilters({ when: "now" })).toBe(true);
  });
});

describe("clusterPins", () => {
  it("keeps a single pin unclustered", () => {
    const pin = {
      id: "loc-1",
      venue_id: "v-1",
      slug: "the-lantern-annex",
      name: "The Lantern Annex",
      lat: "34.1016",
      lng: "-118.3268",
      neighborhood: "Hollywood",
      category: "wine_bar",
      location_confidence: "verified",
      best_offer: null,
    } satisfies MapPin;
    const items = clusterPins([pin], 12);
    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({ kind: "pin", pin });
  });

  it("clusters nearby pins when zoomed out", () => {
    const pins = Array.from({ length: 20 }, (_, index) => ({
      id: `loc-${index}`,
      venue_id: `v-${index}`,
      slug: `venue-${index}`,
      name: `Venue ${index}`,
      lat: String(34.1016 + index * 0.0001),
      lng: String(-118.3268 + index * 0.0001),
      neighborhood: "Hollywood",
      category: "bar",
      location_confidence: "verified",
      best_offer: null,
    })) satisfies MapPin[];
    const items = clusterPins(pins, 12);
    expect(items.some((item) => item.kind === "cluster")).toBe(true);
  });
});

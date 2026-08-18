import { describe, expect, it } from "vitest";

import { filterHref, hasActiveFilters } from "@/features/discovery/filters";

describe("filterHref", () => {
  it("keeps the home path for Los Angeles and omits empty params", () => {
    expect(filterHref("Los Angeles", {})).toBe("/");
    expect(filterHref("Los Angeles", { neighborhood: "Silver Lake", cuisine: "mexican" })).toBe(
      "/?neighborhood=Silver+Lake&cuisine=mexican",
    );
  });

  it("preserves search and compact filter params", () => {
    const href = filterHref("Los Angeles", {
      q: "taco",
      activeNow: true,
      price: "2",
      reservations: true,
      when: "evening",
      minRating: "4",
      ratingSource: "google_places",
      sort: "rating",
    });
    expect(href).toContain("q=taco");
    expect(href).toContain("active_now=1");
    expect(href).toContain("price=2");
    expect(href).toContain("reservations=1");
    expect(href).toContain("when=evening");
    expect(href).toContain("min_rating=4");
    expect(href).toContain("rating_source=google_places");
    expect(href).toContain("sort=rating");
  });

  it("omits the default FindGood.Food rating source", () => {
    expect(filterHref("Los Angeles", { ratingSource: "findgood", minRating: "4" })).toBe("/?min_rating=4");
  });
});

describe("hasActiveFilters", () => {
  it("is false for an empty state", () => {
    expect(hasActiveFilters({})).toBe(false);
    expect(hasActiveFilters({ q: "  " })).toBe(false);
  });
});

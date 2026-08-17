import { describe, expect, it } from "vitest";

import { formatMoney, formatRating, priceLevelLabel, primaryPrice, ratingSourceLabel, titleCaseKey } from "@/lib/format";

describe("formatMoney", () => {
  it("formats decimal strings without using floats as source of truth", () => {
    expect(formatMoney("8.00")).toBe("$8.00");
    expect(formatMoney(null)).toBeNull();
  });
});

describe("primaryPrice", () => {
  it("prefers the first priced item", () => {
    const result = primaryPrice([
      {
        id: "1",
        name: "Oyster",
        description: null,
        category: "food",
        normal_price: "4.00",
        deal_price: "2.00",
        currency: "USD",
        absolute_savings: "2.00",
        percent_savings: "50.00",
      },
    ]);
    expect(result.deal).toBe("$2.00");
    expect(result.savings).toBe("50% off");
  });
});

describe("priceLevelLabel", () => {
  it("renders Yelp-style dollar signs", () => {
    expect(priceLevelLabel(2)).toBe("$$");
    expect(priceLevelLabel(null)).toBeNull();
  });
});

describe("formatRating", () => {
  it("keeps one decimal place", () => {
    expect(formatRating("4.30")).toBe("4.3");
    expect(formatRating(null)).toBeNull();
  });
});

describe("ratingSourceLabel", () => {
  it("names official providers without calling them FindGood scores", () => {
    expect(ratingSourceLabel(["google_places", "yelp"])).toBe("Google and Yelp");
  });
});

describe("titleCaseKey", () => {
  it("turns taxonomy slugs into labels", () => {
    expect(titleCaseKey("natural_wine")).toBe("Natural Wine");
  });
});

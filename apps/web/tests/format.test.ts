import { describe, expect, it } from "vitest";

import { formatMoney, primaryPrice } from "@/lib/format";

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

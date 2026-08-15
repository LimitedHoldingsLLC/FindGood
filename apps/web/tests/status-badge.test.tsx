import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/ui/StatusBadge";

describe("StatusBadge", () => {
  it("renders the availability label from the API", () => {
    render(<StatusBadge status="active_now" label="Until 6 PM" />);
    expect(screen.getByText("Until 6 PM")).toBeTruthy();
  });
});

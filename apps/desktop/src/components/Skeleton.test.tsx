import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoadingLayout, SkeletonCard } from "./Skeleton";

describe("skeletons", () => {
  it("announce the wait once and hide the blocks from screen readers", () => {
    render(
      <LoadingLayout label="Loading your day…">
        <SkeletonCard lines={4} />
      </LoadingLayout>,
    );
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveTextContent("Loading your day…");
    const card = status.querySelector(".card");
    expect(card).toHaveAttribute("aria-hidden", "true");
    expect(card?.querySelectorAll(".animate-pulse")).toHaveLength(5); // title + 4 lines
  });
});

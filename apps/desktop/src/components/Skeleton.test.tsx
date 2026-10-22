import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Delayed, LoadingLayout, SkeletonCard } from "./Skeleton";

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
    expect(card?.querySelectorAll(".skeleton")).toHaveLength(5); // title + 4 lines (shimmer)
  });

  it("are held back briefly so a fast local load does not flash them", () => {
    vi.useFakeTimers();
    try {
      render(<Delayed ms={250}><p>skeleton</p></Delayed>);
      expect(screen.queryByText("skeleton")).toBeNull();
      act(() => vi.advanceTimersByTime(260));
      expect(screen.getByText("skeleton")).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { APP_TOUR, SECTION_TOURS, tourFor } from "../lib/tours";
import { TourOverlay } from "./Tour";

describe("TourOverlay", () => {
  it("walks the steps, skipping missing targets", async () => {
    const onDone = vi.fn();
    render(
      <>
        <button data-tour="a">A</button>
        <button data-tour="c">C</button>
        <TourOverlay tour={{ id: "t", page: null, steps: [
          { target: "a", title: "First", body: "one" },
          { target: "missing", title: "Gone", body: "never shown" },
          { target: "c", title: "Third", body: "three" },
        ] }} onDone={onDone} />
      </>,
    );
    expect(screen.getByRole("dialog", { name: "First" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByRole("dialog", { name: "Third" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByRole("dialog", { name: "First" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(onDone).toHaveBeenCalledWith(false);
  });

  it("finishes with Done", async () => {
    const onDone = vi.fn();
    render(<TourOverlay tour={{ id: "t", page: null, steps: [{ target: null, title: "Only", body: "x" }] }} onDone={onDone} />);
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(onDone).toHaveBeenCalledWith(true);
  });

  it("has a tour for every section and the app", () => {
    expect(tourFor(null)).toBe(APP_TOUR);
    expect(APP_TOUR.steps.length).toBeLessThanOrEqual(3); // v1.2: three steps at most
    expect(APP_TOUR.steps.map((s) => s.title).join(" ")).not.toMatch(/AI|Ollama/);
    for (const id of Object.keys(SECTION_TOURS)) {
      const t = tourFor(id)!;
      expect(t.steps[0].target).toBe(`nav-${t.page}`);
      expect(t.steps.length).toBeLessThanOrEqual(5);
    }
    expect(tourFor("nowhere")).toBeNull();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExerciseArt } from "./ExerciseArt";

const base = { name: "Front Lever", section: "calisthenics" as const, muscles: [{ muscle: "latissimus_dorsi", weight: 1 }, { muscle: "teres_major", weight: 0.75 }] };

describe("ExerciseArt", () => {
  it("shows the bundled photo when there is one", () => {
    render(<ExerciseArt exercise={{ ...base, image: "exercises/pullups.webp" }} />);
    expect(screen.getByTestId("exercise-photo")).toHaveAttribute("src", "exercises/pullups.webp");
    expect(screen.queryByTestId("exercise-tile")).toBeNull();
  });

  it("draws a designed tile, never an empty box, when there is no photo", () => {
    render(<ExerciseArt exercise={{ ...base, image: null }} />);
    const tile = screen.getByTestId("exercise-tile");
    expect(tile.querySelector("svg")).not.toBeNull();
    // the lats sit on the back: the tile draws the back view with them filled
    expect(tile.querySelectorAll('path[data-key="latissimus_dorsi"]').length).toBeGreaterThan(0);
    expect(tile).toHaveTextContent("Lats");
  });

  it("falls back to the tile when the photo fails to load", () => {
    render(<ExerciseArt exercise={{ ...base, image: "exercises/missing.webp" }} />);
    fireEvent.error(screen.getByTestId("exercise-photo"));
    expect(screen.getByTestId("exercise-tile")).toBeInTheDocument();
  });

  it("names the section when no main muscle is known", () => {
    render(<ExerciseArt exercise={{ name: "Box Breathing", section: "meditation", image: null, muscles: [] }} />);
    expect(screen.getByTestId("exercise-tile")).toHaveTextContent("Mind");
  });
});

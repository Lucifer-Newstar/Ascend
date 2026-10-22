import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExerciseArt } from "./ExerciseArt";

const base = { name: "Front Lever", section: "calisthenics" as const, muscles: [{ muscle: "lats", weight: 1 }] };

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

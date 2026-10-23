import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExerciseArt, formTips, secondFrame } from "./ExerciseArt";

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

  it("loops the photo with its second frame, and drops the loop when there is none", () => {
    expect(secondFrame("exercises/push-up.webp")).toBe("exercises/push-up-2.webp");
    expect(secondFrame(null)).toBeNull();
    render(<ExerciseArt exercise={{ ...base, image: "exercises/pullups.webp" }} loop />);
    expect(screen.getByTestId("exercise-frame-2")).toHaveAttribute("src", "exercises/pullups-2.webp");
    fireEvent.error(screen.getByTestId("exercise-frame-2"));
    expect(screen.queryByTestId("exercise-loop")).toBeNull();
    expect(screen.getByTestId("exercise-photo")).toHaveAttribute("src", "exercises/pullups.webp");
  });

  it("turns instructions into three short tips", () => {
    const tips = formTips([
      "Hang from the bar with straight arms. Keep your shoulders active.",
      "Pull your chest to the bar.",
      "Lower slowly under control.",
      "Repeat.",
    ]);
    expect(tips).toEqual(["Hang from the bar with straight arms.", "Pull your chest to the bar.", "Lower slowly under control."]);
    expect(formTips(["x ".repeat(80)])[0].length).toBeLessThanOrEqual(110);
    expect(formTips([])).toEqual([]);
  });
});

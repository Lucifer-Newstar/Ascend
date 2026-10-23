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
    render(<ExerciseArt exercise={{ ...base, image: "exercises/archer-pull-up.webp" }} loop />);
    expect(screen.getByTestId("exercise-frame-2")).toHaveAttribute("src", "exercises/archer-pull-up-2.webp");
    fireEvent.error(screen.getByTestId("exercise-frame-2"));
    expect(screen.queryByTestId("exercise-loop")).toBeNull();
    expect(screen.getByTestId("exercise-photo")).toHaveAttribute("src", "exercises/archer-pull-up.webp");
  });

  it("plays the proper animation over its first frame for an animated move, and falls back to the 2-frame loop", () => {
    const { unmount } = render(<ExerciseArt exercise={{ ...base, name: "Pullups", image: "exercises/pullups.webp" }} loop />);
    expect(screen.getByTestId("exercise-anim")).toBeInTheDocument();
    expect(screen.getByTestId("exercise-anim-img")).toHaveAttribute("src", "exercises/pullups-anim.webp");
    expect(screen.getByTestId("exercise-photo")).toHaveAttribute("src", "exercises/pullups.webp");
    fireEvent.error(screen.getByTestId("exercise-anim-img"));
    expect(screen.queryByTestId("exercise-anim")).toBeNull();
    expect(screen.getByTestId("exercise-frame-2")).toHaveAttribute("src", "exercises/pullups-2.webp");
    unmount();
    // Without loop (a library card) the still photo shows, no animation.
    render(<ExerciseArt exercise={{ ...base, name: "Pullups", image: "exercises/pullups.webp" }} />);
    expect(screen.queryByTestId("exercise-anim")).toBeNull();
  });

  it("animates a martial-arts drill that has no photo, by its name", () => {
    render(<ExerciseArt exercise={{ name: "Front Kick Drill", section: "martial_arts" as const, image: null, muscles: [] }} loop />);
    expect(screen.getByTestId("exercise-anim-img")).toHaveAttribute("src", "exercises/front-kick-drill-anim.webp");
    expect(screen.getByTestId("exercise-photo")).toHaveAttribute("src", "exercises/front-kick-drill.webp");
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

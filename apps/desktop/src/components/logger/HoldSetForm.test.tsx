import type { Exercise } from "@ascend/shared";
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { axeViolations } from "../../test/axe";
import { HoldSetForm } from "./HoldSetForm";

const lsit: Exercise = {
  id: 7, name: "L-sit", equipment: "parallettes", section: "calisthenics", met: null, time_based: false,
  muscles: [{ muscle: "rectus_abdominis", weight: 1 }], measure: "hold",
};

afterEach(() => vi.useRealTimers());

describe("HoldSetForm", () => {
  it("logs the chosen seconds with added load and RPE", async () => {
    const onSubmit = vi.fn();
    const { container } = render(<HoldSetForm exercise={lsit} units="metric" busy={false} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole("button", { name: "30 s" }));
    await userEvent.click(screen.getByRole("button", { name: "Log hold" }));
    expect(onSubmit).toHaveBeenCalledWith({ exercise_id: 7, duration_s: 30, weight_kg: 0, reps: 1, rpe: 8 });
    expect(await axeViolations(container)).toEqual([]);
  });

  it("times a hold with the stopwatch and logs it on stop", () => {
    vi.useFakeTimers();
    const onSubmit = vi.fn();
    render(<HoldSetForm exercise={lsit} units="metric" busy={false} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Start timer" }));
    act(() => { vi.advanceTimersByTime(12_300); });
    expect(screen.getByRole("timer")).toHaveTextContent("12s");
    fireEvent.click(screen.getByRole("button", { name: "Stop & log" }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ duration_s: 12 }));
  });

  it("does not log a zero-second stop", () => {
    vi.useFakeTimers();
    const onSubmit = vi.fn();
    render(<HoldSetForm exercise={lsit} units="metric" busy={false} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Start timer" }));
    fireEvent.click(screen.getByRole("button", { name: "Stop & log" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

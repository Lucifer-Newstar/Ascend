import type { Exercise } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TimedSetForm } from "./TimedSetForm";

const ex = (section: Exercise["section"], name = "Running"): Exercise => ({
  id: 7, name, equipment: "none", section, met: 9.8, time_based: true, muscles: [],
});

describe("TimedSetForm", () => {
  it("logs a run with distance in km and heart rate", async () => {
    const submit = vi.fn();
    render(<TimedSetForm exercise={ex("cardio")} units="metric" onSubmit={submit} />);
    const duration = screen.getByLabelText("Duration (min or m:ss)");
    await userEvent.clear(duration);
    await userEvent.type(duration, "28:30");
    await userEvent.type(screen.getByLabelText("Distance (km)"), "5.2");
    await userEvent.type(screen.getByLabelText("Avg heart rate"), "151");
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    expect(submit).toHaveBeenCalledWith({ exercise_id: 7, duration_s: 1710, distance_m: 5200, avg_hr: 151, rpe: 7 });
  });

  it("converts miles to metres", async () => {
    const submit = vi.fn();
    render(<TimedSetForm exercise={ex("cardio")} units="imperial" onSubmit={submit} />);
    await userEvent.type(screen.getByLabelText("Distance (mi)"), "1");
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    expect(submit.mock.calls[0][0].distance_m).toBe(1609);
  });

  it("meditation has no RPE, distance or heart rate", async () => {
    const submit = vi.fn();
    render(<TimedSetForm exercise={ex("meditation", "Box Breathing")} units="metric" onSubmit={submit} />);
    expect(screen.queryByLabelText(/RPE/)).toBeNull();
    expect(screen.queryByLabelText(/Distance/)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Log sit" }));
    expect(submit).toHaveBeenCalledWith({ exercise_id: 7, duration_s: 600, distance_m: null, avg_hr: null, rpe: null });
  });

  it("rejects an unreadable duration", async () => {
    const submit = vi.fn();
    render(<TimedSetForm exercise={ex("flexibility", "Pigeon Pose")} units="metric" onSubmit={submit} />);
    const duration = screen.getByLabelText("Duration (min or m:ss)");
    await userEvent.clear(duration);
    await userEvent.type(duration, "abc");
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a duration");
    expect(submit).not.toHaveBeenCalled();
  });
});

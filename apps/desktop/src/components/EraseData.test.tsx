import type { TrainerState } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { expectNoAxeViolations } from "../test/axe";
import { EraseDataPanel } from "./EraseData";
import { FirstRunCard } from "./FirstRun";

vi.mock("../api/client", () => ({ api: { eraseData: vi.fn() } }));

const state: TrainerState = { onboarded: false, has_profile: true, has_history: true, demo_data: true, trainer_id: "iskra", tours_done: [] };

describe("Start fresh", () => {
  it("needs ERASE typed before it erases", async () => {
    vi.mocked(api.eraseData).mockResolvedValue({ erased: { workouts: 3 }, safety_backup: "ascend-pre-erase.db" });
    const onErased = vi.fn();
    render(<EraseDataPanel onErased={onErased} />);
    await userEvent.click(screen.getByRole("button", { name: "Erase my data…" }));
    const go = screen.getByRole("button", { name: "Erase my data" });
    expect(go).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Type ERASE/), "erase");
    await userEvent.click(screen.getByLabelText(/Keep my preferences/));
    await expectNoAxeViolations(document.body);
    await userEvent.click(go);
    expect(api.eraseData).toHaveBeenCalledWith(false);
    expect(onErased).toHaveBeenCalledWith({ erased: { workouts: 3 }, safety_backup: "ascend-pre-erase.db" });
  });

  it("the 1.1 welcome offers start fresh when demo data is present", async () => {
    const onTour = vi.fn();
    const onDone = vi.fn();
    render(<FirstRunCard state={state} onTour={onTour} onDone={onDone} onErased={() => {}} />);
    expect(screen.getByTestId("welcome-data-note")).toHaveTextContent("demo data");
    await userEvent.click(screen.getByRole("button", { name: "Start fresh…" }));
    expect(screen.getByRole("alertdialog", { name: "Erase my data" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Take the tour" }));
    expect(onTour).toHaveBeenCalled();
  });

  it("a new profile only gets the tour offer", async () => {
    const onDone = vi.fn();
    render(<FirstRunCard state={{ ...state, has_history: false, demo_data: false }} onTour={() => {}} onDone={onDone} onErased={() => {}} />);
    expect(screen.queryByRole("button", { name: "Start fresh…" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Maybe later" }));
    expect(onDone).toHaveBeenCalled();
  });
});

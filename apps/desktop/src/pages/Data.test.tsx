import type { ImportReport } from "@ascend/shared";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DataPage } from "./Data";

vi.mock("../api/client", () => ({
  api: { importCsv: vi.fn(), exportJson: vi.fn(), exportCsv: vi.fn() },
}));

const report = (over: Partial<ImportReport> = {}): ImportReport => ({
  format: "strong_csv", workouts: 2, sets: 6, unmatched_exercises: ["Zercher Good Morning (Barbell)"], warnings: [],
  dry_run: true, skipped_duplicates: 0, skipped_warmups: 1,
  matched_exercises: { "Squat (Barbell)": "Back Squat" }, ...over,
});
const csv = () => new File(["Date;Workout Name;Exercise Name;Set Order;Weight;Weight Unit\n"], "strong.csv");

function setup(onChanged = vi.fn(), onOpenHistory = vi.fn()) {
  render(
    <ToastProvider>
      <DataPage onChanged={onChanged} onOpenHistory={onOpenHistory} />
    </ToastProvider>,
  );
  return { onChanged, onOpenHistory };
}

describe("DataPage import", () => {
  beforeEach(() => { vi.mocked(api.importCsv).mockReset(); });

  it("previews a file with a dry run, then imports on confirm", async () => {
    vi.mocked(api.importCsv)
      .mockResolvedValueOnce(report())
      .mockResolvedValueOnce(report({ dry_run: false }));
    const { onChanged, onOpenHistory } = setup();

    await userEvent.upload(screen.getByLabelText(/drop your strong export/i), csv());
    expect(await screen.findByText(/ready to import/i)).toBeInTheDocument();
    expect(api.importCsv).toHaveBeenLastCalledWith("strong", expect.objectContaining({ dry_run: true, unit: "kg" }));
    expect(screen.getByText("Zercher Good Morning (Barbell)")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Import 2 workouts" }));
    expect(api.importCsv).toHaveBeenLastCalledWith("strong", expect.objectContaining({ dry_run: false }));
    expect(await screen.findByRole("heading", { name: /^imported/i })).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "See it in History" }));
    expect(onOpenHistory).toHaveBeenCalled();
  });

  it("sends Hevy files to the Hevy importer and hides the unit switch", async () => {
    vi.mocked(api.importCsv).mockResolvedValue(report({ format: "hevy_csv" }));
    setup();
    await userEvent.click(screen.getByLabelText("Hevy"));
    expect(screen.queryByText("Weights in")).not.toBeInTheDocument();
    await userEvent.upload(screen.getByLabelText(/drop your hevy export/i), csv());
    await waitFor(() => expect(api.importCsv).toHaveBeenCalledWith("hevy", expect.anything()));
  });

  it("disables Import when nothing new is in the file", async () => {
    vi.mocked(api.importCsv).mockResolvedValue(report({ workouts: 0, sets: 0, skipped_duplicates: 2 }));
    setup();
    await userEvent.upload(screen.getByLabelText(/drop your strong export/i), csv());
    expect(await screen.findByText(/already in ascend/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import 0 workouts" })).toBeDisabled();
  });

  it("shows the sidecar's message when the file is not an export", async () => {
    vi.mocked(api.importCsv).mockImplementation(async () => {
      throw new Error("this does not look like a Strong or Hevy export");
    });
    setup();
    await userEvent.upload(screen.getByLabelText(/drop your strong export/i), csv());
    expect(await screen.findByText(/not look like a Strong or Hevy export/)).toHaveAttribute("role", "alert");
  });

  it("asks for a fresh preview after an option changes", async () => {
    vi.mocked(api.importCsv).mockResolvedValue(report());
    setup();
    await userEvent.upload(screen.getByLabelText(/drop your strong export/i), csv());
    await screen.findByText(/ready to import/i);
    await userEvent.click(screen.getByLabelText("lb"));
    expect(screen.queryByText(/ready to import/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /check strong.csv again/i }));
    expect(api.importCsv).toHaveBeenLastCalledWith("strong", expect.objectContaining({ unit: "lb", dry_run: true }));
  });
});

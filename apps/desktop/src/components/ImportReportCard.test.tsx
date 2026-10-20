import type { ImportReport } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ImportReportCard } from "./ImportReportCard";

const base: ImportReport = {
  format: "hevy_csv", workouts: 3, sets: 18, unmatched_exercises: [], warnings: [], dry_run: true,
  skipped_duplicates: 1, skipped_warmups: 4, matched_exercises: {},
};

describe("ImportReportCard", () => {
  it("labels a preview and shows the counts", () => {
    render(<ImportReportCard report={base} />);
    expect(screen.getByRole("heading")).toHaveTextContent("Ready to import · Hevy");
    expect(screen.getByText("Preview: nothing saved yet")).toBeInTheDocument();
    expect(screen.getByText("18")).toBeInTheDocument();
    expect(screen.getByText("Warm-ups skipped").previousSibling).toHaveTextContent("4");
  });

  it("lists every unmatched exercise with a singular/plural heading", () => {
    render(<ImportReportCard report={{ ...base, unmatched_exercises: ["Sled Push"] }} />);
    expect(screen.getByText(/1 exercise not in the/)).toBeInTheDocument();
    expect(screen.getByText("Sled Push")).toBeInTheDocument();
  });

  it("explains an import with nothing new", () => {
    render(<ImportReportCard report={{ ...base, workouts: 0, sets: 0, skipped_duplicates: 3, dry_run: false }} />);
    expect(screen.getByRole("heading")).toHaveTextContent("Imported");
    expect(screen.getByText("Every workout in this file is already in ASCEND.")).toBeInTheDocument();
  });

  it("shows dropped rows and the name mapping behind disclosures", () => {
    render(
      <ImportReportCard
        report={{ ...base, warnings: ["2026-09-10 Deadlift set 1: weight outside 0-500 kg"], matched_exercises: { "Squat (Barbell)": "Back Squat" } }}
      />,
    );
    expect(screen.getByText("1 row dropped")).toBeInTheDocument();
    expect(screen.getByText("How names were matched (1)")).toBeInTheDocument();
    expect(screen.getByText("Back Squat")).toBeInTheDocument();
  });
});

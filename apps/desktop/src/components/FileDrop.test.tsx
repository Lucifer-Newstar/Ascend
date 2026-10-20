import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FileDrop } from "./FileDrop";

const csv = () => new File(["Date,Workout Name\n"], "strong.csv", { type: "text/csv" });

describe("FileDrop", () => {
  it("passes a picked file to onFile", async () => {
    const onFile = vi.fn();
    render(<FileDrop label="Choose a CSV" onFile={onFile} />);
    await userEvent.upload(screen.getByLabelText(/choose a csv/i), csv());
    expect(onFile).toHaveBeenCalledWith(expect.objectContaining({ name: "strong.csv" }));
  });

  it("accepts a dropped file and highlights while dragging", () => {
    const onFile = vi.fn();
    render(<FileDrop label="Drop it" onFile={onFile} />);
    const box = screen.getByText("Drop it").closest("label")!;
    fireEvent.dragOver(box);
    expect(box).toHaveAttribute("data-over");
    fireEvent.drop(box, { dataTransfer: { files: [csv()] } });
    expect(onFile).toHaveBeenCalledTimes(1);
    expect(box).not.toHaveAttribute("data-over");
  });

  it("shows the chosen file name instead of the prompt", () => {
    render(<FileDrop label="Choose" fileName="hevy.csv" onFile={() => {}} />);
    expect(screen.getByText("hevy.csv")).toBeInTheDocument();
  });

  it("ignores drops while disabled", () => {
    const onFile = vi.fn();
    render(<FileDrop label="Busy" disabled onFile={onFile} />);
    fireEvent.drop(screen.getByText("Busy").closest("label")!, { dataTransfer: { files: [csv()] } });
    expect(onFile).not.toHaveBeenCalled();
  });
});

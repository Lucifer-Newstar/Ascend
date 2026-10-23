import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ShareDialog } from "./ShareCard";

const card = {
  kind: "pr", title: "New PR", headline: "Bench Press 60 kg", detail: "5 reps", caption: "New PR on ASCEND",
  x_url: "https://x.com/intent/post?text=x", version: "share-v1",
};

describe("ShareDialog", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "shareCard").mockResolvedValue(card);
  });

  it("fits small screens: the dialog scrolls and the image is capped", async () => {
    render(<ShareDialog payload={{ kind: "pr" }} onClose={() => {}} />);
    await screen.findByTestId("share-caption");
    const dialog = screen.getByTestId("share-dialog");
    expect(dialog.className).toMatch(/max-h-\[90vh\]/);
    expect(dialog.className).toMatch(/overflow-y-auto/);
    expect(screen.getByTestId("share-overlay").className).toMatch(/overflow-y-auto/);
    const img = screen.queryByTestId("share-image");
    if (img) expect(img.className).toMatch(/max-h-\[40vh\]/);
    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  });

  it("closes from the backdrop, the Close button and Esc, but not from a click inside", async () => {
    const onClose = vi.fn();
    render(<ShareDialog payload={{ kind: "pr" }} onClose={onClose} />);
    await screen.findByTestId("share-caption");
    fireEvent.mouseDown(screen.getByTestId("share-dialog"));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.mouseDown(screen.getByTestId("share-overlay"));
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(3);
  });
});

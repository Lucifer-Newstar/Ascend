import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { useBlurWhenAway } from "../pages/Profile";
import { BackupsPanel } from "./BackupsPanel";
import { PHOTO_FACTS, PhotoSafety } from "./PhotoSafety";

const backup = (photos_included: boolean) => ({
  path: "C:/data/backups/ascend-20261023-100000.ascendbak",
  size_bytes: 1000,
  sha256: "x".repeat(64),
  created_at: "2026-10-23T10:00:00",
  schema_revision: "0031",
  app_version: "1.2.0",
  reason: "manual",
  photos: 0,
  photos_included,
});

describe("photo safety", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("says where photos live and never mentions body numbers as a feature", () => {
    render(<PhotoSafety />);
    expect(screen.getByText(/stay on this PC/)).toBeInTheDocument();
    expect(PHOTO_FACTS.some((f) => /never estimates body fat or weight/.test(f))).toBe(true);
  });

  it("asks before deleting every photo", async () => {
    const del = vi.spyOn(api, "deleteAllPhotos").mockResolvedValue({ deleted: 3 });
    render(<PhotoSafety />);
    fireEvent.click(screen.getByRole("button", { name: "Delete all progress photos" }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("can't be undone");
    expect(del).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Delete all photos" }));
    await waitFor(() => expect(del).toHaveBeenCalledTimes(1));
  });

  it("makes a backup without photos when the box is unticked and marks it", async () => {
    vi.spyOn(api, "backups").mockResolvedValue([backup(false)]);
    const now = vi.spyOn(api, "backupNow").mockResolvedValue(backup(false));
    render(<BackupsPanel />);
    expect(await screen.findByTestId("backup-no-photos")).toHaveTextContent("No photos");
    fireEvent.click(screen.getByTestId("backup-with-photos"));
    fireEvent.click(screen.getByRole("button", { name: "Back up now" }));
    await waitFor(() => expect(now).toHaveBeenCalledWith(false));
  });

  it("blurs shown photos again when the window loses focus", () => {
    const setReveal = vi.fn();
    renderHook(() => useBlurWhenAway(setReveal));
    act(() => {
      window.dispatchEvent(new Event("blur"));
    });
    expect(setReveal).toHaveBeenCalledWith(false);
  });
});

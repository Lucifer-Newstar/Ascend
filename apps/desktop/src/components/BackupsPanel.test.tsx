import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { BackupsPanel, fileLabel } from "./BackupsPanel";

const B = (reason: string, created_at: string) => ({
  path: `C:/data/backups/ascend-${created_at}-${reason}.ascendbak`,
  size_bytes: 2_400_000,
  sha256: "x".repeat(64),
  created_at,
  schema_revision: "0017",
  app_version: "1.0.0",
  reason,
});

describe("BackupsPanel", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("lists backups with their kind and size", async () => {
    vi.spyOn(api, "backups").mockResolvedValue([B("daily", "2026-10-22T09:00:00"), B("manual", "2026-10-21T20:00:00")]);
    render(<BackupsPanel />);
    expect(await screen.findByText("Daily")).toBeInTheDocument();
    expect(screen.getByText("Manual")).toBeInTheDocument();
    expect(screen.getByText(/2 backups · 4\.6 MB in total/)).toBeInTheDocument();
  });

  it("asks before restoring and only restores after confirming", async () => {
    vi.spyOn(api, "backups").mockResolvedValue([B("daily", "2026-10-22T09:00:00")]);
    const restore = vi.spyOn(api, "restoreBackup").mockResolvedValue({
      restored_from: "x", backup_created_at: "2026-10-22T09:00:00", schema_revision: "0017", safety_backup: "y",
    });
    render(<BackupsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: /Restore the backup/ }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("backed up first");
    expect(restore).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Restore the backup/ }));
    fireEvent.click(screen.getByRole("button", { name: "Restore" }));
    await waitFor(() => expect(restore).toHaveBeenCalledWith(expect.stringContaining("daily")));
  });

  it("backs up on demand", async () => {
    vi.spyOn(api, "backups").mockResolvedValue([]);
    const now = vi.spyOn(api, "backupNow").mockResolvedValue(B("manual", "2026-10-22T10:00:00"));
    render(<BackupsPanel />);
    expect(await screen.findByText("No backups yet.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back up now" }));
    await waitFor(() => expect(now).toHaveBeenCalled());
  });

  it("names a save file you copied into the backups folder", () => {
    expect(fileLabel("C:\\Users\\n\\AppData\\Roaming\\ASCEND\\data\\backups\\ASCEND_tester_save.ascendbak")).toBe("ASCEND_tester_save");
    expect(fileLabel("/data/backups/ascend-20261023-091500-daily.ascendbak")).toBeNull();
  });
});

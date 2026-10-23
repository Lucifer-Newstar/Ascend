import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations } from "../test/axe";
import { Layout, type Page } from "./Layout";

function renderAt(page: Page, title: string, onNavigate = vi.fn()) {
  return render(
    <Layout page={page} onNavigate={onNavigate} title={title}>
      <p>content</p>
    </Layout>,
  );
}

describe("Layout", () => {
  it("shows a visible indicator only while online research is on", async () => {
    const nav = vi.fn();
    const { rerender, container } = renderAt("dashboard", "Dashboard", nav);
    expect(screen.queryByRole("button", { name: "Online research on" })).toBeNull();
    expect(screen.getByText("Offline · data stays on this PC")).toBeInTheDocument();
    rerender(
      <Layout page="dashboard" onNavigate={nav} title="Dashboard" onlineResearch>
        <p>content</p>
      </Layout>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Online research on" }));
    expect(nav).toHaveBeenCalledWith("settings");
    expect(screen.getByText(/only exercise names leave this PC/)).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("has no AI status pill in the top bar (v1.2: AI setup lives in Settings)", () => {
    renderAt("dashboard", "Today");
    expect(screen.queryByRole("switch", { name: /AI coach/ })).toBeNull();
    expect(screen.queryByText(/AI on|AI off/)).toBeNull();
  });

  it("marks the current page and navigates from the sidebar", async () => {
    const nav = vi.fn();
    renderAt("history", "History", nav);
    expect(screen.getByRole("button", { name: "History" })).toHaveAttribute("aria-current", "page");
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(nav).toHaveBeenCalledWith("settings");
  });

  it("sets the window title and moves focus to the heading on page change", () => {
    const { rerender } = renderAt("dashboard", "Dashboard");
    expect(document.title).toBe("Dashboard · ASCEND");
    expect(screen.getByRole("heading", { level: 1 })).not.toHaveFocus(); // not on first paint
    rerender(
      <Layout page="diet" onNavigate={vi.fn()} title="Diet">
        <p>content</p>
      </Layout>,
    );
    expect(document.title).toBe("Diet · ASCEND");
    expect(screen.getByRole("heading", { level: 1, name: "Diet" })).toHaveFocus();
  });

  it("starts a new page at the top instead of the previous page's scroll offset", () => {
    const { rerender } = renderAt("settings", "Settings");
    const main = document.getElementById("main")!;
    main.scrollTop = 400;
    expect(main.scrollTop).toBe(400);
    rerender(
      <Layout page="dashboard" onNavigate={vi.fn()} title="Dashboard">
        <p>content</p>
      </Layout>,
    );
    expect(main.scrollTop).toBe(0);
  });

  it("does not grab focus on first load under StrictMode's double effects", () => {
    render(
      <StrictMode>
        <Layout page="dashboard" onNavigate={vi.fn()} title="Dashboard">
          <p>content</p>
        </Layout>
      </StrictMode>,
    );
    expect(screen.getByRole("heading", { level: 1 })).not.toHaveFocus();
  });

  it("lets the keyboard reach the scrollable main area on pages without controls", async () => {
    renderAt("history", "History");
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("tabindex", "0");
    main.focus();
    expect(main).toHaveFocus();
  });

  it("has a skip link that jumps to the page heading", async () => {
    renderAt("progress", "Progress");
    await userEvent.tab();
    const skip = screen.getByRole("link", { name: "Skip to content" });
    expect(skip).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByRole("heading", { level: 1 })).toHaveFocus();
  });

    it("has no axe violations", async () => {
    const { container } = renderAt("dashboard", "Dashboard");
    await expectNoAxeViolations(container);
  });

  it("labels the rail the v5 way and keeps Ctrl+1…0 in rail order", () => {
    renderAt("dashboard", "Today");
    const nav = screen.getByRole("navigation", { name: "Main" });
    const names = [...nav.querySelectorAll("button")].map((b) => b.textContent?.replace(/Ctrl \d/, "").trim());
    expect(names).toEqual(["Today", "Train", "Exercises", "Skills", "Progress", "Fuel", "Planner", "Profile", "History", "Settings"]);
    expect(screen.getByRole("button", { name: "Skills" })).toHaveAttribute("aria-keyshortcuts", "Control+4");
    expect(screen.getByRole("button", { name: "Settings" })).toHaveAttribute("aria-keyshortcuts", "Control+0");
    expect(screen.getByRole("button", { name: "Profile" })).toHaveAttribute("aria-keyshortcuts", "Control+8");
  });

});

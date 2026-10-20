import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations } from "../test/axe";
import { Layout, type Page } from "./Layout";

function renderAt(page: Page, title: string, onNavigate = vi.fn()) {
  return render(
    <Layout page={page} onNavigate={onNavigate} aiEnabled={false} onToggleAi={() => {}} title={title}>
      <p>content</p>
    </Layout>,
  );
}

describe("Layout", () => {
  it("marks the current page and navigates from the sidebar", async () => {
    const nav = vi.fn();
    renderAt("history", "History", nav);
    expect(screen.getByRole("button", { name: "History" })).toHaveAttribute("aria-current", "page");
    await userEvent.click(screen.getByRole("button", { name: "Import & export" }));
    expect(nav).toHaveBeenCalledWith("data");
  });

  it("sets the window title and moves focus to the heading on page change", () => {
    const { rerender } = renderAt("dashboard", "Dashboard");
    expect(document.title).toBe("Dashboard · ASCEND");
    expect(screen.getByRole("heading", { level: 1 })).not.toHaveFocus(); // not on first paint
    rerender(
      <Layout page="diet" onNavigate={vi.fn()} aiEnabled={false} onToggleAi={() => {}} title="Diet">
        <p>content</p>
      </Layout>,
    );
    expect(document.title).toBe("Diet · ASCEND");
    expect(screen.getByRole("heading", { level: 1, name: "Diet" })).toHaveFocus();
  });

  it("does not grab focus on first load under StrictMode's double effects", () => {
    render(
      <StrictMode>
        <Layout page="dashboard" onNavigate={vi.fn()} aiEnabled={false} onToggleAi={() => {}} title="Dashboard">
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

  it("exposes the AI toggle as a switch", () => {
    renderAt("dashboard", "Dashboard");
    expect(screen.getByRole("switch", { name: /ai coach/i })).toHaveAttribute("aria-checked", "false");
  });

  it("has no axe violations", async () => {
    const { container } = renderAt("dashboard", "Dashboard");
    await expectNoAxeViolations(container);
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { KpiTile, Panel } from "./Page";

describe("Panel", () => {
  it("labels the section with its title and shows the children", () => {
    render(<Panel id="demo" title="Demo card">content</Panel>);
    expect(screen.getByRole("region", { name: "Demo card" })).toHaveTextContent("content");
  });

  it("shows a busy skeleton while loading instead of the children", () => {
    render(<Panel id="demo" title="Demo" loading>content</Panel>);
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("shows a compact error with Retry", async () => {
    const retry = vi.fn();
    render(<Panel id="demo" title="Demo" error="boom" onRetry={retry}>content</Panel>);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("shows the empty state with its one action", async () => {
    const go = vi.fn();
    render(<Panel id="demo" title="Demo" empty={{ title: "Nothing yet.", action: { label: "Log one", onClick: go } }}>content</Panel>);
    expect(screen.getByText("Nothing yet.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Log one" }));
    expect(go).toHaveBeenCalledOnce();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("staggers entry through a CSS variable, not inline animation", () => {
    render(<Panel id="demo" title="Demo" index={3}>x</Panel>);
    const section = screen.getByRole("region", { name: "Demo" });
    expect(section.className).toContain("rise-in");
    expect(section.style.getPropertyValue("--i")).toBe("3");
  });
});

describe("KpiTile", () => {
  it("shows the label, value and sub line", () => {
    render(<KpiTile label="Trend weight" value="74.3 kg" sub="-0.4 kg" />);
    expect(screen.getByText("Trend weight")).toBeInTheDocument();
    expect(screen.getByText("74.3 kg")).toBeInTheDocument();
    expect(screen.getByText("-0.4 kg")).toBeInTheDocument();
  });

  it("hides the value behind a skeleton while loading", () => {
    render(<KpiTile label="Trend weight" value="74.3 kg" loading />);
    expect(screen.queryByText("74.3 kg")).not.toBeInTheDocument();
  });
});

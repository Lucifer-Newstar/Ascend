import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TOAST_MS, ToastProvider, useToast } from "./Toast";

function Trigger({ text, tone }: { text: string; tone?: "info" | "error" }) {
  const toast = useToast();
  return <button type="button" onClick={() => toast(text, tone)}>fire</button>;
}

describe("ToastProvider", () => {
  afterEach(() => vi.useRealTimers());

  it("puts errors in the assertive region and the rest in the polite one", async () => {
    render(
      <ToastProvider>
        <Trigger text="Saved" />
        <Trigger text="Engine offline" tone="error" />
      </ToastProvider>,
    );
    const [info, error] = screen.getAllByRole("button", { name: "fire" });
    await userEvent.click(info);
    await userEvent.click(error);
    expect(screen.getByRole("status")).toHaveTextContent("Saved");
    expect(screen.getByRole("alert")).toHaveTextContent("Engine offline");
  });

  it("can be dismissed", async () => {
    render(
      <ToastProvider>
        <Trigger text="Saved" />
      </ToastProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "fire" }));
    await userEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });

  it("keeps errors on screen longer than info", () => {
    vi.useFakeTimers();
    render(
      <ToastProvider>
        <Trigger text="Saved" />
        <Trigger text="Engine offline" tone="error" />
      </ToastProvider>,
    );
    const [info, error] = screen.getAllByRole("button", { name: "fire" });
    act(() => { info.click(); error.click(); });
    act(() => { vi.advanceTimersByTime(TOAST_MS.info + 10); });
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
    expect(screen.getByText("Engine offline")).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(TOAST_MS.error); });
    expect(screen.queryByText("Engine offline")).not.toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Empty, ErrorState, Loading } from "./States";

describe("shared states", () => {
  it("shows a loading label", () => {
    render(<Loading label="Fetching sets" />);
    expect(screen.getByText("Fetching sets")).toBeInTheDocument();
  });

  it("shows the error and retries on click", async () => {
    const retry = vi.fn();
    render(<ErrorState message="Engine offline" onRetry={retry} />);
    expect(screen.getByText("Engine offline")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("hides retry when no handler is given", () => {
    render(<ErrorState message="x" />);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders an empty state with a hint", () => {
    render(<Empty title="No sets yet" hint="Pick an exercise" />);
    expect(screen.getByText("No sets yet")).toBeInTheDocument();
    expect(screen.getByText("Pick an exercise")).toBeInTheDocument();
  });

  it("has a compact inline error with retry, and an empty state with an action", async () => {
    const retry = vi.fn();
    const act = vi.fn();
    render(<><ErrorState compact message="timeout" onRetry={retry} /><Empty title="No meals" action={{ label: "Log a meal", onClick: act }} /></>);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load: timeout");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await userEvent.click(screen.getByRole("button", { name: "Log a meal" }));
    expect(retry).toHaveBeenCalledOnce();
    expect(act).toHaveBeenCalledOnce();
  });
});

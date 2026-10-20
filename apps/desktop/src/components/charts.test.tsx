import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { BarChart, LineChart } from "./charts";

describe("charts", () => {
  it("line chart exposes its summary and the numbers as a table", async () => {
    render(
      <LineChart
        labels={["1 Oct", "2 Oct", "3 Oct"]}
        unit=" kg"
        summary="Weight trend over 3 days"
        series={[
          { label: "Weigh-ins", values: [76.2, null, 75.8], className: "stroke-muted" },
          { label: "Trend", values: [76.1, 76.0, 75.9], className: "stroke-accent" },
        ]}
      />,
    );
    expect(screen.getByRole("img", { name: "Weight trend over 3 days" })).toBeInTheDocument();
    await userEvent.click(screen.getByText("Show the numbers"));
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Date", "Weigh-ins", "Trend"]);
    const second = within(table).getByRole("rowheader", { name: "2 Oct" }).closest("tr")!;
    expect(within(second).getAllByRole("cell").map((c) => c.textContent)).toEqual(["–", "76 kg"]);
  });

  it("bar chart table uses the value label", () => {
    render(<BarChart labels={["W1", "W2"]} values={[3, 4]} summary="Sessions per week" valueLabel="Sessions" />);
    expect(screen.getByRole("columnheader", { name: "Sessions" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "W2" }).closest("tr")).toHaveTextContent("4");
  });

  it("the table can be switched off", () => {
    render(<BarChart labels={["W1"]} values={[3]} summary="x" table={false} />);
    expect(screen.queryByText("Show the numbers")).not.toBeInTheDocument();
  });

  it("renders nothing without data", () => {
    const { container } = render(<LineChart labels={[]} series={[]} summary="empty" />);
    expect(container).toBeEmptyDOMElement();
  });
});

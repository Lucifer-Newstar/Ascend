import { describe, expect, it } from "vitest";

import { extent, linePath, linearScale, niceTicks } from "./chart";

describe("chart maths", () => {
  it("maps a domain onto a range", () => {
    const y = linearScale([60, 80], [200, 0]);
    expect(y(60)).toBe(200);
    expect(y(70)).toBe(100);
    expect(y(80)).toBe(0);
  });

  it("picks round ticks", () => {
    expect(niceTicks(68.2, 72.9, 4)).toEqual([68, 70, 72]);
    expect(niceTicks(68.2, 72.9, 8)).toEqual([68, 69, 70, 71, 72]);
    expect(niceTicks(0, 950, 4)).toEqual([0, 500]);
    expect(niceTicks(5, 5, 2)).toEqual([4, 5, 6]);
  });

  it("draws a path and breaks it at gaps", () => {
    expect(linePath([{ x: 0, y: 1 }, { x: 2, y: 3 }, null, { x: 4, y: 5 }])).toBe("M0.0 1.0 L2.0 3.0 M4.0 5.0");
  });

  it("pads the extent and ignores nulls", () => {
    expect(extent([70, null, 72], 0.5)).toEqual([69, 73]);
    expect(extent([null])).toBeNull();
  });
});

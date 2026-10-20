import { describe, expect, it } from "vitest";

import { compact, extent, linePath, linearScale, niceTicks, showLabel } from "./chart";

describe("chart maths", () => {
  it("maps a domain onto a range", () => {
    const y = linearScale([60, 80], [200, 0]);
    expect(y(60)).toBe(200);
    expect(y(70)).toBe(100);
    expect(y(80)).toBe(0);
  });

  it("picks round ticks", () => {
    expect(niceTicks(68.2, 72.9, 4)).toEqual([68, 70, 72, 74]);
    expect(niceTicks(68.2, 72.9, 8)).toEqual([68, 69, 70, 71, 72, 73]);
    expect(niceTicks(0, 950, 4)).toEqual([0, 500, 1000]);
    expect(niceTicks(0, 1220, 3)).toEqual([0, 500, 1000, 1500]);
    expect(niceTicks(5, 5, 2)).toEqual([4, 5, 6]);
  });

  it("draws a path and breaks it at gaps", () => {
    expect(linePath([{ x: 0, y: 1 }, { x: 2, y: 3 }, null, { x: 4, y: 5 }])).toBe("M0.0 1.0 L2.0 3.0 M4.0 5.0");
  });

  it("shortens big axis numbers", () => {
    expect(compact(1250)).toBe("1.3k");
    expect(compact(500)).toBe("500");
  });

  it("pads the extent and ignores nulls", () => {
    expect(extent([70, null, 72], 0.5)).toEqual([69, 73]);
    expect(extent([null])).toBeNull();
  });

  it("never draws a regular axis label right next to the last one", () => {
    const shown = (n: number, every: number) => [...Array(n).keys()].filter((i) => showLabel(i, n, every));
    expect(shown(13, 3)).toEqual([0, 3, 6, 9, 12]);
    expect(shown(12, 2)).toEqual([0, 2, 4, 6, 8, 11]); // 10 would sit next to 11
    expect(shown(8, 3)).toEqual([0, 3, 7]); // 6 would sit next to 7
    expect(shown(4, 1)).toEqual([0, 1, 2, 3]);
    expect(shown(1, 1)).toEqual([0]);
  });
});

import { describe, expect, it } from "vitest";

import {
  formatDistance,
  formatDuration,
  formatLength,
  formatWeight,
  fromDisplayWeight,
  parseDuration,
  toDisplayWeight,
} from "./units";

describe("weights", () => {
  it("passes metric through", () => {
    expect(toDisplayWeight(60, "metric")).toBe(60);
    expect(fromDisplayWeight(60, "metric")).toBe(60);
    expect(formatWeight(72.46, "metric")).toBe("72.5 kg");
  });

  it("converts pounds both ways", () => {
    expect(toDisplayWeight(100, "imperial")).toBe(220.5);
    expect(fromDisplayWeight(225, "imperial")).toBe(102.058);
    expect(formatWeight(60, "imperial", 0)).toBe("132 lb");
  });
});

describe("lengths and distances", () => {
  it("formats cm and inches", () => {
    expect(formatLength(82.5, "metric")).toBe("82.5 cm");
    expect(formatLength(81.28, "imperial")).toBe("32 in");
  });

  it("formats km and miles", () => {
    expect(formatDistance(5000, "metric")).toBe("5 km");
    expect(formatDistance(5000, "imperial")).toBe("3.11 mi");
  });
});

describe("durations", () => {
  it("formats seconds", () => {
    expect(formatDuration(95)).toBe("1:35");
    expect(formatDuration(3725)).toBe("1:02:05");
  });

  it("parses minutes, m:ss and h:mm:ss", () => {
    expect(parseDuration("25")).toBe(1500);
    expect(parseDuration("2:30")).toBe(150);
    expect(parseDuration("1:05:00")).toBe(3900);
  });

  it("rejects junk", () => {
    expect(parseDuration("")).toBeNull();
    expect(parseDuration("abc")).toBeNull();
    expect(parseDuration("1:75")).toBeNull();
    expect(parseDuration("1:2:3:4")).toBeNull();
  });
});

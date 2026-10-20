/**
 * axe-core accessibility checks for component tests.
 *
 *   await expectNoAxeViolations(container);
 *
 * jsdom does no layout or painting, so rules that need them (colour contrast) are
 * switched off here; contrast is checked on the real app with Playwright instead.
 */
import axe from "axe-core";
import { expect } from "vitest";

export async function axeViolations(node: Element) {
  const result = await axe.run(node, {
    rules: { "color-contrast": { enabled: false }, region: { enabled: false } },
    resultTypes: ["violations"],
  });
  return result.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}

export async function expectNoAxeViolations(node: Element) {
  expect(await axeViolations(node)).toEqual([]);
}

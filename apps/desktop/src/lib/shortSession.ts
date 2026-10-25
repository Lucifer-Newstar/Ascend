/**
 * The 10-minute session (v1.4): Today asks the sidecar for a short version of today's
 * session and Train shows it as a banner. Kept in sessionStorage for the local day only,
 * so tomorrow opens on the full session again.
 */
import type { ShortSession } from "@ascend/shared";

const KEY = "ascend.shortSession";

export const localDay = (d: Date = new Date()): string =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export function rememberShort(s: ShortSession, now: Date = new Date(), store: Pick<Storage, "setItem"> = window.sessionStorage): void {
  try {
    store.setItem(KEY, JSON.stringify({ day: localDay(now), session: s }));
  } catch {
    // storage full or blocked: the banner is a nicety, Train works without it
  }
}

export function readShort(now: Date = new Date(), store: Pick<Storage, "getItem"> = window.sessionStorage): ShortSession | null {
  try {
    const raw = store.getItem(KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as { day: string; session: ShortSession };
    return v.day === localDay(now) ? v.session : null;
  } catch {
    return null;
  }
}

export function forgetShort(store: Pick<Storage, "removeItem"> = window.sessionStorage): void {
  try {
    store.removeItem(KEY);
  } catch {
    // nothing to forget
  }
}

/** "2 × 8–12" or "2 × 20–30 s" for one item. */
export function shortTarget(i: ShortSession["items"][number]): string {
  const unit = i.measure === "hold" ? " s" : "";
  const range = i.rep_low === i.rep_high ? `${i.rep_low}` : `${i.rep_low}–${i.rep_high}`;
  return `${i.sets} × ${range}${unit} · rest ${i.rest_s} s`;
}

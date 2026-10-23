/**
 * Proper looping animations for the most used moves (v1.2, item 1 part 2). Each one is a
 * small animated WebP next to the move's photos: public/exercises/<slug>-anim.webp, with
 * its first frame as <slug>.webp. Every other move keeps the smooth 2-frame loop.
 * To add one: drop the two files in public/exercises and add the slug here.
 */
export const ANIMATED: ReadonlySet<string> = new Set<string>([
  "pushups",
  "pullups",
  "chin-up",
  "bodyweight-squat",
  "parallel-bar-dip",
  "ring-dips",
  "inverted-row",
  "hanging-leg-raise",
  "muscle-up",
  "handstand-push-ups",
  "mountain-climbers",
  "bodyweight-walking-lunge",
  "barbell-squat",
  "barbell-deadlift",
  "barbell-bench-press-medium-grip",
  "standing-military-press",
  "bent-over-barbell-row",
  "wide-grip-lat-pulldown",
  "dumbbell-bench-press",
  "romanian-deadlift",
  "one-arm-dumbbell-row",
  "rope-jumping",
  "jab-cross-shadow-drill",
  "front-kick-drill",
  "roundhouse-kick-drill",
]);

/** The library's slug for a name ("Jab-Cross Shadow Drill" -> "jab-cross-shadow-drill"). */
export function slugOf(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** The animation for a move and its still first frame, or null when it has none. */
export function animationFor(e: { image?: string | null; name: string }): { anim: string; still: string } | null {
  const fromImage = e.image ? /(?:^|\/)exercises\/([a-z0-9-]+)\.webp$/.exec(e.image)?.[1] : undefined;
  const slug = fromImage ?? slugOf(e.name);
  if (!ANIMATED.has(slug)) return null;
  const base = e.image && fromImage ? e.image.slice(0, e.image.length - `${fromImage}.webp`.length) : "exercises/";
  return { anim: `${base}${slug}-anim.webp`, still: `${base}${slug}.webp` };
}

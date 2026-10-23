/**
 * The backdrop of an event screen (workout finish, boss, timer): the theme's event art
 * behind a dark scrim, or for the plain Light and Dark looks (no art) a solid dark scrim,
 * so the app behind never shows through the words. Fixed to the window, so it stays behind
 * the words when a small screen scrolls them.
 */
export function EventBackdrop({ art, solid = false }: { art: string | null; solid?: boolean }) {
  if (art) return <div className="event-art" style={{ ["--event-bg" as string]: `url(${art})` }} aria-hidden="true" />;
  return <div className={`fixed inset-0 ${solid ? "bg-bg" : ""}`} style={solid ? undefined : { background: "rgb(3 7 18 / 0.86)" }} aria-hidden="true" data-testid="event-scrim" />;
}

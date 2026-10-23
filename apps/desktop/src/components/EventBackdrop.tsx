/**
 * The backdrop of an event screen (workout finish, boss, timer): the theme's event art
 * behind a dark scrim, or for the plain Light and Dark looks (no art) a solid dark scrim,
 * so the app behind never shows through the words.
 */
export function EventBackdrop({ art, solid = false }: { art: string | null; solid?: boolean }) {
  if (art) return <div className="event-art" style={{ ["--event-bg" as string]: `url(${art})` }} aria-hidden="true" />;
  return <div className={`absolute inset-0 ${solid ? "bg-bg" : "bg-[rgba(3,7,18,0.86)]"}`} aria-hidden="true" />;
}

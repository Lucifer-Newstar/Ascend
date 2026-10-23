/**
 * The theme's landing art behind the first-run and lock screens, under a dark scrim so the
 * words on top stay readable (none on the plain Light and Dark looks).
 */
import { useAppTheme } from "../lib/prefs";
import { themeArt } from "../lib/themeArt";

export function LandingArt({ dim = false }: { dim?: boolean }) {
  const art = themeArt(useAppTheme(), "landing");
  if (!art) return null;
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0"
      style={{ backgroundImage: `linear-gradient(90deg, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.7) 45%, rgba(0,0,0,${dim ? 0.6 : 0.2}) 100%), url("${art}")`, backgroundSize: "cover", backgroundPosition: "center" }} />
  );
}

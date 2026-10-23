/**
 * The player's avatar (v1.2): male or female, drawn at four rank stages and wearing the
 * outfit you picked, with your weapon, relic and pet beside it. Body-neutral: progress
 * shows as rank, gear and aura, never as a body change. Decorative next to the words
 * that say the same thing (name, level, rank).
 */
import { avatarArt, byId, cosmeticArt, type AvatarLook } from "../lib/cosmetics";

const AURA: Record<string, string> = {
  E: "148 163 184", // slate
  D: "74 222 128", // green
  C: "56 189 248", // sky
  B: "167 139 250", // violet
  A: "251 146 60", // orange
  S: "250 204 21", // gold
};

export interface AvatarProps {
  look: AvatarLook;
  rank: string;
  outfit?: string;
  weapon?: string;
  relic?: string;
  pet?: string;
  /** Height in px; the figure is drawn at roughly 230x512. */
  height?: number;
  className?: string;
}

export function Avatar({ look, rank, outfit, weapon, relic, pet, height = 220, className = "" }: AvatarProps) {
  const worn = outfit ? cosmeticArt(outfit, look) : null;
  const figure = worn ?? avatarArt(look, rank);
  const aura = AURA[rank] ?? AURA.E;
  const extras = [weapon, relic, pet].map((id) => byId(id)).filter((c) => c && cosmeticArt(c.id));
  return (
    <div className={`relative inline-flex shrink-0 flex-col items-center ${className}`} data-testid="avatar" data-rank={rank} aria-hidden="true">
      <div className="relative" style={{ height, width: Math.round(height * 0.5) }}>
        <span className="avatar-aura absolute inset-x-[-30%] bottom-0 top-[15%] rounded-full"
          style={{ background: `radial-gradient(ellipse at 50% 60%, rgb(${aura} / 0.55), rgb(${aura} / 0) 65%)` }} />
        {figure && <img src={figure} alt="" className="relative h-full w-full object-contain object-bottom drop-shadow-[0_6px_10px_rgba(0,0,0,0.45)]" data-testid="avatar-figure" />}
        <span className="absolute left-0 top-0 rounded-md border px-1.5 py-0.5 font-display text-xs font-bold"
          style={{ borderColor: `rgb(${aura})`, color: `rgb(${aura})`, background: "rgb(0 0 0 / 0.45)" }}>{rank}</span>
      </div>
      {extras.length > 0 && (
        <div className="-mt-3 flex gap-1.5" data-testid="avatar-gear">
          {extras.map((c) => (
            <img key={c!.id} src={cosmeticArt(c!.id)!} alt="" title={c!.name} width={34} height={34}
              className="h-[34px] w-[34px] rounded-full border border-line-2 bg-panel-2 object-contain p-0.5" />
          ))}
        </div>
      )}
    </div>
  );
}

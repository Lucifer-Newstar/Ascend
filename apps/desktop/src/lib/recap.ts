/**
 * Weekly recap video (v1.2, item 13). The week's facts (GET /progress/recap) become six
 * short slides drawn on a canvas; the app plays them, and "Save video" records the same
 * canvas with the browser's own MediaRecorder into a WebM file. No extra software, nothing
 * uploaded. Body-neutral: sessions, records, the boss, habits and rank, never body numbers.
 */
import type { WeekRecap } from "@ascend/shared";

export const RECAP_W = 1280;
export const RECAP_H = 720;
export const SLIDE_MS = 2800;
const FADE_MS = 450;

export interface Slide {
  key: string;
  kicker: string;
  /** The big line; when `count` is set it counts up to that number, followed by `unit`. */
  big: string;
  count?: number;
  unit?: string;
  lines: string[];
}

export interface Palette {
  bg: string;
  panel: string;
  ink: string;
  muted: string;
  accent: string;
  line: string;
}

const SECTION: Record<string, string> = {
  gym: "Strength",
  calisthenics: "Calisthenics",
  cardio: "Cardio",
  flexibility: "Mobility",
  martial_arts: "Martial arts",
  meditation: "Mind",
};

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

function day(iso: string, opts: Intl.DateTimeFormatOptions): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", opts);
}

export function weekLabel(r: Pick<WeekRecap, "week_start" | "week_end">): string {
  const o: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${day(r.week_start, o)} – ${day(r.week_end, o)}`;
}

function prLine(p: WeekRecap["prs"][number]): string {
  return p.weight_kg > 0 ? `${p.exercise} · ${p.weight_kg} kg × ${p.reps}` : `${p.exercise} · ${plural(p.reps, "rep")}`;
}

/** The slides for one week, in order. */
export function recapSlides(r: WeekRecap, trainerName: string): Slide[] {
  const slides: Slide[] = [
    { key: "intro", kicker: "Weekly recap", big: weekLabel(r), lines: [r.headline] },
  ];
  const training: string[] = [`${plural(r.sets, "set")} · ${Math.round(r.active_minutes)} min active`];
  if (r.sections[0]) training.push(`Most of it: ${SECTION[r.sections[0].section] ?? r.sections[0].section} (${plural(r.sections[0].sets, "set")})`);
  if (r.best_day) training.push(`Best day: ${day(r.best_day.day, { weekday: "long" })}, ${plural(r.best_day.sets, "set")}`);
  slides.push({ key: "training", kicker: "Training", big: "", count: r.sessions, unit: r.sessions === 1 ? "session" : "sessions", lines: training });
  slides.push(
    r.prs.length
      ? { key: "records", kicker: "Records", big: "", count: r.prs.length, unit: r.prs.length === 1 ? "new personal record" : "new personal records", lines: r.prs.slice(0, 3).map(prLine) }
      : { key: "records", kicker: "Records", big: "No new records", lines: ["Steady weeks are what build them."] },
  );
  if (r.boss) {
    slides.push({
      key: "boss",
      kicker: `Boss · Tier ${r.boss.tier}`,
      big: r.boss.name,
      lines: [r.boss.defeated ? `Defeated. Title earned: ${r.boss.title}.` : r.complete ? "It held on this time. A new boss arrives Monday." : "Still standing. Every set you log is a hit."],
    });
  }
  const habits = [`Meals logged on ${plural(r.meal_days, "day")}`, `Morning check-ins: ${r.checkins}`];
  if (r.excused_days) habits.push(`${plural(r.excused_days, "missed day")} kept with a reason`);
  slides.push({ key: "habits", kicker: "Habits", big: "", count: r.streak, unit: "day streak", lines: habits });
  slides.push({
    key: "rank",
    kicker: "Rank",
    big: `${r.rank}-Rank · Level ${r.level}`,
    lines: [`+${r.xp} XP this week`, `${r.rank_title}. See you next week. – ${trainerName}`],
  });
  return slides;
}

export const recapLength = (slides: Slide[]) => slides.length * SLIDE_MS;

const FALLBACK: Palette = { bg: "#0b0f17", panel: "#121a2a", ink: "#eef3fb", muted: "#a9b6cb", accent: "#7c5cff", line: "#2c4470" };

/** The theme's colours, so the video matches the app (the theme tokens pass WCAG AA). */
export function readPalette(el: Element = document.documentElement): Palette {
  const css = getComputedStyle(el);
  const v = (name: string, fb: string) => css.getPropertyValue(name).trim() || fb;
  return {
    bg: v("--color-bg", FALLBACK.bg),
    panel: v("--color-panel", FALLBACK.panel),
    ink: v("--color-ink", FALLBACK.ink),
    muted: v("--color-muted", FALLBACK.muted),
    accent: v("--color-accent", FALLBACK.accent),
    line: v("--color-line-2", FALLBACK.line),
  };
}

const ease = (k: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, k)), 3);

/** Which slide is on screen at `t` ms, and how far into it. */
export function slideAt(slides: Slide[], t: number): { index: number; local: number } {
  const total = recapLength(slides);
  const clamped = Math.min(Math.max(0, t), total - 1);
  const index = Math.min(slides.length - 1, Math.floor(clamped / SLIDE_MS));
  return { index, local: clamped - index * SLIDE_MS };
}

/** Draw the frame at `t` ms. Text always sits on a solid panel for readability. */
export function drawFrame(ctx: CanvasRenderingContext2D, slides: Slide[], t: number, p: Palette, reduced = false): void {
  const { index, local } = slideAt(slides, t);
  const s = slides[index];
  ctx.fillStyle = p.bg;
  ctx.fillRect(0, 0, RECAP_W, RECAP_H);
  // a soft accent band behind the panel
  const g = ctx.createLinearGradient(0, 0, RECAP_W, RECAP_H);
  g.addColorStop(0, p.accent);
  g.addColorStop(1, p.bg);
  ctx.globalAlpha = 0.25;
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, RECAP_W, RECAP_H);
  ctx.globalAlpha = 1;
  // story-style progress bars
  const gap = 10;
  const barW = (RECAP_W - 120 - gap * (slides.length - 1)) / slides.length;
  slides.forEach((_, i) => {
    const x = 60 + i * (barW + gap);
    ctx.fillStyle = p.line;
    ctx.fillRect(x, 36, barW, 6);
    const done = i < index ? 1 : i === index ? local / SLIDE_MS : 0;
    ctx.fillStyle = p.accent;
    ctx.fillRect(x, 36, barW * done, 6);
  });
  // solid panel
  const fadeIn = reduced ? 1 : ease(local / FADE_MS);
  const fadeOut = reduced || index === slides.length - 1 ? 1 : ease((SLIDE_MS - local) / FADE_MS);
  const alpha = Math.min(fadeIn, fadeOut);
  const lift = reduced ? 0 : (1 - fadeIn) * 24;
  ctx.fillStyle = p.panel;
  ctx.strokeStyle = p.line;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.rect(110, 96, RECAP_W - 220, RECAP_H - 200);
  ctx.fill();
  ctx.stroke();
  ctx.globalAlpha = alpha;
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = p.accent;
  ctx.font = "700 34px Rajdhani, sans-serif";
  ctx.fillText(s.kicker.toUpperCase(), 170, 190 + lift);
  ctx.fillStyle = p.ink;
  let big = s.big;
  if (s.count !== undefined) {
    const n = reduced ? s.count : Math.round(s.count * ease(local / 900));
    big = `${n} ${s.unit ?? ""}`.trim();
  }
  ctx.font = "700 88px Rajdhani, sans-serif";
  fitText(ctx, big, 170, 300 + lift, RECAP_W - 340, 88);
  ctx.fillStyle = p.muted;
  ctx.font = "500 34px Inter, sans-serif";
  s.lines.slice(0, 3).forEach((line, i) => fitText(ctx, line, 170, 390 + i * 54 + lift, RECAP_W - 340, 34));
  ctx.globalAlpha = 1;
  ctx.fillStyle = p.ink;
  ctx.font = "700 36px Rajdhani, sans-serif";
  ctx.fillText("ASCEND", 110, RECAP_H - 44);
}

/** One line that shrinks its font until it fits `width`. */
function fitText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, width: number, size: number) {
  let px = size;
  const family = ctx.font.replace(/^.*?\d+px\s*/, "");
  const weight = ctx.font.split(" ")[0];
  while (px > 18 && ctx.measureText(text).width > width) {
    px -= 2;
    ctx.font = `${weight} ${px}px ${family}`;
  }
  ctx.fillText(text, x, y);
  ctx.font = `${weight} ${size}px ${family}`;
}

export function canRecord(): boolean {
  return typeof MediaRecorder !== "undefined" && typeof HTMLCanvasElement !== "undefined" && "captureStream" in HTMLCanvasElement.prototype;
}

function webmType(): string {
  for (const t of ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"]) {
    if (MediaRecorder.isTypeSupported?.(t)) return t;
  }
  return "video/webm";
}

/** Draw the whole recap once on `canvas` while MediaRecorder records it; resolves to the WebM. */
export function recordRecap(canvas: HTMLCanvasElement, slides: Slide[], p: Palette, fps = 30): Promise<Blob> {
  const ctx = canvas.getContext("2d");
  if (!ctx || !canRecord()) return Promise.reject(new Error("This build can't record video."));
  canvas.width = RECAP_W;
  canvas.height = RECAP_H;
  const stream = canvas.captureStream(fps);
  const type = webmType();
  const rec = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 2_500_000 });
  const chunks: Blob[] = [];
  rec.ondataavailable = (e) => {
    if (e.data.size) chunks.push(e.data);
  };
  const total = recapLength(slides);
  return new Promise((resolve, reject) => {
    rec.onstop = () => {
      stream.getTracks().forEach((tr) => tr.stop());
      resolve(new Blob(chunks, { type: "video/webm" }));
    };
    rec.onerror = () => reject(new Error("Recording failed."));
    const start = performance.now();
    rec.start(250);
    const tick = () => {
      const t = performance.now() - start;
      drawFrame(ctx, slides, t, p);
      if (t < total + 300) requestAnimationFrame(tick);
      else rec.stop();
    };
    requestAnimationFrame(tick);
  });
}

export function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(new Error("Could not read the video."));
    r.readAsDataURL(blob);
  });
}

/** Save through the validated video:save channel (Electron), or a download in browser dev. */
export async function saveVideo(defaultName: string, blob: Blob): Promise<boolean> {
  const dataUrl = (await blobToDataUrl(blob)).replace(/^data:video\/webm[^,]*;base64,/, "data:video/webm;base64,");
  if (window.ascend?.saveVideo) return (await window.ascend.saveVideo({ defaultName, dataUrl })).saved;
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = defaultName;
  a.click();
  return true;
}

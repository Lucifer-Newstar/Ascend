/**
 * Optional sound effects, off by default. Tiny tones made with WebAudio (no audio files,
 * nothing to download). The preference lives in this browser profile (localStorage), so
 * it needs no server setting.
 */
export type SoundKind = "set" | "quest" | "levelup" | "skill";

export interface SoundPrefs {
  on: boolean;
  /** 0..1 */
  volume: number;
}

const KEY = "ascend.sound";
export const DEFAULT_SOUND: SoundPrefs = { on: false, volume: 0.5 };

export function soundPrefs(): SoundPrefs {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return DEFAULT_SOUND;
    const p = JSON.parse(raw) as Partial<SoundPrefs>;
    return { on: Boolean(p.on), volume: Math.max(0, Math.min(1, Number(p.volume ?? 0.5))) };
  } catch {
    return DEFAULT_SOUND;
  }
}

export function setSoundPrefs(p: SoundPrefs): void {
  localStorage.setItem(KEY, JSON.stringify(p));
}

/** Notes (Hz) and length (s) of each effect: short, soft, never longer than half a second. */
export const TONES: Record<SoundKind, { notes: number[]; step: number; type: OscillatorType }> = {
  set: { notes: [660], step: 0.07, type: "sine" },
  quest: { notes: [523, 784], step: 0.09, type: "triangle" },
  levelup: { notes: [523, 659, 784, 1047], step: 0.08, type: "triangle" },
  skill: { notes: [440, 660, 880], step: 0.1, type: "sine" },
};

let ctx: AudioContext | null = null;

/** Play an effect if sound is on (and the browser has WebAudio). Never throws. */
export function play(kind: SoundKind, prefs: SoundPrefs = soundPrefs()): boolean {
  if (!prefs.on || prefs.volume <= 0) return false;
  const AC = (globalThis as { AudioContext?: typeof AudioContext }).AudioContext;
  if (!AC) return false;
  try {
    ctx ??= new AC();
    const t0 = ctx.currentTime + 0.01;
    const { notes, step, type } = TONES[kind];
    notes.forEach((freq, i) => {
      const osc = ctx!.createOscillator();
      const gain = ctx!.createGain();
      osc.type = type;
      osc.frequency.value = freq;
      const start = t0 + i * step;
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(0.18 * prefs.volume, start + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + step * 1.6);
      osc.connect(gain).connect(ctx!.destination);
      osc.start(start);
      osc.stop(start + step * 1.7);
    });
    return true;
  } catch {
    return false;
  }
}

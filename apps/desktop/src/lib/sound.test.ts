// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_SOUND, play, setSoundPrefs, soundPrefs, TONES } from "./sound";

describe("sound", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it("is off by default and remembers the choice and volume", () => {
    expect(soundPrefs()).toEqual(DEFAULT_SOUND);
    expect(DEFAULT_SOUND.on).toBe(false);
    setSoundPrefs({ on: true, volume: 0.3 });
    expect(soundPrefs()).toEqual({ on: true, volume: 0.3 });
    localStorage.setItem("ascend.sound", "{broken");
    expect(soundPrefs()).toEqual(DEFAULT_SOUND);
  });

  it("plays nothing when off, muted or without WebAudio", () => {
    expect(play("set", { on: false, volume: 1 })).toBe(false);
    expect(play("set", { on: true, volume: 0 })).toBe(false);
    vi.stubGlobal("AudioContext", undefined);
    expect(play("set", { on: true, volume: 1 })).toBe(false);
  });

  it("plays one short oscillator per note, scaled by the volume", () => {
    const oscs: { frequency: { value: number }; start: ReturnType<typeof vi.fn> }[] = [];
    const gains: { setValueAtTime: ReturnType<typeof vi.fn>; linearRampToValueAtTime: ReturnType<typeof vi.fn> }[] = [];
    class FakeCtx {
      currentTime = 0;
      destination = {};
      createOscillator() {
        const o = { type: "", frequency: { value: 0 }, connect: (g: unknown) => g, start: vi.fn(), stop: vi.fn() };
        oscs.push(o);
        return o;
      }
      createGain() {
        const g = { gain: { setValueAtTime: vi.fn(), linearRampToValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() }, connect: vi.fn() };
        gains.push(g.gain);
        return g;
      }
    }
    vi.stubGlobal("AudioContext", FakeCtx);
    expect(play("levelup", { on: true, volume: 0.5 })).toBe(true);
    expect(oscs.map((o) => o.frequency.value)).toEqual(TONES.levelup.notes);
    expect(gains[0].linearRampToValueAtTime.mock.calls[0][0]).toBeCloseTo(0.09);
    // Every effect is under half a second.
    for (const t of Object.values(TONES)) expect(t.notes.length * t.step + t.step).toBeLessThan(0.5);
  });
});

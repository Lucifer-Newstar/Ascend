/**
 * "Scan meal" (food-photo v0). Shown only when /ml/status says a gated food model is on
 * this PC; otherwise it renders nothing. A photo gives up to three suggestions; picking one
 * only adds it to the plate, so the meal is logged by the normal Save after the user checks
 * portions. Nothing is ever logged from the photo alone.
 */
import type { Food, FoodPhotoResult } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";

export const MAX_PHOTO_BYTES = 12 * 1024 * 1024;

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(new Error("could not read that file"));
    r.readAsDataURL(file);
  });
}

export function ScanMeal({ foods, onPick }: { foods: Food[]; onPick: (food: Food) => void }) {
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<FoodPhotoResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const file = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let live = true;
    // Older sidecars have no /ml; any failure just keeps the feature hidden.
    Promise.resolve()
      .then(() => api.mlStatus())
      .then((s) => live && setAvailable(s.food_photo.available))
      .catch(() => live && setAvailable(false));
    return () => {
      live = false;
    };
  }, []);

  if (!available) return null;

  async function scan(f: File) {
    setError(null);
    setResult(null);
    if (f.size > MAX_PHOTO_BYTES) {
      setError("That photo is larger than 12 MB.");
      return;
    }
    setBusy(true);
    try {
      setResult(await api.foodPhoto(await readAsDataUrl(f)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const byId = new Map(foods.map((f) => [f.id, f]));
  const choices = (result?.suggestions ?? []).filter((s) => s.food_id !== null && byId.has(s.food_id));

  return (
    <div className="mt-2" data-testid="scan-meal">
      <input ref={file} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" aria-label="Meal photo"
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = "";
          if (f) void scan(f);
        }} />
      <button type="button" className="btn-ghost w-full px-2 py-1.5 text-xs" disabled={busy} onClick={() => file.current?.click()}>
        {busy ? "Looking at the photo…" : "Scan meal from a photo"}
      </button>
      {error && <p role="alert" className="mt-1 text-xs text-bad">{error}</p>}
      {result && (
        <div className="mt-2 rounded-lg border border-line-2 p-2" aria-live="polite">
          {result.result === "not_food" ? (
            <p className="text-xs text-muted">I don't see food in that photo. Search the table instead.</p>
          ) : (
            <>
              <p className="text-xs text-muted">
                {result.result === "unsure" ? "Not sure. Is it one of these?" : "Is it one of these?"} Pick one to add it to your plate, then check the portions and Save.
              </p>
              <ul className="mt-1.5 flex flex-wrap gap-1.5">
                {choices.map((s) => (
                  <li key={s.label}>
                    <button type="button" className="rounded-full border border-line-2 px-2.5 py-1 text-xs text-ink hover:border-accent/60"
                      onClick={() => {
                        onPick(byId.get(s.food_id!)!);
                        setResult(null);
                      }}>
                      {s.name} <span className="text-faint">{Math.round(s.confidence * 100)}%</span>
                    </button>
                  </li>
                ))}
                <li>
                  <button type="button" className="rounded-full px-2.5 py-1 text-xs text-muted hover:text-ink" onClick={() => setResult(null)}>
                    None of these
                  </button>
                </li>
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * The share dialog for an achievement: a card drawn on this PC from share-v1's caption,
 * then Save image, Copy, Post on X (X's own composer opens; you post it) or Instagram
 * (no desktop posting API, so the image is saved and the caption copied).
 */
import type { ShareCardText } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { api } from "../api/client";
import { copyToClipboard, drawCard, openShareLink, saveImage } from "../lib/share";
import { useTrainer } from "./Trainer";
import { useToast } from "./Toast";

export function ShareDialog({ payload, onClose }: { payload: Record<string, unknown>; onClose: () => void }) {
  const toast = useToast();
  const trainer = useTrainer();
  const [card, setCard] = useState<ShareCardText | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const first = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    api.shareCard(payload).then((c) => {
      setCard(c);
      setImage(drawCard(c, trainer.name));
    }).catch((e: Error) => setError(e.message));
  }, [payload, trainer.name]);
  useEffect(() => first.current?.focus(), [card]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const name = `ascend-${card?.kind ?? "card"}.png`;
  const act = async (fn: () => Promise<unknown>, message: string) => {
    try {
      await fn();
      toast(message, "info");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  };

  // On <body>, and it scrolls: on a 768 px (or 125 % scaled) screen the card, the buttons and
  // Close all stay reachable. A click on the backdrop closes it.
  return createPortal(
    <div className="fixed inset-0 z-50 flex overflow-y-auto bg-[rgba(3,7,18,0.6)] p-4" data-testid="share-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div role="dialog" aria-modal="true" aria-labelledby="share-title" className="m-auto max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl border border-accent/50 bg-panel p-5 shadow-2xl" data-testid="share-dialog">
        <div className="flex items-center justify-between gap-3">
          <h2 id="share-title" className="text-lg font-semibold text-ink">Share</h2>
          <button type="button" className="btn-ghost px-3 py-1 text-sm" onClick={onClose}>Close</button>
        </div>
        {error && <p role="alert" className="mt-2 text-sm text-bad">{error}</p>}
        {card && (
          <>
            {image ? (
              <img src={image} alt={`${card.title}: ${card.headline}`} className="mx-auto mt-3 block max-h-[40vh] w-auto max-w-full rounded-lg border border-line-2 object-contain" data-testid="share-image" />
            ) : (
              <div className="mt-3 rounded-lg border border-accent/40 bg-panel-2 p-5" data-testid="share-preview">
                <p className="text-[11px] uppercase tracking-wider text-accent">{card.title}</p>
                <p className="mt-1 text-2xl font-bold text-ink">{card.headline}</p>
                <p className="text-sm text-muted">{card.detail}</p>
              </div>
            )}
            <p className="mt-3 rounded-md bg-panel-2 p-2 text-xs text-ink" data-testid="share-caption">{card.caption}</p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button ref={first} type="button" className="btn-primary" disabled={!image} onClick={() => void act(() => saveImage(name, image!), "Image saved")}>Save image</button>
              <button type="button" className="btn-ghost" onClick={() => void act(() => copyToClipboard(card.caption, image ?? undefined), "Copied")}>Copy</button>
              <button type="button" className="btn-ghost" onClick={() => void act(() => openShareLink(card.x_url), "X opened with your post ready")}>Post on X</button>
              <button type="button" className="btn-ghost" disabled={!image}
                onClick={() => void act(async () => { await saveImage(name, image!); await copyToClipboard(card.caption); }, "Saved. Caption copied for Instagram")}>Instagram</button>
            </div>
            <p className="mt-2 text-[11px] text-muted">Only the achievement is on the card: no weight, photos or profile details. Nothing is posted for you.</p>
          </>
        )}
      </div>
    </div>,
    document.body,
  );
}

/**
 * Photo safety (v1.2, item 14), in Settings > Profile > Privacy & photos: what happens to
 * progress photos in plain words, and a way to delete them all from this PC.
 */
import { useState } from "react";

import { api } from "../api/client";
import { useToast } from "./Toast";

export const PHOTO_FACTS = [
  "Your progress photos stay on this PC, in ASCEND's data folder. Nothing is uploaded.",
  "Location and camera details are removed when a photo is saved.",
  "Photos are blurred until you choose Show photos, and blur again when you leave the app.",
  "ASCEND never estimates body fat or weight from a photo.",
  "Backups include your photos unless you untick Include progress photos.",
];

export function PhotoSafety() {
  const toast = useToast();
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);

  async function deleteAll() {
    setBusy(true);
    try {
      const r = await api.deleteAllPhotos();
      toast(r.deleted ? `Deleted ${r.deleted} photo${r.deleted === 1 ? "" : "s"} from this PC` : "There were no photos to delete", "info");
      setAsking(false);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not delete the photos", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-line bg-panel-2 p-3" data-testid="photo-safety">
      <h3 className="text-sm font-semibold text-ink">Photo safety</h3>
      <ul className="list-disc space-y-1 pl-5 text-xs text-muted">
        {PHOTO_FACTS.map((f) => <li key={f}>{f}</li>)}
      </ul>
      {!asking ? (
        <button type="button" className="btn-ghost text-bad" onClick={() => setAsking(true)}>Delete all progress photos</button>
      ) : (
        <div role="alertdialog" aria-labelledby="delete-photos-q" className="rounded-md border border-warn/50 bg-panel p-3 text-sm">
          <p id="delete-photos-q" className="text-ink">
            Delete every progress photo from this PC? This can&apos;t be undone. Backups you made earlier keep their copies until you delete them.
          </p>
          <div className="mt-2 flex gap-2">
            <button type="button" className="btn-primary" disabled={busy} onClick={() => void deleteAll()}>Delete all photos</button>
            <button type="button" className="btn-ghost" disabled={busy} onClick={() => setAsking(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

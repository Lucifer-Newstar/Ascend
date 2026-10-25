/**
 * Profile (v1.1): your Hunter card (level, rank, streak, stats, titles), achievements you
 * can share as a card, and the progress photo gallery.
 *
 * Photos stay on this PC. They are re-encoded through a canvas before saving (no EXIF, no
 * GPS) and the sidecar strips metadata again. Thumbnails are blurred until you choose
 * "Show photos". Two photos compare side by side; no model judges them (v1.3: the AI
 * photo feedback was removed, review decision 4).
 */
import type { FeedMessage, PhotoPose, ProgressPhoto } from "@ascend/shared";
import { useEffect, useState, type ChangeEvent } from "react";

import { api } from "../api/client";
import { PageGrid, Panel } from "../components/Page";
import { Avatar } from "../components/Avatar";
import { BossLadder } from "../components/BossLadder";
import { ShareDialog } from "../components/ShareCard";
import { TrainerPortrait, useTrainer } from "../components/Trainer";
import { useToast } from "../components/Toast";
import { Wardrobe, progressFrom } from "../components/Wardrobe";
import { hunterClass } from "../lib/loadout";
import { useOptionalPrefs } from "../lib/prefs";
import { reencodePhoto, saveImage } from "../lib/share";
import { useApi } from "../lib/useApi";

const today = () => new Date().toISOString().slice(0, 10);
const POSES: PhotoPose[] = ["front", "side", "back", "other"];

export function ProfilePage({ refreshKey }: { refreshKey: number }) {
  const [share, setShare] = useState<Record<string, unknown> | null>(null);
  return (
    <PageGrid label="Profile">
      <HunterCard refreshKey={refreshKey} />
      <Achievements refreshKey={refreshKey} onShare={setShare} />
      <WardrobePanel refreshKey={refreshKey} />
      <BossLadderPanel refreshKey={refreshKey} />
      <Gallery />
      {share && <ShareDialog payload={share} onClose={() => setShare(null)} />}
    </PageGrid>
  );
}

function HunterCard({ refreshKey }: { refreshKey: number }) {
  const profile = useApi(api.profile, [refreshKey]);
  const game = useApi(api.game, [refreshKey]);
  const stats = useApi(api.stats, [refreshKey]);
  const titles = useApi(api.titles, [refreshKey]);
  const trainer = useTrainer();
  const prefs = useOptionalPrefs();
  const xp = game.data?.xp;
  const s = prefs?.settings;
  return (
    <Panel id="hunter" index={0} className="col-span-12 xl:col-span-5" title="Hunter card"
      loading={profile.loading && !profile.data} error={!profile.data ? profile.error ?? null : null} onRetry={profile.reload}>
      <div className="flex items-start gap-4">
        {xp ? (
          <Avatar look={s?.avatar ?? "male"} rank={xp.rank} outfit={s?.outfit} weapon={s?.weapon} relic={s?.relic} pet={s?.pet} height={150} />
        ) : (
          <TrainerPortrait mood="proud" size={72} />
        )}
        <div className="min-w-0">
          <p className="text-display-l text-ink" data-testid="hunter-name">{profile.data?.name ?? "Hunter"}</p>
          {xp && <p className="text-sm text-muted">Level {xp.level} · Rank {xp.rank} · {xp.rank_title}</p>}
          {profile.data && (profile.data.equipment?.length ?? 0) > 0 && <p className="text-sm font-semibold text-accent" data-testid="hunter-class">{hunterClass(profile.data.equipment).name}</p>}
          {game.data && <p className="text-sm text-muted">Streak {game.data.streak.current} day{game.data.streak.current === 1 ? "" : "s"} · best {game.data.streak.best}</p>}
          <p className="mt-1 text-[11px] text-muted">Trained by {trainer.name}</p>
        </div>
      </div>
      {stats.data && (
        <ul className="mt-4 grid grid-cols-5 gap-2" aria-label="Hunter stats">
          {stats.data.stats.map((s) => (
            <li key={s.key} className="rounded-lg border border-line-2 p-2 text-center" title={s.formula}>
              <span className="block text-[10px] uppercase tracking-wider text-muted">{s.key}</span>
              <span className="text-lg font-semibold tabular-nums text-ink">{s.value}</span>
            </li>
          ))}
        </ul>
      )}
      {(titles.data ?? []).length > 0 && (
        <div className="mt-4">
          <p className="text-[11px] uppercase tracking-wider text-muted">Titles</p>
          <ul className="mt-1 flex flex-wrap gap-1.5">{titles.data!.map((t) => <li key={`${t.title}-${t.boss}`} className="chip border-accent/50 text-ink">{t.title}</li>)}</ul>
        </div>
      )}
    </Panel>
  );
}

function BossLadderPanel({ refreshKey }: { refreshKey: number }) {
  const ladder = useApi(api.bosses, [refreshKey]);
  return (
    <Panel id="boss-ladder" index={3} className="col-span-12" title="Boss ladder"
      hint="Weekly bosses from E to S by category, and the seasonal bosses with their drops."
      loading={ladder.loading && !ladder.data} error={!ladder.data ? ladder.error ?? null : null} onRetry={ladder.reload}>
      {ladder.data && <BossLadder bosses={ladder.data} />}
    </Panel>
  );
}

function WardrobePanel({ refreshKey }: { refreshKey: number }) {
  const game = useApi(api.game, [refreshKey]);
  const prs = useApi(api.prs, [refreshKey]);
  const titles = useApi(api.titles, [refreshKey]);
  return (
    <Panel id="wardrobe" index={2} className="col-span-12" title="Wardrobe"
      hint="Outfits, weapons, relics and pets, earned by rank, streaks, PRs and bosses."
      loading={game.loading && !game.data} error={!game.data ? game.error ?? null : null} onRetry={game.reload}>
      <Wardrobe progress={progressFrom(game.data, prs.data?.length ?? 0, titles.data)} />
    </Panel>
  );
}

function Achievements({ refreshKey, onShare }: { refreshKey: number; onShare: (p: Record<string, unknown>) => void }) {
  const feed = useApi(api.trainerFeed, [refreshKey]);
  const items: FeedMessage[] = (feed.data?.messages ?? []).filter((m) => m.share);
  return (
    <Panel id="achievements" index={1} className="col-span-12 xl:col-span-7" title="Achievements"
      hint="PRs, skill steps, streaks, boss wins and finished blocks. Share one as a card."
      loading={feed.loading && !feed.data} error={!feed.data ? feed.error ?? null : null} onRetry={feed.reload}>
      {items.length === 0 ? (
        <p className="text-sm text-muted">Nothing to share yet. Your first PR or skill step shows up here.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((m) => (
            <li key={m.id} className="flex items-center justify-between gap-3 rounded-lg border border-line-2 px-3 py-2">
              <span className="text-sm text-ink">{m.text}</span>
              <button type="button" className="btn-ghost shrink-0 px-2 py-1 text-xs" onClick={() => onShare(m.share!)} aria-label={`Share: ${m.text}`}>Share</button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** Photo safety (v1.2): shown photos blur again when the window loses focus or is hidden,
 * so a photo is never left on screen when you step away or switch apps. */
export function useBlurWhenAway(setReveal: (v: boolean) => void) {
  useEffect(() => {
    const hide = () => setReveal(false);
    const onVisibility = () => {
      if (document.visibilityState === "hidden") hide();
    };
    window.addEventListener("blur", hide);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("blur", hide);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [setReveal]);
}

function Gallery() {
  const toast = useToast();
  const photos = useApi(api.photos, []);
  const [reveal, setReveal] = useState(false);
  const [date, setDate] = useState(today());
  const [pose, setPose] = useState<PhotoPose>("front");
  const [busy, setBusy] = useState(false);
  const [picked, setPicked] = useState<number[]>([]);
  const list = photos.data ?? [];
  useBlurWhenAway(setReveal);

  async function add(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      const dataUrl = await reencodePhoto(file);
      await api.addPhoto({ data_url: dataUrl, taken_on: date, pose });
      toast("Photo saved on this PC", "info");
      photos.reload();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const togglePick = (id: number) => {
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id].slice(-2)));
  };

  return (
    <Panel id="gallery" index={4} className="col-span-12" title="Progress photos"
      hint="Private: they stay on this PC, carry no location or camera data, and blur again when you leave the app. Backups include them unless you untick it."
      action={<button type="button" className="btn-ghost px-2 py-1 text-xs" aria-pressed={reveal} onClick={() => setReveal((r) => !r)}>{reveal ? "Blur photos" : "Show photos"}</button>}
      loading={photos.loading && !photos.data} error={!photos.data ? photos.error ?? null : null} onRetry={photos.reload}>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs text-muted">Date<input type="date" className="input mt-1" value={date} max={today()} onChange={(e) => setDate(e.target.value)} /></label>
        <label className="text-xs text-muted">Pose
          <select className="input mt-1" value={pose} onChange={(e) => setPose(e.target.value as PhotoPose)}>
            {POSES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        <label className={`btn-primary cursor-pointer ${busy ? "opacity-60" : ""}`}>
          {busy ? "Saving…" : "Add photo"}
          <input type="file" accept="image/jpeg,image/png" className="sr-only" onChange={(e) => void add(e)} disabled={busy} aria-label="Add a progress photo" />
        </label>
        <p className="text-[11px] text-muted">Same spot, same light, same pose each month makes the comparison honest.</p>
      </div>

      {list.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No photos yet.</p>
      ) : (
        <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-6" aria-label="Photos">
          {list.map((p) => <PhotoTile key={p.id} photo={p} reveal={reveal} picked={picked.includes(p.id)} onPick={() => togglePick(p.id)}
            onDeleted={() => { setPicked((x) => x.filter((i) => i !== p.id)); photos.reload(); }} />)}
        </ul>
      )}

      {picked.length === 2 && (
        <div className="mt-4 space-y-2 border-t border-line pt-3" data-testid="compare">
          <p className="text-sm text-ink">Comparing two photos side by side.</p>
          <div className="grid grid-cols-2 gap-3">
            {picked.map((id) => <PhotoImage key={id} id={id} reveal={reveal} large />)}
          </div>
          <p className="text-[11px] text-muted">You are the judge here: your training log shows the progress that matters.</p>
        </div>
      )}
    </Panel>
  );
}

function PhotoImage({ id, reveal, large = false }: { id: number; reveal: boolean; large?: boolean }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api.photoData(id).then((d) => live && setSrc(d.data_url)).catch(() => undefined);
    return () => { live = false; };
  }, [id]);
  return (
    <div className={`overflow-hidden rounded-lg border border-line-2 bg-panel-2 ${large ? "aspect-[3/4]" : "aspect-square"}`}>
      {src && <img src={src} alt="Progress photo" className={`h-full w-full object-cover transition-[filter] ${reveal ? "" : "blur-xl"}`} data-blurred={!reveal} />}
    </div>
  );
}

function PhotoTile({ photo, reveal, picked, onPick, onDeleted }: { photo: ProgressPhoto; reveal: boolean; picked: boolean; onPick: () => void; onDeleted: () => void }) {
  const toast = useToast();
  async function exportPhoto() {
    try {
      const d = await api.photoData(photo.id);
      const ext = d.mime === "image/png" ? "png" : "jpg";
      if (await saveImage(`ascend-photo-${photo.taken_on}.${ext}`, d.data_url)) toast("Photo saved (no location or camera data)", "info");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }
  async function remove() {
    if (!window.confirm(`Delete the ${photo.pose} photo from ${photo.taken_on}? This can't be undone.`)) return;
    await api.deletePhoto(photo.id).then(onDeleted).catch((e: Error) => toast(e.message, "error"));
  }
  return (
    <li className={`rounded-lg border p-1.5 ${picked ? "border-accent" : "border-line-2"}`} data-testid="photo-tile">
      <PhotoImage id={photo.id} reveal={reveal} />
      <p className="mt-1 text-[11px] text-muted">{photo.taken_on} · {photo.pose}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        <button type="button" className="btn-ghost px-1.5 py-0.5 text-[11px]" aria-pressed={picked} onClick={onPick}>{picked ? "Picked" : "Compare"}</button>
        <button type="button" className="btn-ghost px-1.5 py-0.5 text-[11px]" onClick={() => void exportPhoto()} aria-label={`Export photo from ${photo.taken_on}`}>Export</button>
        <button type="button" className="btn-ghost px-1.5 py-0.5 text-[11px] text-bad" onClick={() => void remove()} aria-label={`Delete photo from ${photo.taken_on}`}>Delete</button>
      </div>
    </li>
  );
}

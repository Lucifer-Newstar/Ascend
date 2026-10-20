import type { Settings } from "@ascend/shared";

import { api } from "../api/client";
import { IconDownload } from "../components/Icons";
import { Segmented } from "../components/Segmented";
import { ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { kcal } from "../lib/format";
import { usePrefs } from "../lib/prefs";
import { useApi } from "../lib/useApi";
import { ProfileForm } from "./Onboarding";

async function saveFile(defaultName: string, content: string): Promise<string | null> {
  if (window.ascend) {
    const res = await window.ascend.saveExport({ defaultName, content });
    return res.saved ? res.path : null;
  }
  // Browser dev mode: trigger a download instead of a native save dialog.
  const url = URL.createObjectURL(new Blob([content], { type: "text/plain" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: defaultName });
  a.click();
  URL.revokeObjectURL(url);
  return defaultName;
}

export function SettingsPage({ onToggleAi, onChanged }: { onToggleAi: () => void; onChanged: () => void }) {
  const profile = useApi(api.profile, []);
  const toast = useToast();
  const { settings, update } = usePrefs();
  const aiEnabled = settings.ai_enabled;

  async function save(patch: Partial<Settings>, message: string) {
    try {
      await update(patch);
      toast(message, "info");
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function exportData(kind: "json" | "workouts" | "meals") {
    try {
      const stamp = new Date().toISOString().slice(0, 10);
      const content = kind === "json" ? JSON.stringify(await api.exportJson(), null, 2) : await api.exportCsv(kind);
      const name = kind === "json" ? `ascend-export-${stamp}.json` : `ascend-${kind}-${stamp}.csv`;
      const path = await saveFile(name, content);
      if (path) toast(`Exported ${name}`, "info");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  if (profile.loading && !profile.data) return <Loading />;
  if (profile.error || !profile.data) return <ErrorState message={profile.error ?? "No profile"} onRetry={profile.reload} />;
  const p = profile.data;

  return (
    <div className="grid max-w-5xl grid-cols-12 gap-5">
      <section className="card col-span-12 p-5 lg:col-span-7">
        <h2 className="card-title mb-4">Profile & targets</h2>
        <ProfileForm initial={p} submitLabel="Save profile" onSaved={() => { toast("Profile saved", "info"); profile.reload(); onChanged(); }} />
        <p className="mt-4 text-xs text-muted">
          Current estimate: BMR {kcal(p.energy.bmr)} · TDEE {kcal(p.energy.tdee)} · target {kcal(p.energy.kcal_target)} kcal ·
          protein {p.energy.protein_target_g} g <span className="text-faint">({p.energy.formula_version}, estimate)</span>
        </p>
      </section>
      <div className="col-span-12 space-y-5 lg:col-span-5">
        <section className="card p-5">
          <h2 className="card-title mb-3">AI coach</h2>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Use local AI (Ollama · qwen3:4b)<br /><span className="text-xs text-muted">Off = rule-based tips only. Nothing leaves this PC either way.</span></span>
            <input type="checkbox" className="h-5 w-5 accent-accent" checked={Boolean(aiEnabled)} onChange={onToggleAi} />
          </label>
        </section>
        <section className="card space-y-4 p-5" aria-labelledby="appearance-title">
          <h2 id="appearance-title" className="card-title">Appearance & units</h2>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Theme</span>
            <Segmented
              label="Theme"
              value={settings.theme}
              options={[{ value: "dark", label: "Dark" }, { value: "light", label: "Light" }, { value: "system", label: "System" }]}
              onChange={(theme) => save({ theme }, `Theme: ${theme}`)}
            />
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Units</span>
            <Segmented
              label="Units"
              value={settings.units}
              options={[{ value: "metric", label: "kg · cm · km" }, { value: "imperial", label: "lb · in · mi" }]}
              onChange={(units) => save({ units }, units === "metric" ? "Units: metric" : "Units: imperial")}
            />
          </div>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">
              Training days per week
              <br />
              <span className="text-xs text-muted">Used by the weekly review to judge adherence.</span>
            </span>
            <select
              className="input w-20"
              value={settings.sessions_per_week}
              onChange={(e) => save({ sessions_per_week: Number(e.target.value) }, "Training days saved")}
            >
              {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
        </section>
        <section className="card p-5">
          <h2 className="card-title mb-3">Export your data</h2>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-ghost" onClick={() => exportData("json")}><IconDownload width={16} height={16} /> Everything (JSON)</button>
            <button type="button" className="btn-ghost" onClick={() => exportData("workouts")}><IconDownload width={16} height={16} /> Workouts (CSV)</button>
            <button type="button" className="btn-ghost" onClick={() => exportData("meals")}><IconDownload width={16} height={16} /> Meals (CSV)</button>
          </div>
        </section>
        <section className="card p-5 text-xs leading-relaxed text-muted">
          <h2 className="card-title mb-2">About</h2>
          ASCEND 0.1.0 · MIT licence · © the ASCEND team.<br />
          Muscle map artwork: react-muscle-highlighter (MIT).<br />
          Food values: approximate, IFCT 2017 / INDB-style.<br />
          TDEE (Mifflin-St Jeor), e1RM (Epley) and burn (MET) are estimates.
        </section>
      </div>
    </div>
  );
}

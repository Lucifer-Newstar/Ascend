/**
 * Settings > AI setup. The app works fully without a model (rule-based tier); this panel
 * shows what the PC has, recommends a model (ai-tiers-v1) and lets the user pick or test it.
 */
import type { AiSetup, AiTest } from "@ascend/shared";
import { useState, type ReactNode } from "react";

import { api } from "../api/client";
import { fallbackLabel } from "../lib/fallback";
import { useApi } from "../lib/useApi";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right text-ink">{children}</dd>
    </div>
  );
}

function Copy({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <span className="inline-flex items-center gap-2">
      <code className="rounded bg-panel-3 px-1.5 py-0.5 text-xs">{text}</code>
      <button type="button" className="text-xs text-accent hover:underline"
        onClick={() => { void navigator.clipboard?.writeText(text).then(() => setDone(true)).catch(() => undefined); }}>
        {done ? "Copied" : "Copy"}
      </button>
    </span>
  );
}

export function AiSetupPanel({ aiEnabled, onToggleAi, onChanged }: { aiEnabled: boolean; onToggleAi: () => void; onChanged?: () => void }) {
  const setup = useApi(api.aiSetup, [aiEnabled]);
  const [test, setTest] = useState<AiTest | null>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const s: AiSetup | null = setup.data;

  async function choose(model: string | null) {
    setError(null);
    try {
      await api.aiModel(model);
      setup.reload();
      onChanged?.();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function runTest() {
    setTesting(true);
    setTest(null);
    try {
      setTest(await api.aiTest());
      setup.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setTesting(false);
    }
  }

  return (
    <section className="card rise-in p-5" aria-labelledby="ai-title" data-tour="ai-setup">
      <h2 id="ai-title" className="card-title mb-3">AI setup</h2>
      <label className="flex items-center justify-between gap-4">
        <span className="text-sm text-ink">
          Use local AI (Ollama)
          <br />
          <span className="text-xs text-muted">Optional. Without it everything still works: chat, tours, plans and goal checks use rules. AI only adds free-form wording. Nothing leaves this PC either way.</span>
        </span>
        <input type="checkbox" className="h-5 w-5 accent-accent" checked={aiEnabled} onChange={onToggleAi} aria-label="Use local AI" />
      </label>
      {setup.loading && !s && <p className="mt-3 text-xs text-muted">Checking this PC…</p>}
      {setup.error && !s && <p className="mt-3 text-xs text-bad">Couldn&apos;t check the AI setup: {setup.error}</p>}
      {s && (
        <>
          <p className={`mt-4 rounded-md border px-3 py-2 text-sm ${s.tier === "ai" ? "border-good/50 text-ink" : "border-line-2 text-muted"}`} data-testid="ai-tier">
            {s.tier === "ai"
              ? `AI mode: ${s.model} is ready.`
              : !s.ai_enabled
                ? "Rule-based mode (AI switched off). The whole app works; answers come from rules."
                : !s.ollama_running
                  ? s.ollama_installed ? "Rule-based mode: Ollama is installed but not running. Start Ollama to use AI." : "Rule-based mode: Ollama isn't installed. Get it from ollama.com, then pull a model."
                  : `Rule-based mode: ${s.model} isn't pulled yet.`}
          </p>
          {s.suggestion && (
            <div className="mt-3 rounded-md border border-warn/60 px-3 py-2 text-sm text-ink" role="status">
              {s.suggestion}
              <div className="mt-2 flex gap-2">
                {s.smaller_model && s.models.some((m) => m.name === s.smaller_model) && (
                  <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => void choose(s.smaller_model)}>Use {s.smaller_model}</button>
                )}
                <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={onToggleAi}>Use rules only</button>
              </div>
            </div>
          )}
          <dl className="mt-3 divide-y divide-line">
            <Row label="Ollama">{s.ollama_running ? `running (v${s.ollama_version})` : s.ollama_installed ? "installed, not running" : "not installed"}</Row>
            <Row label="Memory">{s.hardware.ram_gb != null ? `${s.hardware.ram_gb} GB RAM` : "unknown"}</Row>
            <Row label="Graphics">{s.hardware.vram_gb != null ? `${s.hardware.gpu ?? "GPU"} · ${s.hardware.vram_gb} GB` : "no NVIDIA GPU found (AMD/Intel aren't measured)"}</Row>
            <Row label="Recommended">
              {s.recommended.model ? `${s.recommended.model} (${s.recommended.size_gb} GB)` : "rule-based mode"}
              <span className="block text-xs text-muted">{s.recommended.reason}</span>
              {s.recommended.pull_command && !s.models.some((m) => m.name === s.recommended.model) && <span className="mt-1 block"><Copy text={s.recommended.pull_command} /></span>}
            </Row>
            <Row label="Model in use">
              {s.models.length ? (
                <select className="input w-44" aria-label="Model in use" value={s.models.some((m) => m.name === s.model) ? s.model : ""} onChange={(e) => void choose(e.target.value || null)}>
                  {!s.models.some((m) => m.name === s.model) && <option value="">{s.model} (not pulled)</option>}
                  {s.models.map((m) => <option key={m.name} value={m.name}>{m.name} · {m.size_gb} GB</option>)}
                </select>
              ) : (
                s.model
              )}
            </Row>
          </dl>
          <div className="mt-3 flex items-center gap-3">
            <button type="button" className="btn-ghost px-3 py-1 text-xs" onClick={() => void runTest()} disabled={testing || s.tier !== "ai"}>
              {testing ? "Testing… (a cold start can take a minute)" : "Test the AI"}
            </button>
            {test && (
              <span className="text-xs text-muted" role="status">
                {test.ok ? `Answered in ${test.seconds} s: “${test.reply}”` : fallbackLabel(test.reason)}
              </span>
            )}
          </div>
          {error && <p role="alert" className="mt-2 text-xs text-bad">{error}</p>}
        </>
      )}
    </section>
  );
}

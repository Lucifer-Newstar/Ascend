# Evaluation

> **How ASCEND is judged** — product, engineering, AI/ML and team metrics, with targets,
> how each is measured, and when. Every target is an **estimate** until the first
> measurement; measured values replace it with a date and a link to the run.
> Owner: Navin (protocol + reports); each metric has a measuring member.

---

## 1. Metrics

### Product and reliability

| ID | Metric | Target (est.) | How measured | By | When |
|---|---|---|---|---|---|
| R1 | **Crash-free sessions** | ≥ 99% of sessions on testers' PCs | Local session journal (start, clean exit) shared manually by testers | Gokul | Each beta |
| R2 | Sidecar recoveries without data loss | 100% in the kill test | E2E: kill `ascend-sidecar.exe` mid-write ×20; DB integrity + no lost sets | Jegatheesan | Phase 1 gate on |
| R3 | Cold start to dashboard | < 4 s | Playwright timer on the packaged app, reference laptop, 5 runs, median | Dhanush | Phase 0 gate on |
| R4 | Set logged → map/XP updated | < 150 ms p95 | Dev metrics `ascend_http_request_duration_seconds` + UI timer | Jegatheesan | Phase 1 gate |
| R5 | Migration safety | 0 failed upgrades from any released schema | CI fixture DB upgrade job | Gokul | Every PR |
| R6 | Works with AI off | 100% of v1.0 features usable | Scripted E2E journey with Ollama stopped | Dhanush | Phase 2 gate on |
| R7 | Zero unexpected egress | 0 non-localhost connections | E2E under a blocked-network test | Gokul | Every release |
| R8 | Installer size | < 250 MB | Release asset size | Gokul | Every release |

### AI and ML

| ID | Metric | Target (est.) | How measured | By | When |
|---|---|---|---|---|---|
| M1 | **Food top-3 accuracy** | ≥ 0.85 on the own-photo test set | `ml/src/evaluate.py`, MLflow run | Navin | Each model version |
| M2 | Food top-1 accuracy | ≥ production + 2 points to promote | same | Navin | Each model version |
| M3 | Macro-F1 | not lower than production | same | Navin | Each model version |
| M4 | Calorie MAE per meal | ≤ 120 kcal (estimate; photo portions are rough) | 30 weighed reference meals vs scan result | Navin + Jegatheesan | Phase 2 gate, v1.0 |
| M5 | ONNX parity | identical top-1 on 200 images | CI `ml-eval.yml` | Navin | Each export |
| M6 | **Coach first-token latency** | ≤ 3 s warm, p95 on reference laptop | `ascend_llm_first_token_seconds`; 50 prompts | Jegatheesan | Phase 2 gate, v1.0 |
| M7 | Coach throughput | ≥ 15 tokens/s on reference laptop (estimate) | `ollama run --verbose` + dev metric | Navin | Phase 2 benchmark |
| M8 | Meal scan end to end | 5–15 s | Job duration metric, 30 photos | Jegatheesan | Phase 2 gate |
| M9 | Rules fallback rate | < 5% of chats in normal use | Count of `fallback_reason` ≠ null | Jegatheesan | Beta |
| M10 | Number fidelity | 100% of weekly-review summaries contain only input numbers | Automated check over 100 generated reviews | Jegatheesan | Phase 2 gate |
| M11 | Red-flag routing | 100% of 40 red-flag test messages (EN/TA/mixed) bypass the model | Unit test suite | Jegatheesan + Navin | Every PR |
| M12 | Tamil answer quality | mean ≥ 3.5 / 5 from 2 blind raters on 30 questions | Rating sheet | Navin + Dhanush | Before v1.0 (decides "beta" label) |
| M13 | Scan correction rate (live) | falling or flat; rising 3 weeks → retrain | Local corrections table, exported | Navin | Phase 5 |

### Engineering

| ID | Metric | Target | How measured | By |
|---|---|---|---|---|
| E1 | Rules-module coverage | ≥ 80% lines | `pytest --cov` gate | Jegatheesan |
| E2 | CI duration (PR) | < 12 min | GitHub Actions timings | Gokul |
| E3 | Flaky test rate | < 2% of runs | Re-run statistics | Gokul |
| E4 | Contract drift incidents reaching `main` | 0 | Drift job | Gokul |
| E5 | Release lead time (tag → published) | < 30 min | Release workflow | Gokul |

### Team (genuine history)

| ID | Metric | Target | How measured |
|---|---|---|---|
| T1 | Commits per member by v1.0 | ≥ 60 each, all on their phase-plan tasks (estimate) | `git shortlog -sn` + phase-plan mapping |
| T2 | PRs reviewed per member | ≥ 15 each by v1.0 | GitHub insights |
| T3 | Teach-back | each member demos and explains their own work at every gate | Gate minutes |

## 2. Protocol

1. **Reference hardware** for performance numbers: Navin's laptop (§1 of
   [local-setup.md](../development/local-setup.md#1-hardware-and-os)), plugged in,
   Windows "Best performance", no other GPU apps, after one warm-up run.
2. **Five runs, report the median** (and p95 for latency over ≥ 50 samples).
3. **Datasets are frozen** per evaluation (DVC hash in the report).
4. **Raters for Tamil** see answers in random order without model names.
5. **Reports** go in `docs/operations/reports/YYYY-MM-DD-<topic>.md` with the commit SHA,
   model versions, raw numbers and the command used.
6. **Honesty:** a missed target is reported as missed, with the reason and the next step.

## 3. Gate usage

| Gate | Metrics that must pass |
|---|---|
| Phase 0 | R3 (measured, any value — establishes the baseline), R5 |
| Phase 1 | R2, R4, E1, E4 |
| Phase 2 | M1 baseline recorded, M5, M6, M8, M10, M11, R6 |
| v1.0 (Phase 3) | R1 (beta), R7, R8, M4, M12 (decides Tamil label), E5 |
| Phase 5 | M13 trend + a promoted retrained model that beats M2 |

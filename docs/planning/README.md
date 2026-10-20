# Planning

> Home of the **scope, delivery sequence and schedule** for ASCEND. Each file has one
> job. Decisions that change scope or interfaces are recorded in §2.

---

## 1. Start here

| If you need to know… | Read… |
|---|---|
| How the finished app looks and behaves | [product-vision.md](product-vision.md) |
| What is included, in which release, and how it is accepted | [features.md](features.md) |
| What each phase must deliver and demonstrate | [phases.md](phases.md) |
| When phases are targeted and who is focused on what | [timeline.md](timeline.md) |
| How the first team meeting runs | [kickoff.md](kickoff.md) |
| What is done, in progress or blocked | [tracker.md](tracker.md) |
| What can go wrong where two lanes meet | [integration-edge-cases.md](integration-edge-cases.md) |

## 2. Decision log

Newest at the bottom. Architecture-level decisions also get an ADR.

| # | Date | Decision | Why | Ref |
|---|---|---|---|---|
| D1 | 2026-10-20 | Desktop only (Windows 11), fully offline, no cloud | Owner requirement; privacy; no hosting cost | [ADR-0009](../architecture/adr/0009-offline-first-no-cloud.md) |
| D2 | 2026-10-20 | Electron + React + TS for the UI | Web skills transfer; HTML mockups become components | [ADR-0001](../architecture/adr/0001-electron-react-desktop.md) |
| D3 | 2026-10-20 | Python 3.12 FastAPI sidecar | ML ecosystem; Pydantic contracts | [ADR-0002](../architecture/adr/0002-fastapi-python-sidecar.md) |
| D4 | 2026-10-20 | Coach model qwen3:4b (Tamil beta), not Llama 3.2 3B | Llama 3.2 does not officially support Tamil; qwen3 lists it | [ADR-0004](../architecture/adr/0004-ollama-qwen3-local-llm.md) |
| D5 | 2026-10-20 | Rules decide, LLM explains; app fully usable with AI off | Safety, testability, low-end hardware | [ADR-0005](../architecture/adr/0005-deterministic-engines-llm-explains.md) |
| D6 | 2026-10-20 | Online leaderboards/guilds cut; ghost races against own past weeks instead | Need a server | [features.md §4](features.md#4-cut-or-replaced) |
| D7 | 2026-10-20 | No AI judging of progress photos in v1 | Small local VLMs unreliable; harm of a wrong verdict | [features.md §4](features.md#4-cut-or-replaced) |
| D8 | 2026-10-20 | One shared logger behind all six training sections | One data model → History, PRs, XP, map work everywhere | [product-vision.md](product-vision.md) |
| D9 | 2026-10-20 | Team = AegisDeploy's four members; roles per team-structure | Same team, proven split | [team-structure.md](../team/team-structure.md) |
| D10 | 2026-10-20 | MVP target ~7 Feb 2027 (estimate) | Placement season; v1.0 must be demo-ready | [timeline.md](timeline.md) |
| D11 | 2026-10-20 | Prompts are versioned contracts; every model output is validated and falls back to rules on failure | Makes "the model only explains" testable | [ADR-0011](../architecture/adr/0011-prompt-contracts-and-output-validation.md) |
| D12 | 2026-10-20 | Meal scan is classifier-first; qwen3-vl:2b only as an optional second opinion | Works without a GPU; no model swap per scan; VLM quality unverified | [ADR-0012](../architecture/adr/0012-classifier-first-meal-scan.md) |

| D13 | 2026-10-20 | Rows D1–D12 accepted by the lead; ADR-0001 to ADR-0012 marked Accepted | The skeleton and MVP already depend on them; reopening one needs a superseding ADR | [adr/](../architecture/adr/adr-template.md) |
| D14 | 2026-10-20 | Work lands through feature branches merged with `--no-ff`; the lead merges after CODEOWNERS review | Keeps one merge commit per PR so `main` reads as a list of reviewed changes | [branch-protection.md](../development/branch-protection.md) |

> D1–D12 were proposed on 2026-10-20 and accepted by the lead the same day (D13). Any of them
> can still be raised at the kickoff ([kickoff.md §4](kickoff.md#4-decisions-to-ratify)).

## 3. Change control

- Scope is frozen per release in [features.md](features.md). Anything new goes into
  `BACKLOG.md` at the repo root and is considered at the next phase gate.
- Moving a feature between releases needs the lead's OK and a row in §2.
- A contract change after a phase's contract freeze is additive-only unless an ADR says otherwise.

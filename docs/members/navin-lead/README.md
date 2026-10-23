# Navin Jairam M — Team Lead · MLOps · Releases

> **Member 4** — Team Lead. Architecture · contracts review · MLOps pipeline ·
> Indian-food classifier · release management · evaluation · integration.

## Role

Hold the whole picture: keep the architecture coherent and documented, run the team's
rhythm, own the ML half of the product (the food classifier and the pipeline that trains,
gates and ships it), and decide when a build is good enough to release.

## Status at 1.0.0 (2026-10-23)

The responsibilities below are the plan from 2026-10-20. What shipped in this area:

- **Delivered:** the architecture and 22 ADRs; engine specs and the synthetic-user evaluation
  ([docs/ai/evaluation.md](../../ai/evaluation.md)); the ML pipeline in `ml/` (prepare, train,
  ONNX export with a parity gate, evaluate, DVC stages, MLflow, CI smoke run on synthetic data);
  releases 0.1.0 to 1.0.0 with the CHANGELOG and release notes; the security-review fixes.
- **Planned here, not in 1.0.0:** a food classifier trained on real, licensed photos (the
  pipeline has only run on synthetic smoke data, and no model ships in the app), the evaluation
  gate workflow, drift reports, retraining from corrections, model-only releases and the beta
  channel. The local-model benchmark covers `qwen3:4b` speed on the reference laptop only (see the
  README's Ollama tuning note).

## Primary responsibilities

- Architecture + ADRs; reviewer for contracts, process boundaries and the stack
- Formula specs with worked examples for every engine (load model, progression, XP,
  TDEE, ETA) — Jegatheesan implements, I review against the examples
- **Food classifier:** dataset collection + labelling, `labels.json` → INDB/IFCT ids,
  training (PyTorch + timm in Gokul's CUDA image on WSL2), ONNX export + parity test,
  preprocessing contract
- **MLOps pipeline:** DVC (datasets + `dvc.yaml` stages), MLflow tracking + registry,
  evaluation gate (`ml-eval.yml` with Gokul), model manifest, drift report, retraining from
  corrections, shadow mode
- Local model benchmarking (tokens/s, VRAM, Tamil rating) with Jegatheesan
- **Releases:** versions, changelog, go/no-go, beta → stable promotion, rollback calls,
  model-only releases (Gokul automates; I decide and publish)
- Evaluation protocol and reports; tracker, timeline, decision log; weekly sync

## Repo areas owned

- `ml/`, `docs/architecture/`, `docs/planning/`, `docs/team/`, `docs/operations/evaluation.md`
- Root `README.md`, `CHANGELOG.md`, `BACKLOG.md`
- `docs/members/navin-lead/` (this folder)

## Team-facing guides

- **[kickoff-guide.md](kickoff-guide.md)** — run the Phase 0 kickoff and every weekly sync:
  script, decisions, demo format, gate checklist.
- **[study-path.md](study-path.md)** — what to read and practise, in order: the repo, then
  Linux/Bash, Docker, GitHub Actions, MLOps, and AWS SAA later — with interview explainers.

## Contracts I provide

| Contract | Consumers | Available |
|---|---|---|
| Formula specs + worked examples | Jegatheesan | Phase 1 week 1 |
| `classifier.onnx`, `labels.json`, preprocessing contract + test vector | Jegatheesan | Phase 2 |
| Model manifest (`models-manifest.json`) | Jegatheesan (model manager), Gokul (release) | Phase 2 |
| Release decisions + notes | Gokul, users | Every release |
| Evaluation protocol | everyone | Phase 1 |

## Personal learning goal

DevOps → MLOps. This project carries the **MLOps and release-engineering** half of my
portfolio; Linux, Docker, GitHub Actions and later AWS SAA come from the study path and
my course labs. A local desktop app does not exercise AWS, Terraform or Kubernetes — I
say so honestly in interviews and point to my course work for those.

## My commitments

- Decisions are written down the same day (decision log or ADR).
- I write my own `ml/` code and can explain every stage of the pipeline.
- I never publish a release whose gate metrics I have not read.

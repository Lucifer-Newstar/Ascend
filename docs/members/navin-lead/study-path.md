# Study Path — Navin

> What to read and practise, in order, so you can **explain** ASCEND and grow from DevOps
> into MLOps. Each step says read / do / skim, a rough time (estimate), and the takeaway.
> Tick the boxes as you go. Companion: [kickoff-guide.md](kickoff-guide.md).

---

## Track A — Understand ASCEND (~6 h, first two weeks)

| # | Item | How | Time | Takeaway |
|---|---|---|---|---|
| A1 | [docs/README.md](../../README.md) | read | 15 min | Where every topic lives |
| A2 | [proposal.md](../../project/proposal.md) | read | 30 min | What, why, scope, AI-assistance line |
| A3 | [features.md](../../planning/features.md) | read | 30 min | MVP vs v1.1 vs later; acceptance criteria |
| A4 | [system-architecture.md](../../architecture/system-architecture.md) | read twice | 60 min | Processes, sidecar lifecycle, engines, event bus, model manager |
| A5 | ADRs [0002](../../architecture/adr/0002-fastapi-python-sidecar.md), [0005](../../architecture/adr/0005-deterministic-engines-llm-explains.md), [0008](../../architecture/adr/0008-electron-builder-pyinstaller-packaging.md), [0009](../../architecture/adr/0009-offline-first-no-cloud.md) | read | 40 min | The four decisions interviewers will ask about |
| A6 | `services/sidecar/app/__main__.py`, `core/security.py`, `core/events.py` | read the code | 45 min | Token on stdin, Host check, the event bus |
| A7 | `apps/desktop/electron/sidecar.ts` | read the code | 30 min | Free port, spawn, health polling, backoff |
| A8 | [sequence-diagram.md](../../architecture/uml/sequence-diagram.md) + run it: log a set with `/docs` open | do | 45 min | Follow one request end to end |
| A9 | [ml-pipeline.md](../../architecture/ml-pipeline.md) + [release-process.md](../../operations/release-process.md) | read | 45 min | Your two lanes in full |

**Checkpoint:** explain, without notes, what happens from pressing Enter on a set to the
muscle map changing colour.

## Track B — Linux and Bash (~10 h over 3 weeks)

You use WSL2 (Ubuntu) for Docker and training; CI runners are Linux.

- [ ] B1 Files, permissions, processes: `ls -la`, `chmod`, `ps`, `top`, `kill`, `df -h`, `du -sh` (do it inside WSL)
- [ ] B2 Pipes and text: `grep`, `sed`, `awk`, `sort | uniq -c`, `jq` on the sidecar's JSON logs
- [ ] B3 A Bash script with `set -euo pipefail`, functions, exit codes — e.g. `scripts/check_models.sh` that verifies SHA-256 of downloaded models
- [ ] B4 Environment and PATH, `.bashrc`, `which`, `env`
- [ ] B5 Networking basics: `curl -v http://127.0.0.1:8765/health`, `ss -tlnp`, what `127.0.0.1` vs `0.0.0.0` means (ADR-0009)

**Checkpoint:** you can debug "sidecar not healthy" from a terminal alone.

## Track C — Docker (~10 h, Phase 1–2)

- [ ] C1 Images vs containers, layers, `docker build`, `docker run`, `docker logs`, `docker exec`
- [ ] C2 Write a multi-stage Dockerfile for a small FastAPI app; compare image sizes
- [ ] C3 Compose: read and run `infra/compose/mlflow.yml`; volumes vs bind mounts
- [ ] C4 GPU in WSL2: `docker run --gpus all … nvidia-smi`; why the NVIDIA driver lives on Windows
- [ ] C5 Read Gokul's training image; explain every line in the PR review

**Interview line:** "The app is a desktop installer, not a container. Docker is where I run
the ML training image and MLflow, so training is reproducible on any machine with a GPU."

## Track D — GitHub Actions and release engineering (~12 h, Phase 0–3)

- [ ] D1 Workflow anatomy: triggers, jobs, steps, `runs-on`, matrix, `needs`, caches, artefacts
- [ ] D2 Read `ci.yml` line by line with Gokul; ask why each job exists
- [ ] D3 Secrets vs variables vs environments; protected `release` environment (you are its reviewer)
- [ ] D4 Pinning actions by SHA and why (supply chain)
- [ ] D5 `release.yml`: tag → build → smoke → checksums/SBOM → draft → publish; electron-updater `latest.yml`
- [ ] D6 Do the rollback drill yourself (Phase 3)

**Lesson from your earlier Gamified-Fitness-Tracker repo:** a lint step ending in
`|| true` or `|| echo` can never fail the build — a check that cannot fail is not a check.

## Track E — MLOps (~25 h, Phase 1–5, your main lane)

| # | Topic | Practise on ASCEND |
|---|---|---|
| E1 | Data versioning with DVC (`dvc init`, `add`, `remote`, `repro`, `dvc.lock`) | Meal photo dataset + prepare stage |
| E2 | Experiment tracking with MLflow (params, metrics, artefacts, runs compare) | Baseline + v0 runs |
| E3 | Transfer learning with timm; fixed seeds; train/val/test discipline | Classifier v0; own photos = test only |
| E4 | Metrics: top-1/top-3, macro-F1, confusion matrix, calibration | Evaluate stage |
| E5 | Model registry and promotion; evaluation gates in CI | `ml-eval.yml` |
| E6 | ONNX export, parity tests, CPU inference latency | Export stage |
| E7 | Monitoring without a server: drift signals, correction rate | Phase 5 drift report |
| E8 | Retraining from feedback, shadow deployment | Phase 5 loop |

**Checkpoint (Phase 2 gate):** draw the pipeline from photo to model-in-app on a
whiteboard and say what each tool versions.

## Track F — AWS Solutions Architect Associate (later, after v1.0)

ASCEND does not use the cloud (ADR-0009), so AWS comes from your course and labs. Plan it
for **after the v1.0 release (Feb 2027)** to avoid splitting focus.

- [ ] F1 Set a billing alarm and budget **before** any lab (free-tier credits expire)
- [ ] F2 Core domains: IAM, VPC, EC2/Auto Scaling, S3, RDS/DynamoDB, CloudWatch, resilience and cost
- [ ] F3 Map ASCEND concepts to AWS for interviews: "if this had a backend, model files would sit in S3 behind CloudFront, MLflow on ECS, Releases instead of GitHub…" — clearly labelled as hypothetical
- [ ] F4 Practice exams; book the exam when scores are steady (date: your call)

## Interview explainers (memorise)

| Question | Your 30-second answer |
|---|---|
| Why a sidecar on a random port with a token? | Python owns the ML and the engines; a random port avoids collisions, the token on stdin stops other local apps or web pages calling it, and the Host check blocks DNS rebinding |
| Why doesn't the AI decide anything? | Small local models make up numbers; deterministic engines are testable and versioned; the model explains and every plan change needs the user's OK |
| How do you know the classifier is good? | Own photos are a held-out test set; we gate on top-1/top-3/macro-F1 and calorie MAE; ONNX parity is tested in CI |
| What happens from `git tag` to a user update? | Release workflow builds sidecar + installer, smoke-tests it, attaches checksums and SBOM, I publish, electron-updater picks up `latest.yml` |
| How do you roll back? | Roll forward: unpublish, revert, patch release; backups before every migration protect data |
| What did you personally build? | The MLOps pipeline, the classifier, the evaluation and release decisions — and I can show the commits |

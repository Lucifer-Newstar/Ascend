# Data and Privacy for AI

> What each model sees, where it runs, what is stored, how consent for training photos works
> and how everything is deleted. Owner: **Navin** (privacy review); implementation:
> **Jegatheesan** (sidecar) and **Dhanush** (consent and deletion UI).
> The general rules are in [security-privacy.md](../architecture/security-privacy.md); this file
> adds the AI-specific parts.

---

## 1. Principles

1. **Everything stays on the PC.** Every model runs locally: Ollama on `127.0.0.1:11434`,
   ONNX Runtime and IndicTrans2 inside the sidecar. No AI feature calls the internet.
2. **No telemetry.** No analytics, no crash upload, no usage pings. Development metrics
   (Prometheus) exist only in dev builds, opt-in, on localhost
   ([telemetry-model.md](../architecture/telemetry-model.md)).
3. **Minimum context.** A model sees only what its job needs, built by code into a facts
   block, never the raw database.
4. **Training data only with consent and only by export.** Nothing leaves the PC unless the
   user exports it and sends it themselves.
5. **Deletion is real.** Deleting removes rows and files, not just hides them.

---

## 2. What each model sees

| Model | Sees | Never sees |
|---|---|---|
| Coach (`qwen3:4b` / Lite) | The facts block (age, sex, goal, experience, equipment, diet type, active injury flags, readiness, today's quest, non-optimal muscles, recent PRs, nutrition totals), the last ≤ 6 chat turns, the current message, the user's first name if set | Photos of any kind, body measurements and progress photos, full history, other chats, file paths, the launch token |
| VLM (`qwen3-vl:2b`, optional) | One meal photo (EXIF stripped, downscaled), the allowed class names, the classifier's top-3 | Anything about the user |
| Food classifier (ONNX) | Cropped regions of the meal photo, 224 × 224 | Anything else |
| IndicTrans2 (optional, Tamil Path B) | The text being translated (one message or reply) | Facts, history, photos |
| **Progress photos** | **No model.** No AI judging of physique in v1 (decision D7 in [planning/README.md](../planning/README.md#2-decision-log)) | — |

Context is assembled in one place (`coach/context.py`), so a review of that file is a review
of everything the coach can ever see.

### Local-only enforcement

- The sidecar refuses an `OLLAMA_HOST` that is not a loopback address (`127.0.0.1`, `::1`,
  `localhost`) and shows "This setting would send your data to another computer" instead of
  connecting (planned check, Phase 2).
- The CI egress test runs the packaged app with all non-localhost traffic blocked and fails on
  any attempt (metric R7 in [evaluation.md](../operations/evaluation.md#product-and-reliability)).
- Ollama is a separate program the user installs; its own update checks are outside ASCEND's
  control and are mentioned on the onboarding card. ASCEND keeps Ollama's debug logging
  (`OLLAMA_DEBUG`) off so prompts are not written to Ollama's log files.

---

## 3. What is stored, and for how long

| Data | Table / folder | Kept | User control |
|---|---|---|---|
| Chat messages (text, language, model, `prompt_id`, `prompt_version`, `checks`, `used_data` fact ids, source) | `chat_threads`, `chat_messages` | Until deleted; optional auto-delete after 90 days (planned setting) | Export, delete a thread, delete all chat |
| Proposals and their reason text | `proposals` | With the plan history | Deleted with "delete everything" |
| Meal photos | `%APPDATA%\ASCEND\photos\meals\`, path in `scans` | With the meal; setting **Keep meal photos** (on by default) deletes each photo after the meal is confirmed when off | Delete per meal, delete all scan photos |
| Scan results (items, top-3, model versions, duration) | `scans` | With the meal | Deleted with the meal |
| Corrections (prediction, confidence, top-3, chosen food, unit, qty, oil level, consent flag, model version) | `corrections` | Until deleted | Delete all corrections; excluded from export unless consented |
| Logs | `%APPDATA%\ASCEND\logs\` | Rotated (see telemetry model) | "Delete everything" wipes them |

Log lines **never** contain message text, food names typed by the user, photo content or
paths with the Windows user name; they carry ids, durations, model names and outcome codes
([telemetry-model.md §2](../architecture/telemetry-model.md#2-log-line-shape-sidecar)).

---

## 4. Consent for training photos

The food model improves only from photos users choose to share, and only through a manual
export (Phase 5 loop in [mlops-lifecycle.md §10](mlops-lifecycle.md#10-step-8-the-retraining-loop-opt-in)).

| Step | What happens |
|---|---|
| First scan | A one-time sheet explains: photos and corrections stay on this PC; you can choose to help improve recognition later by exporting them; nothing is sent automatically. Choice: *Allow saving for training* (off by default) |
| Each scan | A checkbox on the confirm screen, **Help improve recognition with this photo**, pre-set from the first-scan choice; stored as `keep_for_training` on each correction |
| Export | Settings → AI → Model health → *Export corrections*: a preview shows counts and thumbnails; options *labels only*, *item crops* (default) or *full photos*; the zip is written where the user chooses |
| Sending | The user sends the zip to the team themselves (for testers: to Navin, with a signed consent note) |
| Team side | Stored on the DVC remote (an external drive, no cloud), with `consent.csv` (contributor id, date, scope: crops or full photos). Never published as a dataset |
| Withdrawal | A contributor asks; their files are removed in a new dataset version, and the next model is trained without them. Models already shipped are replaced at the next model release |

What the export contains: `corrections.csv` (predicted label, confidence, top-3, chosen food
id, unit, qty, model version, date), images per the chosen option, and `export.json` (app
version, labels version, item count). No profile, no chat, no body data. EXIF is already
stripped at import. The export tool warns if the full-photo option is chosen ("photos can show
people or your home").

---

## 5. Deletion

| Action | Removes |
|---|---|
| Delete a chat thread / all chat | Thread and message rows; the facts it referenced are untouched |
| Delete a meal | Meal, items, scan row, its photo file and its correction rows |
| Delete all scan photos | Every file in `photos\meals\`; scan rows keep only the results |
| Delete corrections | All correction rows (personal swaps and "usual quantity" reset) |
| Remove a model | Ollama's copy via its delete API (`DELETE /api/delete`) or ASCEND's own files for the classifier and IndicTrans2 |
| **Delete everything** (typed confirmation) | Database, photos, backups, logs, ASCEND's model files and settings ([security-privacy.md §4](../architecture/security-privacy.md#4-privacy-commitments)); Ollama models are offered as a separate tick box because other apps may use them |

Backups: deleted data can remain in the 7 daily / 4 weekly backups until they rotate out; the
"Delete everything" action deletes backups too, and the delete dialog says so for the
narrower actions.

---

## 6. AI-specific threats

| Threat | Example | Mitigation |
|---|---|---|
| Prompt injection from user content | A food name or imported plan row says "ignore your rules" | Facts are built by formatters that strip control characters, cap length (80 characters per name) and quote user strings; the safety filter and validators do not depend on the model obeying |
| Data leaving via a remote model host | `OLLAMA_HOST` pointed at another machine | Non-loopback hosts refused (§2) |
| Tampered model file | A replaced ONNX file mislabels foods | SHA-256 against the manifest on every load; parity test vector |
| Over-sharing in exports | Full photos with faces | Crops by default; warning on full photos; consent scope recorded |
| Sensitive inferences | Chat history reveals eating worries | Stays local; included only in the user's own exports; never in logs |

---

## 7. DPDP Act note

ASCEND as designed sends the team no personal data, so most data-fiduciary duties under
India's DPDP Act 2023 do not arise ([security-privacy.md §5](../architecture/security-privacy.md#5-indias-dpdp-act--notes-not-legal-advice)).
The Phase 5 corrections export **is** data the team receives: it is collected only from
consenting testers, with a written note, for one stated purpose (improving the food model),
and deleted on request. Before any public collection of corrections, a privacy review and an
ADR are required. This is not legal advice.

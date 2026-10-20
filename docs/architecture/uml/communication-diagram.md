# Communication Diagram — Weekly Review

> **Diagram 12 (UML 2.5 — Behavioural).** The same objects that cooperate on the Sunday
> weekly review, with numbered messages instead of a timeline. Mermaid has no
> communication notation; numbered edge labels carry the sequence.

```mermaid
flowchart LR
    sched[":Scheduler"]
    q[":JobQueue"]
    wr[":WeeklyReviewService"]
    ml[":MuscleLoadService"]
    wk[":WorkoutsService"]
    nu[":NutritionService"]
    mm[":ModelManager"]
    ol[":Ollama"]
    db[(":SQLite")]
    ui[":Renderer"]

    sched -- "1: enqueue(weekly_review)" --> q
    q -- "2: run(job)" --> wr
    wr -- "3: adherence(last 7 + 4 weeks)" --> wk
    wr -- "4: es_vs_target(all muscles)" --> ml
    wr -- "5: kcal_protein_adherence, trend" --> nu
    wr -- "6: score findings, pick top 3, build diffs" --> wr
    wr -- "7: save proposals" --> db
    wr -- "8: summarise(findings)" --> mm
    mm -- "8.1: chat(prompt, numbers)" --> ol
    mm -- "8.2: check numbers ⊆ input, else template" --> mm
    wr -- "9: save summary, emit ReviewReady" --> db
    q -- "10: SSE job.progress = done" --> ui
```

| Step | Rule (v2 plan §09) |
|---|---|
| 6 | Examples: adherence < 70% two weeks → shorten sessions; muscle under target 2 weeks → +2–4 sets; lean-bulk gain > 0.5% BW/week → −150 kcal |
| 8.2 | Any number in the model's text that is not in its input → template summary instead |

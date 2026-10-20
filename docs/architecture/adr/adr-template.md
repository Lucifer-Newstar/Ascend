# ADR Template

Use this template for every Architecture Decision Record. Number sequentially
(`ADR-00NN`), date it, keep the status current (`Proposed` → `Accepted` →
`Superseded by ADR-00NN`), and store it in `docs/architecture/adr/` as
`00NN-short-title.md`. Add a row to the ADR list in [docs/README.md](../../README.md#adr-list).

---

# ADR-00NN: <Short Title>

- **Status:** Proposed | Accepted | Superseded by ADR-00NN
- **Date:** YYYY-MM-DD
- **Deciders:** <names>

## Context

<What is the problem or decision point? What constraints exist (offline, 4 GB VRAM,
Windows, team skills)? What made this decision necessary now?>

## Decision

<What exactly is decided? Concrete enough that implementation can follow directly.
Name versions, files and owners where it matters.>

## Consequences

### Positive

- <benefit 1>
- <benefit 2>

### Negative / Trade-offs

- <cost or risk 1>
- <mitigation, if any>

## Alternatives Considered

| Option | Why rejected |
|---|---|
| <option 1> | <reason> |
| <option 2> | <reason> |

## Validation

<How will we know this was right? A benchmark, a test, a metric in
[evaluation.md](../../operations/evaluation.md).>

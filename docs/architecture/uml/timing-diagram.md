# Timing Diagram — Chat Reply Around a Meal Scan

> **Diagram 13 (UML 2.5 — Behavioural).** How the single 4 GB GPU is shared over time
> when the user starts a meal scan while chatting. Mermaid has no timing diagram, so
> this is PlantUML. Times are **illustrative estimates**, not measurements.

```plantuml
@startuml ascend-gpu-timing
scale 1 as 60 pixels
concise "GPU model" as GPU
robust "Chat job" as CHAT
robust "Scan job" as SCAN
binary "GPU lock" as LOCK

@0
GPU is "qwen3:4b"
CHAT is Idle
SCAN is Idle
LOCK is low

@1
CHAT is Streaming
LOCK is high

@4
CHAT is Idle
LOCK is low

@5
SCAN is Queued

@6
SCAN is Running
LOCK is high
GPU is "unloading"

@7
GPU is "qwen3-vl:2b"

@13
GPU is "unloading"
SCAN is Done

@14
GPU is "qwen3:4b (reload)"
LOCK is low

@15
CHAT is Streaming
LOCK is high

@18
CHAT is Idle
LOCK is low

highlight 6 to 14 : scan holds the GPU
@enduml
```

| Interval (s, est.) | What happens |
|---|---|
| 1–4 | Chat reply streams (holds the GPU lock) |
| 5 | User drops a photo; scan job queued behind chat |
| 6–7 | Chat model unloaded (`keep_alive: 0`), VLM loaded |
| 7–13 | VLM finds items; classifier runs on CPU in parallel per crop |
| 13–14 | VLM unloaded, chat model reloaded |
| 15 | Next chat reply starts — a few seconds later than without the scan |

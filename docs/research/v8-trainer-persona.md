# ASCEND v8 research: the trainer persona

Status: research document for the v8 build. Date: 2026-10-22. Short by design.
Source marks: **[abstract read]**, **[page read]**, **[snippet]**, **[unverified]** (the author's inference).
The character (art made separately for v8) is **Instructor Iskra Vey**, a stern-but-encouraging veteran drill instructor of hunters; see `ART_PROVENANCE.md` for how the art was made.

## 1. What the research says

- **Conversational agents in health are promising but thinly tested.** A JAMIA systematic review found mostly quasi-experimental studies; patient safety was "rarely evaluated" ([Laranjo2018] [abstract read]). A later review found usability and satisfaction performed well (27/30 and 26/31 studies) and positive or mixed effectiveness in 23/30 studies, with mixed qualitative perceptions and limited study quality ([MilneIves2020] [abstract read]). → a coach can help, but it must not be the only way to read the data.
- **Relationship cues keep people engaged.** Work on long-term "relational agents" describes techniques for building and keeping a relationship with a computer agent ([Bickmore2005] [snippet]). → consistent character, memory of the user's progress, and the same voice every time.
- **Interactivity can matter more than a human face.** In one study, high message interactivity made up for a chatbot that was low on human visual cues ([GoSundar2019] [snippet]). → the avatar adds character, but the useful part is the exchange: an insight plus "Why?".
- **Stylised beats near-realistic.** Uncanny-valley effects come from conflicting realism cues in a character's appearance ([Schwind2018] [snippet]). → a clearly stylised cel-shaded character, not a photoreal face.
- **Autonomy-supportive tone.** Autonomous motivation predicts exercise ([Teixeira2012] [abstract read]). In SDT interventions, rises in need support and autonomous motivation, not controlled motivation, tracked behaviour change ([Ntoumanis2021] [abstract read]). One honest caveat: a direct test of "should/must" versus choice-giving wording found **no** difference in perceived autonomy support or reactance ([Altendorf2019] [abstract read]). → use autonomy-supportive wording as a principle, but do not claim it alone changes outcomes.
- **Motivational interviewing (MI).** Interventions that include MI raised physical activity, but no difference was found where MI's own effect could be isolated, and benefits faded after a year ([Zhu2024] [abstract read]). → borrow MI's spirit (reflect, offer choice, no lecturing); do not claim MI efficacy.
- **Over-trust.** Automation bias (over-reliance on automated advice) is mediated by trust and workload; mitigations include showing information rather than bare recommendations and attaching confidence ([Goddard2012] [abstract read]). → every trainer line keeps its "Why?" one tap away and labels estimates as estimates.
- **Nagging.** Excessive notifications can lead to ignored or disabled notifications and disengagement ([NotifFatigue] [snippet]). → the trainer speaks only on real events, with caps (§2.4).

## 2. Decisions for ASCEND v8

### 2.1 Numbers come from engines, never from the model

- Every number the trainer says comes from a deterministic engine (recovery, progression, deload, TDEE, weekly insights, notices) through the existing facts → template path. With AI on, the local model (qwen3:4b) may only *rephrase*. Its output is shown only if the existing number guard passes (every number must match a fact within the rounding rule); otherwise the template is shown. This is the v0.3.0 coach guard, extended to the trainer voice.
- Templates exist for every message type, so the trainer works fully with AI off.
- The plain-mode toggle (top bar and Settings, persisted) switches the same facts to the plain System style. Nothing is hidden behind the persona ([Goddard2012]: information beside the recommendation).

### 2.2 Voice rules

1. Second person, addresses the user as **"Hunter"**; **≤ 40 words**; one idea per message.
2. **Fact first, then the call to action**; numbers only as placeholders filled from engine facts.
3. **Stern but encouraging:** praise effort and progress specifically ("+5 kg on squat since May"), never the person's body or worth.
4. **Autonomy-supportive:** offer a choice where one exists ("Push today, or take the rest day. Your call."); use "should/must" only in safety warnings ([Ntoumanis2021], [Altendorf2019] caveat).
5. **Never shame, never guilt,** never threaten loss (ASCEND never removes progress).
6. **No medical claims,** no diagnoses, no dosages; estimates are called estimates.
7. One flavour line at most; the rest is information.

### 2.3 Expression states (4) and when each appears

| State | Shown when (deterministic trigger) | Example template (≤ 40 words) |
|---|---|---|
| **neutral** (default) | Daily briefing, recovery status, weekly insight, any "Why?" | "Hunter, your chest is recovered and your back needs another day. Today we push. Bench {f1} × {f2} is waiting." |
| **proud** | PR, quest clear, boss raid defeated, streak milestone, adherence ≥ target | "Hunter, new record: squat {f1} kg for {f2}. That is earned strength. Log it and rest well." |
| **warning** | Over-reached muscle, deload trigger, TDEE shortfall large, missed program day (no penalty) | "Hunter, your quads are still at {f1}% readiness. Train them today and you trade progress for fatigue. Upper body instead?" |
| **hyped** | Boss raid start (Monday), rank-up, level-up, comeback after a break | "A new boss rises, Hunter: {f1}. HP {f2} sets. Every set you log hits it. Beat it by Sunday." |

Caps [design; unverified tuning]: at most one unprompted trainer line per screen visit, three per day, and one "warning" per muscle per day. Celebrations respect Reduce motion; the expression change is a crossfade.

### 2.4 Message template style guide

- Structure: `Hunter, <fact with placeholders>. <meaning in plain words>. <one action or choice>.`
- Placeholders `{f1}…` only; the renderer fills digits (the model never types numbers).
- Plain words over jargon ("readiness" over "fatigue index"); keep engine terms for the "Why?" panel.
- Same message types as the System voice (deep research §7.8), mapped to expressions: DAILY QUEST / ANALYSIS / EXPLAIN → neutral; QUEST COMPLETE / SKILL ACQUIRED / PR → proud; WARNING → warning; LEVEL UP / RANK UP / BOSS RAID → hyped.
- Every template has a plain-mode twin (same facts, System style, no name or emotion).

### 2.5 Original character design and copyright

- Characters can be protected by copyright when distinctively delineated, and infringement turns on substantial similarity ([Zecevic2006] [snippet]). So the design must not echo any existing character's signature combination of look, outfit and name.
- What the v8 design does: an original name checked by web search; a written brief with distinctive traits (ash-silver undercut with a teal streak, amber eyes, an eyebrow scar, a charcoal high-collar coat with teal piping and a hexagonal insignia); no franchise, character or artist names in any prompt; all of it recorded in `ART_PROVENANCE.md`.
- Purely AI-generated images may not be protected by copyright in some jurisdictions; the U.S. Copyright Office's 2025 report addresses the copyrightability of AI outputs ([USCO2025] [snippet]). The repo releases the art under its MIT licence as far as it can and says so in the provenance file.
- Do not use the trainer to imitate the Solo Leveling "System" text or its characters; the theme is a genre homage, not a copy [design].

## 3. References

- **Laranjo2018**: Laranjo L et al. (2018). Conversational agents in healthcare: a systematic review. J Am Med Inform Assoc 25(9):1248-58. https://pubmed.ncbi.nlm.nih.gov/30010941/ [abstract read]
- **MilneIves2020**: Milne-Ives M et al. (2020). The effectiveness of artificial intelligence conversational agents in health care: systematic review. J Med Internet Res 22(10):e20346. https://pubmed.ncbi.nlm.nih.gov/33090118/ [abstract read]
- **Bickmore2005**: Bickmore TW, Picard RW (2005). Establishing and maintaining long-term human-computer relationships. ACM Trans Comput-Hum Interact 12(2):293-327. https://dl.acm.org/doi/10.1145/1067860.1067867 [snippet]
- **GoSundar2019**: Go E, Sundar SS (2019). Humanizing chatbots: the effects of visual, identity and conversational cues on humanness perceptions. Comput Hum Behav 97:304-16. https://www.sciencedirect.com/science/article/abs/pii/S0747563219300329 [snippet]
- **Schwind2018**: Schwind V, Wolf K, Henze N (2018). Avoiding the uncanny valley in virtual character design. ACM Interactions 25(5). https://interactions.acm.org/archive/view/september-october-2018/avoiding-the-uncanny-valley-in-virtual-character-design [snippet]
- **Teixeira2012**: Teixeira PJ et al. (2012). Exercise, physical activity, and self-determination theory: a systematic review. Int J Behav Nutr Phys Act 9:78. https://pubmed.ncbi.nlm.nih.gov/22726453/ [abstract read]
- **Ntoumanis2021**: Ntoumanis N et al. (2021). A meta-analysis of self-determination theory-informed intervention studies in the health domain. Health Psychol Rev 15(2):214-44. https://pubmed.ncbi.nlm.nih.gov/31983293/ [abstract read]
- **Altendorf2019**: Altendorf MB et al. (2019). Should or could? Testing the use of autonomy-supportive language and the provision of choice in online computer-tailored alcohol reduction communication. Digit Health 5. https://pmc.ncbi.nlm.nih.gov/articles/PMC6393822/ [abstract read]
- **Zhu2024**: Zhu SF et al. (2024). Effectiveness of behavioural interventions with motivational interviewing on physical activity outcomes in adults: systematic review and meta-analysis. BMJ 386:e078713. https://pubmed.ncbi.nlm.nih.gov/38986547/ [abstract read]
- **Goddard2012**: Goddard K, Roudsari A, Wyatt JC (2012). Automation bias: a systematic review of frequency, effect mediators, and mitigators. J Am Med Inform Assoc 19(1):121-7. https://pmc.ncbi.nlm.nih.gov/articles/PMC3240751/ [abstract read]
- **NotifFatigue**: Designing notifications that empathise with fatigue (ACM, 2025). https://dl.acm.org/doi/10.1145/3715668.3736353 [snippet]
- **Zecevic2006**: Zecevic J (2006). Distinctly delineated fictional characters that constitute the story being told. Vanderbilt J Ent Tech Law 8(2). https://scholarship.law.vanderbilt.edu/cgi/viewcontent.cgi?article=1414&context=jetlaw [snippet]
- **USCO2025**: U.S. Copyright Office (2025). Copyright and Artificial Intelligence, Part 2: Copyrightability. https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf [snippet]

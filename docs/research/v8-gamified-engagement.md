# ASCEND v8 research: gamified engagement without manipulation

Status: research document for the v8 build. Date: 2026-10-22. Short by design: the build depends most on the muscle documents.
Source marks: **[abstract read]**, **[page read]**, **[snippet]** (search snippet only), **[unverified]** (the author's inference).

## 1. What the evidence supports

- **Gamification helps, modestly, and the effect shrinks.** A meta-analysis of 16 RCTs (2,407 participants) found gamified interventions raised physical activity (Hedges g = 0.42), and beat non-gamified active interventions (g = 0.23). At follow-up (about 14 weeks after the end), the effect was smaller (g = 0.15). The authors argue that the effect lasting at all means it is "not just a novelty effect" ([Mazeas2022] [abstract read]). Design implication: tie game elements to the real training, because the game layer alone will not hold attention.
- **Effects depend on context and users.** A widely cited review found mostly positive effects, "greatly dependent on the context" ([Hamari2014] [snippet]).
- **Motivation quality matters.** SDT-based health interventions produce small-to-medium behaviour change; gains in autonomous (not controlled) motivation tracked the improvement ([Ntoumanis2021] [abstract read]).
- **Adaptive, personal goals beat fixed goals.** In a 4-month RCT, adaptive step goals outperformed a static 10,000-step goal, and small immediate rewards beat larger delayed ones ([Adams2017] [abstract read]). Specific, difficult goals outperform "do your best" ([Locke2002] [snippet]).
- **Streaks work best with slack.** Duolingo reports that letting learners equip up to two Streak Freezes raised daily active learners by **0.38%** (relative), and that separating the daily goal from the streak raised day-14 retention by 3.3% and new learners on a streak by 19%. It also reports one downside: fewer learners reached their daily goals ([DuolingoFreeze], [DuolingoStreak] [page read]; company data, not peer-reviewed). Milestone streak animations raised 7-day retention of new learners by 1.7% (same source).
- **Broken streaks can demotivate.** A consumer-research paper studies how a broken streak changes whether people continue ([Silverman2023] [snippet]; the finding's direction was not checked beyond the title and snippet [unverified]). ASCEND's rule that a missed day never removes XP or rank stays.
- **Less on screen is easier.** Progressive disclosure, which moves advanced or rarely used features to a secondary screen, makes apps "easier to learn and less error-prone" ([NNGPD] [page read]).
- **Motion must be optional.** WCAG 2.3.3: "Motion animation triggered by interaction can be disabled, unless the animation is essential"; some users get distraction or nausea from motion ([WCAG233] [page read]).

## 2. What backfires

- **Extrinsic rewards can undermine intrinsic motivation.** In a meta-analysis of 128 experiments, engagement-, completion- and performance-contingent rewards reduced free-choice intrinsic motivation (d = −0.40, −0.36, −0.28). Positive feedback *increased* it (d = 0.33) ([Deci1999] [abstract read]). → reward *information* about progress, not attendance.
- **Punishment and gaming the system.** In Habitica, all 45 field-study users met counterproductive effects. One common example: being punished in especially productive periods because tasks were not checked off in time. How often these effects happened predicted motivation change over time ([Diefenbach2019] [abstract read]).
- **Leaderboards and badges.** In a 16-week classroom study, students in the gamified course (leaderboards, badges) showed less motivation, satisfaction and empowerment over time than the control group ([Hanus2015] [snippet]).
- **Loot boxes.** In 7,422 gamers, loot-box spending was linked to problem-gambling severity (η² = 0.054), more strongly than other in-game spending ([Zendle2018] [abstract read]).

## 3. Decisions for ASCEND v8 (owner decision of 2026-10-22, with the evidence)

**Build**

1. **Weekly boss raid.** A boss appears each Monday. Its HP is scaled to the user's own program or recent weekly volume, logged sets deal damage, and beating it by Sunday gives bonus XP and a title. Missing it costs nothing. Why: an adaptive, specific weekly goal ([Adams2017], [Locke2002]) that rewards the training itself, not attendance ([Deci1999]), with no loss mechanic ([Diefenbach2019]).
   - HP = clamp(median weekly effective sets of the last 4 weeks × 1.0, floor, ceiling); new users use the program's planned weekly sets. Damage = effective sets (the same ES the recovery engine uses), so junk volume is not rewarded beyond the existing ES rules [design; unverified tuning].
   - One celebration on defeat, Reduce-motion aware ([WCAG233]); the title is cosmetic.
2. **"Haven't logged today" banner.** A single in-app line linking to Quick log, shown only after the user's usual training time and dismissible for the day. Why: a low-friction cue inside the app, with none of the notification fatigue risk (§5 of the trainer document); it nudges without punishing.
3. **Keep and polish what exists:** daily quest, streak with freezes (up to 2 banked, mirroring the Duolingo result ([DuolingoFreeze])), XP/rank, the recovery map's "ready" muscles, the program's next session. Level-up and quest-clear moments animate transform/opacity only and switch off with Reduce motion ([WCAG233]).
4. **Simplify screens** with progressive disclosure: one primary action per screen, details behind "Why?" and "More" ([NNGPD]).

**Do not build (and why)**

- No leaderboards or PvP ([Hanus2015]); no loot boxes, random paid rewards or shops ([Zendle2018]); no progress loss or "death" mechanics ([Diefenbach2019]).

## 4. What we dropped and why

- **Achievements system, daily login/check-in rewards, reminder notifications: dropped for v8.**
  - *Over-justification:* rewards given for showing up are exactly the engagement- and completion-contingent kind that reduced intrinsic motivation in [Deci1999] (d = −0.40 and −0.36). A login reward pays for opening the app, not for training.
  - *Diminishing returns:* the gamification effect falls from g = 0.42 to 0.15 at follow-up ([Mazeas2022]). Stacking more reward layers is not supported as a way to stop that decline [unverified: no study read tests "more layers"].
  - *Enough channels already:* ASCEND already gives five daily reasons to return: the daily quest, the streak with freezes, XP/rank progress, recovery-map "ready" muscles, and the program's next session. A sixth and seventh reward channel adds noise and screen clutter, against the progressive-disclosure goal ([NNGPD]) [design judgement].
  - *Notifications:* replaced by the in-app banner, which reaches the user only when they are already in the app. No push permission, no nagging.
- **After v8: feature freeze.** A new idea must replace something or reduce friction. This protects the "less complicated" goal the owner set after the first Windows test.

## 5. References

- **Mazeas2022**: Mazéas A et al. (2022). Evaluating the effectiveness of gamification on physical activity: systematic review and meta-analysis of randomized controlled trials. J Med Internet Res 24(1):e26779. https://pubmed.ncbi.nlm.nih.gov/34982715/ [abstract read]
- **Hamari2014**: Hamari J, Koivisto J, Sarsa H (2014). Does gamification work? A literature review of empirical studies on gamification. HICSS 2014. https://ieeexplore.ieee.org/document/6758978 [snippet]
- **Ntoumanis2021**: Ntoumanis N et al. (2021). A meta-analysis of self-determination theory-informed intervention studies in the health domain. Health Psychol Rev 15(2):214-44. https://pubmed.ncbi.nlm.nih.gov/31983293/ [abstract read]
- **Adams2017**: Adams MA et al. (2017). Adaptive goal setting and financial incentives: a 2 × 2 factorial randomized controlled trial to increase adults' physical activity. BMC Public Health 17:286. https://pubmed.ncbi.nlm.nih.gov/28356097/ [abstract read]
- **Locke2002**: Locke EA, Latham GP (2002). Building a practically useful theory of goal setting and task motivation: a 35-year odyssey. Am Psychol 57(9):705-17. https://med.stanford.edu/content/dam/sm/s-spire/documents/PD.locke-and-latham-retrospective_Paper.pdf [snippet]
- **DuolingoFreeze**: Duolingo blog. The habit-building research behind your Duolingo streak. https://blog.duolingo.com/how-duolingo-streak-builds-habit/ [page read]
- **DuolingoStreak**: Duolingo blog. Improving the streak: forming habits one lesson at a time. https://blog.duolingo.com/improving-the-streak/ [page read]
- **Silverman2023**: Silverman J, Barasch A (2023). On or off track: how (broken) streaks affect consumer decisions. J Consum Res 49(6):1095-. https://academic.oup.com/jcr/article-abstract/49/6/1095/6623414 [snippet]
- **NNGPD**: Nielsen J. Progressive disclosure. Nielsen Norman Group. https://www.nngroup.com/articles/progressive-disclosure/ [page read]
- **WCAG233**: W3C. Understanding Success Criterion 2.3.3: Animation from Interactions (WCAG 2.2). https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html [page read]
- **Deci1999**: Deci EL, Koestner R, Ryan RM (1999). A meta-analytic review of experiments examining the effects of extrinsic rewards on intrinsic motivation. Psychol Bull 125(6):627-68. https://pubmed.ncbi.nlm.nih.gov/10589297/ [abstract read]
- **Diefenbach2019**: Diefenbach S, Müssig A (2019). Counterproductive effects of gamification: an analysis on the example of the gamified task manager Habitica. Int J Hum-Comput Stud 127:190-210. https://doi.org/10.1016/j.ijhcs.2018.09.004 [abstract read]
- **Hanus2015**: Hanus MD, Fox J (2015). Assessing the effects of gamification in the classroom: a longitudinal study on intrinsic motivation, social comparison, satisfaction, effort, and academic performance. Comput Educ 80:152-61. https://www.sciencedirect.com/science/article/abs/pii/S0360131514002000 [snippet]
- **Zendle2018**: Zendle D, Cairns P (2018). Video game loot boxes are linked to problem gambling: results of a large-scale survey. PLoS ONE 13(11):e0206767. https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0206767 [abstract read]

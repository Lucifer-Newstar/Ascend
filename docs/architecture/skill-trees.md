# Skill trees

Calisthenics progressions computed from the sets you log. Code: `services/sidecar/app/modules/skills/`
(`catalog.py` holds the data, `engine.py` the pure progress maths, `service.py` storage and events).
This page is generated from the catalog's contents; when the two differ, the code wins.

## Exercises behind the trees

The trees use 64 calisthenics progression exercises from `workouts/calisthenics_seed.py`, added to the library by migration 0010. (The commit that added them said 62; 64 is the correct count.) Feeders can also be library lifts. A test checks that every exercise named in the catalog exists.

## How progress is computed

Everything is deterministic: the same sets and the same clock give the same answer (`engine.py`, version `skills-v1`).

- **Session**: all sets of one exercise on one calendar day.
- **Criterion** such as `3×8 Pull-up` or `3×20 s Tuck L-sit` (optionally "at +10 kg"). A session's score is the mean of
  `min(1, value / target)` over its best N sets, with missing sets counted as 0. For example, 8, 8, 6 against 3×8 scores 0.92.
- **Window**: only the last 42 days count.
- **Consistency**: a criterion is met after **2 separate sessions** that score 1.0, so one lucky day is not enough.
- **Progress %** = 90 × best session score + 10 × min(1, sessions met ÷ 2). A step's % is the mean over its criteria.
  This means you sit at 95% after your first full session. The UI says "one more session to lock it in".
- **Unlock**: every criterion met, and the step's prerequisites unlocked. Trees can branch and converge (handstand → HSPU).
  Entry steps start unlocked.
  - An unlock is stored once, with the IDs of the sets that proved it, and pays its XP once.
  - Missing training later does not take an unlock away. If the current step has not been trained in 28 days, the skill shows as "rusty".
- **Revocation**: if a set behind an unlock is deleted, or edited so the step no longer holds at the time it was earned,
  the unlock is removed (along with any steps that depended on it) and its XP is reversed with a negative ledger row.
- **Imports**: imported history can unlock steps, but pays no XP.
- **Implausible holds**: on elite statics (full and straddle levers, planche, flag, V-sit), holds over 120 s are ignored
  and counted. On other holds the limit is 600 s.
- **Time to unlock**: shown only when every criterion of the next step has at least 3 sessions spanning at least 7 days, with an
  upward trend.
  - It is a least-squares line through the session scores, extrapolated to 1.0, plus your usual gap for the confirming session.
  - It is labelled as an **estimate**, hidden when the trend is flat or falling, and capped at a year.
  - Otherwise the API says what data is missing.

## Where the numbers come from

The **order** of each progression follows the sources below. The **thresholds** are ASCEND's own design choices,
informed by the common rules in those sources:
- move on at the top of a 3×5–8 rep range;
- hold isometrics for 10–30 s before progressing;
- prove you can do one real rep or hold of the skill before calling it acquired.

They are not measured values. Steps where the sources disagree, or where we found nothing firm, are flagged
**uncertain** in the data and shown that way in the app.

| Key | Source |
|---|---|
| RR | [r/bodyweightfitness Recommended Routine](https://www.reddit.com/r/bodyweightfitness/wiki/kb/recommended_routine/) |
| BWF | [r/bodyweightfitness wiki: exercise progressions (e.g. front lever, pull-up)](https://www.reddit.com/r/bodyweightfitness/wiki/exercises/front-lever/) |
| OG | [Steven Low, Overcoming Gravity, 2nd ed. (2016)](https://stevenlow.org/overcoming-gravity/) |
| GMB | [GMB Fitness tutorials (e.g. L-sit progression)](https://gmb.io/l-sit/) |
| NHE | [Mjolsnes et al. (2004), 10-week Nordic hamstring training trial](https://pubmed.ncbi.nlm.nih.gov/15387805/) |

## Trees

| Skill | Steps | Sources | |
|---|---|---|---|
| Muscle-up | Dead hang → Scapular pull-up → Negative pull-up → Pull-up → Chest-to-bar pull-up → Muscle-up negative → Muscle-up | RR, BWF, OG |  |
| One-arm push-up | Incline push-up → Push-up → Diamond push-up → Archer push-up → Incline one-arm push-up → One-arm push-up | RR, BWF, OG |  |
| Dips | Support hold → Negative dip → Parallel-bar dip → Ring dip → Weighted dip | RR, BWF |  |
| Plank to V-sit | Plank → Hollow body hold → Tuck L-sit → One-leg L-sit → L-sit → V-sit | RR, GMB, OG |  |
| Handstand & HSPU | Pike push-up → Headstand → Wall handstand → Freestanding handstand → Elevated pike push-up → Wall handstand push-up → Freestanding HSPU | BWF, GMB, OG |  |
| Pistol squat | Bodyweight squat → Box pistol → Assisted pistol → Pistol squat | RR, GMB |  |
| Front lever | Tuck front lever → Advanced tuck → One-leg → Straddle → Full front lever | BWF, OG |  |
| Back lever | Skin the cat → German hang → Tuck back lever → Advanced tuck → Straddle → Full back lever | BWF, OG |  |
| Planche (tuck to straddle) | Planche lean → Frog stand → Tuck planche → Advanced tuck planche → Straddle planche | BWF, OG | stretch goal |
| Human flag | Side plank → Vertical flag → Tuck flag → Straddle flag → Human flag | BWF | stretch goal |
| Nordic curl | Single-leg glute bridge → Nordic negative → Nordic curl → Nordic curl 3×5 | NHE, RR |  |
| Dragon flag | Lying leg raise → Tuck negative → Dragon flag negative → Dragon flag | BWF, OG |  |
| Hanging leg raise | Dead hang → Knee raise on bars → Hanging leg raise → Hanging leg raise 3×10 | RR, BWF |  |
| Weighted pull-up | Pull-up → Pull-up 3×8 → Pull-up +10 kg → Pull-up +20 kg | OG, RR |  |
| One-arm hang | Dead hang → Dead hang 60 s → One-arm hang → One-arm hang 3×20 s | OG | stretch goal |
| Bulgarian split squat | Bodyweight squat → Split squat → Bulgarian split squat → Bulgarian split squat 3×12 | RR |  |
| Plyo push-up | Push-up → Push-up 3×15 → Plyo push-up | OG, RR |  |

Every listed step must be shown in 2 sessions within 42 days.

### Muscle-up

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Dead hang | Dead Hang | start here | 0 |  |
| Scapular pull-up | Scapular Pull-up | 3×30 s Dead Hang | 30 |  |
| Negative pull-up | Negative Pull-up | 3×10 Scapular Pull-up | 40 |  |
| Pull-up | Pull-up | 3×5 Negative Pull-up | 80 |  |
| Chest-to-bar pull-up | Chest-to-bar Pull-up | 3×8 Pull-up | 80 |  |
| Muscle-up negative | Muscle-up Negative | 3×8 Pull-up; 3×10 Chest Dip; 3×3 Chest-to-bar Pull-up | 100 |  |
| Muscle-up | Muscle-up | 3×3 Muscle-up Negative; 3×8 Straight Bar Dip; 1×1 Muscle-up | 250 | Counts strict reps; log kipping reps separately if you do them. |

Feeders: Pull-up, Chin-up, Chest-to-bar Pull-up, Chest Dip, Straight Bar Dip, Inverted Row.

### One-arm push-up

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Incline push-up | Incline Push-up | start here | 0 |  |
| Push-up | Push-up | 3×12 Incline Push-up | 30 |  |
| Diamond push-up | Diamond Push-up | 3×15 Push-up | 40 |  |
| Archer push-up | Archer Push-up | 3×10 Diamond Push-up | 80 |  |
| Incline one-arm push-up | Incline One-arm Push-up | 3×6 Archer Push-up (each side) | 100 |  |
| One-arm push-up | One-arm Push-up | 3×5 Incline One-arm Push-up (each side); 1×1 One-arm Push-up (each side) | 250 |  |

Feeders: Push-up, Diamond Push-up, Pseudo Planche Push-up, Chest Dip, Plank.

### Dips

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Support hold | Parallel Bar Support Hold | start here | 0 |  |
| Negative dip | Negative Dip | 3×30 s Parallel Bar Support Hold | 30 |  |
| Parallel-bar dip | Chest Dip | 3×5 Negative Dip | 80 |  |
| Ring dip | Ring Dip | 3×10 Chest Dip; 3×20 s Ring Support Hold | 100 |  |
| Weighted dip | Weighted Dip | 3×8 Ring Dip; 3×5 Weighted Dip at +10 kg | 150 | uncertain. +10 kg is a fixed starting load; relative to bodyweight would be fairer. |

Feeders: Chest Dip, Straight Bar Dip, Close-grip Bench Press, Diamond Push-up, Triceps Pushdown.

### Plank to V-sit

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Plank | Plank | start here | 0 |  |
| Hollow body hold | Hollow Body Hold | 3×60 s Plank | 30 |  |
| Tuck L-sit | Tuck L-sit | 3×30 s Hollow Body Hold | 40 |  |
| One-leg L-sit | One-leg L-sit | 3×15 s Tuck L-sit | 60 |  |
| L-sit | L-sit | 3×15 s One-leg L-sit; 1×10 s L-sit | 200 |  |
| V-sit | V-sit | 3×20 s L-sit; 3×10 Seated Pike Compression; 1×3 s V-sit | 300 | uncertain. Sources agree a strong L-sit and compression come first; numbers vary. |

Feeders: Hollow Body Hold, Hanging Leg Raise, Seated Pike Compression, Parallel Bar Support Hold.

### Handstand & HSPU

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Pike push-up | Pike Push-up | start here | 0 |  |
| Headstand | Headstand | 3×8 Pike Push-up | 40 |  |
| Wall handstand | Wall Handstand | 3×30 s Headstand | 60 |  |
| Freestanding handstand | Freestanding Handstand | 3×60 s Wall Handstand; 1×10 s Freestanding Handstand | 250 |  |
| Elevated pike push-up | Elevated Pike Push-up | 3×12 Pike Push-up; 3×30 s Wall Handstand | 60 |  |
| Wall handstand push-up | Wall Handstand Push-up | 3×8 Elevated Pike Push-up; 1×1 Wall Handstand Push-up | 200 |  |
| Freestanding HSPU | Freestanding Handstand Push-up | 3×5 Wall Handstand Push-up; 3×30 s Freestanding Handstand; 1×1 Freestanding Handstand Push-up | 400 | uncertain. An advanced goal; thresholds are our estimate. |

Feeders: Pike Push-up, Overhead Press, Wall Handstand, Hollow Body Hold.

### Pistol squat

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Bodyweight squat | Bodyweight Squat | start here | 0 |  |
| Box pistol | Box Pistol Squat | 3×20 Bodyweight Squat | 40 |  |
| Assisted pistol | Assisted Pistol Squat | 3×8 Box Pistol Squat (each side) | 60 |  |
| Pistol squat | Pistol Squat | 3×8 Assisted Pistol Squat (each side); 1×1 Pistol Squat (each side) | 200 |  |

Feeders: Bodyweight Squat, Bulgarian Split Squat, Deep Squat Hold, Back Squat.

### Front lever

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Tuck front lever | Tuck Front Lever | 3×5 Pull-up | 60 |  |
| Advanced tuck | Advanced Tuck Front Lever | 3×15 s Tuck Front Lever | 80 |  |
| One-leg | One-leg Front Lever | 3×15 s Advanced Tuck Front Lever | 100 |  |
| Straddle | Straddle Front Lever | 3×10 s One-leg Front Lever | 150 | uncertain.  |
| Full front lever | Front Lever | 3×10 s Straddle Front Lever; 1×5 s Front Lever | 400 | uncertain.  |

Feeders: Pull-up, Inverted Row, Hanging Leg Raise, Hollow Body Hold, Lat Pulldown.

### Back lever

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Skin the cat | Skin the Cat | start here | 0 |  |
| German hang | German Hang | 3×5 Skin the Cat | 40 |  |
| Tuck back lever | Tuck Back Lever | 3×20 s German Hang | 60 |  |
| Advanced tuck | Advanced Tuck Back Lever | 3×15 s Tuck Back Lever | 80 |  |
| Straddle | Straddle Back Lever | 3×15 s Advanced Tuck Back Lever | 120 | uncertain.  |
| Full back lever | Back Lever | 3×10 s Straddle Back Lever; 1×5 s Back Lever | 300 | uncertain.  |

Feeders: Pull-up, Chin-up, Chest Dip, German Hang.

### Planche (tuck to straddle)

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Planche lean | Planche Lean | 3×15 Push-up | 40 |  |
| Frog stand | Frog Stand | 3×20 s Planche Lean | 40 |  |
| Tuck planche | Tuck Planche | 3×30 s Frog Stand; 3×30 s Planche Lean | 150 |  |
| Advanced tuck planche | Advanced Tuck Planche | 3×15 s Tuck Planche | 200 | uncertain.  |
| Straddle planche | Straddle Planche | 3×15 s Advanced Tuck Planche; 1×3 s Straddle Planche | 500 | uncertain. A multi-year goal for most people; sources give wide ranges. |

Feeders: Pseudo Planche Push-up, Planche Lean, Chest Dip, Parallel Bar Support Hold.

### Human flag

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Side plank | Side Plank | start here | 0 |  |
| Vertical flag | Vertical Flag | 3×45 s Side Plank; 3×8 Pull-up | 60 | uncertain.  |
| Tuck flag | Tuck Human Flag | 3×15 s Vertical Flag | 120 | uncertain.  |
| Straddle flag | Straddle Human Flag | 3×10 s Tuck Human Flag | 200 | uncertain.  |
| Human flag | Human Flag | 3×5 s Straddle Human Flag; 1×3 s Human Flag | 400 | uncertain.  |

Feeders: Side Plank, Pull-up, Overhead Press, Russian Twist.

### Nordic curl

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Single-leg glute bridge | Single-leg Glute Bridge | start here | 0 |  |
| Nordic negative | Nordic Curl Negative | 3×12 Single-leg Glute Bridge (each side) | 60 |  |
| Nordic curl | Nordic Curl | 3×6 Nordic Curl Negative; 1×1 Nordic Curl | 200 |  |
| Nordic curl 3×5 | Nordic Curl | 3×5 Nordic Curl | 250 |  |

Feeders: Romanian Deadlift, Leg Curl, Single-leg Glute Bridge, Back Extension.

### Dragon flag

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Lying leg raise | Lying Leg Raise | start here | 0 |  |
| Tuck negative | Tuck Dragon Flag Negative | 3×12 Lying Leg Raise; 3×30 s Hollow Body Hold | 60 |  |
| Dragon flag negative | Dragon Flag Negative | 3×6 Tuck Dragon Flag Negative | 100 |  |
| Dragon flag | Dragon Flag | 3×5 Dragon Flag Negative; 1×1 Dragon Flag | 250 | uncertain.  |

Feeders: Hanging Leg Raise, Hollow Body Hold, Plank, Lying Leg Raise.

### Hanging leg raise

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Dead hang | Dead Hang | start here | 0 |  |
| Knee raise on bars | Knee/Hip Raise On Parallel Bars | 3×45 s Dead Hang | 30 |  |
| Hanging leg raise | Hanging Leg Raise | 3×12 Knee/Hip Raise On Parallel Bars | 60 |  |
| Hanging leg raise 3×10 | Hanging Leg Raise | 3×10 Hanging Leg Raise | 100 |  |

Feeders: Hollow Body Hold, Lying Leg Raise, Dead Hang, Plank.

### Weighted pull-up

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Pull-up | Pull-up | start here | 0 |  |
| Pull-up 3×8 | Pull-up | 3×8 Pull-up | 60 |  |
| Pull-up +10 kg | Weighted Pull Ups | 3×10 Pull-up; 3×5 Weighted Pull Ups at +10 kg | 100 |  |
| Pull-up +20 kg | Weighted Pull Ups | 3×5 Weighted Pull Ups at +20 kg | 150 | uncertain. Threshold is ASCEND's choice; sources give no fixed number. |

Feeders: Pull-up, Chin-up, Inverted Row, Lat Pulldown.

### One-arm hang

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Dead hang | Dead Hang | start here | 0 |  |
| Dead hang 60 s | Dead Hang | 3×60 s Dead Hang | 40 |  |
| One-arm hang | One Handed Hang | 3×60 s Dead Hang; 1×5 s One Handed Hang (each side) | 100 |  |
| One-arm hang 3×20 s | One Handed Hang | 3×20 s One Handed Hang (each side) | 150 | uncertain. |

Feeders: Dead Hang, Scapular Pull-up, Pull-up.

### Bulgarian split squat

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Bodyweight squat | Bodyweight Squat | start here | 0 |  |
| Split squat | Split Squats | 3×20 Bodyweight Squat | 30 |  |
| Bulgarian split squat | Bulgarian Split Squat | 3×12 Split Squats (each side) | 60 |  |
| Bulgarian split squat 3×12 | Bulgarian Split Squat | 3×12 Bulgarian Split Squat (each side) | 100 |  |

Feeders: Bodyweight Squat, Walking Lunge, Single-leg Glute Bridge, Goblet Squat.

### Plyo push-up

| Step | Exercise | Unlocks when | XP | Note |
|---|---|---|---|---|
| Push-up | Push-up | start here | 0 |  |
| Push-up 3×15 | Push-up | 3×15 Push-up | 40 |  |
| Plyo push-up | Plyo Push-up | 3×20 Push-up; 3×5 Plyo Push-up | 80 | uncertain. Stop the set when the push-offs get slow; power work is about speed. |

Feeders: Push-up, Diamond Push-up, Chest Dip, Plank.

## Custom skills

You can write up to 20 trees of your own (`/skills/custom`): 1 to 8 milestones, each a goal on a library exercise
(sets × reps, or sets × seconds for holds, optionally with added kg). The first milestone is open from the start; each one
is reached when its goal is shown in 2 sessions within 42 days, judged by the same engine as the built-in trees. Custom
milestones pay no XP, so a tree you wrote cannot be used to farm levels. Editing a custom tree re-judges it from your
logged sets; deleting it keeps the sets.

## "Train this skill"

`POST /skills/{key}/train` adds up to two items for the next step's unmet criteria, plus one feeder, to today's quest. Each item is
3 sets at a target you can hit today: your best so far, capped at the goal. Items complete from logged sets (`ex:<id>:<reps|hold>:<min>`),
pay 15 XP each, are idempotent per exercise, and are capped at 4 skill items a day.

## Events

- `SkillStepUnlocked`: gamification pays the step's XP (source `skill`, subject to the daily cap).
- `SkillStepRevoked`: gamification appends the reversal.

Both reach the outbox, so the future intelligence layer can read them.

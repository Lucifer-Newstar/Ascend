# The plan builder (v1.4, planbuilder-v1)

> Owner: **Navin**. Code: `services/sidecar/app/modules/planbuilder/` (Jegatheesan), the
> Chat page button (Dhanush). Asked for on 2026-10-25 ("our AI must be able to build the
> workout plan"), with the correction that the interview is optional and free chat is the
> main path.

The trainer builds your week from what you tell it, the way a coach would over a chat. It
works with the local AI off: rules read the sentences, and the numbers always come from
what you typed.

## 1. Free chat (the main path)

Mention things in normal chat and the trainer picks them up:

| You say | The trainer remembers |
|---|---|
| "I have an 8kg dumbbell and two 5kg" | dumbbells 8 kg and 2 × 5 kg (and ticks dumbbells on your profile) |
| "I have a punching bag", "got hand wraps and a gripper" | the bag, wraps, gloves, gripper or jump rope |
| "I want to train muay thai" | the sport (kickboxing, Muay Thai, boxing, taekwondo, karate, MMA) |
| "I trained kicks 3 years ago" | how long ago, so skill days start as a beginner |
| "I can't eat much but I can drink" | liquid calories: the plan suggests shakes |

Each one answers with a card: what will be remembered, the new week day by day, the notes
and the food targets. **Confirm** saves it, saves the plan and follows it; **undo** puts the
facts, your equipment, the program you followed and your training days back. Questions ("how
do I use a punching bag?") are never taken as facts.

A target weight, a goal or days a week said on their own stay the v1.3 profile and plan
edits ("I want to reach 50 kg" sets your target); said together with a fact above, they ride
along in the same card.

## 2. "Build my plan" (optional)

The **Build my plan** button on the Chat page (or the chip, or typing it) asks six short
questions, each with tap-to-answer chips: goal, weight now and target, what you train with,
a sport and when you last trained it, days a week and session length, and appetite. "Skip"
moves on, "Stop" ends it, and it finishes on the same card. Nothing is saved before Confirm.

## 3. What the plan looks like

- **2 to 5 training days**, so at least two rest days.
- **Strength days** (A and B, alternating): push-ups sized to your baseline (incline below 5,
  diamond from 25), pull-ups or negatives when you have a bar or rings, squats and split
  squats, plank or leg raises. Dumbbells are matched to their weights: the heaviest for
  squats (held at the chest) and rows, a pair for floor press, deadlifts and curls. No bench,
  no bench press: floor press instead.
- **Skill days** when you mix in a sport or own a bag: Tuesday and Saturday (with 4 or 5
  days). Footwork, shadow rounds, kicks, bag rounds and a core circuit. After a break of a
  year or more: form first, kicks at waist height for the first 2-3 weeks, bag rounds at
  about 60% power. A gripper adds 3 × 10 each hand after a skill day.
- **Food**: protein 1.6-2 g per kg; for a gain goal about 300-500 kcal a day more, for
  +0.25-0.5 kg a week. With "can't eat much but can drink": a shake (300 ml full-fat milk,
  1-2 bananas or 3-4 dates, 2 tbsp peanut butter, 1 scoop whey; no oats), one a day in week 1,
  two in week 2, up to three in week 3, one more on skill days.
- Under 18 or with "hide calories": no calorie numbers anywhere in the card.

## 4. Realism check

Healthy gain is 0.25-0.5 kg a week, healthy loss 0.25-0.75 kg. More than 1 kg a week either
way is not planned: "8 kg in 4 weeks is 2.0 kg a week. That's faster than is healthy, so I
won't plan it… about 43 kg (realistic) or 44 kg (stretch)", with those two targets as chips.
Only the pace is discussed; never bodies or body fat.

## 5. Where it is stored

The facts are one settings row (`planbuilder.facts`, JSON); the plan is a normal custom
program (`custom-<id>`), so Train, the Planner, progression and the weekly boss treat it like
any other; the training days go into your schedule. No migration.

## 6. Design check

| Rule | How the plan builder keeps it |
|---|---|
| D4 / R3 / R5 | Every change is a card; nothing is saved before Confirm, and undo restores everything. |
| D9 | Rules only, offline, AI off by default. |
| D10 / R12 | No body comments, no medical claims, calorie numbers hidden under 18. |
| D11 | No new page: the Chat page and the existing cards. |

Not built: coach-style follow-ups weeks later ("ready for full power on the bag?"), and a
model phrasing the questions when the local AI is on (the same slots would be filled).

# What the trainer can change from chat (v1.3)

> Owner: **Navin**. Code: `services/sidecar/app/modules/actions/` (`edit_parser.py` reads the
> line, `edits.py` describes, runs and undoes it). UI: the Chat page and the Ctrl+K drawer
> (`apps/desktop/src/pages/Chat.tsx`, `components/TrainerChat.tsx`, `components/ActionCard.tsx`).

Since v1.3 the trainer does more than log sets and meals: it can change your plan, your
settings, your kit and your profile. Every change follows the same three steps as the
older actions:

1. **Propose.** The trainer shows a card with exactly what will change, old value and new.
   Nothing is written yet.
2. **Confirm.** Only the Confirm button (or a typed "yes" right after the card) runs it.
3. **Undo.** A done card offers Undo; it puts the old value back.

All of it works with the local AI **off** (the default): the lines are read by rules.
A question is never an edit: "should I switch to lbs?" gets an answer, not a card.

## What you can say

| Area | Examples | What changes |
|---|---|---|
| Plan: swap a move | "swap bench press for push-ups" | every slot of that move in the plan you follow |
| Plan: sets | "make squats 4 sets" | sets on that move |
| Plan: reps | "change push-ups to 8-12 reps" | the rep range |
| Plan: rest | "rest 90s on squats", "set rest for bench press to 2 min" | rest between sets |
| Plan: add / remove | "add 2 sets of plank to my plan on friday", "remove lateral raise from my plan" | one move on a day |
| Plan: move a day | "move leg day to saturday", "move monday to tue" | the weekday of a session |
| Days per week | "I can train 4 days a week", "set days per week to 3" | the weekly goal the planner and reminders use |
| Theme | "dark mode", "switch to frost theme" | the theme (locked themes stay locked) |
| Units | "switch to lbs", "use kg" | kg/cm or lb/in |
| Reminders | "turn off reminders", "turn on notifications" | the trainer's reminders |
| Other settings | "hide calories", "disable ai", "reduce motion", "switch trainer to vera" | that setting |
| Kit | "I have a bench", "I got a pull-up bar", "I don't have rings anymore", "I have no equipment" | the equipment on your profile |
| Profile | "change my goal to bulk", "I want to reach 50 kg", "set my age to 22", "my height is 5'7", "call me Navin", "I'm a beginner" | that profile field |
| Plan builder (v1.4) | "I have an 8kg dumbbell and two 5kg", "I have a punching bag", "I want to train muay thai", "I trained kicks 3 years ago", "I can't eat much but I can drink", "Build my plan" | remembers it and rebuilds your week ([plan builder](plan-builder.md)) |

## Rules worth knowing

- **Built-in programs are never edited in place.** The first edit to a built-in program saves
  "<name> (my version)" and you follow it from there; the week's progress carries over. Undo
  goes back to the built-in program. Your own programs are edited in place.
- **The plan you see is the plan you edit.** Built-in moves your kit can't do are already
  swapped (for example the floor press for the bench press), so edits name what is on screen.
- **Values are checked.** An age of 9 or a weight of 500 kg is refused in plain words, the same
  limits as the Profile page.
- **A plan edit that would empty a day is refused.**
- **Days per week** does not rewrite the program you follow; it keeps its own days until you
  move or add one.

## Trainers

Six trainers can speak: Iskra (habits, streaks and the weekly boss), Idris (gym and
strength), Dario (calisthenics and skills), Kai (cardio and martial arts), Tara
(flexibility, mobility, meditation and recovery) and Vera (nutrition). In v1.3 the
specialty is a label on the roster and the Chat page; every trainer answers everything,
and none hands a question to another.

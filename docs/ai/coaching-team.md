# The coaching team

Status: implemented on `feat/coaching-team` (item 13, approved by Navin on 26 Oct 2026).

ASCEND's trainers work as one team. The trainer you pick is your **main trainer**: they run
the chat, your reminders and every action card. When a coaching question is in another
trainer's area, the main trainer hands it to that specialist, who answers it under their own
name and portrait.

| Trainer | Area |
| --- | --- |
| Iskra (default main) | Runs the chat; habits, streaks and the weekly boss |
| Idris | Gym, strength and PRs |
| Dario | Calisthenics |
| Kai | Cardio, Muay Thai and martial arts |
| Tara | Mobility, recovery and rest days |
| Vera | Nutrition and shakes |

You can pick any trainer as the main one (Settings > Trainer > Main trainer, the Chat page's
"Change main trainer", or say "make Dario my main trainer" in chat, which is a card you confirm
and can undo). When the main trainer is also the specialist for a question, they answer it
themselves and there is no handoff. Settings > Trainer > **Coaching team** switches the team
off: the main trainer then answers everything, as before v1.4.

## What moves to a specialist

Routing never changes the **facts**, only **who** says them and in which voice. The reply is built first (rules,
help notes, the knowledge base or the local AI, with the number guard and the safety line), and
`services/sidecar/app/modules/trainer/team.py` then stamps the speaker:

- **Moves:** a knowledge-base answer with its citations, a coaching help note (protein, sore
  muscles, first pull-up, RPE...; the list is `FAQ_OWNER`), and a free answer from the local AI.
- **Stays with the main trainer:** app questions and tours, greetings, goal checks, plans, the
  "why?" explanation, and every proposal card (propose, confirm, undo). A meal logged from chat
  is still the main trainer's card; Scan meal still only suggests and never logs.

## Each trainer's voice (trainer-answers-v1)

A coaching answer (knowledge passage, coaching help note, clarifying question) gets one short
opener and, on a short reply, one sign-off in the speaker's voice
(`services/sidecar/app/modules/trainer/voice.py`), following the trainer cards and the persona
rules in [v8-trainer-persona.md](../research/v8-trainer-persona.md):

| Trainer | Style | Example opener / sign-off |
| --- | --- | --- |
| Iskra | Stern drill instructor, calls you "Hunter" | "Facts first, Hunter." / "Your call, Hunter." |
| Vera | Playful hype coach | "Ooh, good one!" / "Easy wins, promise." |
| Kai | High-energy hype-man | "Let's go!" / "Stay light on your feet!" |
| Dario | Calm strategist | "Here's the plan." / "Small steps compound." |
| Tara | Calm and warm | "Gently now." / "Listen to your body." |
| Idris | Steady and exact | "Do it right." / "Form before load." |

Voice lines carry no numbers, no body or loss words and pass the coach guard. A warning, a
pain question, a "not sure" reply, the local AI's own words, app answers and action cards get
no voice, so the safety line always comes first and plain.

## How the topic is picked

1. A specialist named at the start of the message wins: "Kai, how long should I run?", "ask
   Vera about breakfast", "@dario what next".
2. A coaching help note uses its owner from `FAQ_OWNER`.
3. Otherwise the learned intent label and keywords vote: each area word in the message is one
   point, and the intent model's label adds two (`nutrition_question` for Vera, `injury_pain`
   for Tara). The area with the most points wins.
4. With no clear winner, a knowledge-base answer goes to the area of its first passage: a
   library passage names its specialist in its id (`lib:kai:hook-shadow-drill`) and a note file
   has an owner (`NOTE_AREA`: martial arts and cardio to Kai, meditation, mobility and sleep to
   Tara, supplements to Vera...). Since trainer-answers-v1 a free-exercise-db exercise goes by
   what it is (a stretch to Tara, a weights exercise to Idris, a bodyweight one to Dario) and
   food passages go to Vera. Otherwise the main trainer keeps it.

Measured on the 105 in-scope gap questions (each labelled with the specialist who should
answer; one rater, unverified): the right trainer gave the reply for 44 before and **51**
after, out of 71 and 80 coaching replies (62% both times; more questions now get a coaching
reply).

Pain questions go to Tara and keep the line "If it hurts, stop that exercise and get it
checked by a doctor or physiotherapist" in front. Tara does not diagnose.

## What the screens show

- **Chat (drawer and page):** the main trainer's handoff line ("Iskra: That's Vera's area
  (nutrition). Over to her."), then the reply with the specialist's icon and name.
- **Chat page:** the large portrait and the name follow whoever answered last, with
  "Specialist · Iskra runs your chat" under the name, and a **Your team** row lists who covers
  what. The main trainer takes the floor back on the next reply that is not a specialist's.
- **Drawer header:** the specialist's portrait and name, "with Iskra".

## API

`POST /trainer/chat` returns two more fields (docs/contracts/trainer.yaml):

- `speaker`: the trainer id giving the reply (the main trainer, or the specialist);
- `handoff`: the main trainer's handoff line when a specialist answers, otherwise `null`.

`GET/PUT /settings` has `team_handoff` (default `true`; docs/contracts/progress.yaml). "Start
fresh" keeps it, like the chosen trainer.

## Art

All six trainers have their own art in `apps/desktop/src/assets/trainer` (see
ART_PROVENANCE.md); no placeholder portraits are used.

## Tests

- `services/sidecar/tests/api/test_coaching_team.py`: routing per area, label tie-breaks,
  named specialists, help-note owners, what stays with the main trainer, a different main
  trainer, the team switched off, and the chat cards for both settings.
- `apps/desktop/src/components/CoachingTeam.test.tsx`: the handoff line, the specialist's
  label and portrait, the floor going back to the main trainer, the team row, the drawer header.
- `apps/desktop/src/pages/Settings.test.tsx`: the Coaching team switch and the main trainer
  picker.

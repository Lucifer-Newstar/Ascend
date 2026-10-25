# The habit engine (v1.4)

> Owner: **Navin**. Code: `services/sidecar/app/modules/schedule/` (schedule-v1),
> `apps/desktop/src/lib/reminders.ts`, `apps/desktop/src/components/LockScreen.tsx`,
> `apps/desktop/electron/tray.ts`. Source: the v1.3 review, items 2.1 to 2.5 (M1, M3, M6,
> M12, M14), and the design rules in [RULES_AND_BASELINE.md](../RULES_AND_BASELINE.md).

The habit engine turns "I should train" into a plan with a time and a place in the week. It
adds no new page (D11): every part lives on Today, Train, the Planner, Settings or the lock
screen.

## 1. Your training week

Settings > Trainer > **Your training week**: pick the weekdays and, if you like, a usual time.
Until you pick, the program's own weekdays are the suggestion (`source: "program"`).

- The other weekdays are **planned rest**: neutral for the streak (R2), no reminders (R6).
- The weekly target is the number of days you picked.
- The program is still a rotation: the next session is the one after the last you trained.
  The schedule only says *which days* and *when*.

API: `GET/PUT /schedule` (weekdays 0 = Monday … 6 = Sunday, `time` as `"HH:MM"` or null).

## 2. Planned vs done, and planning next week

The Planner shows this week day by day: planned, done, rest, and the coming sessions lined
up on your days. On Sunday you can plan next week (pick different days for that week only);
a week can be planned ahead, never backwards.

API: `GET/PUT /schedule/week`.

## 3. The 10-minute version

"Short on time? 10-minute version" on Today and on the lock screen. It keeps the first moves
of today's session (up to three) at two sets each, with rests capped at 45 s. Train shows it
as a banner for the rest of the local day, with a way back to the full session.

- Any logged set counts for the streak (R1), so a short day keeps it.
- The trainer never calls it lesser; the full session stays next.

API: `GET /schedule/short-session?minutes=10`.

## 4. The lock screen is the workout door

Every launch opens on the lock screen (Settings > Trainer > **Lock screen on launch** turns it
off). It says what today is:

| Today | The lock screen says | Enter does |
|---|---|---|
| A training day | "Today: Push A · 4 moves", with **Start today's session** focused | starts the session on Train |
| Trained already | "Today's session is done ✓ Next: Push B" | opens Today |
| A planned rest day | "Rest day ✓ Recovery is part of the plan." | opens Today |
| No program yet | the hunter tile only | opens Today |

Clicking the hunter tile always opens Today.

## 5. Reminders at your time, and the tray

- With a usual time picked, today's workout reminder appears from **an hour before** it and
  names it ("Your 18:30 session is ready when you are: Push A"); the opt-in evening check
  waits until an hour after it. Without a time, the reminder works as in v1.3.
- Still at most two a day, none on a rest day, no loss words (D2, D5, R6).
- **Keep ASCEND in the tray** (off by default): closing the window keeps ASCEND next to the
  clock, so reminders still arrive. The tray menu opens ASCEND, starts today's workout or
  quits. **Start with Windows** (off by default) registers the installed app as a login
  item; a development run never does.

The renderer hands the two switches to the Electron shell over `desktop:habits` (two strict
booleans, validated in main); tray picks come back on `tray:action`. See the
[IPC contract](../contracts/ipc-contract.md).

## 6. Design check

| Rule | How the habit engine keeps it |
|---|---|
| D2 no loss framing | Reminder copy is invitation only; the R6 tests check the words. |
| D4 autonomy | Days, time, tray, start with Windows and the lock screen are all your choice; the program only suggests days. |
| D5 calm notifications | Two a day at most, none on rest days, tray and start with Windows opt-in. |
| D9 offline | Everything is local; nothing here needs the internet or the AI. |
| D11 fewer screens | No new page: Settings, Today, the Planner, Train and the lock screen. |

Not built yet (review 2.2 and M3): quiet hours, backing off after three ignored reminders,
and suggesting a full session after three short ones in a row.

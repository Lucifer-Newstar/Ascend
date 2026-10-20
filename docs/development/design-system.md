# Design system (v5, "System" palette)

ASCEND's look follows the design research in the v5 redesign: navy-black surfaces, one
saturated **System blue** used sparingly, **arcane violet** for XP and levels, and status
colours that each mean one thing. The tokens live in `apps/desktop/src/index.css`
(`@theme static` for dark, `:root[data-theme="light"]` for light).

## Rules

1. **System blue is for System UI and interactive chrome** (buttons, focus rings, the active
   nav item, System windows). It is never a data status.
2. **One meaning per status colour**, shared by the muscle map, its legend, hover cards and
   the "ready to train" pulse:

   | Status | Token |
   |---|---|
   | Over-reached | `--color-bad` |
   | Recovering | `--color-warn` |
   | Under-trained | `--color-under` (indigo, distinct from System blue) |
   | Optimal / ready | `--color-good` |
   | No data | `--color-nodata` |

   The map reads these from `STATUS_TOKEN` in `src/lib/muscleMap.ts`; a ready muscle pulses
   with an outline in `READY_TOKEN` (`--color-good`), and the legend shows the same token.
3. **XP and levels are violet** (`--color-xp`); PRs and titles are gold (`--color-gold`).
4. **Ranks** have their own tokens (`--color-rank-e` … `--color-rank-s`). A rank badge always
   shows its letter as text and has an accessible name, so rank is never colour-only.
5. **Light theme keeps the shapes and drops the glow**: white panels, borders instead of
   glows, darker accents for contrast.

## Contrast

Every text token (ink, muted, faint, accent, xp, good, warn, bad, under, gold and the six
rank colours) is at least **4.5:1** against `bg`, `panel`, `panel-2` and `panel-3` in both
themes, and `on-accent` text on the accent is at least 4.5:1. Input borders
(`--color-line-input`) are at least 3:1 against panels. `src/lib/tokens.test.ts` reads
`index.css` and asserts all of this with the WCAG formula, so a token change that breaks
contrast fails the test suite.

One deliberate deviation from the research values: the light `--color-line-input` is
`#71839f` instead of `#7a8ca8`, because the latter is 2.98:1 on `panel-2`.

## Typography

| Role | Utility | Font, size/line, weight |
|---|---|---|
| Display XL (level number, big stat) | `text-display-xl` | Rajdhani 48/52, 600 |
| Display L (page titles) | `text-display-l` | Rajdhani 32/36, 600 |
| Window header (`[ DAILY QUEST ]`, stat labels) | `card-title` | Rajdhani 14/20, 600, uppercase, +0.08em |
| H2 (card titles) | `text-h2` | Inter 20/28, 600 |
| H3 | `text-h3` | Inter 16/24, 600 |
| Body | default | Inter 14/22, 400 |
| Small (captions, axes) | `text-small` | Inter 12/18, 500 |
| Numbers | default | tabular figures everywhere |

Only the Latin and Latin Extended font files are bundled.

## Radii, elevation and motion tokens

`--radius-sm` 6 px (chips), `--radius-md` 10 px (buttons, inputs), `--radius-lg` 14 px
(cards). `--shadow-panel` for cards, `--shadow-system` for System windows. Motion uses
`--ease-out` and `--dur-fast` 150 ms / `--dur-base` 220 ms / `--dur-slow` 600 ms; see
[motion.md](motion.md).

## The System window

`components/SystemWindow.tsx` is the one "Solo Leveling" surface, and it is **reserved for
System events**:

| Event | Where | Variant |
|---|---|---|
| Daily quest | Today | `quest` |
| Level up / rank up | top-right notice, any page (`SystemEvents`) | `levelup` |
| Quest complete | top-right notice, any page (`SystemEvents`) | `quest` |
| Skill acquired | modal after the set that unlocked a step (`SkillAcquired`) | `skill` |
| Deload recommended | Coach (and Today) | `warning` |

Everything else (forms, lists, charts, settings) is a normal `card`. Scarcity keeps the
window special.

- **Look:** glass fill (`--color-system-glass`), a 1 px border in the window accent at 45%,
  a soft inner glow, four 8 px corner brackets and a header like `[ DAILY QUEST ]`
  (the brackets are hidden from screen readers; the accessible name is the title).
- **Accent:** `warning` is amber, `levelup` is violet; `notice`, `quest` and `skill` follow
  the rank: E-C System blue, B-A arcane violet, S crimson. Only System UI changes with rank.
- **Motion:** 220 ms entrance (scale 0.98 → 1 and fade) and one 600 ms scan line. With
  Reduce motion it is a 120 ms fade and the scan line is not rendered.
- **Modal** windows (`modal`) trap focus, close on Esc or a backdrop click, and return focus.
  Notices are non-modal regions announced through a polite live region, and close on Esc,
  with their button, or by themselves after 7 seconds (not while hovered or focused).
- **Light theme:** white glass, a firmer border, no glow and no blur.

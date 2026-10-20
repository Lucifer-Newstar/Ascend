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

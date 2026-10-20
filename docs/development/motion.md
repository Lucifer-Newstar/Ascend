# Motion and interaction

ASCEND uses a little motion to make progress feel earned and the muscle map feel
physical. The rules: **quick, quiet, compositor-only, and optional.**

## Principles

- **Transform and opacity only.** Every keyframe in `apps/desktop/src/index.css`
  animates `transform` and/or `opacity`, so it runs on the compositor and never forces
  layout. Two deliberate exceptions, both on small SVGs: the muscle map's colour
  blend (`fill`, 650 ms, only when the view or range changes) and the rings'
  `stroke-dasharray` fill.
- **Short.** 150-900 ms. The only loops are the skeleton shimmer, the streak flame and
  the "ready to train" pulse on the muscle map.
- **No re-render per frame.** The muscle map tilt writes CSS variables from a
  `requestAnimationFrame`; React re-renders only when the hovered muscle changes.
  Count-ups re-render the number span only.
- **Reduced motion is a first-class mode.** `useReducedMotion()` (`src/lib/motion.tsx`)
  is true when the OS asks for it (`prefers-reduced-motion`) or the user turns on
  Settings → *Reduce motion* (stored by the sidecar as `reduce_motion`). CSS follows the
  same two switches. Decoration that only exists to move (confetti, flash, "+XP"
  floats) is not rendered; information is never carried by motion alone.
- **Offline.** No animation library and nothing fetched: CSS keyframes, SVG filters and
  a few lines of React.

## What moves, and where the idea came from

| Piece | What it does | Inspired by |
|---|---|---|
| Muscle map: recovery colours, "ready to train" pulse | Status colours (Recovery view); muscles trained this week and recovered again breathe gently | Fitbod's recovery map, a heat map of fatigue per muscle that tells you what is fresh ([Fitbod help: Muscle Recovery](https://help.fitbod.me/hc/en-us/articles/360006269014-Muscle-Recovery), [Fitbod blog](https://fitbod.me/blog/muscle-recovery/)) |
| Muscle map: Volume view, 1/7/30 days | Heat ramp by share of sets in the window, colours blend when the range changes | Hevy's muscle distribution body and chart, sets per muscle over a chosen period ([Hevy: Muscle Distribution](https://www.hevyapp.com/features/training-chart/)) |
| Muscle map: hover lift and click-through | The hovered muscle scales up on its own box and a card shows sets, volume and last trained; a click opens the drill-down | MuscleWiki's clickable body, where picking a muscle is the way in ([musclewiki.com](https://musclewiki.com/)) |
| Muscle map: tilt, depth, flip | A few degrees of perspective tilt towards the cursor, per-muscle SVG lighting (soft "pillow" shading) and a floor shadow; front/back flips as a card | Polished card-style fitness UIs such as Gymshark Training; kept to 5° so it reads as depth, not a toy |
| Rings, XP bar, count-ups, level-up | Rings draw in, numbers count up, the XP bar slides and sheens on new XP, a level-up gets a short confetti burst and a "Level up!" pill | Apple Fitness rings and their closing celebrations ([Apple Newsroom](https://www.apple.com/newsroom/2025/04/get-active-with-apple-watch/)) |
| Set logged, streak flame, skeleton shimmer, page transitions, card hover | Small confirmations and continuity | General platform conventions |

No artwork, icons or code were taken from these products. Body artwork is
react-muscle-highlighter (MIT, see the README credits).

## Building blocks

- `src/lib/motion.tsx`: `useReducedMotion`, `useOsReducedMotion`, `useCountUp`, `CountUp`.
- `src/components/Celebrate.tsx`: `Confetti`, `Flash`, `useRise` (detects a rise in a
  value), `Transient` (shows something for a moment after a change).
- `src/components/MuscleFigure.tsx`: the 3D figure (tilt, flip, filters, hover).
- `src/components/XpBar.tsx` / `XpChip.tsx`: the Dashboard bar and the header chip.
- CSS classes: `page-enter`, `card-hover`, `card-lift`, `skeleton`, `pop-in`,
  `float-up`, `flame`, `panel-in` / `panel-out`, `set-row-in`, `motion-decor`.

## Checking it

- `npm test -w apps/desktop` covers reduced motion for the hook, count-ups, the XP bar
  and chip, the set-logged float, the drill-down close and the map tilt.
- In the running app, a sweep of the cursor across the map, a flip and a range change
  held 16.7 ms frames in headless Chromium (no frame over 50 ms). Repeat on real Windows
  hardware before a release; headless Chromium is not a GPU.

# Accessibility checklist (desktop renderer)

> Owner: Dhanush. Target: **WCAG 2.2 AA** in both themes. Every new screen or component
> goes through this list before its PR is opened.

## What the app guarantees

| Area | How |
|---|---|
| **Contrast** | Text tokens (`ink`, `muted`, `faint`) and status colours (`accent`, `xp`, `good`, `warn`, `bad`) meet 4.5:1 on `bg`, `panel` and `panel-2`, separately for dark and light (`src/index.css`). Don't put body text in a colour that isn't a token. |
| **Keyboard** | Every action is a real `<button>`, link or form control. Forms submit on Enter (the set logger too). `Ctrl+1`…`Ctrl+8` open pages in sidebar order; `Alt+←/→` go back/forward; `Esc` closes the muscle drill-down. The list is in Settings → Keyboard shortcuts. |
| **Focus** | Visible `:focus-visible` ring everywhere. The first `Tab` shows **Skip to content**. Changing page moves focus to the page `<h1>`; opening a detail panel moves focus into it. |
| **Screen readers** | Page title follows the page (`Progress · ASCEND`). Toasts use two live regions: errors are `role="alert"` (assertive, 7 s, dismissable), the rest `role="status"`. Charts are `role="img"` with a summary plus a **Show the numbers** table. The muscle-map artwork is `aria-hidden`; the lists beside it (Needs attention, All muscles) carry the same information and open the drill-down. |
| **Motion** | `prefers-reduced-motion: reduce` stops ring/XP fills, spinners and skeleton pulses. |
| **Forms** | Every input has a visible `<label>` (or `legend` for radio groups such as `Segmented`). Errors are shown as text next to the form with `role="alert"`, not only by colour. |

## How it is checked

- **Component tests:** `expectNoAxeViolations(container)` from `src/test/axe.ts` runs axe-core
  on the rendered component (contrast is off there because jsdom does not paint). Used by the
  Import & export page, Settings and the app shell; add it to every new page test.
- **Real app, both themes:** axe-core with colour contrast, run with Playwright against
  `vite preview` + the sidecar on every page in dark and light. On 2026-10-20 all 16
  page/theme combinations were clean after this pass (before it: faint text at 2.6:1, warn on
  white at 2.0:1, XP chips at 3.8:1, and `aria-label` on the muscle-map `<path>`s).
- **By hand, once per release:** Windows Narrator over onboarding → log a set → Progress, and
  Windows contrast themes (high contrast) to make sure nothing disappears.

## Known gaps

- The body-map regions themselves are mouse-only; keyboard and screen-reader users use the
  muscle lists instead.
- No high-contrast theme of our own yet; Windows forced colours are only spot-checked.

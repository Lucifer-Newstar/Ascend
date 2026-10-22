# Bundled exercise data

`free_exercise_db.json` is a trimmed copy of `dist/exercises.json` from
[free-exercise-db](https://github.com/yuhonas/free-exercise-db) (retrieved 2026-10-20).

- **Licence:** the Unlicense, a public-domain dedication (checked in the repository's
  `LICENSE.md` and GitHub's licence metadata on 2026-10-20). No attribution is required;
  we credit the project anyway.
- **Kept fields:** id, name, category, equipment, force, level, mechanic, primary and
  secondary muscles, instructions, and the file name of the first image.
- **Images:** the first image of each exercise, resized to 320 px wide (320x213) and stored
  as webp (quality 55) in `apps/desktop/public/exercises/`: 873 files, 5,307,910 bytes
  (about 5.1 MiB) in total, re-fetched 2026-10-22. Three source exercises ship no image
  (Kettlebell Halo, Kettlebell Halo with Overhead Extension, Kettlebell Overhead Triceps
  Extension).
- **Similar-movement pictures:** 14 of ASCEND's own entries reuse the photo of the same or a
  closely related movement (`IMAGE_STANDINS` in `../library.py`, applied by Alembic 0017);
  the detail view says so. Entries with no fitting photo (levers, planche, flags, martial
  arts, meditation...) and custom exercises get a designed tile in the renderer
  (`apps/desktop/src/components/ExerciseArt.tsx`), never an empty box.
- **Rebuild:** `python scripts/build_exercise_library.py` (needs network access once).

The mapping onto ASCEND's 19 muscle regions, sections and movement patterns is in
`../library.py`; the data migration that loads it is `../library_seed.py` (Alembic 0010).

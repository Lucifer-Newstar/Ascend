# Bundled exercise data

`free_exercise_db.json` is a trimmed copy of `dist/exercises.json` from
[free-exercise-db](https://github.com/yuhonas/free-exercise-db) (retrieved 2026-10-20).

- **Licence:** the Unlicense, a public-domain dedication (checked in the repository's
  `LICENSE.md` and GitHub's licence metadata on 2026-10-20). No attribution is required;
  we credit the project anyway.
- **Kept fields:** id, name, category, equipment, force, level, mechanic, primary and
  secondary muscles, instructions, and the file name of the first image.
- **Images:** the first image of each exercise, resized to fit 224x224 and stored as webp
  (quality 50) in `apps/desktop/public/exercises/`: 873 files, about 2.8 MB in total.
- **Rebuild:** `python scripts/build_exercise_library.py` (needs network access once).

The mapping onto ASCEND's 19 muscle regions, sections and movement patterns is in
`../library.py`; the data migration that loads it is `../library_seed.py` (Alembic 0010).

# Progress photos and share cards

Status: built in v1.1. Owner: Jegatheesan (sidecar), Dhanush (renderer).

## Progress photos

- **Where they live.** `<data dir>/photos/`, one file per photo, named `<date>-<random>.jpg|png`. The database row
  (`progress_photos`, migration 0025) holds the date, pose (front, side, back, other), an optional note and the size.
  Nothing is uploaded; there is no sync.
- **Metadata.** The renderer re-encodes every photo through a canvas before sending it (a canvas writes no EXIF), and the
  sidecar strips metadata again on arrival without decoding the image (`app/modules/photos/strip.py`): every JPEG APPn
  segment except JFIF and Adobe, every comment, and every PNG chunk that is not needed to draw the picture. So camera
  model, serial number, GPS position and capture time never reach the data folder. Export saves the stored file, which
  is already clean.
- **Thumbnails.** The gallery shows photos blurred until you choose to reveal them, so the Profile page is safe to open
  with someone looking over your shoulder.
- **Backups.** `.ascendbak` backups carry the photos under `photos/`, each with its checksum in the manifest. Restore puts
  them back; a photo with a bad name or checksum is skipped instead of failing the restore.
- **Erase.** "Start fresh" and Settings > Erase my data delete the rows and the folder.
- **Reminder.** The trainer reminds you once a month (the watcher's `photo_reminder` rule, through the content selector).

## Optional AI feedback on photos

Off by default. It runs only when all of these hold:

1. the user turned on **Progress photo feedback** in Settings;
2. the profile age is 18 or over (under 18 the switch reads as off and the API refuses);
3. the local vision model (`qwen3-vl:2b` by default, `ASCEND_VISION_MODEL` to change) answers on localhost.

The prompt asks for visible changes in posture, definition and symmetry and one training focus, and forbids numbers,
body-fat or weight estimates, comments on looks, skin, face or private areas, and medical claims. The reply then passes
a guard (`vision.guard`) that drops every sentence with a digit, a percent sign or a word about fat, weight, calories,
diet or attractiveness, keeps at most three sentences, and falls back to a neutral line when nothing is left. The answer
is labelled as AI in the UI.

## Share cards

`POST /share/card` turns an achievement (the `share` object on a trainer message: PR, skill step, streak, boss, finished
block, rank) into a title, headline, detail line and caption (`share-v1`, deterministic, no AI). Only the achievement goes
in: never body weight, measurements, photos, age or the name on the profile.

The renderer draws the card on a canvas. From there:

- **Save image**: Electron's save dialog writes the PNG where you choose.
- **Copy**: the image and the caption go to the clipboard.
- **Post on X**: opens X's own post composer (`https://x.com/intent/tweet?text=...`) in the browser through the
  allowlisted `openExternal`; you post it yourself.
- **Instagram**: there is no desktop posting API, so the image is saved and the caption copied for you to paste.

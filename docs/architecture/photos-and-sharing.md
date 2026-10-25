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
- **Reminder.** Off by default (v1.3). With **Settings > Privacy & photos > Monthly photo reminder** on, the trainer
  suggests a photo once a month (the watcher's `photo_reminder` rule, through the content selector).

## No AI judging photos (v1.3)

v1.1 had an optional local AI comparison of two photos. v1.3 removed it (review decision 4):
judging a body from a photo does not help training and can hurt. `photos/vision.py`,
`POST /photos/feedback`, `GET /photos/feedback/status`, the `photo_feedback` setting and the
vision model entry in AI setup are gone. Compare two photos side by side on Profile; asked to
rate a physique, the trainer says it does not rate bodies or photos.

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

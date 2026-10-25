# Trainer character art: provenance

## Character

**Name:** Instructor Iskra Vey ("Iskra" is a Slavic word for "spark").

A web search on 2026-10-22 for "Iskra Vey" (with and without "anime"/"game character") returned no results, and "Instructor Iskra" returned only unrelated real-world fitness and judo instructors. No existing fictional character with this name was found. An earlier candidate, "Instructor Vael", was dropped because it already appears in several web novels.

## Design brief

Iskra Vey is the hunters' veteran drill instructor and ASCEND's in-app coach. She is a woman in her mid-30s with a lean, athletic build and a strong jaw. Her ash-silver hair is cut in an undercut: the left side is shaved, and the longer top sweeps over to one side with a single teal streak at the front. She has sharp, narrow amber eyes and a thin pale scar across her right eyebrow. She wears a charcoal high-collar tactical coat with teal piping, a small glowing cyan hexagon rank insignia on the collar, and black fingerless training gloves. Her default pose is arms crossed. Her manner is stern but encouraging: she appraises before she praises, warns plainly, and celebrates hard when you earn it. The art uses clean modern anime cel-shading (hard-edged two-tone shading, crisp lineart, cyan rim light) to sit on the app's dark navy "system window" UI. The design was written from scratch for this project. It does not reference any existing franchise, character or artist, and no such names were used in any prompt.

Expression set (all at the same head-and-shoulders framing):

| File | State | Pose |
|---|---|---|
| trainer-neutral | calm, appraising (main portrait) | arms crossed |
| trainer-proud | small approving smile | arms crossed |
| trainer-warning | stern frown | open palm raised in a "stop" gesture |
| trainer-hyped | fierce grin | fist raised, with cyan sparks around the fist |

## How the art was made (2026-10-22)

**Image model:** a commercial text-to-image model, called through a hosted image API. One text-to-image endpoint made the main portrait and one image-edit endpoint made the expressions. All requests used 1024x1024 output, a transparent background, high quality, PNG output, and 2 candidates per request.

1. **Main portrait (text-to-image).** Two candidates were generated, and the second was chosen as the canonical reference: it had the calmer face and a cleaner scar. The other candidate was rejected.
   The prompt asked for the scar on the left eyebrow, but the model placed it on her right eyebrow. The design was adopted as rendered, and all later edits keep it on the right.
2. **Expressions (image edit).** Each expression was produced by the edit endpoint with the chosen main portrait as its only reference image. Every prompt fixes the same face, hair, scar, outfit, style and framing, and changes only the expression and arm pose. The first hyped attempt drew the raised arm bare, without the coat sleeve, and the first warning attempt showed a bare forearm between the glove and a pushed-up sleeve. All candidates from both attempts were rejected. Each prompt was revised to require the full sleeve, and the revised versions were used. For each expression, the best of the two candidates from the accepted attempt was kept.
3. **Review.** Every candidate was inspected by eye at full size. Checks covered identity consistency, hands (five fingers on each visible hand), eyes, and stray text, logos or watermarks. Edges were checked composited on dark navy (#0b1220) and on white.
4. **Background removal.** None was needed. The model output native transparency. Alpha clean-up (Python/Pillow + NumPy): the model's fully opaque alpha is 254, so values ≥ 250 were snapped to 255, and values ≤ 8 were snapped to 0 (fully transparent pixels zeroed).
5. **Optimisation.**
   - 512x512 PNG: Pillow resize (premultiplied alpha, Lanczos), then pngquant 2.17 (`--quality 75-95 --speed 1 --strip`, 8-bit palette with alpha). Near-opaque palette alpha entries (≥ 245) were then set to 255 and the file re-saved with Pillow.
   - 256x256 WebP: Pillow/libwebp, lossy colour (quality 82) with lossless alpha (alpha_quality 90, method 6).
   - trainer-icon.webp: a 64x64 face crop of trainer-neutral, encoded the same way.
6. **Metadata.** None was written. The final PNGs contain only the IHDR, PLTE, tRNS, IDAT and IEND chunks: no tEXt, iTXt, zTXt, eXIf or C2PA (caBX) chunks. The WebPs contain only VP8X, ALPH and VP8 (no EXIF or XMP chunk). Checked with exiftool 12.57 and a chunk walk in Python.

### Exact prompts

**Main portrait (text-to-image):**

> Character portrait of an original character: a woman in her mid-30s with a lean athletic build and a strong jaw, short ash-silver hair in an undercut (shaved sides, longer swept top falling to the right) with one single teal streak at the front, sharp narrow amber eyes, a thin pale vertical scar crossing her left eyebrow, light tan skin, no makeup, no earrings. She wears a charcoal-grey high-collar tactical coat with thin teal piping along the collar edge and front seam, the stiff collar standing up to her jaw, and on the right collar tab a small glowing cyan hexagonal insignia (a plain hexagon with a smaller hexagon inside, no letters). Black fingerless training gloves. Expression: neutral, calm and appraising, a veteran drill instructor sizing up a recruit — mouth closed in a level line, eyes steady, brows slightly lowered. Arms crossed over her chest so the forearms and gloved hands show at the bottom of the frame, each hand with five fingers clearly drawn. Clean modern anime cel-shading: crisp dark lineart, two-tone shading with hard shadow edges, subtle rim light in cool cyan from the right, flat colours, no painterly texture. Head-and-shoulders bust portrait, centred, head and shoulders filling the frame with a little margin above the hair, cropped at mid-chest, body turned about 20 degrees to her left while her face and eyes look toward the viewer. Fully transparent background, no backdrop, no floor, no shadow behind her. No text, no letters, no logo, no watermark, no signature, no frame.

**Proud (edit, reference = main portrait):**

> Edit the reference image of the anime woman with short ash-silver undercut hair (shaved left side, long swept top falling to her left over the right side of the picture) with a single teal streak, narrow amber eyes, a thin pale diagonal scar across her right eyebrow (on the left side of the picture), light tan skin, charcoal-grey high-collar tactical coat with teal piping and a small glowing cyan hexagon insignia on the collar, black fingerless gloves. Keep her exactly the same person: identical face shape, eye shape and colour, hair cut, hair colour and teal streak position, scar position, skin tone, coat, piping, insignia and gloves. Keep the same clean anime cel-shading, the same line weight and colours, the same cyan rim light from the right, and the same head-and-shoulders camera framing, head size and position, cropped at mid-chest. Change only her expression and arm pose as follows: Proud: a small, restrained approving smile with the corners of her closed lips lifted slightly, eyes a little softened and brows relaxed, chin raised a touch, the look of a strict mentor quietly pleased with a recruit. Arms stay crossed over her chest as in the reference. Every visible hand has exactly five fingers, correctly jointed. Fully transparent background, no backdrop, no shadow. No text, no letters, no logo, no watermark, no added effects outside her silhouette.

**Warning, first attempt (rejected: bare forearm between glove and a pushed-up sleeve):**

> Edit the reference image of the anime woman with short ash-silver undercut hair (shaved left side, long swept top falling to her left over the right side of the picture) with a single teal streak, narrow amber eyes, a thin pale diagonal scar across her right eyebrow (on the left side of the picture), light tan skin, charcoal-grey high-collar tactical coat with teal piping and a small glowing cyan hexagon insignia on the collar, black fingerless gloves. Keep her exactly the same person: identical face shape, eye shape and colour, hair cut, hair colour and teal streak position, scar position, skin tone, coat, piping, insignia and gloves. Keep the same clean anime cel-shading, the same line weight and colours, the same cyan rim light from the right, and the same head-and-shoulders camera framing, head size and position, cropped at mid-chest. Change only her expression and arm pose as follows: Warning: a stern frown with brows drawn down and together, eyes narrowed and fixed on the viewer, lips pressed tight. Her right arm (on the left side of the picture) is raised in front of her chest with the gloved hand open, palm facing the viewer at shoulder height in a firm 'stop' gesture, fingers together and pointing up; her other arm rests across her waist. Every visible hand has exactly five fingers, correctly jointed. Fully transparent background, no backdrop, no shadow. No text, no letters, no logo, no watermark, no added effects outside her silhouette.

**Warning, used (edit, reference = main portrait):**

> Edit the reference image of the anime woman with short ash-silver undercut hair (shaved left side, long swept top falling to her left over the right side of the picture) with a single teal streak, narrow amber eyes, a thin pale diagonal scar across her right eyebrow (on the left side of the picture), light tan skin, charcoal-grey high-collar tactical coat with teal piping and a small glowing cyan hexagon insignia on the collar, black fingerless gloves. Keep her exactly the same person: identical face shape, eye shape and colour, hair cut, hair colour and teal streak position, scar position, skin tone, coat, piping, insignia and gloves. Keep the same clean anime cel-shading, the same line weight and colours, the same cyan rim light from the right, and the same head-and-shoulders camera framing, head size and position, cropped at mid-chest. Change only her expression and arm pose as follows: Warning: a stern frown with brows drawn down and together, eyes narrowed and fixed on the viewer, lips pressed tight. Her right arm (on the left side of the picture) is raised in front of her chest with the gloved hand open, palm facing the viewer at shoulder height in a firm 'stop' gesture, fingers together and pointing up, thumb relaxed at the side of the palm. The raised arm is fully covered by the charcoal coat sleeve from the shoulder down to the glove cuff, with teal piping at the cuff; no bare skin on the forearm or wrist, only the bare fingers of the fingerless glove; her other arm rests across her waist. Every visible hand has exactly five fingers, correctly jointed. Fully transparent background, no backdrop, no shadow. No text, no letters, no logo, no watermark, no added effects outside her silhouette.

**Hyped, first attempt (rejected: bare raised arm):**

> Edit the reference image of the anime woman with short ash-silver undercut hair (shaved left side, long swept top falling to her left over the right side of the picture) with a single teal streak, narrow amber eyes, a thin pale diagonal scar across her right eyebrow (on the left side of the picture), light tan skin, charcoal-grey high-collar tactical coat with teal piping and a small glowing cyan hexagon insignia on the collar, black fingerless gloves. Keep her exactly the same person: identical face shape, eye shape and colour, hair cut, hair colour and teal streak position, scar position, skin tone, coat, piping, insignia and gloves. Keep the same clean anime cel-shading, the same line weight and colours, the same cyan rim light from the right, and the same head-and-shoulders camera framing, head size and position, cropped at mid-chest. Change only her expression and arm pose as follows: Hyped: a fierce, confident open-mouth grin showing her upper teeth, eyes wide and intense, brows raised with energy. Her right arm (on the left side of the picture) is bent with the gloved fist raised beside her head at cheek height, knuckles toward the viewer, tightly clenched; her other arm rests across her waist. A few thin cyan energy sparks and a faint cyan glow trace the raised fist only. Every visible hand has exactly five fingers, correctly jointed. Fully transparent background, no backdrop, no shadow. No text, no letters, no logo, no watermark, no added effects outside her silhouette.

**Hyped, used (edit, reference = main portrait):**

> Edit the reference image of the anime woman with short ash-silver undercut hair (shaved left side, long swept top falling to her left over the right side of the picture) with a single teal streak, narrow amber eyes, a thin pale diagonal scar across her right eyebrow (on the left side of the picture), light tan skin, charcoal-grey high-collar tactical coat with teal piping and a small glowing cyan hexagon insignia on the collar, black fingerless gloves. Keep her exactly the same person: identical face shape, eye shape and colour, hair cut, hair colour and teal streak position, scar position, skin tone, coat, piping, insignia and gloves. Keep the same clean anime cel-shading, the same line weight and colours, the same cyan rim light from the right, and the same head-and-shoulders camera framing, head size and position, cropped at mid-chest. Change only her expression and arm pose as follows: Hyped: a fierce, confident open-mouth grin showing her upper teeth, eyes wide and intense, brows raised with energy. Her right arm (on the left side of the picture) is bent with the gloved fist raised beside her head at cheek height, knuckles toward the viewer, tightly clenched. The raised arm is fully covered by the charcoal coat sleeve all the way from the shoulder to the wrist, with teal piping at the cuff; no bare skin on the arm, only the bare fingers of the fingerless glove. Her other arm rests across her waist, also in the coat sleeve. Keep her lean build and shoulder width exactly as in the reference. A few thin cyan energy sparks and a faint cyan glow trace the raised fist only. Every visible hand has exactly five fingers, correctly jointed. Fully transparent background, no backdrop, no shadow. No text, no letters, no logo, no watermark, no added effects outside her silhouette.

## Licence status

- **Model provider terms.** The image model provider's terms of use say that, as between the user and the provider and to the extent permitted by law, the user owns the output, and that the provider assigns to the user all of its right, title and interest, if any, in the output. They also note that output may not be unique and other users may receive similar output (read 2026-10-22).
- **API platform terms.** The hosted API's terms of service say the customer owns its input. They require output to be used lawfully and without infringing third-party rights, state that output "may not be unique across users", and do not warrant that output is original or non-infringing. The platform claims no ownership of output in those terms (read 2026-10-22).
- **Copyright.** Purely AI-generated images may not be protected by copyright in some jurisdictions. For example, the US Copyright Office's position is that material generated by AI without sufficient human authorship is not copyrightable (https://www.copyright.gov/ai/). The human contribution here is the character design, the prompts, the selection and rejection of candidates, and the clean-up and compositing. Whether that is enough for protection is unsettled and varies by jurisdiction.
- **Project licence.** As far as any rights exist in these images, the project releases them under the repository's MIT licence, on the same terms as the code.
- **Similarity.** Because outputs may not be unique, similar images could in principle be produced for others. The design avoids imitating any existing character, but no formal similarity search against existing art was carried out.

## Files

The app ships only the 256 px `.webp` expressions and the 64 px icon (this folder). The 512 px PNGs and the contact sheet are release assets, not committed.

| File | Size (bytes) |
|---|---|
| contact_sheet.png | 338608 |
| trainer-hyped.png | 106501 |
| trainer-hyped.webp | 16100 |
| trainer-icon.webp | 2676 |
| trainer-neutral.png | 94914 |
| trainer-neutral.webp | 12200 |
| trainer-proud.png | 95355 |
| trainer-proud.webp | 12862 |
| trainer-warning.png | 96400 |
| trainer-warning.webp | 13922 |

Render cost: 6 requests × 2 candidates = 12 images at the provider's published rate of about $0.053 per 1024x1024 high-quality image, ≈ $0.63 (estimated).

---

# v1.1 roster and boss art

Date: 2026-10-23. The v1.1 trainer images in this folder and the boss images in `../bosses/` were generated for this project. No prompt named an existing franchise, character or artist.

## Common method

**Image model:** the same commercial text-to-image model and hosted image API as the first trainer: a text-to-image endpoint (trainer main portraits, bosses) and an image-edit endpoint (trainer expressions). All requests: 1024x1024, high quality, PNG output, 2 candidates per request. Trainer requests used a transparent background; boss requests used an opaque background. The v1.2 boss redraws (Iron Golem, Grave Warden and the four seasonal bosses) were made the same way and checked side by side against every other boss so no two share a creature type, shape and main colour.

**Style:** written to match the existing trainer (Instructor Iskra Vey, see `apps/desktop/src/assets/trainer/ART_PROVENANCE.md`): clean modern anime cel-shading, crisp dark lineart, hard-edged two-tone shading, cyan rim light from the right, flat colours, head-and-shoulders bust framing, transparent background.

**Trainer workflow:** one main (neutral) portrait per character by text-to-image; the proud, warning and hyped expressions by the edit endpoint with that main portrait as the only reference image. Each edit prompt restates the character's face, hair, outfit and style, keeps the framing, and changes only expression and arm pose. Every candidate was inspected at full size for identity consistency, hands (five fingers), eyes, stray text/logos, and modesty (fully clothed, no suggestive pose).

**Post-processing (Python/Pillow + NumPy):** alpha values ≥ 250 snapped to 255 and ≤ 8 to 0 (the model's opaque alpha is 254); premultiplied-alpha Lanczos resize to 256x256; WebP lossy colour quality 82, alpha_quality 90, method 6. Icons: a 64x64 face crop of the neutral portrait, encoded the same way. Bosses: Lanczos resize to 384x384, WebP quality 82 (no alpha). No metadata written.

## Name checks (web search, 2026-10-23)

The suggested names were searched with and without "anime"/"character" and replaced:

| Suggested | Result | Final name |
|---|---|---|
| Vera Nyx | Pen name of a published romance author (Amazon, Goodreads) and an Instagram creator | **Vera Kestrine** — no results for "Vera Kestrine" or "Vera Kestrine" character |
| Kai Arashi | Used by a manga creator on a creator platform and by game player characters; "Arashi" is also a well-known band | **Kai Hoshimura** — one unrelated result (a name list); none as a character |
| Dario Vance | Name of a recording artist, a fan-module NPC and chatbot characters | **Dario Halvorn** — no results |

Other candidates rejected after searching: Vera Solenne, Vera Kade, Vera Ashvale (real authors/artists), Kai Tenrai (fan-wiki character), Kai Renshiro (web-novel protagonist), Kai Ardent (musician), Dario Castellane (real person).

## Trainers

Iskra Vey is unchanged and remains the fourth choice.

### Vera Kestrine (`vera`)

Playful-confident hype coach, teasing but kind. Mid-20s, athletic. Long straight black hair with a violet streak, violet eyes, small silver studs. Cropped black/violet track jacket with cyan trim over a high-neck navy sports top, black fingerless gloves. Default pose: hand on hip, other hand on the jacket collar.

- Main portrait: 2 candidates; candidate 2 chosen (more modest top). Prompt (short): "Character portrait of an original character: a strikingly attractive, confident woman in her mid-20s with an athletic, fit build, long straight glossy black hair falling past her shoulders with one vivid violet streak through the front left strand, side-swept bangs, large bright violet eyes with sharp eyeliner-style lashes, a playful confident half-smirk, light warm skin, small silver stud earrings. She wears a …" + common style block.
- Proud: closed-lip delighted smile, eyebrow raised, same pose. Warning: unimpressed frown and pout, arms crossed. Hyped: open-mouthed cheer, right fist raised with cyan sparks.
- All expressions accepted on the first attempt.

### Kai Hoshimura (`kai`)

Charming, high-energy hype-man. Mid-20s, athletic. Tousled black hair, amber-gold eyes. Charcoal compression shirt under an open black jacket with cyan trim (sleeves pushed up), black wrist wraps. Default pose: arms crossed.

- Main portrait: 2 candidates; candidate 2 chosen. Prompt (short): "Character portrait of an original character: a handsome, charming man in his mid-20s with an athletic muscular build, tousled messy black hair with a few strands falling over his forehead, warm bright amber-gold eyes, an easy confident grin showing a hint of teeth, light tan skin, defined jaw, clean-shaven. He wears a fitted dark charcoal compression training shirt with a crew neck under an open black bomber-style …" + common style block.
- Proud: wide grin. Warning: stern, open palm raised in a "stop" gesture. Hyped: shouting cheer, fist pumped with cyan sparks.
- All expressions accepted on the first attempt. The hyped pose shows the forearm below the pushed-up sleeve, matching the main portrait.

### Dario Halvorn (`dario`)

Calm strategist / tactician. Early 30s, tall. Swept-back dark-brown hair, short beard, steel-grey eyes. Long navy tactical coat with violet piping and a glowing violet diamond collar insignia, worn open over a black training shirt, black tactical gloves. Default pose: hand at chin.

- Main portrait: 2 candidates; candidate 2 chosen. Prompt (short): "Character portrait of an original character: a tall, handsome, composed man in his early 30s with a lean athletic build, short neat dark-brown hair swept back with a slight wave, a short well-groomed dark beard, calm intelligent steel-grey eyes, olive skin, a strong brow. He wears a long dark navy tactical coat with a high stand-up collar and thin violet piping along the collar and front edge, worn open over a …" + common style block.
- Proud: subtle half-smile. Warning: cold stare, open palm "stop" gesture. Hyped: fierce grin, fist raised with violet sparks.
- All expressions accepted on the first attempt.

Edit prompt template (all expressions): "Edit the reference image of <character description>. Keep exactly the same person … same clean anime cel-shading … same head-and-shoulders camera framing. Change only the expression and arm pose as follows: <expression>. Every visible hand has exactly five fingers, correctly jointed. Tasteful, fully clothed. Fully transparent background … No text, no letters, no logo, no watermark."

## Bosses

Same cel-shaded style, menacing but not gory, bust/creature portrait on a dark navy background with cyan/violet particles and mist. Shared prompt block (short): "Menacing but not gory: no blood, no wounds, no gore. Clean modern anime cel-shading in the style of a dark fantasy game boss card … strong cool cyan rim light, glowing eyes … Square bust portrait … slightly low camera … Dark atmospheric background: deep navy-black gradient with faint drifting cyan and violet glowing particles and soft mist … No text."

| File | Name | Design (prompt, short) | Notes |
|---|---|---|---|
| `bosses/iron-golem.webp` | Iron Golem | a towering humanoid construct built from riveted dark gunmetal iron plates and heavy bolts, a blocky helm-like head with a narrow horizontal visor slit glowing bright cyan, glowing cyan seams and … | Re-rolled: first pass cropped the head at the top edge; the prompt was changed to require the whole head with space above. |
| `bosses/ash-wyvern.webp` | Ash Wyvern | a lean draconic wyvern with charcoal-black scales dusted with pale grey ash, glowing ember-orange cracks along its neck, swept-back horns, narrow glowing orange eyes, jaws half open showing sharp … | Best of 2 candidates, first pass. |
| `bosses/frost-colossus.webp` | Frost Colossus | a gigantic humanoid giant made of pale blue glacial ice and packed snow, jagged ice-crystal crown growing from its head, deep-set glowing icy-white eyes, frost beard of icicles, heavy shoulders … | Re-rolled: first pass cropped the ice crown; same prompt change. |
| `bosses/stone-basilisk.webp` | Stone Basilisk | a huge serpent-lizard with rough granite-grey scales like cracked stone, a crest of rocky spikes on its head, large glowing yellow-green slit-pupil eyes, mouth slightly open with fangs and a forked … | Best of 2 candidates, first pass. |
| `bosses/storm-chimera.webp` | Storm Chimera | a beast with the head of a dark-maned lion at the centre, a curling-horned goat head beside it and a serpent-headed tail rising over its shoulder, storm-grey fur, crackling blue-white lightning … | Best of 2 candidates, first pass. |
| `bosses/grave-warden.webp` | Grave Warden | a tall spectral knight in tarnished dark armour and a tattered black hooded cloak, the face inside the hood a dark void with two glowing pale-cyan eyes and a faint skull-shaped helm visor, a heavy … | Best of 2 candidates, first pass. |
| `bosses/crimson-ogre.webp` | Crimson Ogre | a hulking ogre with deep crimson-red skin, two thick curved horns, a heavy brow, glowing amber eyes, small tusks jutting from its lower jaw, a scowling snarl, a spiked iron collar and leather … | Best of 2 candidates, first pass. |
| `bosses/obsidian-hydra.webp` | Obsidian Hydra | a hydra with three serpentine dragon heads on long necks rising from one body, glossy black obsidian scales with sharp glassy edges catching cyan light, thin glowing violet fissures between the … | Best of 2 candidates, first pass. |
| `bosses/thunder-behemoth.webp` | Thunder Behemoth | an enormous horned beast like a colossal armoured bull-rhino, dark slate-blue hide with heavy plated armour on its head and shoulders, two great forward-curving horns, glowing electric-cyan eyes, … | Best of 2 candidates, first pass. |
| `bosses/venom-manticore.webp` | Venom Manticore | a manticore with a lion-like body and dark purple-black mane, a fierce lion-like monstrous face with glowing toxic-green eyes and sharp fangs, bat-like wings folded behind it, a huge segmented … | Re-rolled for stronger green venom and eyes. |
| `bosses/dusk-leviathan.webp` | Dusk Leviathan | a colossal sea serpent rising out of dark water at twilight, deep indigo and violet scales with glowing bioluminescent cyan spots along its body, finned frill around its head, long jaw with rows of … | Best of 2 candidates, first pass. |
| `bosses/bone-titan.webp` | Bone Titan | a gigantic armoured giant whose body is a stylised frame of bleached ivory bone plates and a horned skull-like helm, hollow eye sockets with bright glowing cyan lights inside, dark tattered banners … | Best of 2 candidates, first pass. |

## Files

Trainers (256x256 RGBA WebP; icons 64x64): `trainers/<id>-neutral.webp`, `-proud.webp`, `-warning.webp`, `-hyped.webp`, `-icon.webp` for `vera`, `kai`, `dario`.
Bosses (384x384 WebP): `bosses/<slug>.webp`.

## v1.2 art (October 2026)

All of the following is original art made for ASCEND and approved by the project lead
before it was added. None of it references an existing franchise, character or artist.

- **Trainers:** new half-body mood art (neutral, hyped, proud, warning) and icons for
  Iskra Vey (`trainer-*.webp`) and Vera Kestrine (`vera-*.webp`). They are 512 px on the
  app's navy background, so the trainer can be shown large on Today and in chat. Kai and
  Dario keep their v1.1 art.
- **Avatars** (`assets/avatars`): a male and a female hunter at the E, C, A and S stages.
  They are body-neutral: rank shows as gear and aura, never as body changes.
- **Cosmetics** (`assets/cosmetics`): 4 outfit sets (male and female), 4 relics, 4 pets
  and 4 weapons. Faith-flavoured looks carry neutral names and are optional.
- **Seasonal bosses** (`assets/bosses`): Harvest Colossus, Winter Wraith, Monsoon Serpent
  and Shadow Sovereign. Iron Golem and Grave Warden were redrawn; Bone Titan is unchanged.

## v1.3 trainers v2 (25 October 2026)

Approved by the project lead on 25 October 2026 before it was added. Iskra Vey
(`trainer-*.webp`) is unchanged and was the style reference. Vera, Kai and Dario were
redrawn so every face is clearly different (skin tone, face shape, hair, eyes, accessories,
accent colour, silhouette), and two new trainers join: Tara and Idris. The v1.1 and v1.2
notes above describe the art these files replace.

| id | look | accent | specialty label |
|---|---|---|---|
| `vera` | light freckled skin, copper curls with bangs, green eyes, gold hoops; coral high-neck crop top, open white track jacket, shaker bottle | coral | nutrition |
| `tara` | Indian, deep brown skin, black top-knot bun, almond eyes, small nose stud; lavender crew-neck top, yoga mat | lavender | flexibility, mobility, meditation, recovery |
| `kai` | Thai, golden tan, spiky black hair, red headband, nose bandage, eyebrow slit, light stubble; open sleeveless hoodie, red hand wraps | red | cardio and martial arts |
| `dario` | Mediterranean, olive skin, long wavy chestnut half-up hair, cleft chin, steel-grey eyes; black tank, wooden gym rings, chalk | emerald | calisthenics and skills |
| `idris` | Black, dark skin, shaved head, full beard, gold earring, hazel eyes; black tank, lifting belt, amber wraps, dumbbell | amber | gym and strength |

Method: the same commercial image model and image-edit endpoint as v1.1 and v1.2 (1024 x 1024,
transparent, high quality, 2 candidates). Each main portrait is an edit that uses Iskra's
v1.2 neutral art only as the style, line, shading and framing reference, with a written
brief for a new person. Follow-up edits on the chosen main: Vera's and Tara's tops changed
to high necklines, Kai made visibly older, Idris's muscle size reduced. Proud, warning and
hyped are edits of the chosen main that change only the expression and arm pose (proud:
thumbs-up; warning: open palm; hyped: raised fist with accent-colour sparks). No franchise,
character or artist names were used in prompts; there is no text or watermark.

Post-processing (Pillow and NumPy): alpha >= 250 set to 255 and <= 8 to 0; one crop window
per character (taken from its neutral and reused for every mood) so the head sits like
Iskra's; premultiplied-alpha Lanczos to 512 x 512 on the app's flat navy (10, 17, 30);
unsharp mask (radius 1, 45 %); WebP quality 88, method 6. Icon: head crop of the 1024
neutral to 128 x 128. Portrait: a 1024 window of the neutral on navy, not upscaled.

Files here, per id: `<id>-neutral.webp`, `-proud`, `-warning`, `-hyped` (512 px RGB),
`<id>-icon.webp` (128 px RGB) and `<id>-portrait.webp` (1024 px RGB, the Chat page's large
portrait; Iskra's Chat portrait is her 512 px neutral). Kai and Dario move from the old
256 px RGBA format to this one. The 1024 px transparent PNG masters are kept outside the
repository to keep it small.

The specialty is a label in the trainer picker and on the Chat page. Every trainer answers
everything; there is no routing of questions to a specialist.

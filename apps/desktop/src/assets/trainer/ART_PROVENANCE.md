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

**Image model:** GPT Image 2.5 (OpenAI), called through the fal.ai API. The endpoints were `openai/gpt-image-2.5/sunburst/text-to-image` (main portrait) and `openai/gpt-image-2.5/sunburst/edit` (expressions). All requests used 1024x1024 output, `background: "transparent"`, `quality: "high"`, PNG output, and 2 candidates per request.

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

- **Model provider terms (OpenAI).** The OpenAI Terms of Use say that, as between the user and OpenAI and to the extent permitted by law, the user owns the Output, and that OpenAI assigns to the user all of its right, title and interest, if any, in the Output. They also note that output may not be unique and other users may receive similar output. Source: https://openai.com/policies/row-terms-of-use/ ("Ownership of content", read 2026-10-22).
- **API platform terms (fal.ai).** fal.ai's Terms of Service say the customer owns its Input. They require Output Content to be used lawfully and without infringing third-party rights. They state that Output Content "may not be unique across users". They also state that fal does not warrant that Output Content is original or non-infringing. fal claims no ownership of Output Content in those terms. Source: https://fal.ai/legal/terms-of-service (read 2026-10-22).
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

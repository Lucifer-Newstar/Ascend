# ASCEND muscle map (bodyMapPaths.ts), v2

> v8 ships 54 keys (levator scapulae folded into the upper trapezius, coracobrachialis left out; ADR-0021).
> v2 redraws the v1 artwork with the same data interface, so no app code changed.

`build_map.py` draws ASCEND's front, back and deep-layer muscle map and writes
`bodyMapPaths.ts` (the app copy lives at `apps/desktop/src/lib/bodyMapPaths.ts`) plus preview PNGs
in `previews/` (not committed). Each muscle is its own fillable path, so the app colours it by
recovery or volume.

```sh
pip install shapely cairosvg numpy pillow
python3 scripts/body_map/build_map.py
cp scripts/body_map/bodyMapPaths.ts apps/desktop/src/lib/bodyMapPaths.ts
```

Set `V1_TS=<path to the v1 bodyMapPaths.ts>` to also render a v1/v2 side-by-side.

## Interface (unchanged from v1)

```ts
export interface MusclePath { key: string; view: "front" | "back"; layer: "surface" | "deep"; d: string; side?: "left" | "right" }
export const BODY_VIEWBOX = "0 0 200 430";          // same as v1, shared by both views
export const BODY_OUTLINE: { front: string; back: string };
export const MUSCLE_KEYS: readonly [...54 keys, same order as v1];
export const MUSCLE_PATHS: MusclePath[];
```

* The viewBox is unchanged: `0 0 200 430`, identical for both views. x = 100 is the midline.
* Same 54 keys, and every key keeps exactly the same view/layer assignment as v1 (checked by comparing
  the (key, view, layer) sets of both files: identical, 64 combinations). Same path count (128).
* One path per key per side. Muscles drawn as several bellies (rectus abdominis blocks, the two calf
  heads, wrist flexor/extensor bellies, rhomboid minor/major) are sub-paths of that one path.
* `side` is the subject's own side: in the front view the subject's right is on the viewer's left; in
  the back view the subject's right is on the viewer's right (same convention as v1).
* `BODY_OUTLINE` is now the whole silhouette (head, neck, torso, arms, hands, legs, feet), drawn
  underneath. The thin seams between muscles show the outline fill, which gives a quiet body silhouette
  under everything. The front and back outlines are the same shape.

## What changed from v1

* **Proportions.** A 7.5-head athletic figure: head 55.5 units of a 417-unit figure, shoulders about
  2.1 heads wide tapering to a narrower waist, elbows at the bottom of the rib cage, wrists at the
  crotch, knees at y 298. v1's head was small and the limbs were tubes and capsules.
* **Limbs are tapered shapes.** Arms and legs are built from a smooth axis plus a width profile, with a
  bulging deltoid, biceps and forearm, a narrow wrist, a quad sweep, a narrow knee, a calf bulge
  (higher on the outer side, lower on the inner side) and a slim ankle. Limb muscles are authored in
  limb coordinates, so they follow the taper.
* **Organic muscle shapes.** Tapered bellies drawn with smooth splines: a fan-shaped pec split into
  clavicular and sternal heads, a rounded deltoid cap with a V insertion, finger-like serratus slips,
  a trapezius kite (upper, middle, lower), a lat wing, rounded glutes, two calf heads with the soleus
  showing beside them and an open Achilles area. Tendon areas (knee, elbow, wrist, linea alba, Achilles)
  are left as body colour.
* **One seam width.** Muscles are carved in priority order with a fixed 1.1-unit seam and clipped to
  the silhouette, so gaps are even and nothing floats outside the body.
* **Deep layer in context.** The deep muscles sit over the full ghosted surface figure (the app draws
  surface paths at 0.35 opacity in deep mode). The psoas now emerges from under the transversus band,
  and the internal obliques sit on the upper flanks.
* **Smaller file.** 44.5 KB against v1's 99 KB (polyline paths simplified to 0.09 units,
  1-decimal coordinates).

## Colours

The app colours the map with its own muted tokens (`--color-map-*` in `apps/desktop/src/index.css`):
flat fills, about 35-50 % saturation, no glow.

## Small sizes (64 x 96 tiles)

At tile size the figure reads as a silhouette with the
highlighted group in the accent colour, and the seams merge. The tile check uses the map's
theme colours; `ExerciseArt` passes its own panel fill and border, which reads the same way.

## Compromises

* **subscapularis** is drawn in the front deep view, at the armpit just lateral to pec minor, where the
  front of the shoulder blade would be seen with the pectorals removed (same choice as v1).
* **transversus_abdominis** is a horizontal band across the abdomen and **internal_obliques** sit above
  it on the flanks. In reality both span the whole abdominal wall in layers.
* **gracilis** and the back-view **vastus_lateralis** are thin edge strips; **adductor_magnus** is a
  small upper-inner wedge in the back view. They are present and hoverable but small, as in most
  commercial maps.
* **levator scapulae** is part of `trap_upper` and **coracobrachialis** has no key (unchanged from v1).
* The figure is gender-neutral and stylised: no face, simple mitten hands with a thumb, simple feet.

## Keys (54)

Per view/layer: front/surface 26, back/surface 27, front/deep 6, back/deep 5.

| key | view/layer | where |
|---|---|---|
| `sternocleidomastoid` | front/surface | neck, mastoid to sternum |
| `trap_upper` | back/surface, front/surface | neck/shoulder slope (both views); includes the levator scapulae strip at the side of the neck |
| `deltoid_anterior` | front/surface | front of the shoulder cap |
| `deltoid_lateral` | back/surface, front/surface | outer shoulder cap (both views) |
| `pec_major_clavicular` | front/surface | upper chest, clavicle to humerus |
| `pec_major_sternal` | front/surface | mid/lower chest |
| `biceps_long` | front/surface | lateral half of the biceps |
| `biceps_short` | front/surface | medial half of the biceps |
| `brachialis` | front/surface | slivers either side of the lower biceps |
| `brachioradialis` | back/surface, front/surface | thumb-side top of the forearm (front), lateral strip (back) |
| `wrist_flexors` | back/surface, front/surface | inner forearm, two bellies separated by a short groove |
| `serratus_anterior` | front/surface | four slips on the side ribs below the armpit |
| `rectus_abdominis` | front/surface | abdominal column with three tendinous lines (one compound path per side) |
| `external_obliques` | back/surface, front/surface | sides of the abdomen (front), flank sliver (back) |
| `latissimus_dorsi` | back/surface, front/surface | sliver at the side (front); large wing (back) |
| `tensor_fasciae_latae` | front/surface | outer hip |
| `sartorius` | front/surface | strap from the front hip to the inner knee |
| `rectus_femoris` | front/surface | middle of the front thigh |
| `vastus_medialis` | front/surface | teardrop above the inner knee |
| `vastus_lateralis` | back/surface, front/surface | outer thigh (front; sliver in back) |
| `gracilis` | back/surface, front/surface | thin strap along the inner thigh (both views) |
| `adductor_longus` | front/surface | inner upper thigh |
| `tibialis_anterior` | front/surface | shin, lateral to the tibia |
| `fibularis` | front/surface | outer lower leg |
| `gastrocnemius` | back/surface, front/surface | inner calf edge (front); two heads (back) |
| `soleus` | back/surface, front/surface | lower calf sides (front); around the lower gastrocnemius (back) |
| `trap_middle` | back/surface | band across the shoulder blades |
| `trap_lower` | back/surface | lower V to mid-back |
| `splenius` | back/surface | upper back of the neck |
| `deltoid_posterior` | back/surface | rear shoulder cap |
| `infraspinatus` | back/surface | on the shoulder blade below its spine |
| `triceps_lateral` | back/surface | outer back of the upper arm |
| `triceps_long` | back/surface | inner/back of the upper arm |
| `teres_minor` | back/surface | thin strip below infraspinatus |
| `teres_major` | back/surface | below teres minor, toward the armpit |
| `wrist_extensors` | back/surface | back of the forearm, two bellies separated by a short groove |
| `erector_spinae` | back/surface | two columns along the lower spine |
| `gluteus_maximus` | back/surface | buttock |
| `gluteus_medius` | back/surface | upper outer buttock |
| `semitendinosus` | back/surface | inner hamstring (superficial) |
| `biceps_femoris` | back/surface | outer hamstring |
| `semimembranosus` | back/surface | inner hamstring edge, medial to/below semitendinosus |
| `adductor_magnus` | back/surface | inner back of the upper thigh |
| `pec_minor` | front/deep | under the upper pec, ribs 3-5 to the coracoid |
| `subscapularis` | front/deep | front deep view, at the armpit just outside the ribcage edge |
| `transversus_abdominis` | front/deep | horizontal band across the abdomen, below the internal obliques; the psoas emerges from beneath it |
| `internal_obliques` | front/deep | upper flanks, lateral to the rectus, above the transversus band |
| `iliopsoas` | front/deep | psoas from the lumbar spine plus the iliacus fan, converging through the groin to the inner femur |
| `vastus_intermedius` | front/deep | under rectus femoris |
| `supraspinatus` | back/deep | above the scapular spine |
| `rhomboids` | back/deep | between the spine and the shoulder blade, split into minor (upper) and major |
| `quadratus_lumborum` | back/deep | deep low back, lowest rib to pelvis, lateral to the spine |
| `gluteus_minimus` | back/deep | under gluteus medius |
| `triceps_medial` | back/deep | lower back of the upper arm, around the triceps tendon |

## How it was drawn

All shapes are hand-placed control points in `build_map.py`: centripetal Catmull-Rom splines for
outlines, a limb frame (axis + lateral/medial width profile) for arms and legs, and shapely for the
boolean carving, seams and clipping. Only the viewer's right half is authored; the left half is mirrored
around x = 100. Proportions follow the classic 7.5-head canon. While
authoring, the silhouette was overlaid once on Mikael Häggström's public-domain collage of Gray's Anatomy
plates (https://commons.wikimedia.org/wiki/File:Muscles_anterior_labeled.png, public domain) to check
landmark heights. Nothing was traced from it or from any app.

## Licence

The artwork (`bodyMapPaths.ts`, the preview PNGs) and `build_map.py` are original work created for the
ASCEND project and are released under the project's MIT licence. No third-party artwork is included.
The only reference consulted for placement (Häggström / Gray's Anatomy 1918) is in the public domain.

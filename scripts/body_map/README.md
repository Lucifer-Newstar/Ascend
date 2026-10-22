# ASCEND muscle map (bodyMapPaths.ts)

> In the repo: the generator lives here; its TypeScript output is committed as
> `apps/desktop/src/lib/bodyMapPaths.ts`. Run `python3 scripts/body_map/build_map.py --no-png`
> and copy `scripts/body_map/bodyMapPaths.ts` over it. Preview PNGs are not committed.
> v8 ships 54 keys (levator scapulae folded into the upper trapezius, coracobrachialis left out; ADR-0021).

An original, hand-authored anatomical muscle map for the ASCEND desktop app:
front view, back view and a deep layer, with every muscle a separately fillable
SVG path so its colour can show recovery state.

## Files

| File | What it is |
|---|---|
| `bodyMapPaths.ts` | Generated TypeScript data module (no React dependency), 99 KB |
| `build_map.py` | The generator: all shapes are defined here. Edit and re-run |
| `front.png`, `back.png` | Surface views, dark theme (left) and light theme (right), sample recovery colours |
| `deep_front.png`, `deep_back.png` | Deep layer drawn on top of a ghosted surface figure |
| `check_labels.png` | Every region in a distinct colour with its key next to it (4 panels) |
| `tile_check_1x.png`, `tile_check_x4.png` | The front view at 64 x 96 px with a few muscles highlighted (actual size and 4x zoom) |

Re-generate: `python3 build_map.py` (needs `shapely`, `cairosvg`, `pillow`).
`python3 build_map.py --no-png` writes only the TypeScript file.

## Data shape

```ts
export interface MusclePath { key: string; view: "front" | "back"; layer: "surface" | "deep"; d: string; side?: "left" | "right" }
export const BODY_VIEWBOX = "0 0 200 430";               // shared by both views
export const BODY_OUTLINE: { front: string; back: string }; // silhouette, drawn underneath
export const MUSCLE_KEYS: readonly string[];             // the 54 keys, in drawing order
export const MUSCLE_PATHS: MusclePath[];                 // 128 paths
```

Rendering order: `BODY_OUTLINE[view]`, then the `surface` paths of that view. For the
deep layer, draw the surface paths ghosted (e.g. opacity 0.3, neutral fill) and then the
`deep` paths of that view on top. Deep muscles sit in their true anatomical position, so
they line up with the ghosted surface.

## Coordinate system

* One viewBox for both views: `0 0 200 430` (about 1 : 2.15, so it fits 260 x 560 or
  300 x 640 with `preserveAspectRatio="xMidYMid meet"`).
* `x = 100` is the body midline. y grows downward: top of head about y 6, chin 56,
  shoulders 85, navel level 162, crotch 220, knees about 308, soles 425.
* `side` is the subject's own side. In the front view the subject's right is on the
  viewer's left (x < 100); in the back view the subject's left is on the viewer's left.
* Pose: relaxed anatomical stance, arms slightly away from the body, palms forward.
  The silhouette is the same for both views.
* Some keys use one compound path per side (several `M...z` subpaths), e.g. the
  rectus abdominis segments, the serratus slips, the two gastrocnemius heads and the
  brachialis slivers. Fill them as one region.

## How it was drawn

1. Each muscle is a closed Catmull-Rom spline (equivalent to a chain of cubic Beziers)
   through hand-placed control points on one side of the body. Arm muscles are placed in
   a local frame along the upper arm and forearm bones (distance along the bone, offset
   from it), so they follow the arm's angle.
2. Shapes are clipped to the body silhouette, inset 0.7 units, so a thin rim of the
   silhouette shows around the figure.
3. Muscles are placed in a fixed order. Each one is trimmed against the ones placed before
   it with a constant 0.85-unit gap, so neighbours share clean borders. Some groups (the
   trapezius thirds, the pectoral heads, the deltoid heads, the posterior thigh) are drawn
   as one mass and then cut into regions. This keeps the gaps consistent.
4. Each finished shape is mirrored around x = 100. The figure is exactly symmetric.
5. The outlines are written out again as compact relative cubic Bezier path data (`c`/`s`).
   Sharp corners are kept where muscles meet, and coordinates are rounded to 0.1.

Muscle positions follow standard textbook anatomy: origins, insertions and the usual
surface relief, as described in standard anatomy texts, e.g. the public-domain
*Gray's Anatomy* (20th ed., 1918). No existing drawing, app artwork or SVG was traced or
copied, and none was used as a base. All coordinates are hand-placed in `build_map.py`.

### Choices worth knowing

* **subscapularis** is drawn in the **front deep view**, at the armpit, lateral to pec minor and just
  outside the ribcage edge. This is the part of the front of the shoulder blade you would see with the
  pectorals removed. It reads better there than as a hidden region on the back.
* **transversus_abdominis** is drawn as a horizontal band across the lower abdomen. **internal_obliques**
  wraps around the band's ends on the flanks. In reality both span the whole abdominal wall.
* **vastus_intermedius** is drawn slightly wider than rectus femoris, which covers it.
* Optional surface keys that were drawn: latissimus_dorsi sliver (front), gastrocnemius inner-calf edge
  (front), external_obliques flank sliver (back). Also brachioradialis and wrist_flexors edges and a
  vastus_lateralis sliver in the back view, plus gracilis in both views.
* The levator scapulae strip at the side of the neck is drawn as part of **trap_upper**. Coracobrachialis
  has no key: that part of the inner upper arm is left as outline.

### Small sizes (64 x 96 tile)

At tile size the 0.85-unit gaps are below one pixel, so the figure reads as a silhouette with
highlighted regions (see `tile_check_x4.png`). For tiles:
* Draw `BODY_OUTLINE` with a 1 px stroke using `vector-effect="non-scaling-stroke"`, so the
  outline stays legible at any scale.
* Give non-highlighted muscles a neutral fill close to the body colour. Use the accent only
  for the few muscles you want to highlight.

## Keys (54)

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
| `wrist_flexors` | back/surface, front/surface | inner forearm (front), medial strip (back) |
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
| `wrist_extensors` | back/surface | back of the forearm |
| `erector_spinae` | back/surface | two columns along the lower spine |
| `gluteus_maximus` | back/surface | buttock |
| `gluteus_medius` | back/surface | upper outer buttock |
| `semitendinosus` | back/surface | inner hamstring (superficial) |
| `biceps_femoris` | back/surface | outer hamstring |
| `semimembranosus` | back/surface | inner hamstring edge, medial to/below semitendinosus |
| `adductor_magnus` | back/surface | inner back of the upper thigh |
| `pec_minor` | front/deep | under the upper pec, ribs 3-5 to the coracoid |
| `subscapularis` | front/deep | front deep view, at the armpit just outside the ribcage edge |
| `transversus_abdominis` | front/deep | horizontal band across the lower abdomen |
| `internal_obliques` | front/deep | sides of the abdomen, wrapping the end of transversus |
| `iliopsoas` | front/deep | lumbar spine / iliac fossa through the groin to the inner femur |
| `vastus_intermedius` | front/deep | under rectus femoris |
| `supraspinatus` | back/deep | above the scapular spine |
| `rhomboids` | back/deep | between the spine and the shoulder blade |
| `quadratus_lumborum` | back/deep | deep low back, lowest rib to pelvis, lateral to the spine |
| `gluteus_minimus` | back/deep | under gluteus medius |
| `triceps_medial` | back/deep | lower back of the upper arm, around the triceps tendon |

Per view/layer: front/surface 26, back/surface 27, front/deep 6, back/deep 5.

## Licence

The artwork (`bodyMapPaths.ts`, the preview PNGs) and `build_map.py` are original work created for the
ASCEND project. They are released under the project's MIT licence. No third-party artwork is included.

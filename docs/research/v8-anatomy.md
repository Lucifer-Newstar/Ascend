# ASCEND v8 research: anatomy for the detailed muscle map

> **Build decision (2026-10-22):** the app ships **54 keys**. Following §2 of `v8-anatomy.md`, levator scapulae is folded into `trap_upper` and coracobrachialis is left out; the rules file the app reads (`services/sidecar/app/modules/workouts/library_data/muscle_rules.json`) is this document's table with those two keys folded the same way. See ADR-0021.

Status: research document for the v8 build. Date: 2026-10-22.
Companion: `v8-exercise-muscle-mapping.md` (how exercises load these muscles) and `v8-exercise-muscle-rules.json`.

Source marks: **[abstract read]** = study abstract read; **[snippet]** = only a search snippet seen; **[unverified]** = the author's inference. Anatomy lines (origin, insertion, action) come from openly accessible references read on 2026-10-22: OpenStax *Anatomy and Physiology 2e*, chapter 11 (CC BY 4.0, sections 11.3-11.6 read), and the Wikipedia infoboxes for each muscle (a last-resort source, used because they give origin and insertion in one line and could be read for all 56 muscles in one pass). Muscle volumes come from the full text of Holzbaur et al. 2007 (MRI, 10 adults).

## 1. The final muscle list

The owner's list is the minimum. The build uses these keys (d = deep or mostly hidden):

- **Chest (4):** pec_major_clavicular, pec_major_sternal, pec_minor (d), serratus_anterior
- **Back (13):** latissimus_dorsi, trap_upper, trap_middle, trap_lower, rhomboids (d), teres_major, teres_minor, infraspinatus, supraspinatus (d), subscapularis (d), erector_spinae, quadratus_lumborum (d), levator_scapulae (d)
- **Neck (2):** sternocleidomastoid, splenius
- **Shoulders (3):** deltoid_anterior, deltoid_lateral, deltoid_posterior
- **Arms (10):** biceps_long, biceps_short, brachialis, coracobrachialis (d), triceps_lateral, triceps_long, triceps_medial (d), brachioradialis, wrist_flexors, wrist_extensors
- **Core (4):** rectus_abdominis, external_obliques, internal_obliques (d), transversus_abdominis (d)
- **Hips (5):** iliopsoas (d), gluteus_maximus, gluteus_medius, gluteus_minimus (d), tensor_fasciae_latae
- **Thighs (11):** rectus_femoris, vastus_lateralis, vastus_medialis, vastus_intermedius (d), sartorius, adductor_longus, adductor_magnus, gracilis, biceps_femoris, semitendinosus, semimembranosus
- **Lower leg (4):** gastrocnemius, soleus, tibialis_anterior, fibularis

**Count check.** The list as given (52 named keys plus levator_scapulae, coracobrachialis and gracilis) contains **56** distinct keys, not 55: the "52" list itself has 53 keys when counted (4 + 12 + 2 + 3 + 9 + 4 + 5 + 10 + 4). All 56 are covered in this document and in the rules table. If the two roll-ups recommended in §2 are accepted (levator_scapulae → trap_upper, coracobrachialis → pec_major_clavicular / biceps_short), the total is **54**.

## 2. Added / rolled up / left out, and why

| Candidate | Decision | Why | Sources |
|---|---|---|---|
| Pec major clavicular / sternal heads | **Keep as 2 keys** (owner list) | Incline vs flat changes which head is emphasised in EMG and in a training study | RodriguezRidao2020, Chaves2020 |
| Pec major abdominal part | **Rolled into `pec_major_sternal`** | No exercise study read that separates it; it shares the sternal head's line of pull and insertion | Wikipedia (pectoralis major); E |
| Trapezius upper / middle / lower | **Added as 3 keys** | Different exercises maximise each part: shrug = upper, prone horizontal abduction = middle, prone overhead raise = lower | Ekstrom2003 |
| Levator scapulae | **Recommend rolling into `trap_upper`** (differs from the tentative list) | No exercise found that loads it apart from the upper trapezius; shrugs load both. It is mostly hidden under trapezius and SCM, so a separate map shape adds little. Keep it only if the neck drawing needs it, and then as readiness-only | Wikipedia (levator scapulae); Ekstrom2003; E |
| Rotator cuff: infraspinatus, supraspinatus, subscapularis (+ teres minor from the owner list) | **Added as 3 keys** | Each has exercises that target it in EMG (side-lying external rotation; full-can / prone abduction; push-up plus / diagonals / internal rotation), and together they are a large share of shoulder muscle (subscapularis alone 6.6% of upper-limb muscle volume) | Reinold2004, Reinold2007, Decker2003, Holzbaur2007 |
| Coracobrachialis | **Recommend leaving out** (fold into `pec_major_clavicular` / `biceps_short`; differs from the tentative list) | Tiny (25 cm³, 0.9% of upper-limb muscle volume), deep, and no gym exercise targets it; in the rules it only reaches 0.25 on flyes and front raises | Holzbaur2007; OpenStax 11.5 |
| Anconeus | **Rolled into `triceps_medial`** | 10.8 cm³, partly blended with the triceps and assists elbow extension | Holzbaur2007; Wikipedia (anconeus) |
| Iliopsoas | **Added** | Trained by hanging leg raises, sit-ups and planks; deep hip-flexion exercises activate it most; leg-raise fatigue otherwise goes nowhere | Juan2024, Imai2017, Escamilla2006a |
| Adductor magnus vs longus | **Added as 2 keys** (the old map had one `adductors` region) | Magnus works in hip extension (squats, hinges) as well as adduction; longus mainly in adduction | Collings2026, Kubo2019, Plotkin2023 |
| Adductor brevis, pectineus | **Rolled into `adductor_longus`** | Deep and small, same action and similar exercise ranking to longus | Collings2026; OpenStax 11.6 |
| Gracilis | **Keep** (tentative list agrees) | Superficial strap on the inner thigh (the map needs a shape there); its exercise forces are ranked separately from the other adductors | Collings2026; OpenStax 11.6 |
| Sartorius | **Keep as readiness-only** | Superficial and visible across the front thigh, so the map needs a shape there; but it has large excursion and small force capacity, and no exercise targets it | Ward2009; OpenStax 11.6 |
| Tensor fasciae latae | **Added** | Works with gluteus medius in abduction; exercises can raise or lower its share relative to the glutes | Selkowitz2013; OpenStax 11.6 |
| Tibialis anterior, fibularis | **Added** | Visible on the front and side of the shin; trainable with tib raises and eversion work. FEDB has no loaded tibialis exercise (see the mapping document) | OpenStax 11.6; E |
| Neck: sternocleidomastoid, splenius | **Added** | Neck muscles only grew with specific neck exercises in a training study; FEDB has 8 neck exercises (front/back/side) | Conley1997 |
| Quadratus lumborum | **Added (deep)** | The side bridge recruited it most on diffusion-weighted MRI; it carries side-plank and carry fatigue | Imai2017 |
| Multifidus | **Rolled into `erector_spinae`** | Deep, worked by the same extension exercises; ASCEND has no exercise that separates them | OpenStax 11.3; E |
| Gastrocnemius medial / lateral heads | **Keep one `gastrocnemius` key** | Toe angle shifts growth between heads, but FEDB names almost never encode toe angle, so no rule could use two keys | Nunes2020 |
| Soleus | **Keep separate** (owner list) | Seated raises grow soleus but not gastrocnemius; standing raises grow both | Kinoshita2023 |
| Forearm sub-groups (pronators, supinator, finger flexors and extensors) | **Rolled up** into `wrist_flexors`, `wrist_extensors` (and `brachioradialis` separately) | No exercises in the library target pronators or the supinator separately; grip and wrist-curl work loads the flexor mass | Holzbaur2007, Ikeda2025 |
| Rhomboid major + minor | **One key `rhomboids`** | Same action, same exercises | OpenStax 11.5 |
| Not added: subclavius, serratus posterior, intercostals, diaphragm, rotatores, scalenes, popliteus, plantaris, hand and foot intrinsics | **Left out** | Not meaningfully targetable or trackable through gym exercises, and not shown on a body map at this scale [unverified judgement] | E |

**Where the evidence suggests a different decision from the tentative list:** (1) roll `levator_scapulae` into `trap_upper`; (2) leave out `coracobrachialis`. Both are small or hidden and no exercise loads them apart from a neighbour. Keeping them costs nothing in the engine (the rules table already covers both); the cost is map clutter and two muscles that will always read "no data" or mirror a neighbour.

## 3. Reference table for all 56 keys

Front view / back view codes, for drawing: **S** = superficial, draw on the base layer; **P** = partly visible (draw the visible part on the base layer); **D** = deep or hidden, draw only on the "deep layer"; **—** = not seen in that view. These view codes are the author's reading of the standard superficial-muscle figures (OpenStax Fig. 11.x "Anterior and posterior views", the public-domain Häggström diagrams) and of each muscle's depth as described in the sources [unverified per muscle: no source lists visibility as a field].

| Key | Muscle | Location | Origin → insertion (one line) | Primary actions | Front view | Back view | Size / recovery note | Sources |
|---|---|---|---|---|---|---|---|---|
| `pec_major_clavicular` | Pectoralis major, clavicular head (upper chest) | Upper chest, below the collarbone | Medial half of clavicle → lateral lip of bicipital groove of humerus | Shoulder flexion, horizontal adduction, internal rotation | S | — | Whole pectoralis major ≈ 290 cm³, 10.7% of upper-limb muscle volume (H07); the head split was not measured | [Wikipedia](https://en.wikipedia.org/wiki/Pectoralis_major); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `pec_major_sternal` | Pectoralis major, sternocostal head (mid/lower chest; abdominal part rolled in) | Bulk of the chest over the sternum and ribs | Sternum, upper costal cartilages (abdominal part: rectus sheath) → lateral lip of bicipital groove | Horizontal adduction, adduction and extension of the flexed arm, internal rotation | S | — | See clavicular head | [Wikipedia](https://en.wikipedia.org/wiki/Pectoralis_major); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `pec_minor` | Pectoralis minor (deep chest) | Under pectoralis major, from ribs to the coracoid | Ribs 3-5 near the costal cartilages → coracoid process of scapula | Draws the scapula forward and down (protraction, depression); raises ribs in forced breathing | D | — | Small; no volume source read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Pectoralis_minor); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs) |
| `serratus_anterior` | Serratus anterior ("boxer's muscle") | Side of the rib cage under the armpit, under the scapula | Outer surfaces of ribs 1-8/9 → costal surface of medial border of scapula | Scapular protraction and upward rotation; holds the scapula on the chest wall | P (side of ribcage) | D (under scapula/lats) | No volume source read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Serratus_anterior_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); Ekstrom2003 |
| `latissimus_dorsi` | Latissimus dorsi (lats) | Broad sheet over the lower and side back | T7-S5 spinous processes, thoracolumbar fascia, iliac crest, lower 4 ribs, inferior angle of scapula → floor of intertubercular groove of humerus | Shoulder adduction, extension, internal rotation | P (edge beside the chest) | S | ≈ 262 cm³, 9.8% of upper-limb muscle volume (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Latissimus_dorsi_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `trap_upper` | Trapezius, upper (descending) part | Neck slope from skull to shoulder | Superior nuchal line, external occipital protuberance, nuchal ligament → lateral third of clavicle | Scapular elevation and upward rotation; neck extension and side bending | P (neck slope) | S | Trapezius volume not in sources read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Trapezius); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); Ekstrom2003 |
| `trap_middle` | Trapezius, middle (transverse) part | Between the shoulder blades, upper back | Upper thoracic spinous processes → acromion and spine of scapula (Wikipedia gives C7-T12 for the whole muscle; how it is split into parts varies by source) | Scapular retraction | — | S | — | [Wikipedia](https://en.wikipedia.org/wiki/Trapezius); Ekstrom2003 |
| `trap_lower` | Trapezius, lower (ascending) part | Mid back, below the scapulae, V shape | Mid and lower thoracic spinous processes → medial end of the spine of scapula (split varies by source) | Scapular depression and upward rotation | — | S | — | [Wikipedia](https://en.wikipedia.org/wiki/Trapezius); Ekstrom2003 |
| `rhomboids` | Rhomboid major and minor (rolled up) | Between spine and scapula, under the trapezius | Spinous processes C7-T5 → medial border of scapula | Scapular retraction and downward rotation; fixes the scapula | — | D (under trapezius) | No volume source read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Rhomboid_major_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs) |
| `teres_major` | Teres major | Lower outer edge of the scapula toward the armpit | Inferior angle of scapula (posterior) → medial lip of intertubercular sulcus | Shoulder adduction, internal rotation, extension (works with the lats) | — | S | ≈ 32.7 cm³, 1.3% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Teres_major_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `teres_minor` | Teres minor (rotator cuff) | Lateral border of scapula, above teres major | Lateral border of scapula → inferior facet of greater tubercle | External rotation; stabilises the humeral head | — | P (small strip, partly under deltoid) | ≈ 28.0 cm³, 1.1% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Teres_minor_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `infraspinatus` | Infraspinatus (rotator cuff) | Lower part of the back of the scapula | Infraspinous fossa → middle facet of greater tubercle | External rotation; stabilises the glenohumeral joint | — | S (partly covered by trapezius and deltoid) | ≈ 118.6 cm³, 4.8% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Infraspinatus_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `supraspinatus` | Supraspinatus (rotator cuff) | Above the spine of the scapula, under the trapezius | Supraspinous fossa → superior facet of greater tubercle | Starts shoulder abduction; stabilises the humerus | — | D (under trapezius) | ≈ 50.0 cm³, 2.0% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Supraspinatus_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `subscapularis` | Subscapularis (rotator cuff) | Front surface of the scapula, against the ribs | Subscapular fossa → lesser tubercle of humerus | Internal rotation; stabilises the shoulder | D (hidden behind ribs and pecs) | D | ≈ 164.5 cm³, 6.6%: the largest cuff muscle (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Subscapularis_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `erector_spinae` | Erector spinae (multifidus rolled in) | Two columns either side of the spine, most visible in the lower back | Sacrum, iliac crest, lumbar and lower thoracic spinous processes → ribs, vertebrae and skull (iliocostalis, longissimus, spinalis) | Spinal extension, side bending; keeps the lumbar curve | — | S (lumbar); D higher up under traps/lats | "The majority of the muscle mass of the back" (OS11.3); no volume number read | [Wikipedia](https://en.wikipedia.org/wiki/Erector_spinae_muscles); [OpenStax 11.3](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-3-axial-muscles-of-the-head-neck-and-back) |
| `quadratus_lumborum` | Quadratus lumborum | Deep lower back between the 12th rib and the pelvis | Posterior iliac crest → rib 12 and L1-L4 transverse processes | Side bending (one side); stabilises the lumbar spine and rib 12 (both) | D | D | No volume source read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Quadratus_lumborum_muscle); [OpenStax 11.4](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax); Imai2017 |
| `levator_scapulae` | Levator scapulae | Side and back of the neck to the top corner of the scapula | Transverse processes C1-C4 → superior part of medial border of scapula | Scapular elevation and downward rotation; neck side bending | P (side of neck) | D (mostly under trapezius) | No volume source read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Levator_scapulae_muscle) |
| `sternocleidomastoid` | Sternocleidomastoid | Front-side of the neck, sternum/clavicle to behind the ear | Manubrium and medial clavicle → mastoid process, superior nuchal line | One side: bends the neck to the same side and turns the face to the other side; both: neck flexion | S | — | Neck muscles grew only with specific neck training (Conley1997) | [Wikipedia](https://en.wikipedia.org/wiki/Sternocleidomastoid_muscle); [OpenStax 11.3](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-3-axial-muscles-of-the-head-neck-and-back); Conley1997 |
| `splenius` | Splenius capitis/cervicis (neck extensors) | Back of the neck under the trapezius | Nuchal ligament, spinous processes C7-T3 → mastoid process and occipital bone | Head and neck extension; rotation and side bending to the same side | — | P (small triangle between traps and SCM) | Splenius and semispinalis are the main head extensors (Conley1997) | [Wikipedia](https://en.wikipedia.org/wiki/Splenius_capitis_muscle); [OpenStax 11.3](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-3-axial-muscles-of-the-head-neck-and-back); Conley1997 |
| `deltoid_anterior` | Deltoid, anterior (clavicular) part | Front of the shoulder | Lateral third of clavicle → deltoid tuberosity of humerus | Shoulder flexion, internal rotation, horizontal adduction | S | P (outline) | Whole deltoid ≈ 380.5 cm³, 15.2%: the largest upper-limb muscle (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Deltoid_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `deltoid_lateral` | Deltoid, lateral (acromial) part | Side cap of the shoulder | Acromion → deltoid tuberosity | Shoulder abduction | S (side) | S (side) | See anterior | [Wikipedia](https://en.wikipedia.org/wiki/Deltoid_muscle); H07 |
| `deltoid_posterior` | Deltoid, posterior (spinal) part | Back of the shoulder | Spine of scapula → deltoid tuberosity | Shoulder extension, horizontal abduction, external rotation | — | S | See anterior | [Wikipedia](https://en.wikipedia.org/wiki/Deltoid_muscle); H07 |
| `biceps_long` | Biceps brachii, long head | Outer half of the front of the upper arm | Supraglenoid tubercle of scapula → radial tuberosity and bicipital aponeurosis | Elbow flexion, forearm supination; weak shoulder flexion (crosses the shoulder) | S | — | Whole biceps ≈ 143.7 cm³, 5.6% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Biceps); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `biceps_short` | Biceps brachii, short head | Inner half of the front of the upper arm | Coracoid process → radial tuberosity and bicipital aponeurosis | Elbow flexion, supination; shoulder flexion/adduction | S | — | See long head | [Wikipedia](https://en.wikipedia.org/wiki/Biceps); H07 |
| `brachialis` | Brachialis | Under the biceps, lower half of the upper arm; edges show on the outer arm | Distal half of anterior humerus → coronoid process and ulnar tuberosity | Elbow flexion in every forearm position | P (edges beside biceps) | P (outer arm) | ≈ 143.7 cm³, 5.7%: as large as the biceps (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Brachialis_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `coracobrachialis` | Coracobrachialis | Inner upper arm near the armpit, under pec and biceps short head | Coracoid process → medial humerus mid-shaft | Shoulder flexion and adduction | D | — | ≈ 25.2 cm³, 0.9% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Coracobrachialis_muscle); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `triceps_lateral` | Triceps brachii, lateral head | Outer back of the upper arm (horseshoe outer edge) | Posterior humerus above the radial groove → olecranon | Elbow extension | P (outer arm) | S | Whole triceps ≈ 372.1 cm³, 14.5% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Triceps); [OpenStax 11.5](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs); H07 |
| `triceps_long` | Triceps brachii, long head | Inner back of the upper arm, toward the armpit | Infraglenoid tubercle of scapula → olecranon | Elbow extension; shoulder extension and adduction (crosses the shoulder) | P (inner arm) | S | See lateral head | [Wikipedia](https://en.wikipedia.org/wiki/Triceps); Kholinne2018; H07 |
| `triceps_medial` | Triceps brachii, medial head (anconeus rolled in) | Deep, under the other two heads; shows just above the elbow | Posterior humerus below the radial groove → olecranon | Elbow extension | — | D (visible only near the elbow) | Anconeus ≈ 10.8 cm³, 0.4% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Triceps); [Wikipedia](https://en.wikipedia.org/wiki/Anconeus_muscle); Kholinne2018 |
| `brachioradialis` | Brachioradialis | Thumb side of the upper forearm | Lateral supracondylar ridge of humerus → radial styloid | Elbow flexion, strongest with the forearm half-turned | S | S (thumb side) | ≈ 65.1 cm³, 2.5% (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Brachioradialis); Caufriez2018; H07 |
| `wrist_flexors` | Wrist flexors (FCR, FCU, palmaris longus; finger flexors rolled in) | Palm side of the forearm | Medial epicondyle (common flexor tendon) → metacarpal bases, pisiform/hamate | Wrist flexion; FCR radial and FCU ulnar deviation | S | — | FCR 34.8 + FCU 37.1 + PL 10.0 cm³; finger flexors FDS 74.2 + FDP 91.6 (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Flexor_carpi_radialis_muscle); [Wikipedia](https://en.wikipedia.org/wiki/Flexor_carpi_ulnaris_muscle); H07; Ikeda2025 |
| `wrist_extensors` | Wrist extensors (ECRL, ECRB, ECU; finger extensors rolled in) | Back of the forearm | Lateral epicondyle and supracondylar ridge → metacarpals 2, 3 and 5 | Wrist extension; radial/ulnar deviation | — | S | ECRL 37.5 + ECRB 21.6 + ECU 17.0 cm³; flexor side is about twice the extensor side (H07) | [Wikipedia](https://en.wikipedia.org/wiki/Extensor_carpi_radialis_longus_muscle); [Wikipedia](https://en.wikipedia.org/wiki/Extensor_carpi_ulnaris_muscle); H07; Ikeda2025 |
| `rectus_abdominis` | Rectus abdominis ("six-pack") | Front of the abdomen either side of the midline | Pubic crest and symphysis → costal cartilages 5-7, xiphoid | Trunk (lumbar) flexion | S | — | No volume source read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Rectus_abdominis_muscle); [OpenStax 11.4](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax) |
| `external_obliques` | External oblique | Sides of the abdomen, outermost layer | Outer surfaces of ribs 5-12 → linea alba, iliac crest, pubic tubercle | Trunk flexion, side bending, rotation to the opposite side | S (sides) | P (flank) | — | [Wikipedia](https://en.wikipedia.org/wiki/Abdominal_external_oblique_muscle); [OpenStax 11.4](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax) |
| `internal_obliques` | Internal oblique | Under the external oblique | Inguinal ligament, iliac crest, thoracolumbar fascia → linea alba, pubis, ribs 10-12 | Rotation to the same side, flexion, abdominal compression | D | D | — | [Wikipedia](https://en.wikipedia.org/wiki/Abdominal_internal_oblique_muscle); [OpenStax 11.4](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax) |
| `transversus_abdominis` | Transversus abdominis (deep core) | Deepest abdominal layer, wraps the trunk like a belt | Iliac crest, inguinal ligament, thoracolumbar fascia, costal cartilages 7-12 → linea alba, xiphoid, pubis | Compresses the abdomen; trunk stabilisation | D | D | — | [Wikipedia](https://en.wikipedia.org/wiki/Transverse_abdominal_muscle); [OpenStax 11.4](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax); Pulkovski2012 |
| `iliopsoas` | Iliopsoas (psoas major + iliacus) | Deep in the abdomen and pelvis to the inner upper thigh | Lumbar vertebrae and iliac fossa → lesser trochanter of femur | Hip flexion | D (a small part shows in the groin) | — | No volume source read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Iliopsoas); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Juan2024 |
| `gluteus_maximus` | Gluteus maximus | The buttock | Ilium, sacrum, coccyx, sacrotuberous ligament, lumbar fascia → gluteal tuberosity and iliotibial tract | Hip extension and external rotation | — | S | Largest gluteal muscle (OS11.6); no volume number read [unverified] | [Wikipedia](https://en.wikipedia.org/wiki/Gluteus_maximus); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs) |
| `gluteus_medius` | Gluteus medius | Upper outer hip, partly under gluteus maximus | Outer surface of ilium → greater trochanter | Hip abduction; anterior fibres internal rotation; pelvic stability on one leg | P (side of hip) | P (above glute max) | Among the strongest lower-limb muscles by PCSA (Ward2009) | [Wikipedia](https://en.wikipedia.org/wiki/Gluteus_medius); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Ward2009 |
| `gluteus_minimus` | Gluteus minimus | Under gluteus medius | Outer ilium between anterior and inferior gluteal lines → greater trochanter | Hip abduction and internal rotation | — | D | — | [Wikipedia](https://en.wikipedia.org/wiki/Gluteus_minimus); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Moore2020 |
| `tensor_fasciae_latae` | Tensor fasciae latae | Front-outer hip below the iliac crest | Iliac crest / ASIS → iliotibial tract | Hip flexion, abduction, internal rotation; tensions the IT band | S (front-side of hip) | — | — | [Wikipedia](https://en.wikipedia.org/wiki/Tensor_fasciae_latae_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Selkowitz2013 |
| `rectus_femoris` | Rectus femoris | Centre front of the thigh | Anterior inferior iliac spine and above the acetabulum → patella via quadriceps tendon, tibial tuberosity | Knee extension and hip flexion (crosses both joints) | S | — | Did not grow with squats in Kubo2019 | [Wikipedia](https://en.wikipedia.org/wiki/Rectus_femoris_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Kubo2019 |
| `vastus_lateralis` | Vastus lateralis ("quad sweep") | Outer front of the thigh | Greater trochanter, intertrochanteric line, linea aspera → patella / tibial tuberosity | Knee extension | S | P (outer thigh) | Among the strongest lower-limb muscles by PCSA (Ward2009) | [Wikipedia](https://en.wikipedia.org/wiki/Vastus_lateralis_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Ward2009 |
| `vastus_medialis` | Vastus medialis ("teardrop") | Inner front of the thigh above the knee | Medial femur (linea aspera, medial lip) → quadriceps tendon | Knee extension | S | — | — | [Wikipedia](https://en.wikipedia.org/wiki/Vastus_medialis); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs) |
| `vastus_intermedius` | Vastus intermedius (deep quad) | Under rectus femoris on the front of the femur | Anterolateral femoral shaft → quadriceps tendon | Knee extension | D | — | — | [Wikipedia](https://en.wikipedia.org/wiki/Vastus_intermedius_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Kojic2022 |
| `sartorius` | Sartorius | Long strap crossing the front of the thigh from hip to inner knee | Anterior superior iliac spine → medial proximal tibia (pes anserinus) | Hip flexion, abduction and lateral rotation; knee flexion | S | — | Large excursion, small force capacity (Ward2009) | [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Ward2009 |
| `adductor_longus` | Adductor longus (brevis, pectineus rolled in) | Upper inner thigh | Pubic body below the crest → middle third of linea aspera | Hip adduction and flexion | S (inner thigh) | — | Hip adductors are among the strongest groups by PCSA (Ward2009) | [Wikipedia](https://en.wikipedia.org/wiki/Adductor_longus_muscle); [Wikipedia](https://en.wikipedia.org/wiki/Adductor_brevis_muscle); [Wikipedia](https://en.wikipedia.org/wiki/Pectineus_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Collings2026 |
| `adductor_magnus` | Adductor magnus | Large inner-rear thigh muscle | Inferior pubic ramus and ischial tuberosity → linea aspera and adductor tubercle | Hip adduction; hip extension (hamstring part); hip flexion (adductor part) | D/P (deep to the other adductors) | P (inner back thigh) | Grew with full squats (Kubo2019) | [Wikipedia](https://en.wikipedia.org/wiki/Adductor_magnus_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Kubo2019; Collings2026 |
| `gracilis` | Gracilis | Thin strap along the inner thigh | Ischiopubic ramus → medial tibia (pes anserinus) | Hip adduction, knee flexion, internal rotation | S (inner thigh) | P | Large excursion (Ward2009) | [Wikipedia](https://en.wikipedia.org/wiki/Gracilis_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Collings2026 |
| `biceps_femoris` | Biceps femoris (outer hamstring) | Outer back of the thigh | Long head ischial tuberosity, short head linea aspera → head of fibula | Knee flexion; hip extension (long head); knee external rotation | — | S | — | [Wikipedia](https://en.wikipedia.org/wiki/Biceps_femoris_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Maeo2024 |
| `semitendinosus` | Semitendinosus (middle/inner hamstring) | Inner back of the thigh, superficial | Ischial tuberosity → pes anserinus (medial tibia) | Knee flexion, hip extension, knee internal rotation | — | S | — | [Wikipedia](https://en.wikipedia.org/wiki/Semitendinosus_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Messer2018 |
| `semimembranosus` | Semimembranosus (inner hamstring) | Inner back of the thigh, under semitendinosus | Ischial tuberosity → medial tibial condyle | Hip extension, knee flexion | — | P (edges beside semitendinosus) | — | [Wikipedia](https://en.wikipedia.org/wiki/Semimembranosus_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs) |
| `gastrocnemius` | Gastrocnemius (medial + lateral heads) | Upper calf, two bellies | Femoral condyles → calcaneus via Achilles tendon | Ankle plantarflexion; knee flexion | P (inner calf) | S | Grew only with knee-straight raises (Kinoshita2023) | [Wikipedia](https://en.wikipedia.org/wiki/Gastrocnemius_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Kinoshita2023 |
| `soleus` | Soleus (deep calf) | Under the gastrocnemius; shows on both sides of the lower calf | Head and shaft of fibula, soleal line of tibia → calcaneus via Achilles tendon | Ankle plantarflexion (any knee angle) | P (inner lower leg) | P/D (under gastrocnemius) | Strongest lower-limb muscle by PCSA (Ward2009) | [Wikipedia](https://en.wikipedia.org/wiki/Soleus_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs); Ward2009; Kinoshita2023 |
| `tibialis_anterior` | Tibialis anterior | Front of the shin, beside the tibia | Upper lateral tibia and interosseous membrane → medial cuneiform, base of 1st metatarsal | Ankle dorsiflexion and inversion | S | — | — | [Wikipedia](https://en.wikipedia.org/wiki/Tibialis_anterior_muscle); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs) |
| `fibularis` | Fibularis (peroneus) longus and brevis | Outer side of the lower leg | Lateral fibula → 1st metatarsal/medial cuneiform (longus), 5th metatarsal (brevis) | Foot eversion; assists plantarflexion | P (outer shin) | P (outer calf) | — | [Wikipedia](https://en.wikipedia.org/wiki/Fibularis_longus); [Wikipedia](https://en.wikipedia.org/wiki/Fibularis_brevis); [OpenStax 11.6](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs) |

## 4. What the map draws where

- **Front, base layer:** `pec_major_clavicular`, `pec_major_sternal`, `serratus_anterior`, `latissimus_dorsi`, `trap_upper`, `levator_scapulae`, `sternocleidomastoid`, `deltoid_anterior`, `deltoid_lateral`, `biceps_long`, `biceps_short`, `brachialis`, `triceps_lateral`, `triceps_long`, `brachioradialis`, `wrist_flexors`, `rectus_abdominis`, `external_obliques`, `gluteus_medius`, `tensor_fasciae_latae`, `rectus_femoris`, `vastus_lateralis`, `vastus_medialis`, `sartorius`, `adductor_longus`, `gracilis`, `gastrocnemius`, `soleus`, `tibialis_anterior`, `fibularis`
- **Front, deep layer:** `pec_minor`, `subscapularis`, `quadratus_lumborum`, `coracobrachialis`, `internal_obliques`, `transversus_abdominis`, `iliopsoas`, `vastus_intermedius`, `adductor_magnus`
- **Back, base layer:** `latissimus_dorsi`, `trap_upper`, `trap_middle`, `trap_lower`, `teres_major`, `teres_minor`, `infraspinatus`, `erector_spinae`, `splenius`, `deltoid_anterior`, `deltoid_lateral`, `deltoid_posterior`, `brachialis`, `triceps_lateral`, `triceps_long`, `brachioradialis`, `wrist_extensors`, `external_obliques`, `gluteus_maximus`, `gluteus_medius`, `vastus_lateralis`, `adductor_magnus`, `gracilis`, `biceps_femoris`, `semitendinosus`, `semimembranosus`, `gastrocnemius`, `soleus`, `fibularis`
- **Back, deep layer:** `serratus_anterior`, `rhomboids`, `supraspinatus`, `subscapularis`, `quadratus_lumborum`, `levator_scapulae`, `triceps_medial`, `internal_obliques`, `transversus_abdominis`, `gluteus_minimus`

Notes for the drawing:

- `subscapularis`, `quadratus_lumborum`, `internal_obliques` and `transversus_abdominis` are deep in **both** views. On the deep layer, draw them as outlines where they lie (subscapularis under the scapula; QL beside the lumbar spine; TrA and internal oblique under the abdominal wall).
- `soleus` is listed by the owner as "deep calf", but its edges are visible either side of the lower gastrocnemius. Draw those edges on the base layer and the full muscle on the deep layer.
- `brachialis`, `triceps_medial`, `semimembranosus` and `adductor_magnus` are partly hidden. Draw the visible strip on the base layer so the base map has no blank gaps.
- `serratus_anterior` shows on the side of the rib cage; it is the classic "boxer's muscle" strip under the armpit.
- `sartorius` and `gracilis` are long straps; they separate the quadriceps from the adductors on the front and inner thigh.
- Heads of one muscle (pec, deltoid, biceps, triceps, quads, hamstrings, gastrocnemius) should be separate SVG paths, so each key can take its own recovery colour.

## 5. Size and recovery-relevant notes

### 5.1 Upper-limb muscle volumes (MRI, 10 young healthy adults)

From the full text of Holzbaur et al. (2007), Table 2 ([Holzbaur2007]):

| Muscle (ASCEND key) | Mean volume, cm³ (SD) | % of upper-limb muscle volume |
|---|---|---|
| Deltoid (3 deltoid keys) | 380.5 (157.7) | 15.2 |
| Triceps, 3 heads (3 triceps keys) | 372.1 (177.3) | 14.5 |
| Pectoralis major (2 pec keys) | 290.0 (169.0) | 10.7 |
| Latissimus dorsi | 262.3 (147.2) | 9.8 |
| Subscapularis | 164.5 (63.9) | 6.6 |
| Brachialis | 143.7 (63.7) | 5.7 |
| Biceps, 2 heads | 143.7 (68.7) | 5.6 |
| Infraspinatus | 118.6 (46.7) | 4.8 |
| Brachioradialis | 65.1 (36.0) | 2.5 |
| Supraspinatus | 50.0 (20.4) | 2.0 |
| Teres major | 32.7 (16.3) | 1.3 |
| Teres minor | 28.0 (13.9) | 1.1 |
| Coracobrachialis | 25.2 (16.6) | 0.9 |
| Wrist flexors (FCR + FCU + PL) | 34.8 + 37.1 + 10.0 | 1.3 + 1.5 + 0.4 |
| Wrist extensors (ECRL + ECRB + ECU) | 37.5 + 21.6 + 17.0 | 1.5 + 0.9 + 0.7 |
| Anconeus (rolled into triceps_medial) | 10.8 (5.2) | 0.4 |
| Total, 32 upper-limb muscles | 2554.0 (1166.7) | 100 |

Points worth carrying into the engine [design inferences marked]:

- The deltoid and triceps are each about **15%** of upper-limb muscle; brachialis is as large as the biceps (5.7% vs 5.6%). That supports giving `brachialis` its own key and a meaningful weight in curls.
- Subscapularis (6.6%) is larger than infraspinatus (4.8%) and supraspinatus (2.0%). The cuff is not trivial in size, but it is rarely the limiting muscle in gym work [unverified], hence readiness-only.
- Coracobrachialis (0.9%) and anconeus (0.4%) are very small, which supports rolling them up.
- The flexor side of the forearm is about twice the extensor side ([Holzbaur2007]); grip-heavy training mostly fatigues `wrist_flexors`.

### 5.2 Lower limb

- By physiological cross-sectional area (force capacity), soleus, gluteus medius and vastus lateralis were the strongest lower-limb muscles. Plantarflexors, knee extensors and hip adductors were the strongest groups at their joints. Sartorius, gracilis and semitendinosus had the largest excursion ([Ward2009] [abstract read]).
- Lower-limb muscle volumes scale with body mass and with height × mass ([Handsfield2014] [abstract read]). The per-muscle volume table in that paper was **not** accessible, so no lower-limb volume numbers are given here.

### 5.3 Recovery findings that matter for the model

- **Size does not set recovery time.** After the same maximal eccentric protocol, elbow flexors and extensors showed greater changes in all damage markers than knee flexors and extensors, and knee flexors more than knee extensors ([Chen2011] [abstract read]). The v7 taxonomy gives quads 48 h and hamstrings 36 h half-lives (estimates). This evidence would, if anything, argue for hamstrings ≥ quads after eccentric work. **Recommendation:** keep the v7 values as estimates, inherit them down to the new keys, and let ASCEND's personal recovery model adjust per user [unverified design].
- **Hamstring damage.** After an eccentric bout, untrained legs showed large T2 (MRI) increases in each hamstring muscle (semitendinosus +52% at 72 h); legs that had trained with leg curls showed almost none ([Maeo2021] [abstract read]). → Training history matters more than which hamstring it is; one half-life for the three hamstring keys is fine.
- **Calves.** Standing raises grew both gastrocnemius heads; seated raises grew only soleus ([Kinoshita2023] [abstract read]). The two keys therefore need separate fatigue tracking (already in the rules).
- **Rectus femoris vs vasti.** Squats grew the vasti but not rectus femoris in one MRI study ([Kubo2019] [abstract read]); another found smaller rectus femoris and vastus intermedius effects ([Kojic2022] [abstract read]). → separate keys are justified.
- **Estimates to label in the UI:** every half-life, capacity and weekly target is an estimate, as `taxonomy.py` already says. No head-specific recovery times were found in the literature read for this document [unverified: absence in the sources read, not proof of absence].

**Suggested size tiers** for capacity (`capacity_es`: 10 for large, 8 for small, as in v7): large (10) = pec heads, lats, erector_spinae, glutes max, quads, hamstrings, adductor_magnus, gastrocnemius, soleus; small (8) = everything else. Inherit the half-life from the v7 parent region; keys with no parent take 24 h (small) or 36 h (large) [unverified estimates, in line with v7's existing scheme].

## 6. Openly licensed body-map artwork

| Option | What it is | Licence | Link | Fit for ASCEND |
|---|---|---|---|---|
| react-muscle-highlighter 1.2.0 (current) | React SVG body (front/back) with coarse regions | MIT (npm registry) | https://www.npmjs.com/package/react-muscle-highlighter | Already in the app, but the regions are coarse (the v7 `map_slug` values); 56 keys need new paths |
| react-body-highlighter 2.0.5 | React SVG body map, front/back | MIT (npm registry) | https://www.npmjs.com/package/react-body-highlighter | Same coarseness problem; useful as a layout reference |
| body-muscles 1.0.0 | SVG muscle body package | Apache-2.0 (npm registry) | https://www.npmjs.com/package/body-muscles | Permissive; detail level not checked [unverified] |
| Mikael Häggström, *Muscles anterior labeled.png* / *Muscle posterior labeled.png* | Labelled front/back superficial muscle diagrams | Public domain (Wikimedia Commons metadata) | https://commons.wikimedia.org/wiki/File:Muscles_anterior_labeled.png · https://commons.wikimedia.org/wiki/File:Muscle_posterior_labeled.png | Best tracing reference for original SVG paths: no licence obligations (credit appreciated) |
| Gray's Anatomy (1918) plates, e.g. *Gray409.png* | Classic engraved anatomy plates | Public domain (Wikimedia Commons metadata) | https://commons.wikimedia.org/wiki/File:Gray409.png | Accurate reference for deep-layer shapes; engraving style, not a ready map |
| OpenStax A&P 2e, Figure 11.x *Anterior and Posterior Views of Muscles* | Textbook illustration of superficial muscles | CC BY 4.0 (Wikimedia Commons metadata) | https://commons.wikimedia.org/wiki/File:1105_Anterior_and_Posterior_Views_of_Muscles.jpg | Usable with attribution; no share-alike |
| Servier Medical Art (SMART) | Medical illustration library | CC BY 4.0 (publisher's page) [snippet] | https://smart.servier.com/ | Usable with attribution; style may not match the app |
| BodyParts3D / Anatomography (and its Commons renders, e.g. *Serratus anterior muscles frontal.png*) | 3D anatomy models and renders, per muscle | CC BY-SA 2.1 Japan (Commons metadata; project page [snippet]) | https://lifesciencedb.jp/bp3d/?lng=en | Very detailed, per-muscle highlight renders, **but share-alike** |
| Z-Anatomy | 3D atlas built on BodyParts3D | CC BY-SA 4.0 (project repo) [snippet] | https://github.com/Z-Anatomy/Models-of-human-anatomy | Share-alike |

### Does CC BY-SA oblige share-alike?

Yes, for **adaptations of the artwork itself**. The CC BY-SA 4.0 legal code says that if you share Adapted Material you produce, "the Adapter's License You apply must be a Creative Commons license with the same License Elements, this version or later, or a BY-SA Compatible License" ([CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en), page read). "Adapted Material" is material "derived from or based upon the Licensed Material" in which it is "translated, altered, arranged, transformed, or otherwise modified" (same page). The CC FAQ sums SA up as requiring "adaptations of the material be released under the same license" ([CC FAQ](https://creativecommons.org/faq/), page read). The same FAQ advises against using CC licences for software and notes they are not compatible with the major software licences, apart from BY-SA 4.0's one-way compatibility with GPLv3.

What that means for ASCEND [interpretation, not legal advice; unverified]:

- An SVG body map traced or modified from a BodyParts3D or Z-Anatomy render would be Adapted Material, so **that SVG** would have to be released under CC BY-SA, with attribution, inside an MIT-licensed repository. The application code would not become CC BY-SA, but the repo would then hold mixed licences that must be declared file by file.
- **Recommended route:** draw **original** SVG paths using the public-domain Häggström diagrams and Gray's plates as visual references (or adapt the CC BY 4.0 OpenStax figure with attribution). Then the map can ship under the repo's MIT licence with a credits line. This avoids share-alike entirely.
- Whatever is used, record it in the credits: source, author, licence, link, and what was changed.

## 7. Limitations

- Wikipedia infoboxes were used for origin and insertion because they could be read for all muscles; each line was checked against the OpenStax sections where OpenStax covers the muscle, but not against Gray's text line by line [unverified].
- The view codes (S/P/D) are the author's reading, not a sourced field.
- Lower-limb volumes and all recovery parameters are not measured here; the size tiers are estimates.
- Muscle-part boundaries (for example the three trapezius parts) vary between sources.

## 8. References

**Anatomy texts**

- OpenStax, *Anatomy and Physiology 2e*, 11.3 Axial muscles of the head, neck and back: https://openstax.org/books/anatomy-and-physiology-2e/pages/11-3-axial-muscles-of-the-head-neck-and-back (page read)
- OpenStax, 11.4 Axial muscles of the abdominal wall and thorax: https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax (page read)
- OpenStax, 11.5 Muscles of the pectoral girdle and upper limbs: https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs (page read)
- OpenStax, 11.6 Appendicular muscles of the pelvic girdle and lower limbs: https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs (page read)
- Wikipedia, *Pectoralis major*: https://en.wikipedia.org/wiki/Pectoralis_major (infobox read 2026-10-22)
- Wikipedia, *Pectoralis minor*: https://en.wikipedia.org/wiki/Pectoralis_minor (infobox read 2026-10-22)
- Wikipedia, *Serratus anterior muscle*: https://en.wikipedia.org/wiki/Serratus_anterior_muscle (infobox read 2026-10-22)
- Wikipedia, *Latissimus dorsi muscle*: https://en.wikipedia.org/wiki/Latissimus_dorsi_muscle (infobox read 2026-10-22)
- Wikipedia, *Trapezius*: https://en.wikipedia.org/wiki/Trapezius (infobox read 2026-10-22)
- Wikipedia, *Rhomboid major muscle*: https://en.wikipedia.org/wiki/Rhomboid_major_muscle (infobox read 2026-10-22)
- Wikipedia, *Rhomboid minor muscle*: https://en.wikipedia.org/wiki/Rhomboid_minor_muscle (infobox read 2026-10-22)
- Wikipedia, *Teres major muscle*: https://en.wikipedia.org/wiki/Teres_major_muscle (infobox read 2026-10-22)
- Wikipedia, *Teres minor muscle*: https://en.wikipedia.org/wiki/Teres_minor_muscle (infobox read 2026-10-22)
- Wikipedia, *Infraspinatus muscle*: https://en.wikipedia.org/wiki/Infraspinatus_muscle (infobox read 2026-10-22)
- Wikipedia, *Supraspinatus muscle*: https://en.wikipedia.org/wiki/Supraspinatus_muscle (infobox read 2026-10-22)
- Wikipedia, *Subscapularis muscle*: https://en.wikipedia.org/wiki/Subscapularis_muscle (infobox read 2026-10-22)
- Wikipedia, *Erector spinae muscles*: https://en.wikipedia.org/wiki/Erector_spinae_muscles (infobox read 2026-10-22)
- Wikipedia, *Quadratus lumborum muscle*: https://en.wikipedia.org/wiki/Quadratus_lumborum_muscle (infobox read 2026-10-22)
- Wikipedia, *Sternocleidomastoid muscle*: https://en.wikipedia.org/wiki/Sternocleidomastoid_muscle (infobox read 2026-10-22)
- Wikipedia, *Splenius capitis muscle*: https://en.wikipedia.org/wiki/Splenius_capitis_muscle (infobox read 2026-10-22)
- Wikipedia, *Levator scapulae muscle*: https://en.wikipedia.org/wiki/Levator_scapulae_muscle (infobox read 2026-10-22)
- Wikipedia, *Deltoid muscle*: https://en.wikipedia.org/wiki/Deltoid_muscle (infobox read 2026-10-22)
- Wikipedia, *Coracobrachialis muscle*: https://en.wikipedia.org/wiki/Coracobrachialis_muscle (infobox read 2026-10-22)
- Wikipedia, *Biceps*: https://en.wikipedia.org/wiki/Biceps (infobox read 2026-10-22)
- Wikipedia, *Brachialis muscle*: https://en.wikipedia.org/wiki/Brachialis_muscle (infobox read 2026-10-22)
- Wikipedia, *Triceps*: https://en.wikipedia.org/wiki/Triceps (infobox read 2026-10-22)
- Wikipedia, *Brachioradialis*: https://en.wikipedia.org/wiki/Brachioradialis (infobox read 2026-10-22)
- Wikipedia, *Rectus abdominis muscle*: https://en.wikipedia.org/wiki/Rectus_abdominis_muscle (infobox read 2026-10-22)
- Wikipedia, *Abdominal external oblique muscle*: https://en.wikipedia.org/wiki/Abdominal_external_oblique_muscle (infobox read 2026-10-22)
- Wikipedia, *Abdominal internal oblique muscle*: https://en.wikipedia.org/wiki/Abdominal_internal_oblique_muscle (infobox read 2026-10-22)
- Wikipedia, *Transverse abdominal muscle*: https://en.wikipedia.org/wiki/Transverse_abdominal_muscle (infobox read 2026-10-22)
- Wikipedia, *Iliopsoas*: https://en.wikipedia.org/wiki/Iliopsoas (infobox read 2026-10-22)
- Wikipedia, *Gluteus maximus*: https://en.wikipedia.org/wiki/Gluteus_maximus (infobox read 2026-10-22)
- Wikipedia, *Gluteus medius*: https://en.wikipedia.org/wiki/Gluteus_medius (infobox read 2026-10-22)
- Wikipedia, *Gluteus minimus*: https://en.wikipedia.org/wiki/Gluteus_minimus (infobox read 2026-10-22)
- Wikipedia, *Tensor fasciae latae muscle*: https://en.wikipedia.org/wiki/Tensor_fasciae_latae_muscle (infobox read 2026-10-22)
- Wikipedia, *Rectus femoris muscle*: https://en.wikipedia.org/wiki/Rectus_femoris_muscle (infobox read 2026-10-22)
- Wikipedia, *Vastus lateralis muscle*: https://en.wikipedia.org/wiki/Vastus_lateralis_muscle (infobox read 2026-10-22)
- Wikipedia, *Vastus medialis*: https://en.wikipedia.org/wiki/Vastus_medialis (infobox read 2026-10-22)
- Wikipedia, *Vastus intermedius muscle*: https://en.wikipedia.org/wiki/Vastus_intermedius_muscle (infobox read 2026-10-22)
- Wikipedia, *Sartorius*: https://en.wikipedia.org/wiki/Sartorius (infobox read 2026-10-22)
- Wikipedia, *Adductor longus muscle*: https://en.wikipedia.org/wiki/Adductor_longus_muscle (infobox read 2026-10-22)
- Wikipedia, *Adductor brevis muscle*: https://en.wikipedia.org/wiki/Adductor_brevis_muscle (infobox read 2026-10-22)
- Wikipedia, *Pectineus muscle*: https://en.wikipedia.org/wiki/Pectineus_muscle (infobox read 2026-10-22)
- Wikipedia, *Gracilis muscle*: https://en.wikipedia.org/wiki/Gracilis_muscle (infobox read 2026-10-22)
- Wikipedia, *Adductor magnus muscle*: https://en.wikipedia.org/wiki/Adductor_magnus_muscle (infobox read 2026-10-22)
- Wikipedia, *Biceps femoris muscle*: https://en.wikipedia.org/wiki/Biceps_femoris_muscle (infobox read 2026-10-22)
- Wikipedia, *Semitendinosus muscle*: https://en.wikipedia.org/wiki/Semitendinosus_muscle (infobox read 2026-10-22)
- Wikipedia, *Semimembranosus muscle*: https://en.wikipedia.org/wiki/Semimembranosus_muscle (infobox read 2026-10-22)
- Wikipedia, *Gastrocnemius muscle*: https://en.wikipedia.org/wiki/Gastrocnemius_muscle (infobox read 2026-10-22)
- Wikipedia, *Soleus muscle*: https://en.wikipedia.org/wiki/Soleus_muscle (infobox read 2026-10-22)
- Wikipedia, *Tibialis anterior muscle*: https://en.wikipedia.org/wiki/Tibialis_anterior_muscle (infobox read 2026-10-22)
- Wikipedia, *Fibularis longus*: https://en.wikipedia.org/wiki/Fibularis_longus (infobox read 2026-10-22)
- Wikipedia, *Fibularis brevis*: https://en.wikipedia.org/wiki/Fibularis_brevis (infobox read 2026-10-22)
- Wikipedia, *Flexor carpi radialis muscle*: https://en.wikipedia.org/wiki/Flexor_carpi_radialis_muscle (infobox read 2026-10-22)
- Wikipedia, *Flexor carpi ulnaris muscle*: https://en.wikipedia.org/wiki/Flexor_carpi_ulnaris_muscle (infobox read 2026-10-22)
- Wikipedia, *Extensor carpi radialis longus muscle*: https://en.wikipedia.org/wiki/Extensor_carpi_radialis_longus_muscle (infobox read 2026-10-22)
- Wikipedia, *Extensor carpi ulnaris muscle*: https://en.wikipedia.org/wiki/Extensor_carpi_ulnaris_muscle (infobox read 2026-10-22)
- Wikipedia, *Anconeus muscle*: https://en.wikipedia.org/wiki/Anconeus_muscle (infobox read 2026-10-22)
- Wikipedia, *Multifidus muscle*: https://en.wikipedia.org/wiki/Multifidus_muscle (infobox read 2026-10-22)

**Studies**

- **Holzbaur2007**: Holzbaur KRS, Murray WM, Gold GE, Delp SL (2007). Upper limb muscle volumes in adult subjects. J Biomech 40(4):742-9. https://nmbl.stanford.edu/publications/pdf/Holzbaur2007a.pdf
- **Ward2009**: Ward SR, Eng CM, Smallwood LH, Lieber RL (2009). Are current measurements of lower extremity muscle architecture accurate? Clin Orthop Relat Res 467(4):1074-82. https://pubmed.ncbi.nlm.nih.gov/18972175/ [abstract read]
- **Handsfield2014**: Handsfield GG et al. (2014). Relationships of 35 lower limb muscles to height and body mass quantified using MRI. J Biomech 47(3):631-8. https://pubmed.ncbi.nlm.nih.gov/24368144/ [abstract read]
- **Chen2011**: Chen TC et al. (2011). Comparison in eccentric exercise-induced muscle damage among four limb muscles. Eur J Appl Physiol 111(2):211-23. https://pubmed.ncbi.nlm.nih.gov/20852880/ [abstract read]
- **Maeo2021**: Maeo S et al. (2021). Greater hamstrings muscle hypertrophy but similar damage protection after training at long versus short muscle lengths. Med Sci Sports Exerc 53(4):825-37. https://pubmed.ncbi.nlm.nih.gov/33009197/ [abstract read]
- **Kinoshita2023**: Kinoshita M et al. (2023). Triceps surae muscle hypertrophy is greater after standing versus seated calf-raise training. Front Physiol 14:1272106. https://pubmed.ncbi.nlm.nih.gov/38156065/ [abstract read]
- **Kubo2019**: Kubo K et al. (2019). Effects of squat training with different depths on lower limb muscle volumes. Eur J Appl Physiol 119(9):1933-42. https://pubmed.ncbi.nlm.nih.gov/31230110/ [abstract read]
- **Kojic2022**: Kojic F et al. (2022). Does back squat exercise lead to regional hypertrophy among quadriceps femoris muscles? Int J Environ Res Public Health 19(23):16226. https://pmc.ncbi.nlm.nih.gov/articles/PMC9737272/ [abstract read]
- **Ekstrom2003**: Ekstrom RA et al. (2003). Surface electromyographic analysis of exercises for the trapezius and serratus anterior muscles. J Orthop Sports Phys Ther 33(5):247-58. https://pubmed.ncbi.nlm.nih.gov/12774999/ [abstract read]
- **Reinold2004**: Reinold MM et al. (2004). Electromyographic analysis of the rotator cuff and deltoid musculature during common shoulder external rotation exercises. J Orthop Sports Phys Ther 34(7):385-94. https://pubmed.ncbi.nlm.nih.gov/15296366/ [abstract read]
- **Reinold2007**: Reinold MM et al. (2007). Electromyographic analysis of the supraspinatus and deltoid muscles during 3 common rehabilitation exercises. J Athl Train 42(4). https://pubmed.ncbi.nlm.nih.gov/18174934/ [abstract read]
- **Decker2003**: Decker MJ et al. (2003). Subscapularis muscle activity during selected rehabilitation exercises. Am J Sports Med 31(1):126-34. https://pubmed.ncbi.nlm.nih.gov/12531769/ [abstract read]
- **Juan2024**: Juan J et al. (2024). Hip flexor muscle activation during common rehabilitation and strength exercises. J Clin Med 13(21):6617. https://pmc.ncbi.nlm.nih.gov/articles/PMC11546833/ [abstract read]
- **Imai2017**: Imai A et al. (2017). Evaluation of psoas major and quadratus lumborum recruitment using diffusion-weighted imaging before and after 5 trunk exercises. J Orthop Sports Phys Ther 47(2):108-14. https://www.jospt.org/doi/10.2519/jospt.2017.6730 [abstract read]
- **Escamilla2006a**: Escamilla RF et al. (2006). Electromyographic analysis of traditional and nontraditional abdominal exercises: implications for rehabilitation and training. Phys Ther 86(5):656-71. https://pubmed.ncbi.nlm.nih.gov/16649890/ [abstract read]
- **Collings2026**: Collings TJ et al. (2026). Hip adductor muscle forces during strength training and rehabilitation exercises. Med Sci Sports Exerc. https://doi.org/10.1249/mss.0000000000004002 [abstract read]
- **Plotkin2023**: Plotkin DL et al. (2023). Hip thrust and back squat training elicit similar gluteus muscle hypertrophy and transfer similarly to the deadlift. Front Physiol 14:1279170. https://pubmed.ncbi.nlm.nih.gov/37877099/ [abstract read]
- **Selkowitz2013**: Selkowitz DM et al. (2013). Which exercises target the gluteal muscles while minimizing activation of the tensor fascia lata? J Orthop Sports Phys Ther 43(2):54-64. https://pubmed.ncbi.nlm.nih.gov/23160432/ [abstract read]
- **Conley1997**: Conley MS et al. (1997). Specificity of resistance training responses in neck muscle size and strength. Eur J Appl Physiol 75(5):443-8. https://pubmed.ncbi.nlm.nih.gov/9189733/ [abstract read]
- **Nunes2020**: Nunes JP et al. (2020). Different foot positioning during calf training to induce portion-specific gastrocnemius muscle hypertrophy. J Strength Cond Res 34(8). https://pubmed.ncbi.nlm.nih.gov/32735428/ [abstract read]
- **Ikeda2025**: Ikeda K et al. (2025). Effects of forearm rotation on wrist flexor and extensor muscle activities. J Orthop Surg Res 20. https://pmc.ncbi.nlm.nih.gov/articles/PMC11740565/ [abstract read]
- **RodriguezRidao2020**: Rodríguez-Ridao D et al. (2020). Effect of five bench inclinations on the electromyographic activity of the pectoralis major, anterior deltoid, and triceps brachii during the bench press exercise. Int J Environ Res Public Health 17(19):7339. https://pmc.ncbi.nlm.nih.gov/articles/PMC7579505/ [abstract read]
- **Chaves2020**: Chaves SFN et al. (2020). Effects of horizontal and incline bench press on neuromuscular adaptations in untrained young men. Int J Exerc Sci. https://pmc.ncbi.nlm.nih.gov/articles/PMC7449336/ [abstract read]
- **Caufriez2018**: Caufriez M et al. (2018). The role of the muscle brachioradialis in elbow flexion: an electromyographic study. J Hand Surg Asian Pac Vol 23(1). https://pubmed.ncbi.nlm.nih.gov/29409427/ [abstract read]
- **Kholinne2018**: Kholinne E et al. (2018). The different role of each head of the triceps brachii muscle in elbow extension. Acta Orthop Traumatol Turc 52(3). https://pmc.ncbi.nlm.nih.gov/articles/PMC6136322/ [abstract read]
- **Moore2020**: Moore D et al. (2020). A systematic review and meta-analysis of common therapeutic exercises that generate highest muscle activity in the gluteus medius and gluteus minimus segments. Int J Sports Phys Ther 15(6). https://pmc.ncbi.nlm.nih.gov/articles/PMC7727410/ [abstract read]
- **Messer2018**: Messer DJ et al. (2018). Hamstring muscle use in women during hip extension and the Nordic hamstring exercise: a functional magnetic resonance imaging study. J Orthop Sports Phys Ther 48(8):607-12. https://pubmed.ncbi.nlm.nih.gov/29685059/ [abstract read]
- **Maeo2024**: Maeo S et al. (2024). Hamstrings hypertrophy is specific to the training exercise: Nordic hamstring versus lengthened state eccentric training. Med Sci Sports Exerc 56(10). https://pmc.ncbi.nlm.nih.gov/articles/PMC11419281/ [abstract read]
- **Pulkovski2012**: Pulkovski N et al. (2012). Ultrasound assessment of transversus abdominis muscle contraction ratio during abdominal hollowing. Eur Spine J 21. https://pmc.ncbi.nlm.nih.gov/articles/PMC3535209/ [abstract read]

**Licences and artwork**

- Creative Commons, CC BY-SA 4.0 legal code: https://creativecommons.org/licenses/by-sa/4.0/legalcode.en (page read)
- Creative Commons FAQ: https://creativecommons.org/faq/ (page read)
- Wikimedia Commons file pages listed in §6 (licence metadata read through the Commons API on 2026-10-22)
- npm registry entries for react-muscle-highlighter, react-body-highlighter, body-muscles (licence field read on 2026-10-22)

# ASCEND v8 research: mapping exercises onto detailed muscles

> **Build decision (2026-10-22):** the app ships **54 keys**. Following §2 of `v8-anatomy.md`, levator scapulae is folded into `trap_upper` and coracobrachialis is left out; the rules file the app reads (`services/sidecar/app/modules/workouts/library_data/muscle_rules.json`) is this document's table with those two keys folded the same way. See ADR-0021.

Status: research document for the v8 build. Date: 2026-10-22.
Companion files: `v8-anatomy.md` (the muscle list and anatomy) and `v8-exercise-muscle-rules.json` (the same rules as this document, machine-readable).

> **Read this first.** Every weight in this document is an **estimate for a fatigue model**, not a measured activation. EMG amplitude, MRI signal change and hypertrophy studies tell us *which* muscles an exercise emphasises and roughly *in what order*. None of them gives a number that can be copied into a weight. The weights below turn that ordering into three or four levels (1.0 / 0.75 / 0.5 / 0.25) so the recovery engine can run deterministically. Where no study was read for a rule, the rule is marked **E** (estimated).

Source marks used in this document: **[abstract read]** = the study's abstract was read (PubMed / Europe PMC); **[snippet]** = only a search-result snippet was seen; **[unverified]** = an inference of the author with no direct source. Full texts were not read except where stated.

## 1. The problem

ASCEND's library comes from free-exercise-db (FEDB) ([FEDB]). The bundled copy has **876 exercises**. Each lists `primary` and `secondary` muscles using only **17 coarse names**. Counted on the bundled file, the primary-muscle frequencies are: quadriceps 148, shoulders 129, abdominals 93, chest 84, hamstrings 79, triceps 73, biceps 53, lats 38, middle back 34, calves 28, lower back 27, forearms 25, glutes 22, traps 15, adductors 13, neck 8, abductors 8.

v7 mapped those 17 names onto 19 regions (`library.py`: primary → 1.0, secondary → 0.5, with name keywords picking the chest or delt region). v8 tracks **56 muscle keys** (the owner's list plus the additions agreed for this release; the full list and the reasons are in `v8-anatomy.md`). So each coarse name has to be split, and the split depends on the exercise. Incline pressing is not flat pressing; an overhead triceps extension is not a pushdown.

The mapper must stay **pure and deterministic**: same name and same FEDB lists always give the same weights. That keeps the "Why?" panel explainable and lets a test pin every output.

## 2. Reference frame: target, synergist, stabiliser

ExRx.net classifies muscles in an exercise as *target*, *synergists*, *stabilisers* and *dynamic stabilisers* ([ExRx] [snippet]). ASCEND uses the same idea as weight levels:

| Role | Weight | Meaning in ASCEND |
|---|---|---|
| Target | 1.0 | Main mover; the exercise is chosen for it |
| Strong synergist | 0.75 | Clearly worked, but second to the target (an ASCEND addition to ExRx's three levels) |
| Synergist | 0.5 | Assists the movement |
| Stabiliser | 0.25 | Holds a joint or posture; light fatigue |

Why 0.5 for a secondary muscle: a 2026 dose-response meta-regression found that counting indirect sets as half a set (the "fractional" method) predicted hypertrophy best, and that telling direct and indirect sets apart "appears essential" ([Pelland2026] [abstract read]). That supports a 0.5 factor for work that is not direct. It does not prove 0.5 is right for fatigue; it is the best published anchor available.

## 3. What the literature says, muscle group by muscle group

Only claims supported by the abstract of a study that was read are stated as findings. EMG shows muscle excitation during the exercise; it does not reliably predict growth (Plotkin et al. 2023 found that higher glute EMG in the hip thrust did not translate into more glute growth than squats ([Plotkin2023] [abstract read])). Longitudinal MRI or ultrasound growth studies are therefore weighted above EMG where both exist.

### 3.1 Chest (pectoralis major heads, pectoralis minor, serratus anterior)

- **Bench angle.** In 30 trained adults at 60% 1RM, upper-pec EMG peaked at a **30°** incline; middle and lower pec were highest at **0°** (flat); anterior deltoid was highest at **60°**. Inclines above 45° raised deltoid activity and reduced pectoral performance ([RodriguezRidao2020] [abstract read]). → *incline* puts the clavicular head first and raises the front delt; *flat* puts the sternal head first.
- **Training study.** After incline vs flat training in untrained men, muscle thickness at the second intercostal space (upper chest) grew more in the incline group (mean difference 0.62 cm vs horizontal); the other sites did not differ ([Chaves2020] [abstract read]). → supports "incline = clavicular target".
- **Decline.** The 2020 paper's introduction reports earlier work finding more lower-pec activity with a decline press ([RodriguezRidao2020] [abstract read]); the original decline study (Glass & Armstrong 1997) was seen only as a citation ([GlassArmstrong1997] [snippet]). → decline: sternal target, clavicular low.
- **Flyes.** Barbell bench press activated pectoralis major, anterior deltoid and triceps more than dumbbell flyes; biceps (as stabiliser) was more active in flyes ([Solstad2020] [abstract read]). In another EMG study the fly produced low medial/posterior deltoid activity (3.4% and 2.5% MVIC) ([Campos2020] [abstract read]). → fly: pec target, front delt and short-head biceps as stabilisers.
- **Pullover.** The barbell pullover emphasised pectoralis major more than latissimus dorsi ([Marchetti2011] [abstract read]); a 2026 review agrees ([DiFonza2026] [abstract read]).
- **Push-ups and serratus.** The standard push-up *plus* gave the highest serratus anterior activation (to 123% MVIC) with the lowest upper-trap/serratus ratio ([Ludewig2004] [abstract read]). Narrow-base push-ups raised triceps and pectoralis activity, and trunk muscles worked as stabilisers ([Marcolin2015] [abstract read]).
- **Grip width.** Narrow-grip bench pressing changed triceps, biceps and anterior-deltoid activity compared with wide grips ([Saeterbakken2021] [abstract read]).
- **Dips and pectoralis minor.** No dip EMG study and no pectoralis minor exercise study was read. Pectoralis minor depresses and protracts the scapula (see `v8-anatomy.md`), which a dip demands; its dip weight (0.5) is **E**.

### 3.2 Shoulders (deltoid heads, rotator cuff)

- **Press vs raise.** Shoulder press: anterior 33.3% MVIC, medial 27.9%, posterior 11.4%. Lateral raise: anterior 21.2%, medial 30.3%, posterior 24%. Bench press and fly gave medial ≤ 5% and posterior ≤ 3.5% ([Campos2020] [abstract read]). → press: anterior target, lateral synergist; lateral raise: lateral target with anterior and posterior as synergists; bench press: no lateral or posterior weight.
- **Raise variations.** Internal humeral rotation during lateral raises raised posterior deltoid, triceps and upper trapezius activity; external rotation raised anterior and medial deltoid; the front raise mainly works anterior deltoid and pectoralis major ([Coratella2020] [abstract read]).
- **Behind-the-neck press.** Back overhead press raised medial and posterior (and partly anterior) deltoid; front press favoured pectoralis major; upper trapezius did not differ ([Coratella2022] [abstract read]).
- **Rear delt and cuff.** Side-lying external rotation gave the most infraspinatus (62% MVIC) and teres minor (67%). Prone horizontal abduction at 100° with external rotation gave the most supraspinatus (82%), middle deltoid (87%) and posterior deltoid (88%) ([Reinold2004] [abstract read]). A neutral hand position on the reverse-fly machine increased posterior deltoid and infraspinatus activity vs pronated ([Schoenfeld2013] [abstract read]).
- **Supraspinatus.** Full can, empty can and prone full can gave similar supraspinatus activity; the empty can recruited more middle deltoid ([Reinold2007] [abstract read]). → lateral raises carry supraspinatus at 0.5.
- **Subscapularis.** Push-up plus and diagonal exercises activated both parts of subscapularis more than traditional internal rotation exercises ([Decker2003] [abstract read]). Only explicit "internal rotation" exercises get subscapularis as target; push-up subscapularis weight is left out (**E**: avoids loading a deep muscle the map cannot show well).

### 3.3 Arms (biceps heads, brachialis, brachioradialis, triceps heads, forearm)

- **Triceps long head.** 12 weeks of cable elbow extension in the overhead position grew the triceps more than the neutral (pushdown-like) position, "particularly in the biarticular triceps brachii long head", even with lower loads ([Maeo2023] [abstract read]). The long head contributes more to elbow extension at shoulder elevation, and the medial head takes over at 90° and above ([Kholinne2018] [abstract read]). → overhead and lying extensions: long head target; pushdowns and kickbacks: lateral and medial heads target, long head 0.5.
- **Biceps by curl type.** Preacher curls grew the distal arm region; incline curls produced no significant regional growth in that study ([ZabaletaKorta2023] [abstract read]). Training in the initial elbow angles (long length) produced more distal biceps growth ([Pedrosa2023] [abstract read]). Incline and standard dumbbell curls keep the biceps active through the whole range; preacher curls only over a short range ([Oliveira2009] [abstract read]). None of these studies measured the long and short heads separately, so the head weights for incline (long head first) and preacher (short head first) follow the common anatomical argument (the long head crosses the shoulder; see `v8-anatomy.md`) and are **E**.
- **Brachioradialis.** EMG suggests brachioradialis is one of the main elbow flexors, slightly *more* active in supination ([Caufriez2018] [abstract read]). This does not support the popular claim that hammer curls single out brachioradialis. ASCEND still gives hammer and reverse curls brachioradialis 1.0 because in those grips the biceps loses its supination role (anatomy), but this is **E** and the conflict is stated here.
- **Forearm.** Forearm rotation changed wrist muscle activity: extensor carpi radialis brevis rose with pronation during wrist extension; flexor carpi radialis rose with supination during wrist flexion ([Ikeda2025] [abstract read]). → palms-up wrist curls: flexors target; palms-down: extensors target.

### 3.4 Back (lats, teres, trapezius parts, rhomboids, erectors)

- **Pull-ups and chin-ups.** Average activation: latissimus dorsi 117-130% MVIC, biceps 78-96%, infraspinatus 71-79%, lower trapezius 45-56%, pectoralis major 44-57%, erector spinae 39-41%, external oblique 31-35%. Pectoralis major and biceps were higher in the chin-up; the movement starts with lower trapezius and pectoralis major ([Youdas2010] [abstract read]).
- **Grip width.** Lat pulldown grip width (1-2× biacromial) gave broadly similar activation; medium grip had minor advantages ([Andersen2014] [abstract read]). → no grip-width rule.
- **Rows vs pulldowns.** The highest lat-to-biceps ratio came in the wide-grip pulldown and the seated row; middle trapezius/rhomboid activity was highest in the seated row; actively retracting the scapula did not change it ([Lehman2004] [abstract read]). A 2026 review favours the front pulldown and, in rows, a narrower grip and lower shoulder abduction for lat EMG ([DiFonza2026] [abstract read]).
- **Trapezius parts.** The unilateral shrug produced the most upper-trap EMG; the prone overhead arm raise (Y raise) the most lower-trap; serratus was highest with large scapular upward rotation ([Ekstrom2003] [abstract read]).
- **Erector spinae.** Barbell deadlift, hex-bar deadlift and hip thrust did not differ in erector spinae EMG; the hip thrust gave the highest gluteus maximus and the barbell deadlift the highest biceps femoris ([Andersen2018] [abstract read]). Romanian deadlift, Roman-chair back extension and seated machine back extension gave the same erector activity ([Andersen2021] [abstract read]).
- **Teres major.** No exercise study was read. It acts with the lats (adduction, extension, internal rotation; `v8-anatomy.md`), so it follows the lats at 0.75 (**E**).

### 3.5 Core (rectus abdominis, obliques, transversus, quadratus lumborum, hip flexors)

- **Crunch family.** Among commercial devices and common exercises, external and internal oblique EMG was highest for the Ab Slide, Torso Track, crunch and bent-knee sit-up; rectus femoris (hip flexor) activity was highest for the bent-knee sit-up and several devices ([Escamilla2006b] [abstract read]).
- **Leg raises and rollouts.** Upper and lower rectus and oblique EMG were highest for the Power Wheel (pike, knee-up, roll-out) and hanging knee-ups with straps; these also loaded "extraneous" muscles such as rectus femoris ([Escamilla2006a] [abstract read]). Exercises in deep hip flexion activated iliopsoas more ([Juan2024] [abstract read]).
- **Planks and side planks.** Diffusion-weighted MRI showed the elbow-toe (front) bridge recruited psoas major most and the side bridge recruited quadratus lumborum most ([Imai2017] [abstract read]). The side bridge was suggested for gluteus medius and external oblique strengthening ([Ekstrom2007] [abstract read]).
- **Transversus.** Abdominal hollowing (drawing-in) is the standard selective manoeuvre for transversus abdominis ([Pulkovski2012] [abstract read]); a drawing-in programme thickened transversus on ultrasound ([Lee2015] [abstract read]). → vacuum / drawing-in: transversus target.
- **Twists.** No twist or wood-chop EMG study was read; trunk rotation is the obliques' anatomical action (`v8-anatomy.md`), so twist rules are **E** apart from the oblique-crunch evidence above.

### 3.6 Thighs and hips

- **Squat vs leg extension.** 10 weeks of full or half squats grew knee extensor volume (4.9% and 4.6%) but **not** rectus femoris or hamstrings; adductors and gluteus maximus grew more with full squats ([Kubo2019] [abstract read]). Another squat study found all four quadriceps grew, rectus femoris and vastus intermedius with smaller effects ([Kojic2022] [abstract read]). The single-joint knee extension gave higher rectus femoris EMG than the leg press, while the leg press gave higher vastus lateralis EMG ([Stien2021] [abstract read]). Knee-extension training produced uneven growth across the quadriceps ([Ema2013] [abstract read]). → squats: vasti target, rectus femoris 0.5; leg extension: rectus femoris joins the vasti at 1.0.
- **Glutes.** Squats and hip thrusts gave similar glute growth; squats grew quadriceps and adductors more ([Plotkin2023] [abstract read]). The hip thrust gave more upper and lower glute max and biceps femoris EMG than the back squat ([Contreras2015] [abstract read]). Step-ups and their variations gave the highest glute max activation in a systematic review, followed by deadlifts, hip thrusts, lunges and squats ([Neto2020] [abstract read]).
- **Glute medius and minimus, TFL.** Side-lying hip abduction was best for gluteus medius ([Distefano2009] [abstract read]). Hip hitch / pelvic drop activated all gluteus medius segments; side-lying abduction, single-leg bridge and single-leg squat targeted gluteus minimus segments ([Moore2020] [abstract read]). The clam, sidestep, unilateral bridge and quadruped hip extension worked the glutes with the least TFL ([Selkowitz2013] [abstract read]). In the monopodal squat, forward lunge and lateral step-up, gluteus medius was the third most active muscle after the vasti ([Muyor2020] [abstract read]).
- **Hamstrings.** Seated leg curls grew the hamstrings more than prone curls (+14% vs +9%), mainly in the biarticular muscles ([Maeo2021] [abstract read]). The 45° hip extension activated the biarticular hamstrings more evenly; the Nordic preferentially recruited semitendinosus ([Messer2018] [abstract read]). Hip-extension training grew biceps femoris long head more than Nordics; both grew semitendinosus ([Bourne2017] [abstract read]). Lengthened-state training grew biceps femoris long head more than Nordics, while Nordics grew knee flexors that do not extend the hip ([Maeo2024] [abstract read]).
- **Adductors.** The Copenhagen adduction produced the highest forces across most adductors; adductor magnus (ischiocondylar part) forces were high in hip-extension exercises; the squat was tier 2 for adductor longus, magnus and gracilis ([Collings2026] [abstract read]).

### 3.7 Calves and shin

- **Standing vs seated.** Standing calf raises grew the gastrocnemius far more than seated raises (lateral head 12.4% vs 1.7%, medial 9.2% vs 0.6%); soleus grew similarly in both (2.1% vs 2.9%) ([Kinoshita2023] [abstract read]). No knee angle isolates soleus or either gastrocnemius head in EMG ([HebertLosier2011] [abstract read]). → seated: soleus target, gastrocnemius 0.25; standing: gastrocnemius target, soleus 0.75.
- **Gastrocnemius heads.** Toes-out favoured the medial head and toes-in the lateral head over 9 weeks ([Nunes2020] [abstract read]). ASCEND keeps one `gastrocnemius` key (see `v8-anatomy.md`), so this is noted but not used.
- **Tibialis anterior and fibularis.** No study was read; their rules come from anatomical action (dorsiflexion; eversion) and are **E**. FEDB has no loaded tibialis exercise (only stretches and foam rolling), so `tibialis_anterior` gets load only from ASCEND's own and custom exercises.

## 4. The mapping algorithm

```
input : name, primary[] and secondary[] (FEDB coarse names), category
output: dict key -> weight in [0, 1]

1. If category == "stretching" or the name matches /smr|stretch|foam roll/ -> {} (no load, as in v7).
2. low = lowercase(name)
3. For each coarse muscle m in primary (scale 1.0) and then in secondary (scale 0.5):
       take REGION_RULES[m] in order; the FIRST rule whose regex matches low wins
       (the last rule of every list is the default and always matches);
       for each (key, w) in that rule: out[key] = max(out[key], w * scale)
4. For each ADDON rule whose regex matches low (and whose "exclude" regex does not):
       for each (key, w): out[key] = max(out[key], w)        # not scaled
5. Drop every key with weight < 0.2 (the floor).
```

Notes:

- **max, not sum.** Two rules naming the same muscle never add up past 1.0. This matches v7's `put()` in `library.py`.
- **Order matters.** Rules are written most-specific first (for example `S3-rear` before `S11-chest-press`, so "reverse machine flyes" is a rear-delt exercise, and `C1-fly-incline` before `C2-fly`).
- **Word boundaries.** Use `\b` where shown. A bare `chin` matched "ma*chin*e" in testing, and a bare `t-bar` matched "uprigh*t bar*bell"; both are fixed in the table.
- **Add-ons** carry muscles FEDB never names (serratus on push-ups, erectors on bent-over rows and barbell squats, grip on hangs and carries).
- **Hand-made ASCEND exercises** (seed, calisthenics and custom exercises with hand-tuned weights) are not FEDB rows. Their old 19-region weights go through the migration table in §8, then a person can tune them.

A reference implementation (Python, about 30 lines) was run over the bundled FEDB file while writing this document; the counts in the tables come from that run. The rules in `v8-exercise-muscle-rules.json` are the same data.

```python
def map_detailed(name, primary, secondary, category=None):
    low = name.lower()
    if category == "stretching" or re.search(r"smr|stretch|foam roll", low):
        return {}
    out = {}
    def put(k, w): out[k] = max(out.get(k, 0.0), w)
    for muscles, scale in ((primary, 1.0), (secondary, 0.5)):
        for m in muscles:
            for rule in RULES["region_rules"][m]:
                if rule["regex"] == "" or re.search(rule["regex"], low):
                    for k, w in rule["weights"].items():
                        put(k, w * scale)
                    break
    for rule in RULES["addons"]:
        if re.search(rule["regex"], low) and not (rule["exclude"] and re.search(rule["exclude"], low)):
            for k, w in rule["weights"].items():
                put(k, w)
    return {k: round(w, 3) for k, w in out.items() if w >= RULES["floor"]}
```

## 5. RULES TABLE

Source column: an author-year tag is a study listed in §11. **E** = estimated (anatomy plus coaching convention; no study read for that rule). **E(anatomy)** = estimated from the muscle's anatomical action in `v8-anatomy.md`. Several tags in one cell: the rule combines them.

*FEDB hits = how many of the 876 bundled FEDB exercises fired the rule (primary or secondary), counted with the reference implementation on 2026-10-22.

#### Coarse muscle: `chest`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| C1-fly-incline | `(incline\|low[- ]?cable\|low[- ]?pulley\|upward).*(fly\|flye\|crossover)\|(fly\|flye\|crossover).*(incline\|low)` | pec_major_clavicular 1, pec_major_sternal 0.5, deltoid_anterior 0.25, biceps_short 0.25 | E | 4 |
| C2-fly | `\b(fly\|flye\|flyes\|flys\|crossover\|pec deck\|butterfly)\b` | pec_major_sternal 1, pec_major_clavicular 0.75, deltoid_anterior 0.25, biceps_short 0.25, coracobrachialis 0.25 | Campos2020,Solstad2020 | 8 |
| C3-pullover | `pullover` | pec_major_sternal 1, latissimus_dorsi 0.5, teres_major 0.5, triceps_long 0.5, serratus_anterior 0.25 | Marchetti2011,DiFonza2026 | 5 |
| C4-dip | `\bdips?\b` | pec_major_sternal 1, pec_minor 0.5, deltoid_anterior 0.5, pec_major_clavicular 0.25 | E | 7 |
| C5-pushup-plus | `push[- ]?up plus\|scap(ular)? push` | serratus_anterior 1, pec_major_sternal 0.5 | Ludewig2004 | 0 |
| C6-pushup-incline | `incline push[- ]?up` | pec_major_sternal 1, deltoid_anterior 0.5, serratus_anterior 0.5, pec_major_clavicular 0.25 | E | 6 |
| C7-pushup-decline | `decline push[- ]?up\|feet elevated\|pike` | pec_major_clavicular 1, pec_major_sternal 0.75, deltoid_anterior 0.75, serratus_anterior 0.5 | E | 2 |
| C8-pushup | `push[- ]?ups?\b\|pushups?\b\|press[- ]?up` | pec_major_sternal 1, pec_major_clavicular 0.5, deltoid_anterior 0.5, serratus_anterior 0.5, triceps_lateral 0.5, triceps_medial 0.5 | Marcolin2015,Ludewig2004 | 12 |
| C9-incline | `incline` | pec_major_clavicular 1, deltoid_anterior 0.75, pec_major_sternal 0.5 | RodriguezRidao2020,Chaves2020 | 9 |
| C10-decline | `decline` | pec_major_sternal 1, pec_major_clavicular 0.25 | RodriguezRidao2020(intro),GlassArmstrong1997[snippet] | 7 |
| C11-closegrip | `close[- ]?grip\|narrow[- ]?grip` | pec_major_sternal 0.75, pec_major_clavicular 0.5, deltoid_anterior 0.5 | Saeterbakken2021 | 4 |
| C0-default | *(default: no trigger matched)* | pec_major_sternal 1, pec_major_clavicular 0.75, pec_minor 0.25 | RodriguezRidao2020 | 70 |

#### Coarse muscle: `shoulders`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| S1-ext-rot | `external rotation\|\bexternal rot` | infraspinatus 1, teres_minor 1, deltoid_posterior 0.5 | Reinold2004 | 4 |
| S2-int-rot | `internal rotation` | subscapularis 1, pec_major_sternal 0.25, teres_major 0.25 | Decker2003,E | 2 |
| S3-rear | `rear\|reverse.*fl[iy]\|face pull\|bent[- ]?over.*(raise\|lateral\|fly)\|prone.*(raise\|fly)\|(raise\|fly).*bent[- ]?over\|lying rear\|back fly\|posterior` | deltoid_posterior 1, infraspinatus 0.5, teres_minor 0.5, trap_middle 0.5, rhomboids 0.5, deltoid_lateral 0.25 | Schoenfeld2013,Reinold2004 | 15 |
| S11-chest-press | `bench\|chest press\|floor press\|push[- ]?ups?\|pushups?\|\bdips?\b\|\bfly\|flye\|crossover\|pec deck\|guillotine` | deltoid_anterior 1, coracobrachialis 0.25 | Campos2020,RodriguezRidao2020 | 73 |
| S4-upright | `upright\|high pull` | deltoid_lateral 1, trap_upper 0.75, deltoid_anterior 0.5, biceps_long 0.25, biceps_short 0.25 | E | 8 |
| S10-pull | `\brows?\b\|pull[- ]?downs?\|pull[- ]?ups?\|\bchin\|face pull\|pullover` | deltoid_posterior 1, infraspinatus 0.5, teres_minor 0.5 | Reinold2004,Youdas2010,E | 22 |
| S5-lateral | `lateral raise\|side raise\|side lateral\|\blateral\b\|\bside\b\|iron cross` | deltoid_lateral 1, deltoid_anterior 0.5, deltoid_posterior 0.5, supraspinatus 0.5, trap_upper 0.5 | Campos2020,Coratella2020,Reinold2007 | 12 |
| S6-front-raise | `front raise\|front .*raise\|front plate\|frontal raise` | deltoid_anterior 1, pec_major_clavicular 0.5, deltoid_lateral 0.25, coracobrachialis 0.25 | Coratella2020 | 7 |
| S7-behind-neck | `behind (the )?neck\|back press` | deltoid_anterior 1, deltoid_lateral 0.75, deltoid_posterior 0.5, trap_upper 0.25, supraspinatus 0.25 | Coratella2022 | 2 |
| S8-arnold | `arnold` | deltoid_anterior 1, deltoid_lateral 0.75, trap_upper 0.25, supraspinatus 0.25 | E | 2 |
| S9-olympic | `clean\|snatch\|jerk` | deltoid_anterior 0.75, trap_upper 0.75, deltoid_lateral 0.5 | E | 41 |
| S0-default | *(default: no trigger matched)* | deltoid_anterior 1, deltoid_lateral 0.5, deltoid_posterior 0.25, trap_upper 0.25, supraspinatus 0.25 | Campos2020,Coratella2022 | 134 |

#### Coarse muscle: `triceps`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| T1-overhead | `overhead\|french\|over ?head\|above head\|seated triceps press\|standing .*triceps (press\|extension)\|tate\|behind the head` | triceps_long 1, triceps_lateral 0.75, triceps_medial 0.75 | Maeo2023,Kholinne2018 | 18 |
| T2-lying | `lying\|skull\|nose\|decline .*extension\|incline .*extension\|jm press` | triceps_long 1, triceps_lateral 0.75, triceps_medial 0.75 | Kholinne2018,E | 12 |
| T3-pushdown | `pushdown\|push[- ]?down\|kickback\|kick back\|press[- ]?down` | triceps_lateral 1, triceps_medial 1, triceps_long 0.5 | Maeo2023 | 5 |
| T4-press | `bench press\|close[- ]?grip\|dips?\b\|push[- ]?up\|board press\|floor press\|pin press` | triceps_lateral 1, triceps_medial 1, triceps_long 0.5 | Saeterbakken2021,E | 61 |
| T0-default | *(default: no trigger matched)* | triceps_lateral 1, triceps_medial 1, triceps_long 0.75 | E | 120 |

#### Coarse muscle: `biceps`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| B1-reverse | `reverse\|pronated\|palms?[- ]down\|overhand` | brachioradialis 1, brachialis 1, wrist_extensors 0.5, biceps_long 0.25, biceps_short 0.25 | Caufriez2018(partial),E | 6 |
| B2-hammer | `hammer\|neutral\|rope curl\|cross[- ]?body\|pinwheel\|zottman` | brachialis 1, brachioradialis 1, biceps_long 0.5, biceps_short 0.5 | E | 8 |
| B3-incline | `incline\|drag curl\|behind` | biceps_long 1, biceps_short 0.75, brachialis 0.75, brachioradialis 0.5 | Oliveira2009,E | 10 |
| B4-preacher | `preacher\|spider\|concentration\|scott\|prone incline\|high cable\|overhead cable` | biceps_short 1, brachialis 1, biceps_long 0.75, brachioradialis 0.5 | ZabaletaKorta2023,Pedrosa2023,E | 11 |
| B5-chin | `\bchin[- ]?up\|\bchin\b\|underhand\|supinated (pull\|row)` | biceps_long 1, biceps_short 1, brachialis 0.75, brachioradialis 0.5 | Youdas2010 | 5 |
| B0-default | *(default: no trigger matched)* | biceps_long 1, biceps_short 1, brachialis 0.75, brachioradialis 0.5 | Caufriez2018,E | 80 |

#### Coarse muscle: `forearms`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| F1-ext | `(palms?[- ]?down\|reverse\|pronated\|overhand).*wrist\|wrist.*(extension\|palms?[- ]?down)\|wrist roller` | wrist_extensors 1, brachioradialis 0.25 | Ikeda2025 | 6 |
| F2-flex | `wrist curl\|palms?[- ]?up\|finger curl\|hand squeeze\|gripper\|grip` | wrist_flexors 1, wrist_extensors 0.25 | Ikeda2025 | 13 |
| F3-carry | `carry\|farmer\|hang\b\|dead hang\|towel\|plate pinch\|pinch` | wrist_flexors 1, wrist_extensors 0.5, brachioradialis 0.25 | E | 10 |
| F4-rot | `supination\|pronation\|rotation` | brachioradialis 0.5, wrist_flexors 0.5, wrist_extensors 0.5, biceps_short 0.25 | E | 3 |
| F0-default | *(default: no trigger matched)* | wrist_flexors 1, wrist_extensors 0.5, brachioradialis 0.5 | E | 83 |

#### Coarse muscle: `lats`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| L1-straight-arm | `straight[- ]?arm\|pullover\|lat pushdown` | latissimus_dorsi 1, teres_major 0.75, triceps_long 0.5, pec_major_sternal 0.25 | Marchetti2011,E | 7 |
| L2-chin | `\bchin\|underhand\|reverse grip\|supinated` | latissimus_dorsi 1, teres_major 0.75, biceps_long 0.75, biceps_short 0.75, brachialis 0.5, trap_lower 0.5, pec_major_sternal 0.25 | Youdas2010,Lehman2004 | 8 |
| L3-row | `\brows?\b\|rowing` | latissimus_dorsi 1, trap_middle 0.75, rhomboids 0.75, teres_major 0.5, deltoid_posterior 0.5, trap_lower 0.25 | Lehman2004,DiFonza2026 | 31 |
| L0-default | *(default: no trigger matched)* | latissimus_dorsi 1, teres_major 0.75, trap_lower 0.5, rhomboids 0.5, trap_middle 0.25, deltoid_posterior 0.25, infraspinatus 0.25 | Youdas2010,Andersen2014,Lehman2004 | 33 |

#### Coarse muscle: `middle back`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| M1-shrug | `shrug\|scapular (retraction\|pull)` | trap_middle 1, rhomboids 1, trap_upper 0.5, levator_scapulae 0.25 | E | 3 |
| M2-chin | `\bchin\|pull[- ]?up\|pulldown` | latissimus_dorsi 1, teres_major 0.75, trap_lower 0.5, rhomboids 0.5, trap_middle 0.5 | Youdas2010 | 18 |
| M0-default | *(default: no trigger matched)* | trap_middle 1, rhomboids 1, latissimus_dorsi 0.75, deltoid_posterior 0.5, trap_lower 0.5, teres_major 0.5, infraspinatus 0.25 | Lehman2004,Ekstrom2003 | 70 |

#### Coarse muscle: `traps`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| P1-upright | `upright\|high pull` | trap_upper 1, deltoid_lateral 0.75, levator_scapulae 0.25 | E | 8 |
| P2-lower | `\by[- ]?raise\|prone.*overhead\|scapular (pull\|depression)\|scap pull` | trap_lower 1, trap_middle 0.5, serratus_anterior 0.25 | Ekstrom2003 | 1 |
| P3-shrug | `shrug\|clean\|snatch\|deadlift\|rack pull` | trap_upper 1, levator_scapulae 0.5, trap_middle 0.25 | Ekstrom2003 | 52 |
| P0-default | *(default: no trigger matched)* | trap_upper 1, trap_middle 0.5, levator_scapulae 0.5, trap_lower 0.25 | E | 31 |

#### Coarse muscle: `neck`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| N1-flex | `face up\|front\|flexion\|\bchin to chest` | sternocleidomastoid 1 | E(anatomy) | 2 |
| N2-ext | `face down\|harness\|extension\|back\b` | splenius 1, trap_upper 0.25 | Conley1997 | 2 |
| N3-side | `side\|lateral` | sternocleidomastoid 0.75, splenius 0.75, levator_scapulae 0.25 | E(anatomy) | 1 |
| N0-default | *(default: no trigger matched)* | sternocleidomastoid 0.75, splenius 0.75, trap_upper 0.25 | E | 0 |

#### Coarse muscle: `lower back`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| Lb1-deadlift | `deadlift\|rack pull\|atlas\|stone\|good morning` | erector_spinae 1, gluteus_maximus 0.5, adductor_magnus 0.5, quadratus_lumborum 0.25, trap_upper 0.25 | Andersen2018,Andersen2021 | 33 |
| Lb2-ext | `hyperextension\|back extension\|superman\|reverse hyper\|bird dog\|roman chair` | erector_spinae 1, gluteus_maximus 0.5, quadratus_lumborum 0.25 | Andersen2021,Ekstrom2007 | 3 |
| Lb3-bridge | `bridge\|pelvic tilt` | gluteus_maximus 1, erector_spinae 0.5 | E | 0 |
| Lb0-default | *(default: no trigger matched)* | erector_spinae 1, quadratus_lumborum 0.5 | E | 76 |

#### Coarse muscle: `abdominals`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| A1-vacuum | `vacuum\|drawing[- ]?in\|hollowing\|draw[- ]?in` | transversus_abdominis 1, internal_obliques 0.5 | Lee2015,Pulkovski2012 | 0 |
| A2-side-plank | `side (plank\|bridge)\|side bend\|oblique bridge\|suitcase` | external_obliques 1, internal_obliques 0.75, quadratus_lumborum 0.75, gluteus_medius 0.5 | Ekstrom2007,Imai2017 | 7 |
| A3-twist | `twist\|russian\|wood ?chop\|rotation\|windmill\|oblique\|elbow to knee\|bicycle\|air bike\|cross[- ]?body crunch\|landmine\|pallof\|spell caster` | external_obliques 1, internal_obliques 1, rectus_abdominis 0.5 | Escamilla2006b,E | 21 |
| A4-legraise | `leg raise\|knee raise\|knee[- ]?up\|leg lift\|hanging\|reverse crunch\|flutter\|scissor\|toes to bar\|knee tuck\|jackknife\|v[- ]?up\|l[- ]?sit\|mountain climber` | rectus_abdominis 1, external_obliques 0.75, iliopsoas 0.75, internal_obliques 0.5, rectus_femoris 0.5 | Escamilla2006a,Juan2024 | 10 |
| A5-rollout | `roll[- ]?out\|ab wheel\|ab roller\|ab slide\|barbell rollout\|body saw` | rectus_abdominis 1, external_obliques 0.75, internal_obliques 0.75, transversus_abdominis 0.5, latissimus_dorsi 0.25 | Escamilla2006a,Escamilla2006b | 4 |
| A6-plank | `plank\|front bridge\|hollow\|dead bug\|stir the pot` | rectus_abdominis 1, transversus_abdominis 0.75, external_obliques 0.5, internal_obliques 0.5, iliopsoas 0.25 | Imai2017,E | 2 |
| A7-situp | `sit[- ]?ups?\|situp\|jack ?knife\|decline crunch` | rectus_abdominis 1, external_obliques 0.5, internal_obliques 0.5, iliopsoas 0.5, rectus_femoris 0.25 | Escamilla2006a,Escamilla2006b | 7 |
| A8-crunch | `crunch\|curl[- ]?up\|cable crunch\|rope crunch` | rectus_abdominis 1, external_obliques 0.5, internal_obliques 0.5, transversus_abdominis 0.25 | Escamilla2006b | 12 |
| A0-default | *(default: no trigger matched)* | rectus_abdominis 1, external_obliques 0.5, internal_obliques 0.5, transversus_abdominis 0.25 | E | 78 |

#### Coarse muscle: `quadriceps`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| Q1-legext | `leg extension\|knee extension\|sissy\|reverse nordic` | rectus_femoris 1, vastus_lateralis 1, vastus_medialis 1, vastus_intermedius 1 | Stien2021,Ema2013 | 3 |
| Q2-lunge | `lunge\|split squat\|step[- ]?up\|bulgarian\|pistol\|single[- ]leg squat\|one[- ]leg squat\|skater` | vastus_lateralis 1, vastus_medialis 1, vastus_intermedius 1, gluteus_maximus 0.75, rectus_femoris 0.5, gluteus_medius 0.5, adductor_magnus 0.5 | Neto2020,Muyor2020 | 19 |
| Q3-squat | `squat\|leg press\|hack\|thruster\|wall sit\|front squat\|zercher\|belt squat` | vastus_lateralis 1, vastus_medialis 1, vastus_intermedius 1, rectus_femoris 0.5, gluteus_maximus 0.5, adductor_magnus 0.5 | Kubo2019,Kojic2022,Plotkin2023 | 50 |
| Q4-hipflex | `hip flexion\|knee drive\|march\|high knee` | rectus_femoris 1, iliopsoas 1, tensor_fasciae_latae 0.25, sartorius 0.25 | Juan2024 | 1 |
| Q0-default | *(default: no trigger matched)* | vastus_lateralis 1, vastus_medialis 1, vastus_intermedius 1, rectus_femoris 0.75 | E | 135 |

#### Coarse muscle: `hamstrings`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| H1-nordic | `nordic\|glute[- ]?ham\|natural ham\|razor curl` | semitendinosus 1, biceps_femoris 0.75, semimembranosus 0.5, gastrocnemius 0.25 | Messer2018,Bourne2017,Maeo2024 | 3 |
| H2-legcurl | `leg curl\|hamstring curl\|ball (leg )?curl\|lying curl\|seated curl\|slider curl` | biceps_femoris 1, semitendinosus 1, semimembranosus 1, gastrocnemius 0.25, sartorius 0.25, gracilis 0.25 | Maeo2021 | 5 |
| H3-hinge | `romanian\|stiff[- ]?leg\|straight[- ]?leg\|good morning\|\brdl\b\|deadlift\|hip extension\|hyperextension\|back extension\|pull[- ]?through\|kettlebell swing\|\bswing` | biceps_femoris 1, semimembranosus 1, semitendinosus 0.75, gluteus_maximus 0.75, adductor_magnus 0.75, erector_spinae 0.5 | Messer2018,Bourne2017,Andersen2021,Collings2026 | 40 |
| H4-knee-dominant | `squat\|leg press\|lunge\|step[- ]?up\|hack\|thruster` | biceps_femoris 0.5, semitendinosus 0.5, semimembranosus 0.5 | Kubo2019,Plotkin2023 | 67 |
| H0-default | *(default: no trigger matched)* | biceps_femoris 1, semitendinosus 1, semimembranosus 1 | E | 136 |

#### Coarse muscle: `glutes`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| G1-abduct | `abduct\|clam\|side[- ]?lying\|lateral (band )?walk\|monster\|sidestep\|side step\|fire hydrant\|hip hike\|pelvic drop\|hip hitch` | gluteus_medius 1, gluteus_minimus 0.75, gluteus_maximus 0.5, tensor_fasciae_latae 0.5 | Distefano2009,Moore2020,Selkowitz2013 | 1 |
| G2-thrust | `hip thrust\|glute bridge\|bridge\|kickback\|kick back\|donkey kick\|hip extension\|pull[- ]?through\|frog pump` | gluteus_maximus 1, biceps_femoris 0.5, semitendinosus 0.25, semimembranosus 0.25, gluteus_medius 0.25, erector_spinae 0.25 | Contreras2015,Andersen2018 | 10 |
| G3-single-bridge | `single[- ]?leg (bridge\|hip thrust)\|one[- ]?leg (bridge\|hip)` | gluteus_maximus 1, gluteus_medius 0.5, biceps_femoris 0.5 | Moore2020 | 0 |
| G0-default | *(default: no trigger matched)* | gluteus_maximus 1, gluteus_medius 0.25, gluteus_minimus 0.25 | Neto2020,E | 213 |

#### Coarse muscle: `abductors`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| Ab1-clam | `clam` | gluteus_medius 1, gluteus_maximus 0.5, gluteus_minimus 0.5, tensor_fasciae_latae 0.25 | Selkowitz2013 | 0 |
| Ab0-default | *(default: no trigger matched)* | gluteus_medius 1, gluteus_minimus 0.75, tensor_fasciae_latae 0.5, gluteus_maximus 0.25 | Distefano2009,Moore2020 | 32 |

#### Coarse muscle: `adductors`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| Ad1-copenhagen | `copenhagen\|side[- ]?lying adduction\|adductor plank` | adductor_longus 1, adductor_magnus 1, gracilis 1 | Collings2026 | 0 |
| Ad2-sumo | `sumo\|wide stance\|plie\|cossack\|side lunge\|lateral lunge` | adductor_magnus 1, adductor_longus 0.75, gracilis 0.5 | E | 6 |
| Ad0-default | *(default: no trigger matched)* | adductor_longus 1, adductor_magnus 0.75, gracilis 0.5 | Collings2026,E | 36 |

#### Coarse muscle: `calves`

| Rule | Name trigger (regex, case-insensitive) | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|
| Ca1-seated | `seated.*(calf\|heel)\|bent[- ]?knee calf\|soleus` | soleus 1, gastrocnemius 0.25, fibularis 0.25 | Kinoshita2023 | 3 |
| Ca2-tib | `tibialis\|toe raise\|dorsiflexion\|tib raise\|anterior tibialis` | tibialis_anterior 1 | E(anatomy) | 0 |
| Ca3-everse | `eversion\|peroneal\|fibularis` | fibularis 1 | E(anatomy) | 0 |
| Ca0-default | *(default: no trigger matched)* | gastrocnemius 1, soleus 0.75, fibularis 0.25 | Kinoshita2023,HebertLosier2011 | 181 |

#### Pattern add-ons (applied to every exercise whose name matches; not scaled)

| Rule | Name trigger | Not when name matches | Detailed muscles (weight) | Source | FEDB hits* |
|---|---|---|---|---|---|
| X1-bent-row | `bent[- ]?over\|\bt[- ]?bar\b\|pendlay\|yates\|renegade` | `seated\|chest[- ]?supported\|lying\|incline\|prone` | erector_spinae 0.5 | E | 13 |
| X2-barbell-axial | `squat\|deadlift\|good morning\|clean\|snatch\|rack pull\|atlas` | `machine\|smith\|leg press\|hack\|belt\|goblet\|bodyweight\|jump\|sissy\|wall` | erector_spinae 0.5, rectus_abdominis 0.25 | Andersen2018,E | 112 |
| X3-pushup | `push[- ]?ups?\b\|pushups?\b` | — | serratus_anterior 0.5, rectus_abdominis 0.25 | Ludewig2004,Marcolin2015 | 21 |
| X4-carry | `carry\|farmer\|yoke\|suitcase` | — | wrist_flexors 1, trap_upper 0.75, quadratus_lumborum 0.5, external_obliques 0.5, internal_obliques 0.5 | E | 3 |
| X5-standing-overhead | `standing.*(press\|military)\|military press\|push press\|jerk` | — | rectus_abdominis 0.25, erector_spinae 0.25 | E | 26 |
| X6-hang | `pull[- ]?ups?\|\bchin[- ]?ups?\|hanging\|muscle[- ]?up` | — | wrist_flexors 0.25, rectus_abdominis 0.25 | Youdas2010 | 14 |
| X7-unilateral-leg | `lunge\|split squat\|step[- ]?up\|single[- ]leg squat\|pistol\|bulgarian` | — | gluteus_medius 0.5 | Muyor2020 | 18 |
| X8-dip | `\bdips?\b` | — | pec_major_sternal 0.5, deltoid_anterior 0.5, pec_minor 0.25 | E | 8 |

## 6. Worked examples (output of the reference implementation)

| Exercise (FEDB) | FEDB primary / secondary | Rules fired | Detailed load (weight ≥ 0.2) |
|---|---|---|---|
| Barbell Bench Press - Medium Grip | chest / shoulders, triceps | C0-default, S11-chest-press, T4-press | pec_major_sternal 1, pec_major_clavicular 0.75, deltoid_anterior 0.5, triceps_lateral 0.5, triceps_medial 0.5, pec_minor 0.25, triceps_long 0.25 |
| Barbell Incline Bench Press - Medium Grip | chest / shoulders, triceps | C9-incline, S11-chest-press, T4-press | pec_major_clavicular 1, deltoid_anterior 0.75, pec_major_sternal 0.5, triceps_lateral 0.5, triceps_medial 0.5, triceps_long 0.25 |
| Dips - Chest Version | chest / shoulders, triceps | C4-dip, S11-chest-press, T4-press, X8-dip | pec_major_sternal 1, pec_minor 0.5, deltoid_anterior 0.5, triceps_lateral 0.5, triceps_medial 0.5, pec_major_clavicular 0.25, triceps_long 0.25 |
| Pushups | chest / shoulders, triceps | C8-pushup, S11-chest-press, T4-press, X3-pushup | pec_major_sternal 1, pec_major_clavicular 0.5, deltoid_anterior 0.5, serratus_anterior 0.5, triceps_lateral 0.5, triceps_medial 0.5, triceps_long 0.25, rectus_abdominis 0.25 |
| Cable Crossover | chest / shoulders | C2-fly, S11-chest-press | pec_major_sternal 1, pec_major_clavicular 0.75, deltoid_anterior 0.5, biceps_short 0.25, coracobrachialis 0.25 |
| Side Lateral Raise | shoulders / — | S5-lateral | deltoid_lateral 1, deltoid_anterior 0.5, deltoid_posterior 0.5, supraspinatus 0.5, trap_upper 0.5 |
| Face Pull | shoulders / middle back | S3-rear, M0-default | deltoid_posterior 1, infraspinatus 0.5, teres_minor 0.5, trap_middle 0.5, rhomboids 0.5, latissimus_dorsi 0.375, deltoid_lateral 0.25, trap_lower 0.25, teres_major 0.25 |
| Lying Triceps Press | triceps / — | T2-lying | triceps_long 1, triceps_lateral 0.75, triceps_medial 0.75 |
| Triceps Pushdown | triceps / — | T3-pushdown | triceps_lateral 1, triceps_medial 1, triceps_long 0.5 |
| Hammer Curls | biceps / — | B2-hammer | brachialis 1, brachioradialis 1, biceps_long 0.5, biceps_short 0.5 |
| Preacher Curl | biceps / — | B4-preacher | biceps_short 1, brachialis 1, biceps_long 0.75, brachioradialis 0.5 |
| Pullups | lats / biceps, middle back | L0-default, B0-default, M2-chin, X6-hang | latissimus_dorsi 1, teres_major 0.75, trap_lower 0.5, rhomboids 0.5, biceps_long 0.5, biceps_short 0.5, brachialis 0.375, trap_middle 0.25, deltoid_posterior 0.25, infraspinatus 0.25, brachioradialis 0.25, wrist_flexors 0.25, rectus_abdominis 0.25 |
| Seated Cable Rows | middle back / biceps, lats, shoulders | M0-default, B0-default, L3-row, S10-pull | trap_middle 1, rhomboids 1, latissimus_dorsi 0.75, deltoid_posterior 0.5, trap_lower 0.5, teres_major 0.5, biceps_long 0.5, biceps_short 0.5, brachialis 0.375, infraspinatus 0.25, brachioradialis 0.25, teres_minor 0.25 |
| Barbell Shrug | traps / — | P3-shrug | trap_upper 1, levator_scapulae 0.5, trap_middle 0.25 |
| Barbell Full Squat | quadriceps / calves, glutes, hamstrings, lower back | Q3-squat, Ca0-default, G0-default, H4-knee-dominant, Lb0-default, X2-barbell-axial | vastus_lateralis 1, vastus_medialis 1, vastus_intermedius 1, rectus_femoris 0.5, gluteus_maximus 0.5, adductor_magnus 0.5, gastrocnemius 0.5, erector_spinae 0.5, soleus 0.375, biceps_femoris 0.25, semitendinosus 0.25, semimembranosus 0.25, quadratus_lumborum 0.25, rectus_abdominis 0.25 |
| Leg Extensions | quadriceps / — | Q1-legext | rectus_femoris 1, vastus_lateralis 1, vastus_medialis 1, vastus_intermedius 1 |
| Romanian Deadlift | hamstrings / calves, glutes, lower back | H3-hinge, Ca0-default, G0-default, Lb1-deadlift, X2-barbell-axial | biceps_femoris 1, semimembranosus 1, semitendinosus 0.75, gluteus_maximus 0.75, adductor_magnus 0.75, erector_spinae 0.5, gastrocnemius 0.5, soleus 0.375, rectus_abdominis 0.25 |
| Seated Leg Curl | hamstrings / — | H2-legcurl | biceps_femoris 1, semitendinosus 1, semimembranosus 1, gastrocnemius 0.25, sartorius 0.25, gracilis 0.25 |
| Barbell Hip Thrust | glutes / calves, hamstrings | G2-thrust, Ca0-default, H0-default | gluteus_maximus 1, biceps_femoris 0.5, semitendinosus 0.5, semimembranosus 0.5, gastrocnemius 0.5, soleus 0.375, gluteus_medius 0.25, erector_spinae 0.25 |
| Thigh Abductor | abductors / glutes | Ab0-default, G1-abduct | gluteus_medius 1, gluteus_minimus 0.75, tensor_fasciae_latae 0.5, gluteus_maximus 0.25 |
| Standing Calf Raises | calves / — | Ca0-default | gastrocnemius 1, soleus 0.75, fibularis 0.25 |
| Seated Calf Raise | calves / — | Ca1-seated | soleus 1, gastrocnemius 0.25, fibularis 0.25 |
| Crunches | abdominals / — | A8-crunch | rectus_abdominis 1, external_obliques 0.5, internal_obliques 0.5, transversus_abdominis 0.25 |
| Russian Twist | abdominals / lower back | A3-twist, Lb0-default | external_obliques 1, internal_obliques 1, rectus_abdominis 0.5, erector_spinae 0.5, quadratus_lumborum 0.25 |
| Plank | abdominals / — | A6-plank | rectus_abdominis 1, transversus_abdominis 0.75, external_obliques 0.5, internal_obliques 0.5, iliopsoas 0.25 |
| Hanging Leg Raise | abdominals / — | A4-legraise, X6-hang | rectus_abdominis 1, external_obliques 0.75, iliopsoas 0.75, internal_obliques 0.5, rectus_femoris 0.5, wrist_flexors 0.25 |
| Barbell Deadlift | lower back / calves, forearms, glutes, hamstrings, lats, middle back, quadriceps, traps | Lb1-deadlift, Ca0-default, F0-default, G0-default, H3-hinge, L0-default, M0-default, Q0-default, P3-shrug, X2-barbell-axial | erector_spinae 1, gluteus_maximus 0.5, adductor_magnus 0.5, trap_upper 0.5, gastrocnemius 0.5, wrist_flexors 0.5, biceps_femoris 0.5, semimembranosus 0.5, latissimus_dorsi 0.5, rhomboids 0.5, trap_middle 0.5, vastus_lateralis 0.5, vastus_medialis 0.5, vastus_intermedius 0.5, soleus 0.375, semitendinosus 0.375, teres_major 0.375, rectus_femoris 0.375, quadratus_lumborum 0.25, wrist_extensors 0.25, brachioradialis 0.25, trap_lower 0.25, deltoid_posterior 0.25, levator_scapulae 0.25, rectus_abdominis 0.25 |

Results of the run: 123 of 876 exercises carry no load (stretches and foam rolling, as in v7). The rest load a median of **8** keys at weight ≥ 0.2. The deadlift is the widest (FEDB lists 8 secondary regions for it).

## 7. Coverage of the 56 keys in FEDB

Exercises loading each key at ≥ 0.75 / at any weight ≥ 0.2:

| Key | ≥ 0.75 | ≥ 0.2 |
|---|---|---|
| pec_major_clavicular | 53 | 128 |
| pec_major_sternal | 68 | 143 |
| pec_minor | 0 | 40 |
| serratus_anterior | 0 | 26 |
| latissimus_dorsi | 60 | 111 |
| trap_upper | 32 | 179 |
| trap_middle | 33 | 124 |
| trap_lower | 1 | 101 |
| rhomboids | 33 | 110 |
| teres_major | 28 | 110 |
| teres_minor | 4 | 41 |
| infraspinatus | 4 | 72 |
| supraspinatus | 0 | 75 |
| subscapularis | 2 | 2 |
| erector_spinae | 16 | 188 |
| quadratus_lumborum | 6 | 97 |
| levator_scapulae | 0 | 90 |
| sternocleidomastoid | 3 | 3 |
| splenius | 3 | 3 |
| deltoid_anterior | 93 | 285 |
| deltoid_lateral | 23 | 219 |
| deltoid_posterior | 15 | 170 |
| biceps_long | 41 | 121 |
| biceps_short | 41 | 136 |
| brachialis | 50 | 120 |
| coracobrachialis | 0 | 17 |
| triceps_lateral | 70 | 216 |
| triceps_long | 42 | 218 |
| triceps_medial | 70 | 216 |
| brachioradialis | 13 | 184 |
| wrist_flexors | 15 | 119 |
| wrist_extensors | 6 | 113 |
| rectus_abdominis | 59 | 274 |
| external_obliques | 39 | 141 |
| internal_obliques | 30 | 141 |
| transversus_abdominis | 2 | 43 |
| iliopsoas | 10 | 20 |
| gluteus_maximus | 52 | 231 |
| gluteus_medius | 2 | 71 |
| gluteus_minimus | 2 | 39 |
| tensor_fasciae_latae | 0 | 33 |
| rectus_femoris | 70 | 224 |
| vastus_lateralis | 131 | 206 |
| vastus_medialis | 131 | 206 |
| vastus_intermedius | 131 | 206 |
| sartorius | 0 | 6 |
| adductor_longus | 6 | 42 |
| adductor_magnus | 27 | 138 |
| gracilis | 0 | 47 |
| biceps_femoris | 59 | 248 |
| semitendinosus | 59 | 248 |
| semimembranosus | 56 | 248 |
| gastrocnemius | 12 | 188 |
| soleus | 15 | 184 |
| tibialis_anterior | 0 | 0 |
| fibularis | 0 | 15 |

Gaps a programmer should know about:

- `tibialis_anterior` has **no** loaded FEDB exercise. It is loaded only by ASCEND's own or custom exercises (tib raises). The map should show it, but it will usually read "no data". That is honest.
- `subscapularis`, `sternocleidomastoid`, `splenius`, `sartorius`, `iliopsoas` and `fibularis` have few FEDB exercises. Treat them as **readiness-only** keys (no weekly volume target; see §9).
- Deep keys (`pec_minor`, `supraspinatus`, `subscapularis`, `transversus_abdominis`, `quadratus_lumborum`, `vastus_intermedius`, `gluteus_minimus`, `internal_obliques`, `triceps_medial`, `rhomboids`, `soleus` from the front) belong on the map's deep layer (see `v8-anatomy.md` for which view).

## 8. Migrating existing history (19 old regions → 56 keys)

**How ASCEND stores load today.** Fatigue is not stored; `progress/muscle_load.py` recomputes it from logged sets: each set contributes ES = weight(exercise, muscle) × effort, decayed by the muscle's half-life. The weights live per exercise in the `exercise_muscles` table. Personal recovery speed is learned per muscle by `intelligence/personal.py`. So a fair migration has three parts.

1. **Library exercises (FEDB rows): re-map, do not translate.** Recompute their `exercise_muscles` rows with the new mapper from the FEDB name and lists. Every past set then replays with the new weights automatically, because sets point at exercises. This is the most accurate option and needs no guessing.
2. **Hand-made and custom exercises** (rows whose weights were written by hand against the old regions): translate each old region weight `w_old` through the table below. New weight = `w_old × w_table`, combined with **max** when two old regions feed the same key (for example `upper_chest` and `lower_chest` both feed the pec heads). Mark these rows `migrated_from_v7 = true` so the UI can invite a review.
3. **Learned per-muscle parameters** (personal recovery speed, any per-region calibration): each new key **inherits** its parent region's learned value, the region with the largest weight in the table. Keys with no parent start from the population default.

**Why copy and not split.** The engine works out readiness per muscle as fatigue ÷ capacity. If a region's fatigue were *divided* among its children, every child would look fresher than the region did yesterday, and the app would suddenly say "chest recovered" after a heavy bench day. Copying the parent's load at weight 1.0 into its main child (and lower weights into the others) keeps yesterday's readiness the same on migration day. That is the fair choice for the user [unverified: a design argument, not a measured result].

| Old region (v7) | New keys and weights | Reason |
|---|---|---|
| `upper_chest` | pec_major_clavicular 1.0, pec_major_sternal 0.5 | Old rule sent "incline" work here (library.py); new C9-incline gives the same split. |
| `lower_chest` | pec_major_sternal 1.0, pec_major_clavicular 0.5, pec_minor 0.25 | Old default for flat/decline pressing; new C0-default (clavicular 0.75 there; 0.5 here because decline work also landed in this region). |
| `front_delts` | deltoid_anterior 1.0 | One-to-one. |
| `side_delts` | deltoid_lateral 1.0, supraspinatus 0.25 | Lateral raises recruit supraspinatus (Reinold 2007); kept at stabiliser level. |
| `rear_delts` | deltoid_posterior 1.0, infraspinatus 0.5, teres_minor 0.5 | Rear-delt work is horizontal abduction / external rotation (Reinold 2004, Schoenfeld 2013). |
| `biceps` | biceps_long 1.0, biceps_short 1.0, brachialis 0.75, brachioradialis 0.5 | Same as B0-default. |
| `triceps` | triceps_lateral 1.0, triceps_medial 1.0, triceps_long 0.75 | Same as T0-default. |
| `forearms` | wrist_flexors 1.0, wrist_extensors 0.75, brachioradialis 0.5 | Old region mixed flexion and extension work; extensors kept high so no muscle starts falsely "fresh". |
| `traps` | trap_upper 1.0, trap_middle 0.5, levator_scapulae 0.5, trap_lower 0.25 | Old region was mostly shrugs (Ekstrom 2003) plus the old neck rule (neck → traps 0.25). |
| `lats` | latissimus_dorsi 1.0, teres_major 0.75, trap_lower 0.25 | Same as L0-default core. |
| `rhomboids` | rhomboids 1.0, trap_middle 1.0, deltoid_posterior 0.25 | Old "middle back" region; rows load mid-trapezius and rhomboids most (Lehman 2004). |
| `lower_back` | erector_spinae 1.0, quadratus_lumborum 0.5 | Same as Lb0-default. |
| `abs` | rectus_abdominis 1.0, external_obliques 0.5, internal_obliques 0.5, transversus_abdominis 0.25 | Same as A0-default. |
| `obliques` | external_obliques 1.0, internal_obliques 1.0, quadratus_lumborum 0.25 | Same as A3-twist core. |
| `glutes` | gluteus_maximus 1.0, gluteus_medius 0.5, gluteus_minimus 0.25, tensor_fasciae_latae 0.25 | Old map sent FEDB "abductors" to glutes at 0.5, so abductor work lived here. |
| `quads` | vastus_lateralis 1.0, vastus_medialis 1.0, vastus_intermedius 1.0, rectus_femoris 0.75 | Old region held both squats (RF low) and leg extensions (RF high); 0.75 is the compromise. |
| `hamstrings` | biceps_femoris 1.0, semitendinosus 1.0, semimembranosus 1.0 | Same as H0-default. |
| `adductors` | adductor_longus 1.0, adductor_magnus 1.0, gracilis 0.5 | Old region held adductor machine and wide-stance work. |
| `calves` | gastrocnemius 1.0, soleus 1.0 | Old region held standing and seated raises; both heads copied at 1.0. |

Keys with **no** v7 parent, which start at zero load and population defaults: serratus_anterior, subscapularis, sternocleidomastoid, splenius, coracobrachialis, iliopsoas, sartorius, tibialis_anterior, fibularis. The old map had no region for them; the v7 `neck` rule (neck → traps 0.25) is the only exception, and those sets now replay through the `neck` rules.

Migration checks the build should run:

- For a seeded demo history, readiness of each old region on migration day should equal the readiness of its weight-1.0 child within rounding (copy, not split).
- Weekly effective sets: the sum over a region's children is **expected** to be higher than the old region's total, because one set now counts on several keys. Volume targets must change with it (§9).
- An idempotent migration (running it twice changes nothing), with a down-migration that restores the 19-region rows from a saved copy.

## 9. Volume targets and capacity for the new keys (recommendation)

The v7 weekly targets (`weekly_low`/`weekly_high`, effective sets per week) were set per region and are already marked as estimates in `taxonomy.py`. Published volume guidance is per muscle *group*, not per head. Recommendation [unverified, design]:

- **Owner's-list keys that replace an old region one-to-one** (for example `deltoid_lateral`, `latissimus_dorsi`, `gastrocnemius`) inherit the old region's targets.
- **Heads of one muscle** (pec heads, biceps heads, triceps heads, the four quadriceps, the three hamstrings) each inherit the parent's targets. Because one set now loads several heads, each head reaches its target at about the same set count as the old region did.
- **Small, deep or rarely loaded keys** (rotator cuff, `pec_minor`, `levator_scapulae`, `coracobrachialis`, `transversus_abdominis`, `quadratus_lumborum`, neck, `sartorius`, `gracilis`, `tibialis_anterior`, `fibularis`, `iliopsoas`, `tensor_fasciae_latae`) are **readiness-only**: show recovery colour, never an "under-trained" warning. No evidence was found for weekly set targets for these muscles, and warning a user that their subscapularis is under-trained would be noise.
- Half-life and capacity: inherit the parent's values. Size alone does not set recovery time. In one study, the same maximal eccentric protocol damaged elbow flexors and extensors more than knee extensors, and knee flexors more than knee extensors ([Chen2011] [abstract read]). Keep these values as estimates and let the personal recovery model adjust them.

## 10. Tests the build should add

1. **Golden table:** the 27 examples in §6 pinned in a unit test (exact weights).
2. **Every key reachable:** each of the 56 keys has at least one exercise (FEDB, seed or calisthenics) that loads it at ≥ 0.5, except where a key is readiness-only by design. If `tibialis_anterior` has none, add a hand-made "Tibialis raise".
3. **Regex hygiene:** no rule matches inside another word (a test list including "machine", "upright barbell", "reverse machine flyes", "seated one-leg calf raise").
4. **Determinism:** shuffling the order of FEDB `secondary` lists does not change the output (true because combine = max).
5. **Old-vs-new sanity:** for every FEDB exercise, the new top-weighted key belongs to the old top region (or a documented exception such as the pullover).

## 11. Limitations and what is unverified

- Every weight is an estimate. EMG amplitude depends on electrode placement and normalisation and is not a dose of fatigue. The weights should be described in the viva as "a transparent, literature-ordered heuristic", not as measured activation.
- Only abstracts were read for the studies below (the Holzbaur 2007 full text was read for `v8-anatomy.md`). Numbers quoted here come from the abstracts.
- Many studies are small (8-30 participants), often untrained or female-only samples (for example Messer 2018, Zabaleta-Korta 2023, Pedrosa 2023), which limits how far they generalise.
- No study was read for dips, twists, wood chops, teres major, tibialis anterior or fibularis. Their rules are **E**.
- The hammer-curl rule conflicts with the one brachioradialis EMG study read (§3.3).
- FEDB's `secondary` lists are generous (for example calves listed for squats and hip thrusts). The mapper respects them at half weight; a later version could trim them per exercise.

## 12. References

- **RodriguezRidao2020**: Rodríguez-Ridao D et al. (2020). Effect of five bench inclinations on the electromyographic activity of the pectoralis major, anterior deltoid, and triceps brachii during the bench press exercise. Int J Environ Res Public Health 17(19):7339. https://pmc.ncbi.nlm.nih.gov/articles/PMC7579505/ [abstract read]
- **Chaves2020**: Chaves SFN et al. (2020). Effects of horizontal and incline bench press on neuromuscular adaptations in untrained young men. Int J Exerc Sci. https://pmc.ncbi.nlm.nih.gov/articles/PMC7449336/ [abstract read]
- **GlassArmstrong1997**: Glass SC, Armstrong T (1997). Electromyographical activity of the pectoralis muscle during incline and decline bench presses. J Strength Cond Res 11(3). https://www.researchgate.net/profile/Stephen-Glass [snippet]
- **Saeterbakken2021**: Saeterbakken AH et al. (2021). The effect of grip width on muscle strength and electromyographic activity in bench press among novice- and resistance-trained men. Int J Environ Res Public Health 18(12):6444. https://pmc.ncbi.nlm.nih.gov/articles/PMC8296276/ [abstract read]
- **Solstad2020**: Solstad TE et al. (2020). A comparison of muscle activation between barbell bench press and dumbbell flyes in resistance-trained males. J Sports Sci Med. https://pmc.ncbi.nlm.nih.gov/articles/PMC7675616/ [abstract read]
- **Marchetti2011**: Marchetti PH, Uchida MC (2011). Effects of the pullover exercise on the pectoralis major and latissimus dorsi muscles as evaluated by EMG. J Appl Biomech 27(4):380-4. https://pubmed.ncbi.nlm.nih.gov/21975179/ [abstract read]
- **DiFonza2026**: Di Fonza et al. (2026). Electromyographic analysis of latissimus dorsi activation during common resistance training exercises: a narrative review. J Funct Morphol Kinesiol 11(3):315. https://pubmed.ncbi.nlm.nih.gov/42647355/ [abstract read]
- **Ludewig2004**: Ludewig PM et al. (2004). Relative balance of serratus anterior and upper trapezius muscle activity during push-up exercises. Am J Sports Med 32(2):484-93. https://pubmed.ncbi.nlm.nih.gov/14977678/ [abstract read]
- **Marcolin2015**: Marcolin G et al. (2015). Selective activation of shoulder, trunk, and arm muscles: a comparative analysis of different push-up variants. J Athl Train 50(11). https://pmc.ncbi.nlm.nih.gov/articles/PMC4732391/ [abstract read]
- **Campos2020**: Campos YAC et al. (2020). Different shoulder exercises affect the activation of deltoid portions in resistance-trained individuals. J Hum Kinet 75:5-14. https://pmc.ncbi.nlm.nih.gov/articles/PMC7706677/ [abstract read]
- **Coratella2020**: Coratella G et al. (2020). An electromyographic analysis of lateral raise variations and frontal raise in competitive bodybuilders. Int J Environ Res Public Health 17(17):6015. https://pubmed.ncbi.nlm.nih.gov/32824894/ [abstract read]
- **Coratella2022**: Coratella G et al. (2022). Front vs back and barbell vs machine overhead press: an electromyographic analysis. Front Physiol 13:825880. https://pmc.ncbi.nlm.nih.gov/articles/PMC9354811/ [abstract read]
- **Reinold2004**: Reinold MM et al. (2004). Electromyographic analysis of the rotator cuff and deltoid musculature during common shoulder external rotation exercises. J Orthop Sports Phys Ther 34(7):385-94. https://pubmed.ncbi.nlm.nih.gov/15296366/ [abstract read]
- **Reinold2007**: Reinold MM et al. (2007). Electromyographic analysis of the supraspinatus and deltoid muscles during 3 common rehabilitation exercises. J Athl Train 42(4). https://pubmed.ncbi.nlm.nih.gov/18174934/ [abstract read]
- **Decker2003**: Decker MJ et al. (2003). Subscapularis muscle activity during selected rehabilitation exercises. Am J Sports Med 31(1):126-34. https://pubmed.ncbi.nlm.nih.gov/12531769/ [abstract read]
- **Schoenfeld2013**: Schoenfeld B et al. (2013). Effect of hand position on EMG activity of the posterior shoulder musculature during a horizontal abduction exercise. J Strength Cond Res 27(10). https://pubmed.ncbi.nlm.nih.gov/23302754/ [abstract read]
- **Maeo2023**: Maeo S et al. (2023). Triceps brachii hypertrophy is substantially greater after elbow extension training performed in the overhead versus neutral arm position. Eur J Sport Sci 23(7):1240-50. https://pubmed.ncbi.nlm.nih.gov/35819335/ [abstract read]
- **Kholinne2018**: Kholinne E et al. (2018). The different role of each head of the triceps brachii muscle in elbow extension. Acta Orthop Traumatol Turc 52(3). https://pmc.ncbi.nlm.nih.gov/articles/PMC6136322/ [abstract read]
- **ZabaletaKorta2023**: Zabaleta-Korta A et al. (2023). Regional hypertrophy: the effect of exercises at long and short muscle lengths in recreationally trained women. J Hum Kinet 87. https://pmc.ncbi.nlm.nih.gov/articles/PMC10407320/ [abstract read]
- **Pedrosa2023**: Pedrosa GF et al. (2023). Training in the initial range of motion promotes greater muscle adaptations than at final in the arm flexors of young women. Sports 11(2):39. https://pmc.ncbi.nlm.nih.gov/articles/PMC9960616/ [abstract read]
- **Oliveira2009**: Oliveira LF et al. (2009). Effect of the shoulder position on the biceps brachii EMG in different dumbbell curls. J Sports Sci Med 8(1). https://pmc.ncbi.nlm.nih.gov/articles/PMC3737788/ [abstract read]
- **Caufriez2018**: Caufriez M et al. (2018). The role of the muscle brachioradialis in elbow flexion: an electromyographic study. J Hand Surg Asian Pac Vol 23(1). https://pubmed.ncbi.nlm.nih.gov/29409427/ [abstract read]
- **Ikeda2025**: Ikeda K et al. (2025). Effects of forearm rotation on wrist flexor and extensor muscle activities. J Orthop Surg Res 20. https://pmc.ncbi.nlm.nih.gov/articles/PMC11740565/ [abstract read]
- **Youdas2010**: Youdas JW et al. (2010). Surface electromyographic activation patterns and elbow joint motion during a pull-up, chin-up, or Perfect-Pullup rotational exercise. J Strength Cond Res 24(12):3404-14. https://pubmed.ncbi.nlm.nih.gov/21068680/ [abstract read]
- **Andersen2014**: Andersen V et al. (2014). Effects of grip width on muscle strength and activation in the lat pull-down. J Strength Cond Res 28(4):1135-42. https://pubmed.ncbi.nlm.nih.gov/24662157/ [abstract read]
- **Lehman2004**: Lehman GJ et al. (2004). Variations in muscle activation levels during traditional latissimus dorsi weight training exercises: an experimental study. Dyn Med 3:4. https://pmc.ncbi.nlm.nih.gov/articles/PMC449729/ [abstract read]
- **Ekstrom2003**: Ekstrom RA et al. (2003). Surface electromyographic analysis of exercises for the trapezius and serratus anterior muscles. J Orthop Sports Phys Ther 33(5):247-58. https://pubmed.ncbi.nlm.nih.gov/12774999/ [abstract read]
- **Conley1997**: Conley MS et al. (1997). Specificity of resistance training responses in neck muscle size and strength. Eur J Appl Physiol 75(5):443-8. https://pubmed.ncbi.nlm.nih.gov/9189733/ [abstract read]
- **Andersen2018**: Andersen V et al. (2018). Electromyographic comparison of barbell deadlift, hex bar deadlift, and hip thrust exercises: a cross-over study. J Strength Cond Res 32(3):587-93. https://pubmed.ncbi.nlm.nih.gov/28151780/ [abstract read]
- **Andersen2021**: Andersen V et al. (2021). Comparison of muscle activity in three single-joint, hip extension exercises in resistance-trained women. J Sports Sci Med 20(2):181-7. https://pmc.ncbi.nlm.nih.gov/articles/PMC8057707/ [abstract read]
- **Ekstrom2007**: Ekstrom RA et al. (2007). Electromyographic analysis of core trunk, hip, and thigh muscles during 9 rehabilitation exercises. J Orthop Sports Phys Ther 37(12):754-62. https://pubmed.ncbi.nlm.nih.gov/18560185/ [abstract read]
- **Imai2017**: Imai A et al. (2017). Evaluation of psoas major and quadratus lumborum recruitment using diffusion-weighted imaging before and after 5 trunk exercises. J Orthop Sports Phys Ther 47(2):108-14. https://www.jospt.org/doi/10.2519/jospt.2017.6730 [abstract read]
- **Escamilla2006a**: Escamilla RF et al. (2006). Electromyographic analysis of traditional and nontraditional abdominal exercises: implications for rehabilitation and training. Phys Ther 86(5):656-71. https://pubmed.ncbi.nlm.nih.gov/16649890/ [abstract read]
- **Escamilla2006b**: Escamilla RF et al. (2006). An electromyographic analysis of commercial and common abdominal exercises: implications for rehabilitation and training. J Orthop Sports Phys Ther 36(2):45-57. https://pubmed.ncbi.nlm.nih.gov/16494072/ [abstract read]
- **Lee2015**: Lee JS et al. (2015). Effects of selective exercise for the deep abdominal muscles and lumbar stabilization exercise on the thickness of the transversus abdominis and postural maintenance. J Phys Ther Sci 27(2):367-70. https://pmc.ncbi.nlm.nih.gov/articles/PMC4339139/ [abstract read]
- **Pulkovski2012**: Pulkovski N et al. (2012). Ultrasound assessment of transversus abdominis muscle contraction ratio during abdominal hollowing. Eur Spine J 21. https://pmc.ncbi.nlm.nih.gov/articles/PMC3535209/ [abstract read]
- **Juan2024**: Juan J et al. (2024). Hip flexor muscle activation during common rehabilitation and strength exercises. J Clin Med 13(21):6617. https://pmc.ncbi.nlm.nih.gov/articles/PMC11546833/ [abstract read]
- **Stien2021**: Stien N et al. (2021). Electromyographic comparison of five lower-limb muscles between single- and multi-joint exercises among trained men. J Sports Sci Med 20(1):56-61. https://pmc.ncbi.nlm.nih.gov/articles/PMC7919354/ [abstract read]
- **Ema2013**: Ema R et al. (2013). Inhomogeneous architectural changes of the quadriceps femoris induced by resistance training. Eur J Appl Physiol 113(11):2691-703. https://pubmed.ncbi.nlm.nih.gov/23949789/ [abstract read]
- **Kubo2019**: Kubo K et al. (2019). Effects of squat training with different depths on lower limb muscle volumes. Eur J Appl Physiol 119(9):1933-42. https://pubmed.ncbi.nlm.nih.gov/31230110/ [abstract read]
- **Kojic2022**: Kojic F et al. (2022). Does back squat exercise lead to regional hypertrophy among quadriceps femoris muscles? Int J Environ Res Public Health 19(23):16226. https://pmc.ncbi.nlm.nih.gov/articles/PMC9737272/ [abstract read]
- **Plotkin2023**: Plotkin DL et al. (2023). Hip thrust and back squat training elicit similar gluteus muscle hypertrophy and transfer similarly to the deadlift. Front Physiol 14:1279170. https://pubmed.ncbi.nlm.nih.gov/37877099/ [abstract read]
- **Neto2020**: Neto WK et al. (2020). Gluteus maximus activation during common strength and hypertrophy exercises: a systematic review. J Sports Sci Med 19(1):195-203. https://pubmed.ncbi.nlm.nih.gov/32132843/ [abstract read]
- **Muyor2020**: Muyor JM et al. (2020). Electromyographic activity in the gluteus medius, gluteus maximus, biceps femoris, vastus lateralis, vastus medialis and rectus femoris during the monopodal squat, forward lunge and lateral step-up exercises. PLoS One 15(4):e0230841. https://pmc.ncbi.nlm.nih.gov/articles/PMC7112217/ [abstract read]
- **Contreras2015**: Contreras B et al. (2015). A comparison of gluteus maximus, biceps femoris, and vastus lateralis EMG activity in the back squat and barbell hip thrust exercises. J Appl Biomech 31(6):452-8. https://pubmed.ncbi.nlm.nih.gov/26214739/ [abstract read]
- **Distefano2009**: Distefano LJ et al. (2009). Gluteal muscle activation during common therapeutic exercises. J Orthop Sports Phys Ther 39(7):532-40. https://pubmed.ncbi.nlm.nih.gov/19574661/ [abstract read]
- **Moore2020**: Moore D et al. (2020). A systematic review and meta-analysis of common therapeutic exercises that generate highest muscle activity in the gluteus medius and gluteus minimus segments. Int J Sports Phys Ther 15(6). https://pmc.ncbi.nlm.nih.gov/articles/PMC7727410/ [abstract read]
- **Selkowitz2013**: Selkowitz DM et al. (2013). Which exercises target the gluteal muscles while minimizing activation of the tensor fascia lata? J Orthop Sports Phys Ther 43(2):54-64. https://pubmed.ncbi.nlm.nih.gov/23160432/ [abstract read]
- **Messer2018**: Messer DJ et al. (2018). Hamstring muscle use in women during hip extension and the Nordic hamstring exercise: a functional magnetic resonance imaging study. J Orthop Sports Phys Ther 48(8):607-12. https://pubmed.ncbi.nlm.nih.gov/29685059/ [abstract read]
- **Bourne2017**: Bourne MN et al. (2017). Impact of the Nordic hamstring and hip extension exercises on hamstring architecture and morphology. Br J Sports Med 51(5):469-77. https://pubmed.ncbi.nlm.nih.gov/27660368/ [abstract read]
- **Maeo2021**: Maeo S et al. (2021). Greater hamstrings muscle hypertrophy but similar damage protection after training at long versus short muscle lengths. Med Sci Sports Exerc 53(4):825-37. https://pubmed.ncbi.nlm.nih.gov/33009197/ [abstract read]
- **Maeo2024**: Maeo S et al. (2024). Hamstrings hypertrophy is specific to the training exercise: Nordic hamstring versus lengthened state eccentric training. Med Sci Sports Exerc 56(10). https://pmc.ncbi.nlm.nih.gov/articles/PMC11419281/ [abstract read]
- **Collings2026**: Collings TJ et al. (2026). Hip adductor muscle forces during strength training and rehabilitation exercises. Med Sci Sports Exerc. https://doi.org/10.1249/mss.0000000000004002 [abstract read]
- **Kinoshita2023**: Kinoshita M et al. (2023). Triceps surae muscle hypertrophy is greater after standing versus seated calf-raise training. Front Physiol 14:1272106. https://pubmed.ncbi.nlm.nih.gov/38156065/ [abstract read]
- **HebertLosier2011**: Hébert-Losier K et al. (2011). Peak triceps surae muscle activity is not specific to knee flexion angles during MVIC. J Electromyogr Kinesiol 21(5):819-26. https://pubmed.ncbi.nlm.nih.gov/21669538/ [abstract read]
- **Nunes2020**: Nunes JP et al. (2020). Different foot positioning during calf training to induce portion-specific gastrocnemius muscle hypertrophy. J Strength Cond Res 34(8). https://pubmed.ncbi.nlm.nih.gov/32735428/ [abstract read]
- **Pelland2026**: Pelland JC et al. (2026). The resistance training dose response: meta-regressions exploring the effects of weekly volume and frequency on muscle hypertrophy and strength gains. Sports Med. https://pubmed.ncbi.nlm.nih.gov/41343037/ [abstract read]
- **Holzbaur2007**: Holzbaur KRS, Murray WM, Gold GE, Delp SL (2007). Upper limb muscle volumes in adult subjects. J Biomech 40(4):742-9. https://nmbl.stanford.edu/publications/pdf/Holzbaur2007a.pdf
- **Chen2011**: Chen TC et al. (2011). Comparison in eccentric exercise-induced muscle damage among four limb muscles. Eur J Appl Physiol 111(2):211-23. https://pubmed.ncbi.nlm.nih.gov/20852880/ [abstract read]
- **ExRx**: ExRx.net. Exercise, muscle, and program notes (target, synergist, stabiliser, dynamic stabiliser definitions). https://exrx.net/Notes/Notes [snippet]
- **FEDB**: yuhonas/free-exercise-db: open public-domain exercise dataset (Unlicense). https://github.com/yuhonas/free-exercise-db

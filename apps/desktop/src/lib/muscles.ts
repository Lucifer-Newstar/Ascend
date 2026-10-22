/**
 * The 54 muscles and heads ASCEND tracks (taxonomy v2; keys match the sidecar's
 * progress/taxonomy.py). `short` is the name used on small cards; `label` everywhere else.
 */
export interface MuscleInfo {
  key: string;
  label: string;
  short: string;
  region: string;
  parent: string;
  deep: boolean;
}

export const MUSCLES: MuscleInfo[] = [
  { key: "pec_major_clavicular", label: "Upper chest (clavicular head)", short: "Upper chest", region: "Chest", parent: "Pectoralis major", deep: false },
  { key: "pec_major_sternal", label: "Mid/lower chest (sternal head)", short: "Lower chest", region: "Chest", parent: "Pectoralis major", deep: false },
  { key: "pec_minor", label: "Pectoralis minor", short: "Pectoralis minor", region: "Chest", parent: "", deep: true },
  { key: "serratus_anterior", label: "Serratus anterior", short: "Serratus anterior", region: "Chest", parent: "", deep: false },
  { key: "latissimus_dorsi", label: "Lats (latissimus dorsi)", short: "Lats", region: "Back", parent: "", deep: false },
  { key: "teres_major", label: "Teres major", short: "Teres major", region: "Back", parent: "", deep: false },
  { key: "trap_upper", label: "Upper trapezius", short: "Upper trapezius", region: "Back", parent: "Trapezius", deep: false },
  { key: "trap_middle", label: "Middle trapezius", short: "Middle trapezius", region: "Back", parent: "Trapezius", deep: false },
  { key: "trap_lower", label: "Lower trapezius", short: "Lower trapezius", region: "Back", parent: "Trapezius", deep: false },
  { key: "rhomboids", label: "Rhomboids", short: "Rhomboids", region: "Back", parent: "", deep: true },
  { key: "infraspinatus", label: "Infraspinatus", short: "Infraspinatus", region: "Back", parent: "Rotator cuff", deep: false },
  { key: "teres_minor", label: "Teres minor", short: "Teres minor", region: "Back", parent: "Rotator cuff", deep: false },
  { key: "supraspinatus", label: "Supraspinatus", short: "Supraspinatus", region: "Back", parent: "Rotator cuff", deep: true },
  { key: "subscapularis", label: "Subscapularis", short: "Subscapularis", region: "Back", parent: "Rotator cuff", deep: true },
  { key: "erector_spinae", label: "Erector spinae", short: "Lower back (erectors)", region: "Back", parent: "", deep: false },
  { key: "quadratus_lumborum", label: "Quadratus lumborum", short: "Quadratus lumborum", region: "Back", parent: "", deep: true },
  { key: "sternocleidomastoid", label: "Sternocleidomastoid", short: "Sternocleidomastoid", region: "Neck", parent: "", deep: false },
  { key: "splenius", label: "Splenius (neck extensors)", short: "Neck extensors", region: "Neck", parent: "", deep: false },
  { key: "deltoid_anterior", label: "Front delts", short: "Front delts", region: "Shoulders", parent: "Deltoid", deep: false },
  { key: "deltoid_lateral", label: "Side delts", short: "Side delts", region: "Shoulders", parent: "Deltoid", deep: false },
  { key: "deltoid_posterior", label: "Rear delts", short: "Rear delts", region: "Shoulders", parent: "Deltoid", deep: false },
  { key: "biceps_long", label: "Biceps long head", short: "Biceps long head", region: "Arms", parent: "Biceps brachii", deep: false },
  { key: "biceps_short", label: "Biceps short head", short: "Biceps short head", region: "Arms", parent: "Biceps brachii", deep: false },
  { key: "brachialis", label: "Brachialis", short: "Brachialis", region: "Arms", parent: "", deep: false },
  { key: "triceps_lateral", label: "Triceps lateral head", short: "Triceps lateral head", region: "Arms", parent: "Triceps brachii", deep: false },
  { key: "triceps_long", label: "Triceps long head", short: "Triceps long head", region: "Arms", parent: "Triceps brachii", deep: false },
  { key: "triceps_medial", label: "Triceps medial head", short: "Triceps medial head", region: "Arms", parent: "Triceps brachii", deep: true },
  { key: "brachioradialis", label: "Brachioradialis", short: "Brachioradialis", region: "Arms", parent: "Forearm", deep: false },
  { key: "wrist_flexors", label: "Wrist flexors", short: "Wrist flexors", region: "Arms", parent: "Forearm", deep: false },
  { key: "wrist_extensors", label: "Wrist extensors", short: "Wrist extensors", region: "Arms", parent: "Forearm", deep: false },
  { key: "rectus_abdominis", label: "Abs (rectus abdominis)", short: "Abs", region: "Core", parent: "", deep: false },
  { key: "external_obliques", label: "External obliques", short: "External obliques", region: "Core", parent: "Obliques", deep: false },
  { key: "internal_obliques", label: "Internal obliques", short: "Internal obliques", region: "Core", parent: "Obliques", deep: true },
  { key: "transversus_abdominis", label: "Transversus abdominis", short: "Transversus abdominis", region: "Core", parent: "", deep: true },
  { key: "iliopsoas", label: "Hip flexors (iliopsoas)", short: "Hip flexors", region: "Hips", parent: "", deep: true },
  { key: "gluteus_maximus", label: "Gluteus maximus", short: "Glute max", region: "Hips", parent: "Glutes", deep: false },
  { key: "gluteus_medius", label: "Gluteus medius", short: "Glute med", region: "Hips", parent: "Glutes", deep: false },
  { key: "gluteus_minimus", label: "Gluteus minimus", short: "Glute min", region: "Hips", parent: "Glutes", deep: true },
  { key: "tensor_fasciae_latae", label: "Tensor fasciae latae", short: "TFL", region: "Hips", parent: "", deep: false },
  { key: "rectus_femoris", label: "Rectus femoris", short: "Rectus femoris", region: "Thighs", parent: "Quadriceps", deep: false },
  { key: "vastus_lateralis", label: "Vastus lateralis", short: "Vastus lateralis", region: "Thighs", parent: "Quadriceps", deep: false },
  { key: "vastus_medialis", label: "Vastus medialis", short: "Vastus medialis", region: "Thighs", parent: "Quadriceps", deep: false },
  { key: "vastus_intermedius", label: "Vastus intermedius", short: "Vastus intermedius", region: "Thighs", parent: "Quadriceps", deep: true },
  { key: "sartorius", label: "Sartorius", short: "Sartorius", region: "Thighs", parent: "", deep: false },
  { key: "adductor_longus", label: "Adductor longus (and brevis)", short: "Adductor longus", region: "Thighs", parent: "Adductors", deep: false },
  { key: "adductor_magnus", label: "Adductor magnus", short: "Adductor magnus", region: "Thighs", parent: "Adductors", deep: false },
  { key: "gracilis", label: "Gracilis", short: "Gracilis", region: "Thighs", parent: "Adductors", deep: false },
  { key: "biceps_femoris", label: "Biceps femoris", short: "Biceps femoris", region: "Thighs", parent: "Hamstrings", deep: false },
  { key: "semitendinosus", label: "Semitendinosus", short: "Semitendinosus", region: "Thighs", parent: "Hamstrings", deep: false },
  { key: "semimembranosus", label: "Semimembranosus", short: "Semimembranosus", region: "Thighs", parent: "Hamstrings", deep: false },
  { key: "gastrocnemius", label: "Gastrocnemius", short: "Gastrocnemius", region: "Lower legs", parent: "Calves", deep: false },
  { key: "soleus", label: "Soleus", short: "Soleus", region: "Lower legs", parent: "Calves", deep: false },
  { key: "tibialis_anterior", label: "Tibialis anterior", short: "Tibialis anterior", region: "Lower legs", parent: "", deep: false },
  { key: "fibularis", label: "Fibularis (peroneals)", short: "Peroneals", region: "Lower legs", parent: "", deep: false },
];

export const REGIONS = ["Chest", "Back", "Neck", "Shoulders", "Arms", "Core", "Hips", "Thighs", "Lower legs"] as const;

export const MUSCLE_INFO: Record<string, MuscleInfo> = Object.fromEntries(MUSCLES.map((m) => [m.key, m]));

/** Display names by key (kept as a record for existing imports). */
export const MUSCLE_LABEL: Record<string, string> = Object.fromEntries(MUSCLES.map((m) => [m.key, m.label]));

/** Display name for a key. v7 region keys (old exports) still read sensibly. */
const LEGACY_LABEL: Record<string, string> = {
  upper_chest: "Upper chest", lower_chest: "Chest", front_delts: "Front delts", side_delts: "Side delts",
  rear_delts: "Rear delts", biceps: "Biceps", triceps: "Triceps", forearms: "Forearms", traps: "Traps",
  lats: "Lats", rhomboids: "Mid-back", lower_back: "Lower back", abs: "Abs", obliques: "Obliques",
  glutes: "Glutes", quads: "Quads", hamstrings: "Hamstrings", adductors: "Adductors", calves: "Calves",
};

export const muscleLabel = (key: string): string => MUSCLE_LABEL[key] ?? LEGACY_LABEL[key] ?? key;
export const muscleShort = (key: string): string => MUSCLE_INFO[key]?.short ?? muscleLabel(key);

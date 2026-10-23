"""Solo-safe martial-arts drills (v1.2): boxing, kickboxing / Muay Thai solo work, basic
kicks and stances, and fighter conditioning. Every drill is done alone, in the air or on a
bag: no partner, no weapons, no grappling, throws or locks.

MET values are approximate, from the Compendium of Physical Activities (boxing, punching
bag 5.5; martial arts, moderate pace 5.3; vigorous 10.3; rope skipping 11.8); they feed
the calorie ESTIMATE only. Muscle weights use the library's scale (1.0 primary, 0.5
secondary, 0.25 minor) and are rule-of-thumb estimates, kept modest because time-based
load is converted to effective sets.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Drill:
    name: str
    style: str  # boxing | kickboxing | kicks | conditioning (shown as a tag)
    equipment: str  # none | bag | rope
    met: float
    difficulty: str
    muscles: dict[str, float]
    instructions: tuple[str, ...]
    aliases: tuple[str, ...] = field(default_factory=tuple)


_CORE = {"external_obliques": 0.5, "internal_obliques": 0.5, "rectus_abdominis": 0.25}
_PUNCH = {
    "deltoid_anterior": 0.5,
    "deltoid_lateral": 0.25,
    "triceps_lateral": 0.25,
    "serratus_anterior": 0.25,
}

DRILLS: tuple[Drill, ...] = (
    # --- Boxing ---
    Drill(
        "Boxing Stance and Guard Drill",
        "boxing",
        "none",
        4.0,
        "beginner",
        {"deltoid_anterior": 0.25, "gastrocnemius": 0.25, "external_obliques": 0.25},
        (
            "Stand side-on, feet shoulder-width apart, lead foot forward and knees soft.",
            "Hands up by your cheeks, elbows in, chin tucked.",
            "Bounce lightly on the balls of your feet for the whole round, guard always up.",
            "Rest a minute between rounds.",
        ),
        ("boxing guard", "fighting stance"),
    ),
    Drill(
        "Jab-Cross Shadow Drill",
        "boxing",
        "none",
        5.5,
        "beginner",
        {**_PUNCH, **_CORE},
        (
            "From your guard, snap the lead hand straight out and back: the jab.",
            "Turn the back hip and heel and throw the rear hand straight: the cross.",
            "Bring each hand straight back to your cheek; breathe out on every punch.",
            "Keep the punches relaxed; speed comes from the turn, not from tensing.",
        ),
        ("one-two", "jab cross"),
    ),
    Drill(
        "Boxing Footwork Drill",
        "boxing",
        "none",
        6.0,
        "beginner",
        {"gastrocnemius": 0.5, "soleus": 0.5, "vastus_lateralis": 0.25, "gluteus_medius": 0.25},
        (
            "Step forward with the lead foot first, then slide the back foot after it.",
            "Step back with the back foot first, then the lead foot; never cross your feet.",
            "Add side steps and small pivots on the lead foot.",
            "Stay light and keep your guard up the whole time.",
        ),
        ("footwork", "boxing steps"),
    ),
    Drill(
        "Slip and Roll Drill",
        "boxing",
        "none",
        5.5,
        "intermediate",
        {
            "external_obliques": 0.5,
            "internal_obliques": 0.5,
            "vastus_lateralis": 0.25,
            "gluteus_maximus": 0.25,
        },
        (
            "From your guard, bend the knees and dip the head just outside an imaginary jab: a slip.",
            "Bend at the knees and roll under an imaginary hook in a U shape.",
            "Come back up in your stance with your hands still up.",
            "Move the head with the legs and hips, not by bending the neck.",
        ),
        ("head movement", "bob and weave"),
    ),
    Drill(
        "Heavy Bag Combos",
        "boxing",
        "bag",
        6.5,
        "intermediate",
        {**_PUNCH, **_CORE, "latissimus_dorsi": 0.25},
        (
            "Wrap your hands and wear bag gloves.",
            "Throw short combinations (jab-cross, jab-cross-hook) and move after each one.",
            "Hit with the first two knuckles and keep the wrist straight.",
            "Work 2-3 minute rounds with a minute of rest.",
        ),
        ("bag work", "punching bag combos"),
    ),
    # --- Kickboxing / Muay Thai, solo ---
    Drill(
        "Teep Push Kick Drill",
        "kickboxing",
        "none",
        6.0,
        "beginner",
        {"iliopsoas": 0.5, "rectus_femoris": 0.5, "gluteus_maximus": 0.25, **_CORE},
        (
            "From your stance, lift the lead knee to your chest.",
            "Push the ball of the foot straight out, as if pushing a door shut.",
            "Pull the leg back to the knee and set it down in your stance.",
            "Keep your hands up and lean back only a little.",
        ),
        ("push kick", "teep"),
    ),
    Drill(
        "Roundhouse Kick Drill",
        "kickboxing",
        "none",
        7.0,
        "intermediate",
        {"gluteus_medius": 0.5, "iliopsoas": 0.5, "adductor_longus": 0.25, **_CORE},
        (
            "Step out slightly with the lead foot and turn it out.",
            "Swing the back leg round, turning the hip over, and land the shin at waist height or lower.",
            "Swing the same-side arm down for balance and keep the other hand up.",
            "Return to your stance; go slow and low until the balance is solid.",
        ),
        ("round kick", "turning kick"),
    ),
    Drill(
        "Knee Strike Drill",
        "kickboxing",
        "none",
        7.0,
        "beginner",
        {"iliopsoas": 0.5, "rectus_abdominis": 0.5, "gluteus_maximus": 0.25, "gastrocnemius": 0.25},
        (
            "From your stance, reach both hands forward as if holding the bag.",
            "Drive the back knee up and forward while pulling the hands down.",
            "Rise on the toes of the standing foot and push the hips through.",
            "Step back to your stance and switch legs each round.",
        ),
        ("knees", "knee strikes"),
    ),
    Drill(
        "Kickboxing Shadow Rounds",
        "kickboxing",
        "none",
        7.5,
        "intermediate",
        {**_PUNCH, **_CORE, "iliopsoas": 0.25, "gluteus_medius": 0.25},
        (
            "Mix punches, teeps, knees and low kicks in the air.",
            "Throw two or three strikes, then move, then guard.",
            "Picture an opponent; breathe out on every strike.",
            "Work 3 minute rounds with a minute of rest.",
        ),
        ("shadow kickboxing", "muay thai shadow"),
    ),
    # --- Basic kicks and stances (taekwondo / karate basics) ---
    Drill(
        "Front Kick Drill",
        "kicks",
        "none",
        5.3,
        "beginner",
        {"rectus_femoris": 0.5, "iliopsoas": 0.5, "vastus_medialis": 0.25, **_CORE},
        (
            "Stand in a front stance with your hands in a guard.",
            "Lift the back knee high, then snap the lower leg out, striking with the ball of the foot.",
            "Snap the leg back to the knee before you put it down.",
            "Kick at waist height or lower until it feels controlled.",
        ),
        ("snap kick",),
    ),
    Drill(
        "Side Kick Drill",
        "kicks",
        "none",
        5.3,
        "intermediate",
        {"gluteus_medius": 0.5, "gluteus_maximus": 0.5, "tensor_fasciae_latae": 0.25, **_CORE},
        (
            "Stand side-on and lift the kicking knee across your body.",
            "Turn the standing foot away and push the heel straight out to the side.",
            "Keep the toes level or slightly down and the body in one line.",
            "Pull the knee back before setting the foot down.",
        ),
        ("side thrust kick",),
    ),
    Drill(
        "Horse Stance Hold",
        "kicks",
        "none",
        3.5,
        "beginner",
        {
            "vastus_lateralis": 0.5,
            "vastus_medialis": 0.5,
            "adductor_magnus": 0.5,
            "gluteus_maximus": 0.25,
        },
        (
            "Stand with your feet about twice shoulder-width apart, toes forward.",
            "Sink down as if sitting on a low stool, knees pushed out over the toes.",
            "Keep the back upright and the fists at your hips.",
            "Hold, breathing slowly; stand up if a knee hurts.",
        ),
        ("horse riding stance",),
    ),
    Drill(
        "Stance Walk Drill",
        "kicks",
        "none",
        4.0,
        "beginner",
        {
            "vastus_lateralis": 0.5,
            "gluteus_maximus": 0.5,
            "adductor_longus": 0.25,
            "gastrocnemius": 0.25,
        },
        (
            "Step forward into a long front stance: front knee bent, back leg straight.",
            "Step through into the next stance on the other side, keeping the height level.",
            "Add a punch with each step once the stance is steady.",
            "Walk the length of the room and back.",
        ),
        ("front stance walk", "stepping stances"),
    ),
    # --- Fighter conditioning ---
    Drill(
        "Sprawl Drill",
        "conditioning",
        "none",
        8.0,
        "intermediate",
        {
            "rectus_abdominis": 0.5,
            "pec_major_sternal": 0.25,
            "gluteus_maximus": 0.25,
            "vastus_lateralis": 0.25,
        },
        (
            "From your stance, drop your hands to the floor.",
            "Kick both legs back and sink the hips to the floor, chest up.",
            "Snap the feet back under you and return to your stance, hands up.",
            "Go at a pace you can keep with good form for the whole round.",
        ),
        ("sprawls",),
    ),
    Drill(
        "Fighter Jump Rope Rounds",
        "conditioning",
        "rope",
        11.8,
        "beginner",
        {"gastrocnemius": 0.5, "soleus": 0.5, "deltoid_lateral": 0.25, "wrist_flexors": 0.25},
        (
            "Turn the rope from the wrists, elbows close to the body.",
            "Jump just high enough to clear the rope, landing softly on the balls of the feet.",
            "Mix in a boxer's skip, shifting weight from foot to foot.",
            "Work 3 minute rounds with a minute of rest.",
        ),
        ("skipping", "jump rope"),
    ),
    Drill(
        "Fighter Core Circuit",
        "conditioning",
        "none",
        5.0,
        "beginner",
        {
            "rectus_abdominis": 0.5,
            "external_obliques": 0.5,
            "internal_obliques": 0.5,
            "transversus_abdominis": 0.5,
        },
        (
            "Rotate through 30 seconds each: plank, mountain climbers, side plank each side, hollow hold.",
            "Rest 15 seconds between moves.",
            "Keep the lower back flat on the hollow hold; bend the knees if it lifts.",
            "Two to four rounds.",
        ),
        ("core circuit",),
    ),
)

DRILL_NAMES = frozenset(d.name for d in DRILLS)

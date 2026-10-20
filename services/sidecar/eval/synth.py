"""Synthetic users with known parameters, for evaluating the recovery and progression
engines (docs/ai/evaluation.md). Pure Python, seeded, deterministic.

A synthetic user has hidden ground truth the engines never see:

* per muscle group, a true recovery factor k_true (log-uniform 0.65-1.55) that scales
  the prior half-lives, and a true fatigue sensitivity alpha (how much a fully fatigued
  muscle loses: 8-20 % of its strength);
* per exercise, a true strength curve S(t) (kg of 1RM) that rises with diminishing
  returns, optionally with a plateau from a known week (an injected stall);
* a sleep sensitivity, daily sleep, and day-to-day noise in performance;
* habits: how close to failure they stop, whether they log RPE and how noisily.

The truth deliberately differs from the engine in places, so the evaluation is not the
engine checking itself: the true intensity curve is 1 - 0.08 RIR (the engine assumes
1 - 0.1 (RIR - 1)), the true sleep effect is per user (the engine uses one constant),
RPE is logged with noise and sometimes not at all, and an optional "delayed" kernel
makes fatigue peak a day after training (DOMS-like) where the engine assumes a pure
exponential. What the evaluation shows is that the engines' estimation machinery works
under these assumptions, not that the assumptions are true of real people.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from app.modules.progress.taxonomy import MUSCLE_BY_KEY, MUSCLES
from app.modules.workouts.seed import EXERCISES

START = datetime(2025, 1, 6, 0, 0)  # a Monday; the date itself does not matter
GROUPS = tuple(dict.fromkeys(m.group for m in MUSCLES))
WEIGHTS: dict[str, dict[str, float]] = {name: dict(ms) for name, _, ms in EXERCISES}
EQUIPMENT: dict[str, str] = {name: eq for name, eq, _ in EXERCISES}

# Splits used by synthetic users: exercise names from the seeded library.
SPLITS: dict[str, list[list[str]]] = {
    "ppl": [
        ["Barbell Bench Press", "Overhead Press", "Incline Dumbbell Press", "Triceps Pushdown"],
        ["Barbell Row", "Lat Pulldown", "Face Pull", "Dumbbell Curl"],
        ["Back Squat", "Romanian Deadlift", "Leg Curl", "Standing Calf Raise"],
    ],
    "upper_lower": [
        ["Barbell Bench Press", "Barbell Row", "Overhead Press", "Lat Pulldown", "Dumbbell Curl"],
        ["Back Squat", "Romanian Deadlift", "Leg Extension", "Standing Calf Raise"],
    ],
    "full_body": [
        ["Back Squat", "Barbell Bench Press", "Barbell Row", "Lateral Raise"],
        ["Romanian Deadlift", "Overhead Press", "Lat Pulldown", "Triceps Pushdown"],
    ],
}
# Typical starting 1RMs (kg) for a recreational lifter, scaled per user.
BASE_1RM: dict[str, float] = {
    "Barbell Bench Press": 70,
    "Overhead Press": 42,
    "Incline Dumbbell Press": 26,
    "Triceps Pushdown": 40,
    "Barbell Row": 65,
    "Lat Pulldown": 65,
    "Face Pull": 30,
    "Dumbbell Curl": 16,
    "Back Squat": 95,
    "Romanian Deadlift": 90,
    "Leg Curl": 50,
    "Leg Extension": 60,
    "Standing Calf Raise": 80,
    "Lateral Raise": 12,
}
LOWER = {"Back Squat", "Romanian Deadlift", "Leg Curl", "Leg Extension", "Standing Calf Raise"}

Kernel = Literal["exp", "delayed"]


def true_intensity(rir: float) -> float:
    return max(0.35, min(1.0, 1.0 - 0.08 * rir))


def kernel(hours: float, half_life: float, kind: Kernel) -> float:
    if hours < 0:
        return 0.0
    e = 2.0 ** (-hours / half_life)
    if kind == "exp":
        return e
    g = (hours / 24.0) * math.exp(1.0 - hours / 24.0)
    return 0.6 * e + 0.4 * g


@dataclass
class User:
    uid: int
    k_true: dict[str, float]
    alpha: float
    noise_sd: float
    rpe_log_prob: float
    rpe_sd: float
    sleep_effect: float
    sleep_mean: float
    split: str
    gap_weights: tuple[float, float, float, float]
    strength0: dict[str, float]
    gain: dict[str, float]  # fractional gain at saturation
    tau_weeks: dict[str, float]
    plateau_week: dict[str, float | None]
    rir_stop: tuple[int, int]
    kernel: Kernel = "exp"
    checkin_prob: float = 0.7

    def strength(self, ex: str, t: datetime) -> float:
        weeks = (t - START).total_seconds() / (7 * 86400)
        p = self.plateau_week.get(ex)
        if p is not None:
            weeks = min(weeks, p)
        return self.strength0[ex] * (
            1 + self.gain[ex] * (1 - math.exp(-weeks / self.tau_weeks[ex]))
        )


def make_user(
    rng: random.Random,
    uid: int,
    kernel_kind: Kernel = "exp",
    stalls: bool = False,
    frequent: bool = False,
) -> User:
    """A random user. `frequent` makes a full-body lifter training most days who logs RPE
    every set: the case where fatigue carries over between sessions and is measurable."""
    split = "full_body" if frequent else rng.choice(list(SPLITS))
    exercises = sorted({e for day in SPLITS[split] for e in day})
    scale = rng.uniform(0.7, 1.4)
    plateau: dict[str, float | None] = {}
    for e in exercises:
        plateau[e] = rng.uniform(8, 30) if stalls and rng.random() < 0.5 else None
    gw = [rng.uniform(0.5, 3.0), rng.uniform(1.0, 3.0), rng.uniform(0.2, 1.5), rng.uniform(0, 0.6)]
    if frequent:
        gw = [3.0, 1.0, 0.1, 0.0]
    user = User(
        uid=uid,
        k_true={g: math.exp(rng.uniform(math.log(0.65), math.log(1.55))) for g in GROUPS},
        alpha=rng.uniform(0.08, 0.20),
        noise_sd=rng.uniform(0.012, 0.03),
        rpe_log_prob=rng.choice([0.0, 0.5, 0.9, 1.0]),
        rpe_sd=rng.uniform(0.3, 1.0),
        sleep_effect=rng.uniform(0.05, 0.35),
        sleep_mean=rng.uniform(2.8, 4.3),
        split=split,
        gap_weights=(gw[0], gw[1], gw[2], gw[3]),
        strength0={e: BASE_1RM[e] * scale * rng.uniform(0.85, 1.15) for e in exercises},
        gain={e: rng.uniform(0.15, 0.6) for e in exercises},
        tau_weeks={e: rng.uniform(15, 60) for e in exercises},
        plateau_week=plateau,
        rir_stop=(1, 3),
        kernel=kernel_kind,
    )
    if frequent:
        user.rpe_log_prob = 1.0
        user.rpe_sd = rng.uniform(0.3, 0.6)
        user.noise_sd = rng.uniform(0.008, 0.015)
        user.alpha = rng.uniform(0.15, 0.30)
    return user


@dataclass(frozen=True)
class LoggedSet:
    exercise: str
    at: datetime
    weight_kg: float
    reps: int
    rpe: float | None
    true_rir: float
    set_index: int


@dataclass
class Session:
    start: datetime
    exercises: list[str]
    sleep: int
    soreness: str
    checkin_logged: bool
    sets: list[LoggedSet] = field(default_factory=list)
    # ground truth at the session start, per muscle: readiness
    true_readiness: dict[str, float] = field(default_factory=dict)
    # ground truth per exercise: today's capacity (1RM-equivalent before set fatigue)
    true_capacity: dict[str, float] = field(default_factory=dict)
    true_strength: dict[str, float] = field(default_factory=dict)


class Truth:
    """Ground-truth fatigue bookkeeping for one user."""

    def __init__(self, user: User) -> None:
        self.u = user
        self.contribs: list[tuple[str, float, datetime]] = []  # muscle, ES_true, at

    def add_set(self, ex: str, at: datetime, reps: int, true_rir: float) -> None:
        v = 0.85 if reps <= 4 else (1.1 if reps > 20 else 1.0)
        es = true_intensity(true_rir) * v
        for m, w in WEIGHTS[ex].items():
            self.contribs.append((m, w * es, at))

    def fatigue(self, muscle: str, t: datetime) -> float:
        mus = MUSCLE_BY_KEY[muscle]
        h = mus.half_life_h * self.u.k_true[mus.group]
        total = 0.0
        for m, es, at in self.contribs:
            if m != muscle:
                continue
            hours = (t - at).total_seconds() / 3600
            if hours <= 0 or hours > 12 * h:
                continue
            total += es * kernel(hours, h, self.u.kernel)
        return total

    def modifier(self, sleep: int) -> float:
        return 1.0 + self.u.sleep_effect * (1 - (sleep - 1) / 4)

    def readiness(self, muscle: str, t: datetime, sleep: int) -> float:
        mus = MUSCLE_BY_KEY[muscle]
        return 1 - min(1.0, self.modifier(sleep) * self.fatigue(muscle, t) / mus.capacity_es)

    def capacity_factor(self, ex: str, t: datetime, sleep: int) -> float:
        prim = {m: w for m, w in WEIGHTS[ex].items() if w >= 1.0}
        tot = sum(prim.values())
        phi = sum(w * (1 - self.readiness(m, t, sleep)) for m, w in prim.items()) / tot
        return 1 - self.u.alpha * phi

    def prune(self, t: datetime) -> None:
        cutoff = t - timedelta(days=12)
        self.contribs = [c for c in self.contribs if c[2] >= cutoff]


def schedule(user: User, rng: random.Random, days: int) -> list[tuple[datetime, list[str]]]:
    out: list[tuple[datetime, list[str]]] = []
    day = 0
    rot = 0
    plan = SPLITS[user.split]
    while day < days:
        start = START + timedelta(days=day, hours=rng.choice([7, 8, 18, 19, 20]))
        out.append((start, plan[rot % len(plan)]))
        rot += 1
        day += rng.choices([1, 2, 3, 4], weights=user.gap_weights)[0]
    return out


def increment(ex: str) -> float:
    eq = EQUIPMENT.get(ex, "barbell")
    if eq == "barbell":
        return 5.0 if ex in LOWER else 2.5
    return 2.5


def round_to(x: float, step: float) -> float:
    return max(step, round(x / step) * step)


def max_reps(capacity: float, load: float) -> float:
    """Epley inverse: reps possible at a load for today's capacity."""
    if load <= 0:
        return 30.0
    return max(0.0, 30.0 * (capacity / load - 1.0))


def perform(
    user: User,
    rng: random.Random,
    truth: Truth,
    ex: str,
    at: datetime,
    load: float,
    target_reps: int,
    set_index: int,
    cap_today: float,
    stop_rir: int,
) -> LoggedSet:
    cap = cap_today * (1 - 0.025 * set_index)  # within-session fatigue across sets
    possible = max_reps(cap, load)
    reps = int(min(target_reps, math.floor(possible - stop_rir)))
    if reps < 1:
        reps = max(0, int(math.floor(possible)))  # push to failure when short
    true_rir = max(0.0, possible - reps)
    rpe: float | None = None
    if rng.random() < user.rpe_log_prob and reps > 0:
        raw = 10 - true_rir + rng.gauss(0, user.rpe_sd)
        rpe = min(10.0, max(5.0, round(raw * 2) / 2))
    if reps > 0:
        truth.add_set(ex, at, reps, true_rir)
    return LoggedSet(ex, at, load, reps, rpe, round(true_rir, 2), set_index)


def daily_sleep(user: User, rng: random.Random) -> int:
    return int(min(5, max(1, round(rng.gauss(user.sleep_mean, 0.9)))))


def soreness_report(truth: Truth, t: datetime, sleep: int, rng: random.Random) -> str:
    worst = min(truth.readiness(m.key, t, sleep) for m in MUSCLES)
    if worst < 0.35 and rng.random() < 0.8:
        return "a_lot"
    if worst < 0.65 and rng.random() < 0.7:
        return "some"
    return "none"


def simulate_self_coached(user: User, rng: random.Random, days: int = 365) -> list[Session]:
    """History of a user who coaches themselves: 3 sets in an 8-10 rep range, +1 increment
    when every set reaches 10 reps, stopping 1-3 reps short of failure."""
    truth = Truth(user)
    loads: dict[str, float] = {}
    sessions: list[Session] = []
    for start, exercises in schedule(user, rng, days):
        truth.prune(start)
        sleep = daily_sleep(user, rng)
        sess = Session(
            start=start,
            exercises=list(exercises),
            sleep=sleep,
            soreness=soreness_report(truth, start, sleep, rng),
            checkin_logged=rng.random() < user.checkin_prob,
        )
        sess.true_readiness = {m.key: truth.readiness(m.key, start, sleep) for m in MUSCLES}
        t = start
        for ex in exercises:
            s_true = user.strength(ex, start)
            cap = (
                s_true
                * truth.capacity_factor(ex, start, sleep)
                * math.exp(rng.gauss(0, user.noise_sd))
            )
            sess.true_capacity[ex] = cap
            sess.true_strength[ex] = s_true
            if ex not in loads:
                loads[ex] = round_to(s_true / (1 + 12 / 30), increment(ex))
            done = []
            for i in range(3):
                t += timedelta(minutes=3)
                stop = rng.randint(*user.rir_stop)
                done.append(perform(user, rng, truth, ex, t, loads[ex], 10, i, cap, stop))
            sess.sets.extend(done)
            if all(s.reps >= 10 for s in done):
                loads[ex] += increment(ex)
            elif sum(1 for s in done if s.reps < 6) >= 2:
                loads[ex] = round_to(loads[ex] * 0.9, increment(ex))
        sessions.append(sess)
    return sessions

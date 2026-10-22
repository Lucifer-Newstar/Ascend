#!/usr/bin/env python3
"""ASCEND muscle map v2: original artwork generator.

Draws the front and back figure (surface + deep layer) from hand-placed control points and writes
bodyMapPaths.ts plus preview PNGs next to this script.  Run:  python3 build_map.py
(needs shapely, cairosvg, numpy, pillow), then copy bodyMapPaths.ts to apps/desktop/src/lib/.

Construction
  * The body silhouette is built first: head, torso, arms and legs.  Arms and legs are "limbs":
    a smooth axis with a width profile (lateral / medial half-width along the axis).
  * Limb muscles are authored in limb coordinates (s = distance along the axis in viewBox units,
    v = -1 medial edge .. +1 lateral edge), so they follow the limb's taper automatically.
  * Torso muscles are authored in viewBox coordinates.
  * Each region is carved in priority order: a muscle loses whatever a higher-priority neighbour
    (grown by the seam width) already covers, and everything is clipped to the silhouette.  This
    gives one consistent seam width everywhere.
  * Only the viewer's right half is authored; the left half is mirrored around x = 100.
"""
import math, os, re, sys, json
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity

OUT = os.path.dirname(os.path.abspath(__file__))
VB_W, VB_H = 200, 430
CX = 100.0
GAP = 1.1          # seam between neighbouring muscles (viewBox units)
RIM = 0.55         # inset of muscles from the silhouette edge

# ---------------------------------------------------------------- curves
def crs(pts, closed=True, n=10, alpha=0.5):
    """Centripetal Catmull-Rom spline through pts, sampled n points per segment."""
    P = [np.asarray(p, float) for p in pts]
    if closed:
        P = [P[-1]] + P + [P[0], P[1]]
    else:
        P = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** alpha
        for t in np.linspace(t1, t2, n, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    if not closed:
        out.append(P[-2])
    return np.array(out)

def poly(pts, n=10):
    g = Polygon(crs(pts, True, n))
    return g if g.is_valid else g.buffer(0)

def pchip(xs, ys, x):
    """Monotone cubic interpolation (Fritsch-Carlson), clamped outside the range."""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float); x = np.clip(np.asarray(x, float), xs[0], xs[-1])
    h = np.diff(xs); d = np.diff(ys) / h
    m = np.zeros_like(ys)
    m[0], m[-1] = d[0], d[-1]
    for k in range(1, len(xs) - 1):
        if d[k - 1] * d[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])
    i = np.clip(np.searchsorted(xs, x) - 1, 0, len(h) - 1)
    t = (x - xs[i]) / h[i]
    return ((2*t**3 - 3*t**2 + 1) * ys[i] + (t**3 - 2*t**2 + t) * h[i] * m[i]
            + (-2*t**3 + 3*t**2) * ys[i+1] + (t**3 - t**2) * h[i] * m[i+1])

# ---------------------------------------------------------------- limbs
class Limb:
    """A limb: smooth axis + width profile.  s = arc length from the first axis point."""
    def __init__(self, axis, stations):
        A = crs(axis, closed=False, n=60)
        seg = np.hypot(*np.diff(A, axis=0).T)
        self.A, self.d = A, np.r_[0, np.cumsum(seg)]
        self.L = self.d[-1]
        T = np.gradient(A, axis=0)
        T /= np.linalg.norm(T, axis=1)[:, None]
        k = 25  # smooth the tangent so the frame bends gently at joints
        Ts = np.array([T[max(0, i - k):i + k + 1].mean(0) for i in range(len(T))])
        self.T = Ts / np.linalg.norm(Ts, axis=1)[:, None]
        st = np.array(stations, float)
        self.ss, self.lat, self.med = st[:, 0], st[:, 1], st[:, 2]

    def frame(self, s):
        s = np.asarray(s, float)
        sc = np.clip(s, 0, self.L)
        x = np.interp(sc, self.d, self.A[:, 0]); y = np.interp(sc, self.d, self.A[:, 1])
        tx = np.interp(sc, self.d, self.T[:, 0]); ty = np.interp(sc, self.d, self.T[:, 1])
        n = np.hypot(tx, ty); tx, ty = tx / n, ty / n
        ext = s - sc  # extrapolate past the ends along the tangent
        return x + tx * ext, y + ty * ext, tx, ty

    def xy(self, s, v):
        s = np.asarray(s, float); v = np.asarray(v, float)
        x, y, tx, ty = self.frame(s)
        w = np.where(v >= 0, pchip(self.ss, self.lat, s), pchip(self.ss, self.med, s))
        return np.stack([x + ty * v * w, y - tx * v * w], -1)   # lateral normal = (ty, -tx)

    def outline(self, s0, s1, n=160):
        s = np.linspace(s0, s1, n)
        lat = self.xy(s, np.ones_like(s)); med = self.xy(s[::-1], -np.ones_like(s))
        return np.vstack([lat, med])

    def shape(self, sv, n=12):
        """Closed spline authored in (s, v), sampled densely in limb space, mapped to the page."""
        P = np.array(sv, float); P[:, 1] *= 12.0          # isotropic-ish space for the spline
        D = crs(P, True, n); D[:, 1] /= 12.0
        D = densify(D, 1.2)
        g = Polygon(self.xy(D[:, 0], D[:, 1]))
        return g if g.is_valid else g.buffer(0)

    def strap(self, sv_line, half_w):
        P = np.array(sv_line, float); P[:, 1] *= 12.0
        D = crs(P, False, 14); D[:, 1] /= 12.0
        return LineString(self.xy(D[:, 0], D[:, 1])).buffer(half_w, cap_style=1)

def densify(D, step):
    out = [D[0]]
    for a, b in zip(D, np.vstack([D[1:], D[:1]])):
        n = max(1, int(np.ceil(abs(b[0] - a[0]) / step)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out[:-1])

def tri(a, b, w0, w1=0.0, n=40):
    """Tapered teardrop from point a (width w0) to point b (width w1)."""
    a, b = np.array(a, float), np.array(b, float)
    L = np.linalg.norm(b - a); u = (b - a) / L; nrm = np.array([-u[1], u[0]])
    t = np.linspace(0, 1, n)
    w = (w0 * (1 - t) + w1 * t) * np.sin(np.pi * np.clip(t * 0.85 + 0.15, 0, 1)) ** 0.6
    left = a + np.outer(t * L, u) + np.outer(w, nrm)
    right = a + np.outer(t * L, u) - np.outer(w, nrm)
    return Polygon(np.vstack([left, right[::-1]])).buffer(0)

def mirror(g):
    return affinity.scale(g, xfact=-1, yfact=1, origin=(CX, 0))

def parts(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]

def tidy(g, r=0.38, min_area=1.2):
    g = g.buffer(-r, join_style=1).buffer(r, join_style=1)
    return unary_union([p for p in parts(g) if p.area >= min_area])

# ---------------------------------------------------------------- body (viewer's right half)
# 7.5-head figure: top of head y 6, chin 61, shoulders 84, nipples 117, navel 167, pubis 212,
# knee 300, ankle 400, sole 423.  One head = 55.5 units.
ARM = Limb([(142.5, 90), (152.6, 127), (163.4, 163), (172, 192), (180.4, 220), (185, 242), (188.4, 264)],
           # s, lateral half-width, medial half-width          (elbow s~77, wrist s~137)
           [(-6, 12.5, 12.5), (0, 14.2, 13), (12, 15.4, 13.4), (26, 14.6, 13.6), (40, 13.8, 14.2),
            (55, 13.0, 13.4), (68, 11.6, 11.4), (77, 10.8, 10.4), (86, 13.0, 11.0), (98, 12.8, 10.8),
            (112, 10.0, 9.0), (126, 7.4, 6.8), (137, 6.4, 6.0), (145, 7.6, 7.2), (156, 8.1, 7.5),
            (166, 7.2, 6.8), (174, 5.4, 5.4), (180, 2.0, 2.0)])
LEG = Limb([(119, 190), (118.2, 245), (117, 298), (116.4, 350), (116, 398), (118, 416)],
           # knee s~108, ankle s~208
           [(0, 17.0, 17.6), (8, 20.5, 17.4), (16, 22.0, 17.0), (30, 21.6, 15.4), (50, 20.0, 13.4),
            (70, 17.8, 12.2), (88, 15.2, 12.6), (100, 12.6, 11.8), (108, 11.6, 11.0), (116, 11.8, 11.2),
            (128, 13.6, 13.0), (140, 13.4, 13.6), (156, 11.0, 11.4), (176, 7.9, 8.1), (192, 7.2, 7.3),
            (204, 7.6, 8.0), (212, 8.0, 8.8), (220, 8.8, 9.6), (228, 7.6, 8.4), (232, 3.0, 3.5)])
S_ELBOW, S_WRIST, S_KNEE, S_ANKLE = 77, 137, 108, 208

HEAD = [(100, 6), (110.5, 8), (118, 15.5), (121, 27), (120, 38), (117.5, 47.5), (112.5, 55.5),
        (106, 60), (100, 61.5)]
TORSO = [(100, 50), (112, 54), (114, 62), (114.5, 70), (118, 74), (125, 77.6), (133, 80.6), (139, 83),
         (143, 92), (142, 108), (139.5, 118.5), (138.2, 126), (138, 133), (136.6, 145),
         (134.2, 157), (132.8, 167), (133.6, 178), (136.5, 189), (139.6, 199), (140.5, 207),
         (130, 214), (112, 214), (101, 213.5)]
DELT_CAP = [(129, 80.5), (141, 82.4), (151, 86.6), (157.6, 94), (160.4, 105), (160, 117), (157, 127),
            (150, 124), (141, 100)]
THUMB = None  # set in silhouette()

def half_to_full(pts):
    pts = list(pts)
    return pts + [(2 * CX - x, y) for x, y in reversed(pts) if abs(x - CX) > 1e-6]

def silhouette():
    head = Polygon(crs(half_to_full(HEAD), True, 10))
    torso_half = Polygon(crs([(CX - 0.01, 48)] + TORSO[1:] + [(CX - 0.01, 213.5)], True, 10)).buffer(0)
    torso = unary_union([torso_half, mirror(torso_half)]).buffer(0.3).buffer(-0.3)
    arm = Polygon(ARM.outline(-6, 180)).buffer(0)
    tip = Point(*ARM.xy(178.5, 0)).buffer(5.6)                    # rounded finger tips
    # thumb: palms face forward, so the thumb sits on the lateral side of the hand
    t0 = ARM.xy(141, 0.7); t1 = ARM.xy(160, 1.35)
    thumb = LineString([t0, (t0 + t1) / 2 + np.array([0.8, 0.4]), t1]).buffer(2.7, cap_style=1)
    leg = Polygon(LEG.outline(0, 230)).buffer(0)
    toe = Point(*LEG.xy(226.5, 0.1)).buffer(8.0)
    toe = affinity.scale(toe, 1.05, 0.62)
    delt = poly(DELT_CAP)
    right = unary_union([arm, tip, thumb, leg, toe, delt])
    body = unary_union([head, torso, right, mirror(right)])
    body = body.buffer(1.6, join_style=1).buffer(-1.6, join_style=1)   # blend joints
    body = body.buffer(-0.8, join_style=1).buffer(0.8, join_style=1)
    return body

BODY = silhouette()
# Regions used for clipping (viewer's right half only, generous)
HALF = box(CX + 0.3, 0, VB_W, VB_H)
ARM_REGION = Polygon(ARM.outline(-30, 180)).buffer(0).union(poly(DELT_CAP)).buffer(0.01)
LEG_REGION = Polygon(LEG.outline(-40, 230)).buffer(0)

# ---------------------------------------------------------------- helpers for authoring
def P(pts, n=10):            # torso shape in page coordinates
    return poly(pts, n)
def A(sv):                   # arm shape in limb coordinates
    return ARM.shape(sv)
def L(sv):                   # leg shape in limb coordinates
    return LEG.shape(sv)
def side_of(curve, g, keep="left", far=60):
    """Split g by an open curve (page coords, running top to bottom); keep the part on one side."""
    C = crs(curve, False, 12)
    sgn = -1 if keep == "left" else 1
    region = Polygon(np.vstack([C, [C[-1] + [sgn * far, 0], C[0] + [sgn * far, 0]]])).buffer(0)
    return g.intersection(region)
def cut(g, curve, w=GAP, closed=False):
    C = crs(curve, closed, 12)
    return g.difference(LineString(C).buffer(w / 2, cap_style=2))
def arm_band(v0, v1, s0=-40, s1=200):
    return Polygon(np.vstack([ARM.xy(np.linspace(s0, s1, 80), np.full(80, v0)),
                              ARM.xy(np.linspace(s1, s0, 80), np.full(80, v1))])).buffer(0)
def leg_band(v0, v1, s0=-40, s1=240):
    return Polygon(np.vstack([LEG.xy(np.linspace(s0, s1, 80), np.full(80, v0)),
                              LEG.xy(np.linspace(s1, s0, 80), np.full(80, v1))])).buffer(0)

# Shapes shared by both views
DELTOID = P([(128.5, 82.4), (140, 82.6), (151, 85.4), (160, 92.5), (165, 104), (165, 116), (162, 123),
             (158.4, 126.6), (154.6, 123.6), (148.6, 115), (141, 104.6), (135, 94.6), (130, 87.4)])
DELT_SPLIT = [(141.5, 83), (150, 92.6), (155, 104), (157.6, 115), (158.4, 128)]

# ---------------------------------------------------------------- FRONT, surface (priority order)
def front_surface():
    S = []
    S.append(("sternocleidomastoid", P([(116, 51), (113.6, 60), (108.2, 70.5), (103.2, 78.6), (105.6, 80.2),
                                        (110.8, 73), (116.6, 63), (119.2, 53)])))
    S.append(("deltoid_anterior", side_of(DELT_SPLIT, DELTOID, "left")))
    S.append(("deltoid_lateral", side_of(DELT_SPLIT, DELTOID, "right")))
    pec = P([(102.4, 82.6), (114, 80.8), (126, 82.2), (133.4, 85.6), (139.5, 95), (145.5, 104.5), (150, 110.5),
             (147.4, 114), (141, 118.4), (132, 125.6), (122, 131.2), (112, 134.2), (105, 133.8), (102.4, 131)])
    upper = [(100, 92.5), (114, 94.2), (128, 97.6), (141, 102.6), (156, 108.5)]
    up = Polygon(np.vstack([crs(upper, False, 12), [(156, 60), (100, 60)]])).buffer(0)
    S.append(("pec_major_clavicular", pec.intersection(up)))
    S.append(("pec_major_sternal", pec.difference(up)))
    S.append(("trap_upper", P([(112.5, 60), (114.6, 70), (124, 76.8), (139, 82.4), (136, 85.6), (124, 82.8),
                               (114, 79.6), (110.8, 72)])))
    bic = A([(14, 0.1), (20, 0.62), (36, 0.86), (54, 0.76), (66, 0.42), (72, 0.04), (67, -0.34), (56, -0.74),
             (38, -0.88), (22, -0.74), (12, -0.3)])
    S.append(("biceps_long", bic.intersection(arm_band(0.02, 3))))
    S.append(("biceps_short", bic.intersection(arm_band(-3, 0.02))))
    br = A([(46, 1.04), (64, 1.04), (76, 0.66), (80, 0.0), (76, -0.66), (64, -1.04), (48, -1.04), (54, 0)])
    br = br.difference(A([(64, 0.0), (70, 0.34), (90, 0.4), (90, -0.4), (70, -0.34)]))
    S.append(("brachialis", br))
    S.append(("brachioradialis", A([(57, 0.86), (72, 1.05), (90, 1.07), (110, 0.8), (128, 0.42), (132, 0.2),
                                    (114, 0.26), (94, 0.3), (80, 0.26), (68, 0.5)])))
    wf = A([(80, 0.16), (94, 0.2), (114, 0.14), (132, -0.04), (134, -0.5), (118, -0.98), (98, -1.08),
            (82, -1.0), (78, -0.4)])
    wf = cut(wf, [ARM.xy(94, -0.36), ARM.xy(108, -0.42), ARM.xy(122, -0.34)], GAP * 0.9)
    S.append(("wrist_flexors", wf))
    ser = unary_union([tri((140, 119.4), (127, 130), 3.2, 1.0), tri((139.6, 127.4), (126.6, 139), 3.3, 1.0),
                       tri((138.6, 135.4), (126.4, 147.6), 3.2, 1.0), tri((137.4, 143.4), (127, 154.6), 2.8, 0.8)])
    S.append(("serratus_anterior", ser))
    S.append(("latissimus_dorsi", P([(139.6, 118), (139.2, 130), (137.6, 146), (135.4, 158), (133.2, 161),
                                     (134.4, 146), (135.6, 131), (136.4, 121)])))
    rec = P([(101, 130), (110, 129.4), (116.6, 131.6), (117.6, 145), (116.8, 160), (115.6, 175), (113.6, 190),
             (109, 203), (104.4, 211), (101, 211.6)])
    for y in (144.5, 158, 171.5):
        rec = cut(rec, [(98, y + 0.6), (108, y - 0.3), (120, y + 0.8)], 1.3)
    S.append(("rectus_abdominis", rec))
    S.append(("external_obliques", P([(117.8, 137), (127, 138), (137.4, 145), (134.4, 158), (133.2, 168),
                                      (134.4, 180), (136, 189), (131, 195.5), (121, 201.6), (114.4, 203.6),
                                      (114.8, 180), (116.4, 158)])))
    # thigh
    S.append(("sartorius", LEG.strap([(0, 0.62), (14, 0.42), (32, 0.06), (54, -0.42), (76, -0.76), (96, -0.95),
                                      (116, -1.0)], 2.2)))
    S.append(("tensor_fasciae_latae", L([(2, 0.72), (6, 1.06), (22, 1.1), (40, 1.0), (45, 0.86), (30, 0.72),
                                          (12, 0.58)])))
    S.append(("rectus_femoris", L([(4, 0.2), (16, 0.5), (38, 0.6), (62, 0.52), (84, 0.34), (98, 0.14), (102, 0.0),
                                   (92, -0.22), (66, -0.42), (36, -0.44), (12, -0.16)])))
    S.append(("vastus_medialis", L([(58, -0.46), (74, -0.32), (92, -0.16), (104, -0.1), (110, -0.34), (108, -0.8),
                                    (98, -1.08), (82, -1.1), (66, -0.9)])))
    S.append(("vastus_lateralis", L([(8, 0.85), (30, 1.1), (62, 1.1), (88, 1.04), (102, 0.8), (110, 0.46),
                                     (100, 0.2), (80, 0.3), (48, 0.48), (22, 0.6)])))
    S.append(("gracilis", L([(20, -0.76), (46, -0.74), (70, -0.84), (96, -1.0), (96, -1.16), (50, -1.16),
                             (18, -1.16)])))
    S.append(("adductor_longus", L([(10, -0.2), (22, -0.16), (38, -0.36), (54, -0.62), (62, -0.86), (52, -0.94),
                                    (30, -0.98), (14, -0.9), (6, -0.6)])))
    # lower leg
    S.append(("tibialis_anterior", L([(116, 0.06), (118, 0.58), (136, 0.64), (158, 0.5), (178, 0.28),
                                      (194, 0.12), (192, -0.04), (166, -0.1), (136, -0.14)])))
    S.append(("fibularis", L([(114, 0.62), (132, 0.7), (158, 0.66), (182, 0.56), (196, 0.5), (192, 1.12),
                              (158, 1.12), (124, 1.12)])))
    S.append(("gastrocnemius", L([(116, -0.5), (134, -0.46), (152, -0.56), (164, -0.8), (160, -1.1),
                                  (128, -1.1)])))
    S.append(("soleus", L([(150, -0.5), (172, -0.56), (190, -0.7), (186, -1.1), (162, -1.1)])))
    return S

# ---------------------------------------------------------------- BACK, surface
def back_surface():
    S = []
    S.append(("splenius", P([(106.2, 50.6), (111.2, 52.6), (113.8, 60), (113.6, 67), (110.4, 66.4),
                             (107.8, 58)])))
    S.append(("trap_upper", P([(101, 50), (106, 51.5), (108, 60), (111, 68), (118, 74.5), (130, 79.6),
                               (141.4, 83.2), (139, 86.8), (130, 86), (120, 84.6), (110, 83), (101, 82)])))
    S.append(("trap_middle", P([(101, 82.4), (112, 83.6), (124, 85.4), (138.4, 87.6), (136, 91.6), (127, 95),
                                (118, 99.5), (108, 103.5), (101, 105.5)])))
    S.append(("trap_lower", P([(101, 104), (110, 101.5), (120, 97.6), (124.6, 99), (121.6, 106), (114, 122),
                               (107, 138), (101, 152.6)])))
    S.append(("deltoid_posterior", side_of(DELT_SPLIT, DELTOID, "left")))
    S.append(("deltoid_lateral", side_of(DELT_SPLIT, DELTOID, "right")))
    S.append(("infraspinatus", P([(119.6, 99), (128, 96.4), (137, 95.6), (140.2, 101), (138.6, 108),
                                  (133, 115), (126, 122), (121, 124.6), (118.6, 112)])))
    S.append(("teres_minor", P([(131.6, 115), (137.6, 107.4), (141.8, 104.4), (143.4, 109.4), (139.4, 114.8),
                                (134.2, 119.4)])))
    S.append(("teres_major", P([(122, 125.8), (130, 119.8), (138, 115.4), (143.8, 112.6), (146.4, 117.4),
                                (140.4, 123.4), (131, 129.4), (124, 131.4)])))
    S.append(("erector_spinae", P([(101.6, 140), (105, 138), (109, 150), (113, 168), (115, 184), (114, 196),
                                   (110, 204), (104, 207), (101.6, 204)])))
    S.append(("latissimus_dorsi", P([(101, 146), (106, 138), (113, 131), (121, 128), (130, 124), (138, 119),
                                     (145, 117), (142.6, 124), (139.6, 135), (137, 150), (135, 165), (133, 178),
                                     (129.6, 187), (122, 184), (112, 172), (104, 162), (101, 156)])))
    S.append(("external_obliques", P([(133.8, 165), (137.6, 169.6), (139.4, 182), (139.6, 192.4), (134, 194.4),
                                      (128.6, 189.4), (131.8, 178)])))
    S.append(("triceps_lateral", A([(14, 0.3), (20, 1.04), (40, 1.08), (56, 0.9), (64, 0.46), (60, 0.14),
                                    (44, 0.06), (26, 0.06)])))
    S.append(("triceps_long", A([(10, -0.3), (18, 0.04), (40, 0.02), (58, 0.0), (68, -0.2), (66, -0.66),
                                 (52, -1.04), (28, -1.1), (12, -0.96)])))
    S.append(("brachioradialis", A([(60, 0.86), (76, 1.07), (98, 1.07), (116, 0.86), (108, 0.7), (86, 0.72),
                                    (70, 0.66)])))
    we = A([(80, 0.62), (96, 0.66), (116, 0.6), (132, 0.28), (134, -0.12), (118, -0.5), (96, -0.6),
            (82, -0.48), (78, 0.1)])
    we = cut(we, [ARM.xy(94, 0.12), ARM.xy(108, 0.08), ARM.xy(122, 0.08)], GAP * 0.9)
    S.append(("wrist_extensors", we))
    S.append(("wrist_flexors", A([(78, -0.62), (96, -0.72), (118, -0.66), (130, -0.6), (118, -1.08),
                                  (96, -1.1), (80, -1.02)])))
    S.append(("gluteus_medius", P([(112, 192.4), (124, 189.6), (134, 191), (139.8, 197), (141.6, 207.4),
                                   (140, 215), (133.4, 208.6), (124.6, 203), (116.6, 199.4)])))
    S.append(("gluteus_maximus", P([(102, 214), (103.4, 206), (108, 201.4), (116.4, 200.4), (125, 203),
                                    (132.4, 208.4), (137.6, 216), (138.8, 226), (135.6, 235.6), (128.4, 242.4),
                                    (118.4, 245.6), (109.6, 245), (104.2, 241.6), (102, 233)])))
    S.append(("vastus_lateralis", L([(30, 0.9), (60, 0.92), (86, 0.94), (104, 0.92), (112, 1.2), (80, 1.2),
                                     (34, 1.2)])))
    S.append(("biceps_femoris", L([(44, 0.0), (56, 0.5), (76, 0.88), (98, 0.94), (112, 0.88), (118, 0.6),
                                   (106, 0.36), (86, 0.1), (62, -0.06)])))
    S.append(("adductor_magnus", L([(30, -0.46), (46, -0.5), (58, -0.62), (66, -0.9), (54, -0.98), (38, -0.98),
                                    (28, -0.84)])))
    S.append(("semitendinosus", L([(46, -0.08), (62, 0.02), (84, -0.06), (100, -0.22), (111, -0.46), (104, -0.62),
                                   (86, -0.58), (66, -0.62), (48, -0.5)])))
    S.append(("gracilis", L([(46, -0.9), (74, -0.9), (100, -0.93), (118, -0.96), (112, -1.2), (60, -1.2),
                             (44, -1.2)])))
    S.append(("semimembranosus", L([(58, -0.54), (84, -0.54), (104, -0.58), (116, -0.62), (119, -0.94), (102, -0.98),
                                    (80, -0.98), (62, -0.94)])))
    gl = L([(112, 0.1), (118, 0.64), (132, 0.94), (148, 0.88), (160, 0.54), (163, 0.12), (150, 0.04), (126, 0.03)])
    gm = L([(112, -0.1), (120, -0.68), (134, -1.02), (152, -1.0), (168, -0.62), (173, -0.12), (160, -0.04),
            (128, -0.04)])
    S.append(("gastrocnemius", unary_union([gl, gm])))
    sol = L([(140, -1.08), (156, -1.1), (176, -0.94), (194, -0.52), (199, -0.2), (199, 0.2), (194, 0.52),
             (176, 0.94), (156, 1.1), (140, 1.08), (150, 0)])
    sol = sol.difference(L([(178, -0.26), (210, -0.3), (210, 0.3), (178, 0.26), (172, 0)]))
    S.append(("soleus", sol))
    return S

# ---------------------------------------------------------------- DEEP layers
def front_deep():
    S = []
    S.append(("pec_minor", P([(138.6, 91), (134, 97), (126, 108), (120.6, 121), (116, 123.6), (113.6, 117),
                              (116.6, 107), (124, 98), (132, 92.6)])))
    S.append(("subscapularis", P([(135, 96.6), (141, 98.8), (144, 108), (142, 117), (138, 121.6), (134.4, 115),
                                  (133.4, 105)])))
    S.append(("internal_obliques", P([(116.6, 140), (126, 138.6), (137, 146), (134.6, 158), (133.6, 168.6),
                                      (126, 172), (118.4, 168), (116.2, 155)])))
    S.append(("transversus_abdominis", P([(101, 152), (114, 150.6), (126, 152.6), (134.4, 160), (135, 172),
                                          (129, 182), (116, 186.6), (101, 188)])))
    S.append(("iliopsoas", P([(102.8, 160), (106.8, 159.6), (109.6, 173), (113.4, 185), (118, 185.4),
                              (124.4, 182.6), (130.2, 185), (130, 194), (125, 204.6), (119.8, 214), (117.6, 224),
                              (116.4, 230), (112.6, 229.6), (111.8, 218), (108.4, 202), (104.8, 184),
                              (103, 170)])))
    S.append(("vastus_intermedius", L([(14, 0.26), (30, 0.62), (60, 0.62), (86, 0.4), (99, 0.1), (97, -0.14),
                                       (80, -0.42), (50, -0.52), (24, -0.38), (12, -0.06)])))
    return S

def back_deep():
    S = []
    S.append(("supraspinatus", P([(117.6, 88.6), (127, 86.8), (137, 86.6), (141.6, 88.4), (137, 92.2),
                                  (127, 95.2), (119.6, 96.6)])))
    rh = P([(101.8, 86.2), (108, 88), (116.6, 96), (119.8, 108), (121.2, 123), (117, 126.4), (110, 118.4),
            (101.8, 108.4)])
    rh = cut(rh, [(99, 92.6), (110, 96.6), (122, 101.6)], GAP)
    S.append(("rhomboids", rh))
    S.append(("quadratus_lumborum", P([(106.6, 162), (113, 161), (119, 166), (121.6, 176), (120.6, 187),
                                       (115, 191), (108, 190), (106.2, 178)])))
    S.append(("gluteus_minimus", P([(120.6, 198), (130, 195.6), (137.6, 199.6), (139.6, 207), (134, 212.4),
                                    (125, 209.4)])))
    S.append(("triceps_medial", A([(46, -0.56), (58, -0.66), (70, -0.56), (77, -0.28), (77, 0.3), (70, 0.56),
                                   (58, 0.6), (48, 0.44), (42, 0)])))
    return S

# ---------------------------------------------------------------- carving
def carve(items, gap=GAP):
    clip = BODY.buffer(-RIM, join_style=1).intersection(HALF)
    taken, out = None, []
    for key, g in items:
        g = g.buffer(0).intersection(clip)
        if taken is not None:
            g = g.difference(taken.buffer(gap, join_style=1))
        g = tidy(g)
        if g.is_empty:
            print("WARNING empty region:", key); continue
        out.append((key, g))
        taken = g if taken is None else unary_union([taken, g])
    return out

def build():
    layers = {("front", "surface"): front_surface(), ("back", "surface"): back_surface(),
              ("front", "deep"): front_deep(), ("back", "deep"): back_deep()}
    paths = []
    for (view, layer), items in layers.items():
        for key, g in carve(items):
            # viewer's right half: subject's left in the front view, subject's right in the back view
            paths.append(dict(key=key, view=view, layer=layer, side="left" if view == "front" else "right", g=g))
            paths.append(dict(key=key, view=view, layer=layer, side="right" if view == "front" else "left",
                              g=mirror(g)))
    return paths

# ---------------------------------------------------------------- path encoding
def _n(v):
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    if s in ("-0", ""): s = "0"
    if s.startswith("0."): s = s[1:]
    elif s.startswith("-0."): s = "-" + s[2:]
    return s

def _pair(a, b):
    sa, sb = _n(a), _n(b)
    return sa + ("" if sb.startswith("-") else " ") + sb

def ring_d(coords, tol=0.09):
    ls = LineString(coords).simplify(tol, preserve_topology=False)
    c = np.round(np.array(ls.coords) * 10).astype(int)
    if len(c) > 1 and (c[0] == c[-1]).all(): c = c[:-1]
    keep = [c[0]]
    for p in c[1:]:
        if (p != keep[-1]).any(): keep.append(p)
    c = np.array(keep)
    s = "M" + _pair(c[0][0] / 10, c[0][1] / 10) + "l"
    prev = c[0]; chunks = []
    for p in c[1:]:
        d = p - prev; prev = p
        chunks.append(_pair(d[0] / 10, d[1] / 10))
    out = chunks[0] if chunks else ""
    for ch in chunks[1:]:
        out += ch if ch.startswith("-") else " " + ch
    return s + out + "z"

def geom_d(g):
    s = ""
    for p in parts(g):
        p = p.buffer(0)
        from shapely.geometry.polygon import orient
        p = orient(p, 1.0)
        s += ring_d(list(p.exterior.coords))
        for r in p.interiors:
            s += ring_d(list(r.coords))
    return s

V1_KEYS = ["sternocleidomastoid", "trap_upper", "deltoid_anterior", "deltoid_lateral",
  "pec_major_clavicular", "pec_major_sternal", "biceps_long", "biceps_short",
  "brachialis", "brachioradialis", "wrist_flexors", "serratus_anterior",
  "rectus_abdominis", "external_obliques", "latissimus_dorsi", "tensor_fasciae_latae",
  "sartorius", "rectus_femoris", "vastus_medialis", "vastus_lateralis",
  "gracilis", "adductor_longus", "tibialis_anterior", "fibularis",
  "gastrocnemius", "soleus", "trap_middle", "trap_lower",
  "splenius", "deltoid_posterior", "infraspinatus", "triceps_lateral",
  "triceps_long", "teres_minor", "teres_major", "wrist_extensors",
  "erector_spinae", "gluteus_maximus", "gluteus_medius", "semitendinosus",
  "biceps_femoris", "semimembranosus", "adductor_magnus", "pec_minor",
  "subscapularis", "transversus_abdominis", "internal_obliques", "iliopsoas",
  "vastus_intermedius", "supraspinatus", "rhomboids", "quadratus_lumborum",
  "gluteus_minimus", "triceps_medial"]

def write_ts(paths):
    outline = geom_d(BODY)
    keys = "\n".join("  " + ", ".join(f'"{k}"' for k in V1_KEYS[i:i + 4]) + "," for i in range(0, len(V1_KEYS), 4))
    rows = []
    order = {k: i for i, k in enumerate(V1_KEYS)}
    lay = {("front", "surface"): 0, ("back", "surface"): 1, ("front", "deep"): 2, ("back", "deep"): 3}
    for p in sorted(paths, key=lambda p: (lay[(p["view"], p["layer"])], order[p["key"]], p["side"])):
        rows.append(f'  {{ key: "{p["key"]}", view: "{p["view"]}", layer: "{p["layer"]}", side: "{p["side"]}", '
                    f'd: "{geom_d(p["g"])}" }},')
    ts = f"""// ASCEND anatomical muscle map (v2): original artwork, generated by build_map.py.
// Do not edit by hand: change the shapes in build_map.py and re-run it.
// Coordinates: one shared viewBox for both views, x = 100 is the body midline.
// "side" is the subject's own side (front view: subject's right is on the viewer's left).

export interface MusclePath {{
  key: string;
  view: "front" | "back";
  layer: "surface" | "deep";
  d: string;
  side?: "left" | "right";
}}

export const BODY_VIEWBOX = "0 0 {VB_W} {VB_H}";

/** Whole-body silhouette (head, torso, limbs, hands, feet), drawn underneath the muscles. */
export const BODY_OUTLINE: {{ front: string; back: string }} = {{
  front: "{outline}",
  back: "{outline}",
}};

export const MUSCLE_KEYS = [
{keys}
] as const;

export const MUSCLE_PATHS: MusclePath[] = [
{chr(10).join(rows)}
];
"""
    open(os.path.join(OUT, "bodyMapPaths.ts"), "w").write(ts)
    return ts, outline

# ---------------------------------------------------------------- previews
THEMES = {
    "dark": dict(bg="#0b1220", fill="#16213a", border="#2c4470", ink="#e8f0ff", sub="#8fa3c4"),
    "light": dict(bg="#f3f6fb", fill="#e2e9f3", border="#afc0d8", ink="#0b1424", sub="#5a6b86"),
}
# Suggested muted recovery palette (HSL saturation 55-65 %, no glow)
PALETTE = {"ready": "#3e9e7c", "light": "#c9a440", "moderate": "#d07a45", "heavy": "#c2525d"}
DEMO = {"pec_major_sternal": "heavy", "pec_major_clavicular": "moderate", "deltoid_anterior": "moderate",
        "triceps_lateral": "light", "triceps_long": "light", "rectus_femoris": "ready", "vastus_lateralis": "ready",
        "vastus_medialis": "ready", "biceps_long": "ready", "biceps_short": "ready", "latissimus_dorsi": "moderate",
        "teres_major": "light", "biceps_femoris": "heavy", "semitendinosus": "heavy", "semimembranosus": "moderate",
        "gluteus_maximus": "light", "gastrocnemius": "ready", "rectus_abdominis": "light", "external_obliques": "ready",
        "pec_minor": "moderate", "transversus_abdominis": "light", "iliopsoas": "ready", "rhomboids": "moderate",
        "supraspinatus": "light", "quadratus_lumborum": "ready", "triceps_medial": "light", "vastus_intermedius": "ready",
        "trap_middle": "moderate", "infraspinatus": "light", "deltoid_posterior": "light", "erector_spinae": "light",
        "sartorius": "ready"}

def figure_svg(paths, outline, view, layer, theme, w, fills=None, ghost_op=0.35, extra="", bg=True,
               stroke_scale=1.0, h=None):
    T = THEMES[theme]
    fills = fills if fills is not None else {k: PALETTE[v] for k, v in DEMO.items()}
    h = h or w * VB_H / VB_W
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB_W} {VB_H}" width="{w}" height="{h}">']
    if bg: s.append(f'<rect x="-50" y="-50" width="400" height="600" fill="{T["bg"]}"/>')
    s.append(f'<path d="{outline}" fill="{T["fill"]}" stroke="{T["border"]}" stroke-width="{0.8*stroke_scale}" opacity="0.9"/>')
    def draw(p, ghost):
        f = T["fill"] if ghost else fills.get(p["key"], T["fill"])
        op = f' opacity="{ghost_op}"' if ghost else ""
        return f'<path d="{p["d"]}" fill="{f}" stroke="{T["border"]}" stroke-width="{0.6*stroke_scale}"{op}/>'
    for p in paths:
        if p["view"] == view and p["layer"] == "surface": s.append(draw(p, layer == "deep"))
    if layer == "deep":
        for p in paths:
            if p["view"] == view and p["layer"] == "deep": s.append(draw(p, False))
    s.append(extra + "</svg>")
    return "".join(s)

def render(svg, path, w=None):
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=path)

def panel_row(paths, outline, theme, w, views, fills=None, gap=16, label=True):
    """Several views side by side in one PNG (via one SVG)."""
    T = THEMES[theme]
    h = w * VB_H / VB_W
    W = len(views) * w + (len(views) + 1) * gap
    H = h + (34 if label else 0) + gap
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{T["bg"]}"/>']
    for i, (view, layer, title) in enumerate(views):
        x = gap + i * (w + gap)
        inner = figure_svg(paths, outline, view, layer, theme, w, fills=fills, bg=False)
        inner = inner.replace('<svg ', f'<svg x="{x}" y="{gap}" ', 1)
        s.append(inner)
        if label:
            s.append(f'<text x="{x + w/2}" y="{gap + h + 24}" font-family="DejaVu Sans" font-size="15" '
                     f'fill="{T["sub"]}" text-anchor="middle">{title}</text>')
    s.append("</svg>")
    return "".join(s)


def check_image(paths, outline, path, w=420):
    import colorsys
    keys = V1_KEYS
    cols = {}
    for i, k in enumerate(keys):
        h = (i * 0.61803) % 1.0
        r, g, b = colorsys.hls_to_rgb(h, 0.55, 0.55)
        cols[k] = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
    views = [("front", "surface", "FRONT"), ("back", "surface", "BACK"), ("front", "deep", "DEEP FRONT"),
             ("back", "deep", "DEEP BACK")]
    margin = 150
    h = w * VB_H / VB_W
    PW = w + 2 * margin
    W, H = PW * len(views), h + 60
    sc = w / VB_W
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    for i, (view, layer, title) in enumerate(views):
        x0 = i * PW + margin
        inner = figure_svg(paths, outline, view, layer, "light", w, fills=cols, bg=False, ghost_op=0.25)
        s.append(inner.replace("<svg ", f'<svg x="{x0}" y="40" ', 1))
        s.append(f'<text x="{x0 + w/2}" y="26" font-family="DejaVu Sans" font-weight="bold" font-size="18" '
                 f'text-anchor="middle" fill="#0b1424">{title}</text>')
        # one label per key, at the viewer's-right copy (largest part), leader line to the right margin
        labs = []
        for p in paths:
            if p["view"] != view or p["layer"] != layer: continue
            g = p["g"]
            if g.centroid.x < CX: continue
            big = max(parts(g), key=lambda q: q.area)
            pt = big.representative_point()
            labs.append([pt.y, pt.x, p["key"]])
        labs.sort()
        ys = [l[0] for l in labs]
        step = 11.5 / sc
        for j in range(1, len(ys)):
            ys[j] = max(ys[j], ys[j - 1] + step)
        over = ys[-1] - (VB_H - 4) if ys else 0
        if over > 0: ys = [y - over for y in ys]
        for j in range(len(ys) - 2, -1, -1):
            ys[j] = min(ys[j], ys[j + 1] - step)
        for (py, px, key), ly in zip(labs, ys):
            X1, Y1 = x0 + px * sc, 40 + py * sc
            X2, Y2 = x0 + w + 8, 40 + ly * sc
            s.append(f'<circle cx="{X1}" cy="{Y1}" r="2.2" fill="#0b1424"/>')
            s.append(f'<polyline points="{X1},{Y1} {X2 - 10},{Y2} {X2},{Y2}" fill="none" stroke="#0b1424" stroke-width="0.7"/>')
            s.append(f'<text x="{X2 + 3}" y="{Y2 + 3.5}" font-family="DejaVu Sans" font-size="10.5" fill="{cols[key]}" '
                     f'stroke="#000" stroke-width="0.25">{key}</text>')
    s.append("</svg>")
    render("".join(s), path)


def tile_check(paths, outline, path):
    """64x96 tiles (as used for exercise art), shown at 1x and enlarged x4 (nearest neighbour)."""
    from PIL import Image
    import io, cairosvg
    acc = {"dark": "#3e9e7c", "light": "#2f8a6b"}
    cases = [("front", {"pec_major_sternal": 1, "pec_major_clavicular": 1, "deltoid_anterior": .5, "triceps_lateral": .5}),
             ("back", {"latissimus_dorsi": 1, "teres_major": .5, "biceps_long": .5, "trap_middle": .5, "rhomboids": .5}),
             ("front", {"rectus_femoris": 1, "vastus_lateralis": 1, "vastus_medialis": 1, "gluteus_maximus": .5}),
             ("back", {"biceps_femoris": 1, "semitendinosus": 1, "semimembranosus": 1, "gluteus_maximus": .5})]
    tiles = []
    for theme in ("dark", "light"):
        T = THEMES[theme]
        for view, m in cases:
            fills = {k: (acc[theme] if w >= 1 else ("#2a5b55" if theme == "dark" else "#9fcfbd")) for k, w in m.items()}
            fig_h = 92; fig_w = fig_h * VB_W / VB_H
            inner = figure_svg(paths, outline, view, "surface", theme, fig_w, fills=fills, bg=False)
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="96"><rect width="64" height="96" rx="6" '
                   f'fill="{T["bg"]}"/>' + inner.replace("<svg ", f'<svg x="{(64-fig_w)/2}" y="2" ', 1) + "</svg>")
            tiles.append(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGB"))
    W = 8 * 64 + 9 * 8
    sheet = Image.new("RGB", (W * 4 // 4 + 0, 96 + 16 + 96 * 4 + 16), "#7f8a99")
    for i, t in enumerate(tiles):
        sheet.paste(t, (8 + i * 72, 8))
        big = t.resize((64 * 4 // 2 * 1, 96 * 4 // 2 * 1), Image.NEAREST)
    big_sheet = Image.new("RGB", (8 * (128 + 8) + 8, 192 + 16), "#7f8a99")
    for i, t in enumerate(tiles):
        big_sheet.paste(t.resize((128, 192), Image.NEAREST), (8 + i * 136, 8))
    out = Image.new("RGB", (max(sheet.width, big_sheet.width), 96 + 16 + big_sheet.height), "#7f8a99")
    out.paste(sheet.crop((0, 0, sheet.width, 112)), (0, 0)); out.paste(big_sheet, (0, 112))
    out.save(path)


def parse_ts(path):
    t = open(path).read()
    rows = re.findall(r'\{ key: "(\w+)", view: "(\w+)", layer: "(\w+)",(?: side: "\w+",)? d: "([^"]+)" \}', t)
    of = re.search(r'front: "([^"]+)"', t).group(1); ob = re.search(r'back: "([^"]+)"', t).group(1)
    return [dict(key=k, view=v, layer=l, d=d) for k, v, l, d in rows], {"front": of, "back": ob}

def compare_image(paths, outline, path, v1_ts):
    v1, v1o = parse_ts(v1_ts)
    T = THEMES["dark"]; w = 260; h = w * VB_H / VB_W; gap = 18
    views = [("front", "surface", "Front"), ("back", "surface", "Back"), ("front", "deep", "Deep front"),
             ("back", "deep", "Deep back")]
    W = 4 * w + 5 * gap; RH = h + 60
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{2*RH + 20}">',
         f'<rect width="{W}" height="{2*RH + 20}" fill="{T["bg"]}"/>']
    for r, (label, P_, O_) in enumerate([("v1", v1, None), ("v2", paths, outline)]):
        y0 = 10 + r * RH
        s.append(f'<text x="{gap}" y="{y0 + 26}" font-family="DejaVu Sans" font-weight="bold" font-size="20" fill="{T["ink"]}">{label}</text>')
        for i, (view, layer, title) in enumerate(views):
            x = gap + i * (w + gap)
            o = O_ if O_ is not None else v1o[view]
            inner = figure_svg(P_, o, view, layer, "dark", w, bg=False)
            s.append(inner.replace("<svg ", f'<svg x="{x}" y="{y0 + 36}" ', 1))
            s.append(f'<text x="{x + w/2}" y="{y0 + 36 + h + 18}" font-family="DejaVu Sans" font-size="13" fill="{T["sub"]}" text-anchor="middle">{title}</text>')
    s.append("</svg>")
    render("".join(s), path)

def main():
    paths = build()
    ts, outline = write_ts(paths)
    for p in paths: p["d"] = geom_d(p["g"])
    size = len(ts.encode())
    counts = {}
    for p in paths:
        counts.setdefault((p["view"], p["layer"]), set()).add(p["key"])
    allkeys = set(p["key"] for p in paths)
    print("TS bytes", size, "paths", len(paths), "keys", len(allkeys))
    for k, v in counts.items(): print(k, len(v))
    missing = set(V1_KEYS) - allkeys
    assert not missing, missing
    pv = os.path.join(OUT, "previews"); os.makedirs(pv, exist_ok=True)
    views = [("front", "surface", "Front"), ("back", "surface", "Back"), ("front", "deep", "Deep front"),
             ("back", "deep", "Deep back")]
    for theme in ("dark", "light"):
        for view, layer, title in views:
            name = f"{'deep_' if layer == 'deep' else ''}{view}{'' if theme == 'dark' else '_light'}.png"
            render(figure_svg(paths, outline, view, layer, theme, 260), os.path.join(pv, name))
        render(panel_row(paths, outline, theme, 260, views), os.path.join(pv, f"all_{theme}.png"))
    check_image(paths, outline, os.path.join(pv, "key_check.png"))
    tile_check(paths, outline, os.path.join(pv, "tile_check_64x96.png"))
    v1_ts = os.environ.get("V1_TS", "")  # optional: path to the v1 bodyMapPaths.ts for a side-by-side
    if v1_ts and os.path.exists(v1_ts):
        compare_image(paths, outline, os.path.join(pv, "compare_v1_v2.png"), v1_ts)
    return paths, outline

if __name__ == "__main__":
    main()


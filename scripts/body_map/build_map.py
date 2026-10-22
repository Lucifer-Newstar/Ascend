#!/usr/bin/env python3
"""ASCEND anatomical muscle map generator.

Hand-authored, original artwork. Every muscle is defined below as a closed
Catmull-Rom spline (converted to cubic Beziers) through hand-placed control
points on ONE side of the body (viewer's left, x < 100). Shapes are then
  1. clipped to the body silhouette (inset slightly, so a thin rim shows),
  2. trimmed against the muscles placed before them with a constant gap,
  3. mirrored around the centre line x = 100,
and finally re-emitted as compact cubic-Bezier path data.

Run:  python3 build_map.py      (needs: shapely, cairosvg, pillow)
Writes bodyMapPaths.ts and preview PNGs next to this script.
"""
import math, os, sys
from shapely.geometry import Polygon, MultiPolygon, LineString, box, GeometryCollection
from shapely.ops import unary_union
from shapely import affinity

OUT = os.path.dirname(os.path.abspath(__file__))
W, H = 200, 430
CX = 100.0
GAP = 0.85          # gap between neighbouring muscles (viewBox units)
INSET = 0.7         # how far muscles sit inside the silhouette edge
MIN_AREA = 1.2

# ---------------------------------------------------------------- geometry helpers
def _pt(p):
    return (p[0], p[1]), (len(p) > 2 and p[2] == 'c')

def _bez(p1, c1, c2, p2, n, out):
    for k in range(n):
        t = k/n; a = (1-t)**3; b = 3*(1-t)**2*t; c = 3*(1-t)*t*t; d = t**3
        out.append((a*p1[0]+b*c1[0]+c*c2[0]+d*p2[0], a*p1[1]+b*c1[1]+c*c2[1]+d*p2[1]))

def spline_closed(pts, n=14):
    P, C = zip(*[_pt(p) for p in pts])
    m = len(P); out = []
    for i in range(m):
        p0, p1, p2, p3 = P[i-1], P[i], P[(i+1) % m], P[(i+2) % m]
        t1 = (0, 0) if C[i] else ((p2[0]-p0[0])/6, (p2[1]-p0[1])/6)
        t2 = (0, 0) if C[(i+1) % m] else ((p3[0]-p1[0])/6, (p3[1]-p1[1])/6)
        _bez(p1, (p1[0]+t1[0], p1[1]+t1[1]), (p2[0]-t2[0], p2[1]-t2[1]), p2, n, out)
    return out

def spline_open(pts, n=14):
    P = [(p[0], p[1]) for p in pts]
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P)-2):
        p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
        _bez(p1, (p1[0]+(p2[0]-p0[0])/6, p1[1]+(p2[1]-p0[1])/6),
             (p2[0]-(p3[0]-p1[0])/6, p2[1]-(p3[1]-p1[1])/6), p2, n, out)
    out.append(P[-2])
    return out

def S(pts):
    """Smooth closed shape through control points ('c' marks a sharp corner)."""
    return Polygon(spline_closed(pts)).buffer(0)

def strap(center, w0, w1, taper=0.08):
    """A tapering band along a smooth centre line (sartorius, gracilis ...)."""
    c = spline_open(center, 16)
    L = [0.0]
    for i in range(1, len(c)):
        L.append(L[-1] + math.dist(c[i-1], c[i]))
    tot = L[-1]; left = []; right = []
    for i, p in enumerate(c):
        a = c[max(i-1, 0)]; b = c[min(i+1, len(c)-1)]
        dx, dy = b[0]-a[0], b[1]-a[1]; l = math.hypot(dx, dy) or 1
        nx, ny = -dy/l, dx/l
        s = L[i]/tot
        w = (w0 + (w1-w0)*s) * min(1.0, (min(s, 1-s)/taper)) ** 0.5
        left.append((p[0]+nx*w/2, p[1]+ny*w/2)); right.append((p[0]-nx*w/2, p[1]-ny*w/2))
    return Polygon(left + right[::-1]).buffer(0)

class Limb:
    """Local frame along a limb segment: t in [0,1] along the bone, u = offset
    (positive = lateral, i.e. away from the body's centre line)."""
    def __init__(self, a, b):
        self.a = a; dx, dy = b[0]-a[0], b[1]-a[1]
        self.len = math.hypot(dx, dy); self.d = (dx/self.len, dy/self.len)
        n = (-self.d[1], self.d[0])
        if n[0] > 0: n = (-n[0], -n[1])
        self.n = n
    def __call__(self, t, u, *flag):
        x = self.a[0] + self.d[0]*t*self.len + self.n[0]*u
        y = self.a[1] + self.d[1]*t*self.len + self.n[1]*u
        return (x, y) + flag

def ext_line(pts, k=300):
    (x0, y0), (x1, y1) = pts[0], pts[1]
    l = math.hypot(x1-x0, y1-y0); a = (x0-(x1-x0)/l*k, y0-(y1-y0)/l*k)
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    l = math.hypot(x1-x0, y1-y0); b = (x1+(x1-x0)/l*k, y1+(y1-y0)/l*k)
    return [a] + list(pts) + [b]

def split(g, line, side='above', gap=GAP):
    """Cut g along a polyline with a gap; returns (part on `side`, the rest)."""
    pts = ext_line([(p[0], p[1]) for p in line])
    far = 2000
    if side == 'above':   cap = [(pts[-1][0], -far), (pts[0][0], -far)]
    elif side == 'below': cap = [(pts[-1][0], far), (pts[0][0], far)]
    elif side == 'left':  cap = [(-far, pts[-1][1]), (-far, pts[0][1])]
    else:                 cap = [(far, pts[-1][1]), (far, pts[0][1])]
    half = Polygon(pts + cap).buffer(0)
    cut = LineString(pts).buffer(gap/2, cap_style=2)
    return (g.intersection(half).difference(cut), g.difference(half).difference(cut))

def split_region(g, region, gap=GAP):
    """Cut g by a polygon region with a gap; returns (inside, outside)."""
    R = Polygon(region).buffer(0)
    cut = R.exterior.buffer(gap/2, cap_style=2)
    return g.intersection(R).difference(cut), g.difference(R).difference(cut)

def mirror(g):
    return affinity.scale(g, xfact=-1, yfact=1, origin=(CX, 0))

def parts(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, (MultiPolygon, GeometryCollection)):
        return [p for q in g.geoms for p in parts(q)]
    return []

def clean(g):
    ps = [p for p in parts(g.buffer(0)) if p.area >= MIN_AREA]
    return unary_union(ps) if ps else Polygon()

# ---------------------------------------------------------------- skeleton frames
U = Limb((63.0, 94.0), (45.0, 162.0))      # upper arm: shoulder joint -> elbow
F = Limb((45.0, 162.0), (32.0, 222.0))     # forearm: elbow -> wrist
Hd = Limb((32.0, 222.0), (32.0 - 0.2118*37, 222.0 + 0.9773*37))  # hand

# ---------------------------------------------------------------- silhouette
def silhouette():
    head = S([(100, 5.5), (108.5, 6.8), (115, 12), (117.5, 22), (117, 33), (115.3, 41),
              (112, 48.5), (106.5, 54.5), (100, 56.5), (93.5, 54.5), (88, 48.5), (84.7, 41),
              (83, 33), (82.5, 22), (85, 12), (91.5, 6.8)])
    neck = S([(90, 44, 'c'), (110, 44, 'c'), (111.6, 60), (113, 72), (100, 78), (87, 72), (88.4, 60)])
    torso = S([(100, 62, 'c'), (88.8, 63), (87.4, 69), (81.6, 74.5), (71, 78.5), (62, 82),
               (57.5, 87), (58, 97), (62, 106), (66.5, 113), (68.8, 122), (69.6, 133),
               (70.6, 146), (71.6, 158), (71.4, 168), (70.2, 178), (67.6, 189), (64.3, 200),
               (62.6, 213), (62.2, 228), (63.0, 248), (65.4, 270), (68.8, 289), (71.0, 302),
               (71.4, 313), (70.4, 326), (69.8, 340), (70.6, 355), (72.6, 370), (74.8, 386),
               (75.8, 397), (74.6, 405), (72.4, 413), (71.8, 419.5), (74.5, 423.6), (83, 424.6),
               (88.6, 422.8), (88.8, 415), (87.4, 406), (87.2, 398), (88.2, 386), (90.8, 368),
               (93.3, 348), (93.4, 331), (91.8, 319), (92.6, 306), (93.6, 292), (94.2, 276),
               (95.4, 258), (97.4, 240), (99.2, 226), (100, 221, 'c')])
    arm = S([U(-0.16, -3), U(-0.12, 7.4), U(0.04, 14.4), U(0.2, 14.6), U(0.36, 11.6), U(0.55, 10.4),
             U(0.78, 9.6), U(0.98, 9.4), F(0.13, 10.8), F(0.35, 8.9), F(0.62, 6.8), F(0.85, 5.8),
             F(1.0, 5.6), F(1.0, -5.3), F(0.82, -5.7), F(0.55, -7.2), F(0.3, -8.8), F(0.1, -9.8),
             U(0.93, -8.8), U(0.72, -9.8), U(0.5, -10.6), U(0.3, -10.2), U(0.14, -8), U(0.0, -4)])
    hand = S([Hd(0.0, 5.6), Hd(0.12, 7.4), Hd(0.27, 9.2), Hd(0.42, 9.6), Hd(0.5, 8.3), Hd(0.42, 6.6),
              Hd(0.6, 6.2), Hd(0.82, 5.0), Hd(0.97, 2.4), Hd(1.0, -0.6), Hd(0.93, -3.8),
              Hd(0.7, -5.6), Hd(0.4, -6.2), Hd(0.15, -5.8), Hd(0.0, -5.3)])
    left = unary_union([torso, arm, hand]).intersection(box(0, 0, CX, H))
    body = unary_union([left, mirror(left), head, neck]).buffer(0)
    body = body.buffer(1.6, join_style=1).buffer(-1.6, join_style=1)   # fillet armpits / crotch
    body = body.buffer(-0.6, join_style=1).buffer(0.6, join_style=1)   # round sharp tips
    return body

SIL = silhouette()
CLIP_L = SIL.buffer(-INSET).intersection(box(0, 0, CX - GAP/2, H))

class Layer:
    """Collects muscles for one view/layer. Earlier muscles win overlaps;
    later ones are trimmed so that a constant GAP separates neighbours."""
    def __init__(self, view, layer):
        self.view, self.layer = view, layer
        self.occ = Polygon(); self.items = []   # (key, geometry on the x<100 side)
    def add(self, key, g, gap=GAP):
        g = g.intersection(CLIP_L)
        others = unary_union([o for k, o in self.items if k != key]) if self.items else Polygon()
        if not others.is_empty:                # same key merges seamlessly; others keep the gap
            g = g.difference(others.buffer(gap, join_style=1))
        g = clean(g)
        if g.is_empty:
            print('  ! empty', self.view, self.layer, key); return
        self.occ = unary_union([self.occ, g])
        for i, (k, old) in enumerate(self.items):
            if k == key:                       # same key added twice: one compound region
                self.items[i] = (k, unary_union([old, g])); return
        self.items.append((key, g))

# ================================================================= FRONT SURFACE
def front_surface():
    L = Layer('front', 'surface')
    L.add('sternocleidomastoid', S([(89.6, 48.6), (92.8, 48.0), (95.6, 57), (98.2, 68), (99.6, 76.5, 'c'),
                                    (99.6, 80.5, 'c'), (95.4, 80.6), (92.8, 72.5), (90.4, 62)]))
    L.add('trap_upper', strap(  # levator scapulae strip, folded into trap_upper
        [(89.2, 55.5), (89.6, 63), (88.6, 70.5)], 4.0, 3.4, 0.2))
    L.add('trap_upper', S([(88.0, 66), (91.5, 70), (93.5, 75.5), (92.5, 79.2), (80, 80.4), (68, 83),
                           (59, 86.5), (57, 82), (67, 77.5), (79, 72.8), (86, 67.5)]))
    # deltoid (whole cap), split into anterior / lateral
    delt = S([U(-0.17, -2.5), U(-0.13, 6.5), U(-0.02, 13.8), U(0.13, 15.4), U(0.28, 13.4),
              U(0.38, 9.0), U(0.44, 6.0, 'c'), U(0.34, 1.6), U(0.22, -3.0), U(0.08, -7.4),
              U(-0.06, -8.6)])
    lat, ant = split(delt, [U(-0.4, 4.6), U(-0.1, 4.4), U(0.2, 5.8), U(0.6, 5.0)], side='left')
    L.add('deltoid_anterior', ant); L.add('deltoid_lateral', lat)
    pec = S([(99.0, 83.4, 'c'), (90, 82.6), (80, 83.6), (71, 86.4), (64.5, 91.5), (61.2, 99),
             (62.0, 106), (65.6, 112.4), (71.6, 118.8), (78.6, 123.6), (86.6, 126.4), (94.0, 126.6),
             (99.0, 125.2, 'c')])
    up, low = split(pec, [(102, 99.6), (90, 97.6), (78, 95.0), (66, 92.6), (58, 91.8)], side='above')
    L.add('pec_major_clavicular', up); L.add('pec_major_sternal', low)
    bic = S([U(0.27, -1.5), U(0.33, -6.8), U(0.47, -9.6), U(0.64, -9.4), U(0.8, -6.8),
             U(0.92, -2.6), U(0.97, 0.4, 'c'), U(0.9, 3.4), U(0.76, 6.9), U(0.58, 8.6),
             U(0.44, 7.6), U(0.34, 4.4)])
    blong, bshort = split(bic, [U(0.1, -0.2), U(0.5, -0.9), U(0.95, 0.2)], side='left')
    L.add('biceps_long', blong); L.add('biceps_short', bshort)
    L.add('brachialis', unary_union([
        S([U(0.5, 8.0), U(0.66, 10.6), U(0.86, 9.6), U(1.0, 6.0), U(0.92, 3.0), U(0.75, 5.0)]),
        S([U(0.58, -8.0), U(0.74, -10.6), U(0.9, -8.6), U(1.0, -4.2), U(0.9, -3.0), U(0.78, -6.0)])]))
    L.add('brachioradialis', S([U(0.72, 11.2), F(-0.08, 12.0), F(0.12, 12.0), F(0.3, 10.0), F(0.5, 7.4),
                                F(0.7, 5.6), F(0.9, 4.4, 'c'), F(0.72, 3.4), F(0.5, 2.6), F(0.3, 2.6),
                                F(0.12, 3.4), U(0.92, 6.2)]))
    L.add('wrist_flexors', S([F(0.04, 2.0), F(0.07, -5.0), F(0.14, -10.5), F(0.36, -9.2), F(0.62, -7.0),
                              F(0.84, -5.0), F(0.92, -1.5), F(0.88, 3.0), F(0.7, 4.4), F(0.4, 4.4),
                              F(0.18, 4.0)]))
    ser = unary_union([S([(66.5, y-3.4), (72, y-1.4), (78.2, y+2.2), (79.8, y+3.6, 'c'), (77.4, y+4.3),
                          (71.5, y+3.4), (66, y+2.2)]) for y in (113.5, 121.5, 129.5, 137.5)])
    L.add('serratus_anterior', ser)
    ra = S([(99.0, 122.0, 'c'), (92, 121.6), (86.8, 124.0), (85.6, 138), (85.4, 155), (85.9, 170),
            (87.4, 187), (89.8, 199), (93.6, 207.5), (97.3, 212.6), (99.0, 213.6, 'c')])
    for yl, yr in ((143.6, 144.8), (160.4, 161.8), (178.0, 179.4)):
        a, b = split(ra, [(102, yr), (93, yr + 0.4), (84, yl)], side='above', gap=1.25)
        ra = unary_union([a, b])
    L.add('rectus_abdominis', ra)
    L.add('external_obliques', S([(88, 136), (84, 128.6), (78.5, 126.4), (73, 128.5), (69.2, 137),
                                  (69.6, 152), (71.0, 166), (70.8, 178), (72.6, 186), (79, 191.5),
                                  (87.5, 199.5), (93.5, 206.5), (96.5, 212), (93, 190), (90, 165)]))
    L.add('latissimus_dorsi', S([(63.5, 108), (69.8, 112), (70.4, 126), (71.2, 141), (72.6, 155),
                                 (70.2, 157), (66.6, 138), (63.0, 120)]))
    # hip & thigh
    L.add('tensor_fasciae_latae', S([(73.4, 187), (69.4, 190), (65.4, 198), (63.6, 208), (64.4, 218),
                                     (67.0, 221.5), (70.0, 212), (73.2, 200), (75.6, 192)]))
    L.add('sartorius', strap([(74.0, 188.0), (77.4, 204), (82.0, 221), (86.6, 241), (90.2, 261),
                              (92.6, 279), (93.6, 296), (92.6, 313)], 6.2, 4.4))
    L.add('rectus_femoris', S([(77.6, 202), (74.2, 214), (73.0, 233), (74.4, 256), (77.6, 277),
                               (81.0, 292.5, 'c'), (84.2, 279), (85.8, 257), (85.2, 234), (82.0, 215)]))
    L.add('vastus_medialis', S([(84.2, 258), (89.0, 264), (92.2, 277), (93.0, 290), (90.6, 300.5),
                                (85.4, 302.5), (81.4, 298), (81.0, 285), (82.2, 270)]))
    L.add('vastus_lateralis', S([(68.0, 204), (63.4, 220), (62.6, 246), (64.8, 270), (68.6, 290),
                                 (73.6, 302), (78.8, 301), (80.0, 292), (76.6, 270), (75.2, 245),
                                 (75.6, 222), (72.0, 208)]))
    L.add('gracilis', strap([(98.0, 217), (96.0, 238), (94.0, 258), (92.6, 278), (92.0, 296), (91.4, 316)], 4.8, 3.4))
    L.add('adductor_longus', S([(99.2, 213.5), (93.5, 215), (88.0, 225), (85.4, 240), (86.4, 252),
                                (90.4, 262), (95.4, 252), (98.4, 236)]))
    # lower leg
    L.add('tibialis_anterior', S([(78.6, 315.5), (75.2, 326), (74.6, 345), (76.8, 366), (81.0, 386),
                                  (82.6, 393, 'c'), (82.8, 380), (82.0, 352), (81.4, 330), (81.2, 318)]))
    L.add('fibularis', S([(74.0, 316.5), (70.6, 330), (70.4, 350), (72.6, 370), (75.6, 391),
                          (77.6, 388), (77.2, 366), (75.8, 345), (76.4, 326), (77.2, 318)]))
    L.add('gastrocnemius', S([(88.6, 316.5), (92.0, 326), (93.8, 342), (91.6, 360), (88.8, 364),
                              (87.4, 348), (87.0, 330)]))
    L.add('soleus', unary_union([
        S([(87.6, 360), (91.2, 358), (91.0, 372), (88.6, 388), (86.8, 391), (86.8, 375)]),
        S([(71.2, 348), (73.0, 360), (75.8, 382), (74.6, 386), (71.6, 372), (70.2, 358)])]))
    return L

# ================================================================= BACK SURFACE
def back_surface():
    L = Layer('back', 'surface')
    trap = S([(99.4, 45.5, 'c'), (97.6, 47.5), (96.6, 56), (95.0, 64), (90.6, 70.5), (81, 75.8),
              (70, 80), (61.5, 83.5), (58.6, 87.6), (64, 90.6), (74.5, 93.4), (84.6, 96.6),
              (87.6, 106), (89.8, 121), (93.0, 140), (96.6, 160), (99.4, 177, 'c')])
    upper, rest = split(trap, [(102, 82.0), (88, 84.0), (74, 88.4), (58, 92.4)], side='above')
    low, mid = split_region(rest, [(103, 111.5), (93, 105.6), (86.6, 99.0), (84.6, 97.2), (83.6, 150),
                                   (83.6, 300), (103, 300)])
    L.add('trap_upper', upper); L.add('trap_middle', mid); L.add('trap_lower', low)
    L.add('splenius', S([(96.6, 47.4), (92.6, 47.6), (89.4, 52.4), (89.2, 58.6), (92.2, 61.6), (95.4, 58.4)]))
    L.add('trap_upper', strap(  # levator scapulae strip, folded into trap_upper
        [(89.8, 57.5), (89.8, 64), (88.4, 70.5), (85.4, 76.5)], 4.0, 3.2, 0.15))
    delt = S([U(-0.17, -2.5), U(-0.13, 6.5), U(-0.02, 13.8), U(0.13, 15.4), U(0.28, 13.4),
              U(0.38, 9.0), U(0.44, 6.0, 'c'), U(0.32, 0.6), U(0.18, -4.4), U(0.05, -8.6),
              U(-0.07, -9.8)])
    lat, post = split(delt, [U(-0.4, 4.6), U(-0.1, 4.4), U(0.2, 5.8), U(0.6, 5.0)], side='left')
    L.add('deltoid_posterior', post); L.add('deltoid_lateral', lat)
    L.add('infraspinatus', S([(87.6, 100.5), (79, 97.6), (69.6, 97.8), (64.8, 103), (66.0, 109.6),
                              (71.6, 116.4), (79.0, 122.0), (85.0, 124.6), (87.8, 115)]))
    L.add('triceps_lateral', S([U(0.24, 8.4), U(0.38, 11.2), U(0.58, 10.8), U(0.74, 7.8), U(0.81, 3.4),
                                U(0.71, 1.0), U(0.55, 1.6), U(0.38, 4.4)]))
    L.add('triceps_long', S([U(0.12, -2.0), U(0.25, -9.6), U(0.46, -11.4), U(0.68, -10.4), U(0.81, -6.0),
                             U(0.84, -0.6), U(0.73, 0.4), U(0.55, -0.6), U(0.36, 1.0)]))
    L.add('teres_minor', strap([(64.6, 113.6), (68.6, 118.8), (75.0, 124.0), (80.6, 127.2)], 5.8, 4.4, 0.15))
    L.add('teres_major', strap([(62.6, 121.6), (67.0, 126.2), (74.0, 131.0), (81.6, 133.2), (85.2, 132.6)], 8.8, 7.0, 0.12))
    L.add('brachioradialis', S([U(0.72, 10.8), F(-0.1, 11.6), F(0.12, 11.6), F(0.34, 9.6), F(0.3, 6.8),
                                F(0.12, 7.6), U(0.95, 7.0)]))
    L.add('wrist_flexors', S([F(0.05, -10.6), F(0.32, -9.6), F(0.62, -7.6), F(0.66, -4.4), F(0.34, -5.4),
                              F(0.1, -5.8)]))
    L.add('wrist_extensors', S([F(0.04, 8.0), F(0.18, 10.6), F(0.42, 8.8), F(0.7, 6.8), F(0.94, 4.8),
                                F(0.97, -4.6), F(0.72, -6.4), F(0.4, -7.6), F(0.14, -9.6), F(0.06, -4.0),
                                F(0.07, 3.0)]))
    L.add('erector_spinae', S([(99.0, 146, 'c'), (96.0, 147.5), (93.4, 158), (92.2, 172), (91.8, 186),
                               (92.2, 196), (94.6, 201.6), (99.0, 203, 'c')]))
    L.add('latissimus_dorsi', S([(87.6, 127.6), (81.0, 134.0), (71.0, 132.6), (62.0, 124.0), (63.6, 137),
                                 (65.6, 150), (68.6, 160), (71.6, 170), (76.4, 180.4), (83.4, 186.6),
                                 (90.4, 185), (94.8, 170), (98.6, 152), (99.0, 134)]))
    L.add('external_obliques', S([(69.0, 158), (67.6, 172), (68.6, 184), (75.6, 191.0), (82.4, 190.4),
                                  (76.0, 181.6), (72.0, 170)]))
    L.add('gluteus_maximus', S([(99.0, 224.0, 'c'), (96.6, 213.0), (93.4, 204.6), (87.6, 203.0), (80.0, 206.0),
                                (73.4, 210.4), (68.6, 216.4), (67.0, 225.0), (68.0, 234.0), (72.4, 240.4),
                                (80.0, 244.6), (89.0, 245.6), (95.4, 244.8), (99.0, 242.4, 'c')]))
    L.add('gluteus_medius', S([(73.0, 185.0), (67.0, 191.0), (64.0, 200.0), (64.2, 212.0), (67.6, 218.0),
                               (75.0, 211.0), (84.0, 205.0), (91.8, 200.6), (91.2, 191.6), (83.0, 187.0)]))
    # posterior thigh: one mass, tiled into neighbouring muscles (shared borders, constant gaps)
    L.add('gracilis', strap([(94.6, 247), (92.8, 262), (91.8, 280), (91.2, 298), (90.0, 316)], 4.6, 3.4))
    mass = S([(99.2, 244, 'c'), (60, 238, 'c'), (61.5, 272), (66, 292), (72, 305), (77.4, 313.5, 'c'),
              (80.2, 303), (83.4, 300.6), (86.8, 307), (90.8, 315.5, 'c'), (95, 300), (99.2, 280, 'c')])
    regions = {
        'vastus_lateralis': [(40, 220), (67.4, 236), (66.6, 262), (68.2, 285), (71.6, 305), (40, 330)],
        'biceps_femoris': [(67.4, 236), (81.2, 240), (80.6, 270), (80.8, 298), (79, 330), (60, 330),
                           (71.6, 305), (68.2, 285), (66.6, 262)],
        'semitendinosus': [(81.2, 240), (88.4, 240), (87.8, 262), (87.2, 282), (86.2, 305), (84, 330),
                           (79, 330), (80.8, 298), (80.6, 270)],
        'adductor_magnus': [(88.4, 240), (101, 240), (101, 255), (88.6, 267.5), (87.8, 262)],
        'semimembranosus': [(88.6, 267.5), (101, 255), (101, 330), (84, 330), (86.2, 305), (87.2, 282)],
    }
    for key in ('semitendinosus', 'biceps_femoris', 'semimembranosus', 'adductor_magnus', 'vastus_lateralis'):
        L.add(key, mass.intersection(Polygon(regions[key])).buffer(-GAP/2, join_style=1))
    L.add('gastrocnemius', unary_union([
        S([(81.4, 312.4), (76.0, 316), (72.4, 328), (73.0, 344), (76.8, 357.4), (80.6, 354.6),
           (82.2, 338), (82.6, 321)]),
        S([(85.0, 312.4), (84.0, 326), (84.6, 345), (87.4, 362.6), (90.8, 357.6), (93.0, 342),
           (92.6, 326), (89.4, 314.6)])]))
    L.add('soleus', S([(71.6, 340), (70.6, 358), (73.8, 374), (78.0, 382.6), (84.0, 384), (88.4, 380.4),
                       (91.0, 368), (92.0, 352), (89.0, 364.6), (84.0, 368.6), (79.6, 366), (75.4, 359)]))
    return L

# ================================================================= DEEP LAYERS
def front_deep():
    L = Layer('front', 'deep')
    L.add('pec_minor', S([(67.6, 94.0, 'c'), (75.6, 98.4), (83.4, 104.6), (88.0, 111.6), (87.6, 118.8),
                          (82.6, 124.4), (76.6, 118.0), (71.0, 105.6)]))
    L.add('subscapularis', S([(64.2, 99.2), (68.8, 104.0), (71.8, 113.4), (71.0, 124.2), (66.8, 127.0),
                              (63.6, 117.0), (62.6, 106.4)]))
    L.add('transversus_abdominis', S([(99.0, 168.0, 'c'), (91.0, 167.4), (83.0, 169.6), (77.0, 174.0),
                                      (75.6, 178.6), (80.0, 183.6), (88.0, 188.4), (94.0, 191.0), (99.0, 191.6, 'c')]))
    L.add('internal_obliques', S([(87.4, 127.6), (80.0, 129.4), (73.4, 133.0), (69.8, 142.0), (69.8, 156.0),
                                  (71.0, 170.0), (72.4, 182.0), (76.6, 190.0), (84.0, 196.6), (90.4, 203.6),
                                  (92.0, 196.0), (86.6, 180.0), (86.0, 160.0), (86.0, 142.0)]))
    L.add('iliopsoas', S([(95.6, 177.0), (88.6, 178.4), (80.4, 183.0), (75.8, 191.0), (79.6, 201.6),
                          (84.6, 213.0), (87.4, 225.6), (90.0, 233.4, 'c'), (93.0, 222.0), (93.8, 205.6),
                          (95.8, 190.6)]))
    L.add('vastus_intermedius', S([(78.0, 211.6), (72.6, 224.0), (70.4, 248.0), (72.6, 272.0), (78.0, 290.4),
                                   (83.6, 289.6), (86.6, 270.0), (87.0, 245.0), (85.0, 222.0), (81.6, 212.4)]))
    return L

def back_deep():
    L = Layer('back', 'deep')
    L.add('supraspinatus', S([(86.6, 89.4), (80.4, 86.4), (71.6, 85.8), (64.6, 87.2), (62.2, 90.0),
                              (69.6, 92.4), (78.6, 94.6), (86.4, 96.8)]))
    L.add('rhomboids', S([(99.0, 78.4, 'c'), (99.0, 121.0, 'c'), (93.0, 126.0), (86.8, 129.4), (85.0, 113.0),
                          (85.6, 99.0), (86.6, 89.4)]))
    L.add('quadratus_lumborum', S([(94.4, 166.4), (86.4, 167.0), (79.6, 174.0), (78.4, 185.4), (84.0, 192.4),
                                   (92.6, 192.0), (94.8, 180.0)]))
    L.add('gluteus_minimus', S([(73.6, 188.6), (68.2, 194.0), (66.6, 203.6), (72.6, 206.2), (81.0, 200.4),
                                (86.4, 194.6), (80.4, 189.6)]))
    L.add('triceps_medial', S([U(0.55, -4.6), U(0.66, -8.8), U(0.84, -8.4), U(0.96, -4.2), U(0.97, 3.2),
                               U(0.86, 7.6), U(0.7, 7.4), U(0.6, 3.6), U(0.72, -0.4)]))
    return L

# ================================================================= path output
def _fmt(v):
    s = ('%.1f' % v)
    if s.endswith('.0'): s = s[:-2]
    if s in ('-0',): s = '0'
    if s.startswith('0.'): s = s[1:]
    elif s.startswith('-0.'): s = '-' + s[2:]
    return s

def _nums(vals):
    out = ''
    for v in vals:
        f = _fmt(v)
        out += f if (not out or f[0] == '-') else ' ' + f
    return out

def _densify(pts, step):
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i+1) % n]
        k = max(1, int(math.dist(a, b) / step))
        for j in range(k):
            out.append((a[0] + (b[0]-a[0])*j/k, a[1] + (b[1]-a[1])*j/k))
    return out

def _corners(pts, win=1.5, ang=42):
    n = len(pts); cs = []
    for i in range(n):
        def walk(step):
            d = 0; j = i
            while d < win:
                k = (j + step) % n; d += math.dist(pts[j], pts[k]); j = k
                if j == i: break
            return pts[j]
        a, b = walk(-1), walk(1); p = pts[i]
        v1 = (p[0]-a[0], p[1]-a[1]); v2 = (b[0]-p[0], b[1]-p[1])
        l1 = math.hypot(*v1); l2 = math.hypot(*v2)
        if l1 == 0 or l2 == 0: cs.append(0); continue
        c = max(-1, min(1, (v1[0]*v2[0]+v1[1]*v2[1])/(l1*l2)))
        cs.append(math.degrees(math.acos(c)))
    idx = [i for i in range(n) if cs[i] > ang and cs[i] >= cs[i-1] and cs[i] >= cs[(i+1) % n]]
    keep = []
    for i in idx:
        if keep and math.dist(pts[i], pts[keep[-1]]) < 1.0:
            if cs[i] > cs[keep[-1]]: keep[-1] = i
            continue
        keep.append(i)
    if len(keep) > 1 and math.dist(pts[keep[0]], pts[keep[-1]]) < 1.0: keep.pop()
    return keep

def _resample(chain, step):
    L = [0.0]
    for i in range(1, len(chain)): L.append(L[-1] + math.dist(chain[i-1], chain[i]))
    tot = L[-1]
    k = max(1, round(tot / step)); out = [chain[0]]; j = 0
    for s in range(1, k):
        target = tot * s / k
        while L[j+1] < target: j += 1
        seg = L[j+1] - L[j] or 1
        f = (target - L[j]) / seg
        out.append((chain[j][0] + (chain[j+1][0]-chain[j][0])*f, chain[j][1] + (chain[j+1][1]-chain[j][1])*f))
    out.append(chain[-1])
    return out

def _cr_segments(P, closed):
    """Catmull-Rom through P -> list of cubic segments (p1, c1, c2, p2)."""
    segs = []; n = len(P)
    rng = range(n) if closed else range(n-1)
    for i in rng:
        if closed:
            p0, p1, p2, p3 = P[i-1], P[i], P[(i+1) % n], P[(i+2) % n]
        else:
            p0 = P[max(i-1, 0)]; p1 = P[i]; p2 = P[i+1]; p3 = P[min(i+2, n-1)]
        c1 = (p1[0]+(p2[0]-p0[0])/6, p1[1]+(p2[1]-p0[1])/6)
        c2 = (p2[0]-(p3[0]-p1[0])/6, p2[1]-(p3[1]-p1[1])/6)
        segs.append((p1, c1, c2, p2, i > 0))
    return segs

def ring_d(coords, step=3.3):
    pts = list(coords)[:-1]
    dense = _densify(pts, 0.4)
    cs = _corners(dense)
    segs = []
    if len(cs) < 1:
        loop = _resample(dense + [dense[0]], step)[:-1]
        if len(loop) < 3: loop = pts
        segs = _cr_segments(loop, True)
    else:
        n = len(dense)
        for a, b in zip(cs, cs[1:] + [cs[0] + n]):
            chain = [dense[i % n] for i in range(a, b + 1)]
            P = _resample(chain, step)
            if len(P) == 2:
                segs.append((P[0], P[0], P[1], P[1], False))
            else:
                segs.extend(_cr_segments(P, False))
    start = (round(segs[0][0][0], 1), round(segs[0][0][1], 1))
    d = 'M' + _nums(start); cur = start
    prev_smooth_ok = False
    for p1, c1, c2, p2, smooth in segs:
        e = (round(p2[0], 1), round(p2[1], 1))
        straight = (c1 == p1 and c2 == p2)
        if straight:
            if e == cur: continue
            d += 'l' + _nums((e[0]-cur[0], e[1]-cur[1]))
            prev_smooth_ok = False
        else:
            rc2 = (round(c2[0]-cur[0], 1), round(c2[1]-cur[1], 1))
            if smooth and prev_smooth_ok:      # Catmull-Rom joints are C1: reflected control point
                d += 's' + _nums((rc2[0], rc2[1], e[0]-cur[0], e[1]-cur[1]))
            else:
                d += 'c' + _nums((c1[0]-cur[0], c1[1]-cur[1], rc2[0], rc2[1], e[0]-cur[0], e[1]-cur[1]))
            prev_smooth_ok = True
        cur = e
    return d + 'z'

def geom_d(g, step=3.3):
    out = []
    for p in parts(g):
        out.append(ring_d(p.exterior.coords, step))
        for r in p.interiors:
            out.append(ring_d(r.coords, step))
    return ''.join(out)

# ================================================================= assemble
def build():
    layers = [front_surface(), back_surface(), front_deep(), back_deep()]
    paths = []
    for L in layers:
        for key, g in L.items:
            near = 'right' if L.view == 'front' else 'left'     # x < 100 side, as the subject sees it
            far = 'left' if near == 'right' else 'right'
            paths.append(dict(key=key, view=L.view, layer=L.layer, side=near, d=geom_d(g), geom=g))
            gm = mirror(g)
            paths.append(dict(key=key, view=L.view, layer=L.layer, side=far, d=geom_d(gm), geom=gm))
    outline = geom_d(SIL, 2.2)
    return paths, outline

def write_ts(paths, outline):
    keys = []
    for p in paths:
        if p['key'] not in keys: keys.append(p['key'])
    lines = [
        '// ASCEND anatomical muscle map: original artwork, generated by build_map.py.',
        '// Do not edit by hand: change the shapes in build_map.py and re-run it.',
        '// Coordinates: one shared viewBox for both views, x = 100 is the body midline.',
        '// "side" is the subject\'s own side (front view: subject\'s right is on the viewer\'s left).',
        '',
        'export interface MusclePath {',
        '  key: string;',
        '  view: "front" | "back";',
        '  layer: "surface" | "deep";',
        '  d: string;',
        '  side?: "left" | "right";',
        '}',
        '',
        'export const BODY_VIEWBOX = "0 0 %d %d";' % (W, H),
        '',
        '/** Non-muscle body silhouette (head, neck, hands, feet, joints), drawn underneath. */',
        'export const BODY_OUTLINE: { front: string; back: string } = {',
        '  front: "%s",' % outline,
        '  back: "%s",' % outline,
        '};',
        '',
        'export const MUSCLE_KEYS = [',
    ]
    for i in range(0, len(keys), 4):
        lines.append('  ' + ' '.join('"%s",' % k for k in keys[i:i+4]))
    lines += ['] as const;', '', 'export const MUSCLE_PATHS: MusclePath[] = [']
    for p in paths:
        lines.append('  { key: "%s", view: "%s", layer: "%s", side: "%s", d: "%s" },'
                     % (p['key'], p['view'], p['layer'], p['side'], p['d']))
    lines += ['];', '']
    path = os.path.join(OUT, 'bodyMapPaths.ts')
    open(path, 'w').write('\n'.join(lines))
    return path, keys

# ================================================================= previews
THEMES = {
    'dark':  dict(bg='#0b1220', body='#18233a', stroke='#33445f', neutral='#2c3b55', deep='#4a6290',
                  fresh='#22a57a', recovering='#e0a63a', fatigued='#e5545d', text='#e6edf7'),
    'light': dict(bg='#f4f6fa', body='#e3e8f0', stroke='#b9c2d0', neutral='#bcc6d4', deep='#8c9bb3',
                  fresh='#27b07f', recovering='#e8a62a', fatigued='#e24b52', text='#1b2433'),
}
DEMO = {  # a sample "day after push day" recovery state, for the previews only
    'fatigued': {'pec_major_clavicular', 'pec_major_sternal', 'deltoid_anterior', 'triceps_lateral',
                 'triceps_long', 'triceps_medial', 'pec_minor'},
    'recovering': {'rectus_femoris', 'vastus_lateralis', 'vastus_medialis', 'vastus_intermedius',
                   'deltoid_lateral', 'serratus_anterior', 'gluteus_maximus', 'adductor_longus'},
    'fresh': {'latissimus_dorsi', 'biceps_long', 'biceps_short', 'brachialis', 'trap_middle',
              'trap_lower', 'rhomboids', 'biceps_femoris', 'semitendinosus', 'semimembranosus',
              'rectus_abdominis', 'external_obliques', 'gastrocnemius', 'soleus'},
}
def demo_state(key):
    for s, ks in DEMO.items():
        if key in ks: return s
    return 'neutral'

PAD = '-8 -5 216 440'

def figure_svg(paths, outline, view, layer, theme, px_w, fill_of=None, stroke_px=None, extra=''):
    T = THEMES[theme]
    vb = [float(v) for v in PAD.split()]
    scale = px_w / vb[2]; px_h = round(vb[3] * scale)
    sw = (stroke_px / scale) if stroke_px else 0.55
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" width="%d" height="%d">' % (PAD, px_w, px_h),
         '<rect x="-50" y="-50" width="400" height="600" fill="%s"/>' % T['bg'],
         '<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
         % (outline, T['body'], T['stroke'], sw)]
    fill_of = fill_of or (lambda k: T[demo_state(k)])
    if layer == 'surface':
        for p in paths:
            if p['view'] == view and p['layer'] == 'surface':
                s.append('<path d="%s" fill="%s"/>' % (p['d'], fill_of(p['key'])))
    else:
        for p in paths:
            if p['view'] == view and p['layer'] == 'surface':
                s.append('<path d="%s" fill="%s" opacity="0.32"/>' % (p['d'], T['neutral']))
        for p in paths:
            if p['view'] == view and p['layer'] == 'deep':
                f = fill_of(p['key'])
                s.append('<path d="%s" fill="%s"/>' % (p['d'], T['deep'] if f == T['neutral'] else f))
    s.append(extra)
    s.append('</svg>')
    return '\n'.join(s)

def render(svg, path):
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=path)

def side_by_side(files, out, bg=(11, 18, 32)):
    from PIL import Image
    ims = [Image.open(f).convert('RGB') for f in files]
    w = sum(i.width for i in ims); h = max(i.height for i in ims)
    c = Image.new('RGB', (w, h), bg); x = 0
    for i in ims:
        c.paste(i, (x, 0)); x += i.width
    c.save(out, optimize=True)
    for f in files: os.remove(f)

def previews(paths, outline):
    for view, layer, name in (('front', 'surface', 'front'), ('back', 'surface', 'back'),
                              ('front', 'deep', 'deep_front'), ('back', 'deep', 'deep_back')):
        tmp = []
        for theme in ('dark', 'light'):
            f = os.path.join(OUT, '_%s_%s.png' % (name, theme))
            render(figure_svg(paths, outline, view, layer, theme, 600), f); tmp.append(f)
        side_by_side(tmp, os.path.join(OUT, name + '.png'))

def _hues(n):
    import colorsys
    out = []
    for i in range(n):
        h = (i * 0.618034) % 1.0
        r, g, b = colorsys.hls_to_rgb(h, 0.55 if i % 2 else 0.45, 0.75)
        out.append('#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255)))
    return out

def check_image(paths, outline):
    from PIL import Image
    panels = []
    for view, layer in (('front', 'surface'), ('back', 'surface'), ('front', 'deep'), ('back', 'deep')):
        ps = [p for p in paths if p['view'] == view and p['layer'] == layer]
        keys = []
        for p in ps:
            if p['key'] not in keys: keys.append(p['key'])
        col = dict(zip(keys, _hues(len(keys))))
        # one anchor per key: alternate columns by height order
        anchors = []
        for k in keys:
            gl = [p['geom'] for p in ps if p['key'] == k]
            left = min(gl, key=lambda g: g.centroid.x); right = max(gl, key=lambda g: g.centroid.x)
            anchors.append((k, left, right, left.centroid.y))
        anchors.sort(key=lambda a: a[3])
        cols = {'L': [], 'R': []}
        for i, a in enumerate(anchors):
            cols['L' if i % 2 == 0 else 'R'].append(a)
        txt = []
        for side, items in cols.items():
            ys = []; sp = 6.2
            for a in items:
                y = max(a[3], (ys[-1] + sp) if ys else -1e9); ys.append(y)
            over = (ys[-1] - 425) if ys else 0
            if over > 0:
                ys = [y - over for y in ys]
                for i in range(1, len(ys)):
                    ys[i] = max(ys[i], ys[i-1] + sp)
            for a, y in zip(items, ys):
                g = a[1] if side == 'L' else a[2]
                rp = g.representative_point()
                lx = -4 if side == 'L' else 204
                anchor = 'end' if side == 'L' else 'start'
                txt.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width=".35"/>'
                           % (lx + (1 if side == 'L' else -1), y - 1.2, rp.x, rp.y, col[a[0]]))
                txt.append('<circle cx="%.1f" cy="%.1f" r=".9" fill="#fff" stroke="#000" stroke-width=".25"/>' % (rp.x, rp.y))
                txt.append('<text x="%.1f" y="%.1f" font-family="DejaVu Sans" font-size="4.1" fill="%s" text-anchor="%s">%s</text>'
                           % (lx, y, col[a[0]], anchor, a[0]))
        T = THEMES['dark']
        s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-100 -14 400 448" width="1200" height="1344">',
             '<rect x="-200" y="-200" width="800" height="900" fill="%s"/>' % T['bg'],
             '<text x="100" y="-6" font-family="DejaVu Sans" font-size="6" fill="#fff" text-anchor="middle">%s / %s (%d keys)</text>'
             % (view.upper(), layer.upper(), len(keys)),
             '<path d="%s" fill="%s" stroke="%s" stroke-width=".5"/>' % (outline, T['body'], T['stroke'])]
        if layer == 'deep':
            for p in paths:
                if p['view'] == view and p['layer'] == 'surface':
                    s.append('<path d="%s" fill="#2c3b55" opacity=".35"/>' % p['d'])
        for p in ps:
            s.append('<path d="%s" fill="%s"/>' % (p['d'], col[p['key']]))
        s += txt + ['</svg>']
        f = os.path.join(OUT, '_check_%s_%s.png' % (view, layer))
        render('\n'.join(s), f); panels.append(f)
    ims = [Image.open(f).convert('RGB') for f in panels]
    w, h = ims[0].size
    c = Image.new('RGB', (w*2, h*2))
    for i, im in enumerate(ims):
        c.paste(im, ((i % 2)*w, (i//2)*h))
    c.save(os.path.join(OUT, 'check_labels.png'), optimize=True)
    for f in panels: os.remove(f)

def tile_check(paths, outline):
    """64x96 fallback-tile legibility: few muscles highlighted, 1 px outline."""
    from PIL import Image
    sets = [('chest', {'pec_major_clavicular', 'pec_major_sternal'}),
            ('quads', {'rectus_femoris', 'vastus_lateralis', 'vastus_medialis'}),
            ('biceps', {'biceps_long', 'biceps_short', 'brachialis'}),
            ('abs', {'rectus_abdominis', 'external_obliques'})]
    tiles = []
    for theme in ('dark', 'light'):
        T = THEMES[theme]
        for name, ks in sets:
            def fill(k, ks=ks, T=T):
                return T['fatigued'] if k in ks else T['neutral']
            svg = figure_svg(paths, outline, 'front', 'surface', theme, 44, fill_of=fill, stroke_px=1.0)
            svg = svg.replace('width="44" height="90"', 'width="64" height="96"')
            svg = svg.replace('viewBox="%s"' % PAD, 'viewBox="-58 -8 316 440"', 1)
            f = os.path.join(OUT, '_tile_%s_%s.png' % (theme, name))
            render(svg, f); tiles.append(f)
    ims = [Image.open(f).convert('RGB') for f in tiles]
    big = Image.new('RGB', (len(sets) * (64*4 + 16) + 16, 2 * (96*4 + 16) + 16), (90, 90, 90))
    small = Image.new('RGB', (len(sets) * 72 + 8, 2 * 104 + 8), (90, 90, 90))
    for i, im in enumerate(ims):
        r, cidx = divmod(i, len(sets))
        big.paste(im.resize((256, 384), Image.NEAREST), (16 + cidx * 272, 16 + r * 400))
        small.paste(im, (8 + cidx * 72, 8 + r * 104))
    big.save(os.path.join(OUT, 'tile_check_x4.png'), optimize=True)
    small.save(os.path.join(OUT, 'tile_check_1x.png'), optimize=True)
    for f in tiles: os.remove(f)

if __name__ == '__main__':
    paths, outline = build()
    ts, keys = write_ts(paths, outline)
    print('keys:', len(keys), ' paths:', len(paths), ' ts bytes:', os.path.getsize(ts))
    if '--no-png' not in sys.argv:
        previews(paths, outline); check_image(paths, outline); tile_check(paths, outline)

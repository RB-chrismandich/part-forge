#!/usr/bin/env python3
"""Reusable machinery for parametric printable-part generators.

Distilled from a working shade-bar saddle generator, with two of that script's
own rough edges fixed rather than inherited.

**Fix 1 - the bpy import is guarded.** The original put `import bpy` at module
scope, which made several hundred lines of pure-Python polygon math unimportable,
and therefore untestable, outside a running Blender process. Everything above the
GEOMETRY KERNEL banner here runs in a plain interpreter, so the geometry can be
unit-tested and independently re-derived.

**Fix 2 - measurement is a layer, not a copy-paste.** The original grew about a
dozen slight variations of "cast a fan of rays, fit a circle, compare" - one per
feature, no shared code, no BVH reuse. `Probe` and `Acceptance` below are that
missing layer.

`Acceptance` also makes "reported, not gated" a first-class call rather than a
convention. A measured-but-unenforced quantity that is not labelled reads as
checked, and a passing count then reads as coverage. `note()` keeps those
quantities out of the pass tally by construction.

Layout
------
    CONSTANTS               unit conversions, default tolerances
    GEOMETRY KERNEL         pure Python, no bpy, unit-testable
    MEASUREMENT             Probe (BVH ray casting), circle fitting
    ACCEPTANCE              Check, Acceptance - the gate and its report
    BLENDER SOLIDS          scene setup, prism/loft/hull, boolean, cleanup
    POSITIONAL TOPOLOGY     weld by position, the invariant a slicer sees
    EXPORT                  print orientation, bed placement, gated write

Import from a generator that lives anywhere:

    import sys, os
    sys.path.insert(0, os.environ.get("PART_FORGE_SCRIPTS", "."))
    from part_kit import Acceptance, Probe, boolean, loft_solid, prism
"""

from __future__ import annotations

import math
import os

try:
    import bpy
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    HAVE_BPY = True
except ImportError:  # importable outside Blender so the kernel can be tested
    bpy = bmesh = Vector = BVHTree = None
    HAVE_BPY = False


# ===========================================================================
#  CONSTANTS
# ===========================================================================

MM_PER_IN = 25.4
MM2_PER_IN2 = MM_PER_IN ** 2
LBF_TO_N = 4.4482216152605

#: Dimension-bearing geometry built from primitives. Any deviation is a bug.
TOL_TIGHT = 2.0e-3      # mm
#: Form features that emerge from booleans and lofts, where tessellation
#: legitimately moves the surface by more than TOL_TIGHT.
TOL_LOOSE = 5.0e-2      # mm
#: Positional weld for exported float32 geometry. Well above the format's ulp
#: (a few times 1e-6 mm near 50 mm) and below any real feature.
WELD_POSITIONAL = 1.0e-4  # mm
#: Below this, a connected component is debris rather than geometry.
NULL_VOLUME = 1.0e-6    # mm^3


# ===========================================================================
#  GEOMETRY KERNEL  -  pure Python, no bpy, unit-testable
# ===========================================================================
#
# Profiles are lists of (u, v) tuples in a 2D working plane, wound
# counter-clockwise. The caller maps them into 3D, which keeps this layer free
# of any opinion about which axis is which.

def circumscribed_circle(cu, cv, r, n):
    """An n-gon that *contains* the circle of radius r, rather than inscribing it.

    A polygon through the circle's points cuts inside it, so a bore built that
    way is undersized by the sagitta and a shaft will not fit. Scaling the radius
    by 1/cos(pi/n) puts the polygon's edge midpoints on the true circle, so the
    error falls entirely outside the intended surface.
    """
    if n < 3:
        raise ValueError(f"circumscribed_circle needs n >= 3, got {n}")
    rr = r / math.cos(math.pi / n)
    return [
        (cu + rr * math.cos(2.0 * math.pi * i / n + math.pi / n),
         cv + rr * math.sin(2.0 * math.pi * i / n + math.pi / n))
        for i in range(n)
    ]


def rounded_rect(w, h, r, seg, origin="corner"):
    """Rectangle w x h with corner radius r. `origin` is "corner" or "centre"."""
    r = min(r, w / 2.0, h / 2.0)
    if origin == "centre":
        u0, v0 = -w / 2.0, -h / 2.0
    elif origin == "corner":
        u0, v0 = 0.0, 0.0
    else:
        raise ValueError(f"origin must be 'corner' or 'centre', got {origin!r}")

    if r <= 0.0:
        return [(u0, v0), (u0 + w, v0), (u0 + w, v0 + h), (u0, v0 + h)]

    pts = []
    centres = ((u0 + w - r, v0 + r), (u0 + w - r, v0 + h - r),
               (u0 + r, v0 + h - r), (u0 + r, v0 + r))
    for i, (cu, cv) in enumerate(centres):
        a0 = -math.pi / 2.0 + i * math.pi / 2.0
        for j in range(seg + 1):
            a = a0 + (math.pi / 2.0) * j / seg
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def clip_halfplane(poly, a, b, c):
    """Sutherland-Hodgman clip of `poly` to the half-plane a*u + b*v <= c."""
    if not poly:
        return []
    out = []
    n = len(poly)
    for i in range(n):
        cur, nxt = poly[i], poly[(i + 1) % n]
        dc = a * cur[0] + b * cur[1] - c
        dn = a * nxt[0] + b * nxt[1] - c
        if dc <= 0.0:
            out.append(cur)
        if (dc < 0.0) != (dn < 0.0) and dc != dn:
            t = dc / (dc - dn)
            out.append((cur[0] + t * (nxt[0] - cur[0]),
                        cur[1] + t * (nxt[1] - cur[1])))
    return out


def clip_below(poly, v_max):
    """Keep only the part of `poly` at or below v = v_max."""
    return clip_halfplane(poly, 0.0, 1.0, v_max)


def erode_convex(poly, d):
    """Inset a convex polygon by distance d on every edge.

    This is the flare idiom: eroding by `d` per unit of travel along the sweep
    axis produces exactly a 45-degree taper when d equals the travel step, which
    is also the steepest overhang an FDM printer manages unsupported. One
    operation satisfies both the shape and the printability constraint.

    Returns [] when the erosion consumes the profile - check for that rather
    than lofting an empty ring.
    """
    if d <= 0.0:
        return list(poly)
    out = list(poly)
    n = len(poly)
    for i in range(n):
        au, av = poly[i]
        bu, bv = poly[(i + 1) % n]
        eu, ev = bu - au, bv - av
        ln = math.hypot(eu, ev)
        if ln < 1e-12:
            continue
        # inward normal for counter-clockwise winding
        nu, nv = ev / ln, -eu / ln
        out = clip_halfplane(out, nu, nv, nu * au + nv * av - d)
        if not out:
            return []
    return out


def hull2d(pts):
    """Andrew's monotone-chain convex hull, counter-clockwise."""
    p = sorted(set((round(u, 9), round(v, 9)) for u, v in pts))
    if len(p) < 3:
        return p

    def build(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and _cross(out[-2], out[-1], q) <= 0.0:
                out.pop()
            out.append(q)
        return out

    lower = build(p)
    upper = build(reversed(p))
    return lower[:-1] + upper[:-1]


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def point_in_poly(pt, poly):
    """Crossing-number test. Boundary cases are not resolved; keep samples off edges."""
    u, v = pt
    inside = False
    n = len(poly)
    for i in range(n):
        au, av = poly[i]
        bu, bv = poly[(i + 1) % n]
        if (av > v) != (bv > v):
            t = (v - av) / (bv - av)
            if u < au + t * (bu - au):
                inside = not inside
    return inside


def span_at_v(poly, v):
    """Horizontal extent of `poly` at height v, as (u_min, u_max) or None."""
    us = []
    n = len(poly)
    for i in range(n):
        au, av = poly[i]
        bu, bv = poly[(i + 1) % n]
        if (av > v) != (bv > v):
            t = (v - av) / (bv - av)
            us.append(au + t * (bu - au))
    return (min(us), max(us)) if us else None


def dist_to_poly(pt, poly):
    """Shortest distance from a point to a polygon's boundary."""
    u, v = pt
    best = math.inf
    n = len(poly)
    for i in range(n):
        au, av = poly[i]
        bu, bv = poly[(i + 1) % n]
        eu, ev = bu - au, bv - av
        ln2 = eu * eu + ev * ev
        t = 0.0 if ln2 < 1e-18 else max(0.0, min(1.0, ((u - au) * eu + (v - av) * ev) / ln2))
        best = min(best, math.hypot(u - (au + t * eu), v - (av + t * ev)))
    return best


def polygon_area(poly):
    """Signed shoelace area; positive for counter-clockwise winding."""
    n = len(poly)
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
                     for i in range(n))


def tangent_fillet(p, u1, u2, r, seg=16):
    """Arc of radius r tangent to both rays leaving p along unit directions u1, u2.

    Solved analytically because a bevel that assumes a right angle leaves a ledge
    wherever the junction is not 90 degrees - and real junctions are not. Neither
    direction is assumed square to anything.

        centre = p + (r / sin(theta/2)) * bisector
        tangent points = p + (r / tan(theta/2)) * u

    Returns the arc points from the u1 tangent point to the u2 tangent point.
    Raises when the included angle is degenerate, since no finite arc exists.
    """
    u1 = _unit2(u1)
    u2 = _unit2(u2)
    cos_t = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
    theta = math.acos(cos_t)
    if theta < 1e-6 or abs(math.pi - theta) < 1e-6:
        raise ValueError(f"tangent_fillet: included angle {math.degrees(theta):.4f} deg is degenerate")

    half = theta / 2.0
    bis = _unit2((u1[0] + u2[0], u1[1] + u2[1]))
    centre = (p[0] + (r / math.sin(half)) * bis[0],
              p[1] + (r / math.sin(half)) * bis[1])
    setback = r / math.tan(half)
    t1 = (p[0] + setback * u1[0], p[1] + setback * u1[1])
    t2 = (p[0] + setback * u2[0], p[1] + setback * u2[1])

    a1 = math.atan2(t1[1] - centre[1], t1[0] - centre[0])
    a2 = math.atan2(t2[1] - centre[1], t2[0] - centre[0])
    # take the short way round; the fillet arc is always the minor arc
    da = (a2 - a1 + math.pi) % (2.0 * math.pi) - math.pi
    return [(centre[0] + r * math.cos(a1 + da * i / seg),
             centre[1] + r * math.sin(a1 + da * i / seg)) for i in range(seg + 1)]


def _unit2(v):
    ln = math.hypot(v[0], v[1])
    if ln < 1e-12:
        raise ValueError("_unit2: zero-length vector")
    return (v[0] / ln, v[1] / ln)


def fit_circle(pts):
    """Algebraic least-squares circle fit. Returns (cu, cv, r, residual_max).

    `residual_max` is the largest deviation of any sample from the fitted radius,
    which is the number worth gating on - a good centre with a poor residual means
    the surface is not the arc it was supposed to be.
    """
    n = len(pts)
    if n < 3:
        raise ValueError(f"fit_circle needs 3 points, got {n}")

    # Solve [2u 2v 1][a b c]' = u^2 + v^2  in the least-squares sense.
    sxx = sxy = syy = sx = sy = 0.0
    sxz = syz = sz = 0.0
    for u, v in pts:
        z = u * u + v * v
        sxx += u * u
        sxy += u * v
        syy += v * v
        sx += u
        sy += v
        sxz += u * z
        syz += v * z
        sz += z
    a = [[2.0 * sxx, 2.0 * sxy, sx],
         [2.0 * sxy, 2.0 * syy, sy],
         [2.0 * sx, 2.0 * sy, float(n)]]
    sol = _solve3(a, [sxz, syz, sz])
    cu, cv, c = sol
    r2 = c + cu * cu + cv * cv
    if r2 <= 0.0:
        raise ValueError("fit_circle: degenerate fit, samples are collinear")
    r = math.sqrt(r2)
    resid = max(abs(math.hypot(u - cu, v - cv) - r) for u, v in pts)
    return cu, cv, r, resid


def _solve3(a, b):
    """Gaussian elimination with partial pivoting on a 3x3 system."""
    m = [list(a[i]) + [b[i]] for i in range(3)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-14:
            raise ValueError("_solve3: singular system")
        m[col], m[piv] = m[piv], m[col]
        for row in range(3):
            if row == col:
                continue
            f = m[row][col] / m[col][col]
            for k in range(col, 4):
                m[row][k] -= f * m[col][k]
    return [m[i][3] / m[i][i] for i in range(3)]


# ===========================================================================
#  MEASUREMENT
# ===========================================================================

class Probe:
    """Ray-cast measurement against a finished mesh, with the BVH built once.

    Exists because a generator that grows one bespoke ray fan per feature ends up
    with a dozen near-identical loops, no shared bug fix, and a rebuilt
    acceleration structure per call.

    The discipline this class serves: **measure the mesh, never restate the
    parameter.** A check comparing a nominal wrap angle to itself proves the
    assignment operator works. Cast at the surface and gate what comes back.
    """

    def __init__(self, obj, depsgraph=None):
        if not HAVE_BPY:
            raise RuntimeError("Probe needs Blender; run this inside bpy")
        self.obj = obj
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        self._bm = bm
        self.tree = BVHTree.FromBMesh(bm)

    def free(self):
        self._bm.free()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.free()
        return False

    def cast(self, origin, direction, max_dist=1.0e4):
        """One ray. Returns (location, normal, face_index, distance) or None."""
        d = Vector(direction)
        if d.length < 1e-12:
            raise ValueError("Probe.cast: zero-length direction")
        loc, nor, idx, dist = self.tree.ray_cast(Vector(origin), d.normalized(), max_dist)
        return None if loc is None else (loc, nor, idx, dist)

    def fan(self, centre, axis_u, axis_v, radius, angles_deg, inward=True):
        """Cast a fan of rays in the plane spanned by axis_u, axis_v.

        Rays start on a circle of `radius` about `centre` and aim inward by
        default, so a hit distance measures material rather than air. Returns a
        list of (angle_deg, hit_or_None).
        """
        cu, cv = Vector(axis_u).normalized(), Vector(axis_v).normalized()
        c = Vector(centre)
        out = []
        for a in angles_deg:
            r = math.radians(a)
            offset = cu * (radius * math.cos(r)) + cv * (radius * math.sin(r))
            origin = c + offset
            direction = -offset if inward else offset
            out.append((a, self.cast(origin, direction)))
        return out

    def surface_arc(self, centre, axis_u, axis_v, radius, a0, a1, step_deg=0.25):
        """Sample the surface radius over an angular sweep.

        Returns [(angle_deg, radius_at_surface)] for angles that hit. Useful for
        measuring a delivered wrap angle, an arc's true extent, or a chamfer's
        end - all quantities a parameter names but does not describe.
        """
        n = max(1, int(round(abs(a1 - a0) / step_deg)))
        angles = [a0 + (a1 - a0) * i / n for i in range(n + 1)]
        out = []
        for a, hit in self.fan(centre, axis_u, axis_v, radius, angles):
            if hit is not None:
                out.append((a, radius - hit[3]))
        return out

    def thickness_at(self, point, direction, max_dist=1.0e4, eps=1.0e-4):
        """Material thickness from a surface point along `direction`.

        Starts just inside the surface so the first hit is the opposing wall.
        Reads a chord rather than a throat inside a fillet, so it is a screen for
        gross thin walls and not a certificate. Callipers on the printed part
        remain the authority.
        """
        d = Vector(direction).normalized()
        hit = self.cast(Vector(point) + d * eps, d, max_dist)
        return None if hit is None else hit[3] + eps

    def min_wall(self, stations, axis_u, axis_v, r_inner, angles_deg,
                 max_wall=1.0e3, eps=1.0e-4):
        """Worst wall thickness around a bore or trough, over several stations.

        Rays start just *outside* the inner surface at `r_inner` and travel
        outward, so the first hit is the outer surface and the distance is
        material. Casting inward instead would return where the inner surface
        sits, which is a radius and not a thickness - a distinction worth keeping
        sharp, because a function that returns the wrong quantity under the right
        name is exactly the kind of gate this plugin exists to catch. Use
        `surface_arc` when the radial position is what is wanted.

        `stations` is an iterable of centres, and there is deliberately no
        single-station overload. Sampling one station is how a sweep measures a
        ridge for a project's entire history and never the thinner groove floor
        beside it.

        Returns (thickness, station, angle_deg) for the worst sample, or None.
        """
        worst = None
        cu, cv = Vector(axis_u).normalized(), Vector(axis_v).normalized()
        for centre in stations:
            c = Vector(centre)
            for a in angles_deg:
                rad = math.radians(a)
                d = cu * math.cos(rad) + cv * math.sin(rad)
                hit = self.cast(c + d * (r_inner + eps), d, max_wall)
                if hit is None:
                    continue
                t = hit[3] + eps
                if worst is None or t < worst[0]:
                    worst = (t, tuple(centre), a)
        return worst


# ===========================================================================
#  ACCEPTANCE
# ===========================================================================

class Check:
    """One acceptance line: what was measured, what was expected, and the verdict."""

    __slots__ = ("name", "got", "want", "tol", "ok", "kind", "why")

    def __init__(self, name, got, want, tol, ok, kind, why=""):
        self.name, self.got, self.want = name, got, want
        self.tol, self.ok, self.kind, self.why = tol, ok, kind, why

    def as_dict(self):
        return {"name": self.name, "got": self.got, "want": self.want,
                "tol": self.tol, "ok": self.ok, "kind": self.kind, "why": self.why}


class Acceptance:
    """Collects checks and notes, and decides whether the part may be exported.

    Two tolerance regimes, because one blanket epsilon either passes real defects
    or fails on tessellation noise:

        tight()  dimension-bearing geometry from primitives   ~2e-3 mm
        loose()  form features from booleans and lofts        ~5e-2 mm

    And a third call that is not a check at all:

        note()   measured, printed, deliberately not enforced

    `note()` exists so "reported, not gated" cannot be mistaken for coverage. An
    unenforced quantity that is not labelled reads as checked, and then a passing
    count reads as a guarantee. Notes never enter the tally.
    """

    def __init__(self, tag, tol_tight=TOL_TIGHT, tol_loose=TOL_LOOSE):
        self.tag = tag
        self.tol_tight = tol_tight
        self.tol_loose = tol_loose
        self.checks = []
        self.notes = []

    # -- gated -------------------------------------------------------------

    def tight(self, name, got, want, why=""):
        return self._num(name, got, want, self.tol_tight, "tight", why)

    def loose(self, name, got, want, why=""):
        return self._num(name, got, want, self.tol_loose, "loose", why)

    def within(self, name, got, want, tol, why=""):
        """Explicit tolerance, for a check that belongs to neither regime."""
        return self._num(name, got, want, tol, "explicit", why)

    def exact(self, name, got, want, why=""):
        ok = got == want
        self.checks.append(Check(name, got, want, 0.0, ok, "exact", why))
        return ok

    def at_least(self, name, got, floor, why=""):
        ok = got is not None and got >= floor
        self.checks.append(Check(name, got, f">= {floor}", None, ok, "floor", why))
        return ok

    def at_most(self, name, got, cap, why=""):
        ok = got is not None and got <= cap
        self.checks.append(Check(name, got, f"<= {cap}", None, ok, "cap", why))
        return ok

    def _num(self, name, got, want, tol, kind, why):
        ok = got is not None and abs(got - want) <= tol
        self.checks.append(Check(name, got, want, tol, ok, kind, why))
        return ok

    # -- not gated ---------------------------------------------------------

    def note(self, name, value, why=""):
        """Reported, not gated. Kept out of the pass tally on purpose."""
        self.notes.append(Check(name, value, None, None, None, "note", why))

    def coverage(self, name, tested, skipped, why=""):
        """Record how many samples a check actually looked at.

        A scan whose every station takes an early-out branch passes having tested
        nothing. Reporting tested-versus-skipped is what stops a check quietly
        going vacuous.
        """
        self.notes.append(Check(name, {"tested": tested, "skipped": skipped},
                                None, None, None, "coverage", why))
        if tested == 0:
            self.notes.append(Check(name + " [VACUOUS]", 0, None, None, None, "coverage",
                                    "tested nothing; this check is currently not measuring anything"))

    # -- verdict -----------------------------------------------------------

    @property
    def ok(self):
        return all(c.ok for c in self.checks)

    @property
    def failures(self):
        return [c for c in self.checks if not c.ok]

    def near_limit(self, frac=0.1):
        """Checks that passed within `frac` of their bound - the next regression."""
        out = []
        for c in self.checks:
            if not c.ok:
                continue
            if c.kind == "floor" and isinstance(c.got, (int, float)):
                floor = float(str(c.want).lstrip(">= "))
                if floor and c.got <= floor * (1.0 + frac):
                    out.append(c)
            elif c.kind == "cap" and isinstance(c.got, (int, float)):
                cap = float(str(c.want).lstrip("<= "))
                if cap and c.got >= cap * (1.0 - frac):
                    out.append(c)
        return out

    def render(self):
        L = [f"  {self.tag}: {len(self.checks) - len(self.failures)}/{len(self.checks)} checks"]
        for c in self.checks:
            mark = "PASS" if c.ok else "FAIL"
            got = f"{c.got:.4f}" if isinstance(c.got, float) else c.got
            want = f"{c.want:.4f}" if isinstance(c.want, float) else c.want
            tol = f" +/- {c.tol:g}" if c.tol else ""
            L.append(f"    [{mark}] {c.name:<34} {got}   want {want}{tol}")
            if not c.ok and c.why:
                L.append(f"           {c.why}")
        if self.notes:
            L.append("  reported, not gated (these are NOT part of the count above):")
            for c in self.notes:
                got = f"{c.got:.4f}" if isinstance(c.got, float) else c.got
                L.append(f"    [note] {c.name:<34} {got}")
                if c.why:
                    L.append(f"           {c.why}")
        for c in self.near_limit():
            L.append(f"    [near] {c.name} passed at {c.got} against {c.want}")
        return "\n".join(L)

    def as_dict(self):
        return {
            "tag": self.tag,
            "ok": self.ok,
            "checks": [c.as_dict() for c in self.checks],
            "notes": [c.as_dict() for c in self.notes],
            "failures": [c.name for c in self.failures],
            "near_limit": [c.name for c in self.near_limit()],
        }


# ===========================================================================
#  BLENDER SOLIDS
# ===========================================================================

def _need_bpy(what):
    if not HAVE_BPY:
        raise RuntimeError(f"{what} needs Blender; run this inside bpy")


def scene_setup(unit_scale=0.001):
    """Metric, one Blender unit == one millimetre.

    Pair with `use_scene_unit=False, global_scale=1.0` at export, or the scale is
    applied twice and the part ships a thousand times too small.
    """
    _need_bpy("scene_setup")
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    scn.unit_settings.scale_length = unit_scale
    scn.unit_settings.length_unit = "MILLIMETERS"


def purge(*names):
    """Remove objects by name, and any mesh they orphan.

    Only mesh data is collected. The startup scene's Light and Camera carry
    PointLight and Camera data blocks, and handing either to `meshes.remove`
    raises - so clearing the default scene has to check the type rather than
    assume every object owns a mesh.
    """
    _need_bpy("purge")
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)


def prism(name, pts2d, to3d, extrude):
    """Extrude a 2D profile into a closed solid.

    `to3d` maps (u, v) to a 3D coordinate; `extrude` is the vector swept along.
    """
    _need_bpy("prism")
    bm = bmesh.new()
    verts = [bm.verts.new(to3d(u, v)) for u, v in pts2d]
    face = bm.faces.new(verts)
    ret = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=moved, vec=Vector(extrude))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _object_from_bmesh(name, bm)


def loft_solid(name, rings, to3d, cap=True):
    """Stitch a sequence of equal-length rings into a solid.

    Hand-written rather than delegated because a convex-hull sweep cannot express
    a non-convex profile, and every ring must carry the same vertex count so the
    quads close. Raises on a length mismatch rather than producing a torn surface.
    """
    _need_bpy("loft_solid")
    if len(rings) < 2:
        raise ValueError(f"loft_solid needs 2 or more rings, got {len(rings)}")
    n = len(rings[0])
    for i, r in enumerate(rings):
        if len(r) != n:
            raise ValueError(f"loft_solid: ring {i} has {len(r)} points, ring 0 has {n}")

    bm = bmesh.new()
    grid = [[bm.verts.new(to3d(i, u, v)) for u, v in ring] for i, ring in enumerate(rings)]
    for i in range(len(grid) - 1):
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((grid[i][j], grid[i][k], grid[i + 1][k], grid[i + 1][j]))
    if cap:
        bm.faces.new(list(reversed(grid[0])))
        bm.faces.new(grid[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _object_from_bmesh(name, bm)


def hull_solid(name, rings):
    """Convex hull of a point cloud. Only valid when the result *is* convex."""
    _need_bpy("hull_solid")
    bm = bmesh.new()
    for ring in rings:
        for co in ring:
            bm.verts.new(co)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _object_from_bmesh(name, bm)


def _object_from_bmesh(name, bm):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def boolean(target, cutter, operation, solver="MANIFOLD", keep_cutter=False):
    """Apply a boolean, retry with the exact solver, and raise if nothing happened.

    A boolean that silently does nothing is the worst outcome available: the part
    still looks plausible and is wrong. The volume comparison is the only reliable
    way to notice, because the modifier reports success either way.
    """
    _need_bpy("boolean")
    before = mesh_volume(target)
    for attempt in (solver, "EXACT"):
        _apply_boolean(target, cutter, operation, attempt)
        after = mesh_volume(target)
        if abs(after - before) > NULL_VOLUME:
            if not keep_cutter:
                purge(cutter.name)
            return target
    raise RuntimeError(
        f"boolean {operation} of {cutter.name} into {target.name} changed nothing "
        f"(volume {before:.6f} -> {after:.6f}) after both solvers; the cutter "
        f"probably does not overlap the target"
    )


def _apply_boolean(target, cutter, operation, solver):
    mod = target.modifiers.new(name="_bool", type="BOOLEAN")
    mod.operation = operation
    mod.object = cutter
    try:
        mod.solver = solver
    except TypeError:  # older builds lack this solver enum value
        mod.solver = "EXACT"
    _apply_modifiers(target)


def _apply_modifiers(obj):
    """Bake modifiers via the depsgraph, avoiding operator context entirely."""
    dg = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(dg)
    mesh = bpy.data.meshes.new_from_object(evaluated)
    obj.modifiers.clear()
    old = obj.data
    obj.data = mesh
    if old.users == 0:
        bpy.data.meshes.remove(old)


def clean_mesh(obj, merge_dist=5.0e-3):
    """Weld coincident vertices and drop degenerate geometry.

    Run between boolean stages. Coincident-but-distinct vertices accumulate across
    operations and the next boolean chokes on them.
    """
    _need_bpy("clean_mesh")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_dist)
    bmesh.ops.dissolve_degenerate(bm, dist=merge_dist, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def mesh_volume(obj):
    """Signed volume by the divergence theorem, on triangulated geometry."""
    _need_bpy("mesh_volume")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    total = 0.0
    for f in bm.faces:
        a, b, c = (v.co for v in f.verts)
        total += a.dot(b.cross(c)) / 6.0
    bm.free()
    return total


def triangulate_and_purge(obj, null_volume=NULL_VOLUME):
    """Triangulate, drop debris components, and assert the volume did not move.

    The assertion is the point. A purge that changes the total volume removed
    something real, and reporting the dropped volume separately is what lets that
    be told apart from removing genuine debris.
    """
    _need_bpy("triangulate_and_purge")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)

    groups = _face_groups(bm)
    vols = [(_group_volume(g), g) for g in groups]
    vols.sort(key=lambda t: -abs(t[0]))
    kept, dropped = [], []
    for vol, g in vols:
        (kept if abs(vol) > null_volume else dropped).append((vol, g))

    if len(kept) != 1:
        bm.free()
        raise RuntimeError(
            f"triangulate_and_purge: expected 1 solid component, found {len(kept)} "
            f"with volumes {[round(v, 6) for v, _ in kept]}"
        )

    vol_before = sum(v for v, _ in vols)
    for _, g in dropped:
        bmesh.ops.delete(bm, geom=list(g), context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    stats = {
        "triangles": len(bm.faces),
        "components": len(groups),
        "dropped_components": len(dropped),
        "volume": kept[0][0],
        "volume_dropped": sum(v for v, _ in dropped),
    }
    bm.free()

    if abs(stats["volume"] - vol_before) > max(1e-6, abs(vol_before) * 1e-9) + abs(stats["volume_dropped"]):
        raise RuntimeError(
            f"triangulate_and_purge changed the solid: {vol_before:.6f} -> "
            f"{stats['volume']:.6f}, dropped {stats['volume_dropped']:.6f}"
        )
    return stats


def _face_groups(bm):
    """Connected components of faces, by shared vertices."""
    seen, groups = set(), []
    for f in bm.faces:
        if f in seen:
            continue
        stack, group = [f], set()
        while stack:
            cur = stack.pop()
            if cur in group:
                continue
            group.add(cur)
            for e in cur.edges:
                for nb in e.link_faces:
                    if nb not in group:
                        stack.append(nb)
        seen |= group
        groups.append(group)
    return groups


def _group_volume(faces):
    total = 0.0
    for f in faces:
        vs = list(f.verts)
        a = vs[0].co
        for i in range(1, len(vs) - 1):
            total += a.dot(vs[i].co.cross(vs[i + 1].co)) / 6.0
    return total


# ===========================================================================
#  POSITIONAL TOPOLOGY  -  the invariant a slicer sees
# ===========================================================================

def weld_by_position(coords, tol=WELD_POSITIONAL):
    """Group coordinates into welded ids the way a consumer would.

    An authoring tool counts faces per *topological* edge; a slicer reconstructs
    topology *by position*. Two vertices at the same coordinate but distinct in
    the tool's data structures are one vertex downstream, and the edges meeting
    there become one edge with too many faces on it. That divergence is how a
    mesh reported as having zero non-manifold edges was refused by a slicer for
    having two.

    Exact match first, then a 27-neighbour grid union-find, so a pair straddling
    a cell boundary still merges.
    """
    inv = 1.0 / tol
    cells = {}
    parent = list(range(len(coords)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i, co in enumerate(coords):
        key = tuple(int(math.floor(c * inv + 0.5)) for c in co)
        cells.setdefault(key, []).append(i)

    tol2 = tol * tol
    for key, members in cells.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    nb = cells.get((key[0] + dx, key[1] + dy, key[2] + dz))
                    if not nb:
                        continue
                    for i in members:
                        for j in nb:
                            if i >= j:
                                continue
                            a, b = coords[i], coords[j]
                            d2 = sum((a[k] - b[k]) ** 2 for k in range(3))
                            if d2 <= tol2:
                                union(i, j)

    remap, ids = {}, []
    for i in range(len(coords)):
        root = find(i)
        if root not in remap:
            remap[root] = len(remap)
        ids.append(remap[root])
    return ids, len(remap)


def positional_topology(triangles, tol=WELD_POSITIONAL):
    """Manifoldness as a slicer computes it. Delegates to the standalone auditor.

    Kept as a thin wrapper so a generator can gate on the same code path the
    external audit uses, rather than a second implementation that might agree by
    accident.
    """
    mesh_audit = _load_mesh_audit()
    verts, faces, exact, risk = mesh_audit.weld(triangles, tol)
    topo = mesh_audit.topology(verts, faces, metric_verts=exact)
    topo["weld_boundary_risk"] = risk
    topo["vertex_digest"] = mesh_audit.vertex_digest(verts)
    return topo


def _load_mesh_audit():
    """Import the standalone auditor from this script's own directory.

    Blender's bundled Python does not have the plugin's scripts on its path, and
    a generator may be `exec()`d from anywhere, so the location is resolved from
    this module's file rather than from the working directory.
    """
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import mesh_audit
    return mesh_audit


# ===========================================================================
#  EXPORT
# ===========================================================================

def export_stl(obj, filepath, rotate_euler=None, drop_to_bed=True, centre_xy=True):
    """Write a binary STL from a disposable copy of `obj`.

    The canonical object keeps an identity transform and never moves. Print
    orientation is baked into the copy's *vertex data*, not carried as an object
    rotation, because a rotation on the object is a rotation the exporter may or
    may not apply - and a baked-in transform nobody can see is the signature of an
    imported mesh nobody can reason about.

    `use_scene_unit=False, global_scale=1.0` pairs with a scene whose
    `scale_length` is already 0.001, so millimetre coordinates are written
    directly instead of being scaled twice.
    """
    _need_bpy("export_stl")
    tmp = obj.copy()
    tmp.data = obj.data.copy()
    tmp.name = "_tmp_export"
    bpy.context.collection.objects.link(tmp)
    try:
        if rotate_euler:
            bm = bmesh.new()
            bm.from_mesh(tmp.data)
            mat = Vector((0.0, 0.0, 0.0)).to_track_quat("Z", "Y").to_matrix().to_4x4()
            from mathutils import Euler
            mat = Euler(rotate_euler, "XYZ").to_matrix().to_4x4()
            bmesh.ops.transform(bm, matrix=mat, verts=bm.verts)
            bm.to_mesh(tmp.data)
            bm.free()

        lo = [min(v.co[i] for v in tmp.data.vertices) for i in range(3)]
        hi = [max(v.co[i] for v in tmp.data.vertices) for i in range(3)]
        shift = [0.0, 0.0, 0.0]
        if centre_xy:
            shift[0] = -(lo[0] + hi[0]) / 2.0
            shift[1] = -(lo[1] + hi[1]) / 2.0
        if drop_to_bed:
            shift[2] = -lo[2]
        if any(shift):
            for v in tmp.data.vertices:
                v.co[0] += shift[0]
                v.co[1] += shift[1]
                v.co[2] += shift[2]

        for o in bpy.context.selected_objects:
            o.select_set(False)
        tmp.select_set(True)
        bpy.context.view_layer.objects.active = tmp
        bpy.ops.wm.stl_export(
            filepath=filepath, export_selected_objects=True,
            global_scale=1.0, use_scene_unit=False,
            apply_modifiers=True, ascii_format=False,
            forward_axis="Y", up_axis="Z",
        )
        return {"dims": [round(hi[i] - lo[i], 4) for i in range(3)],
                "tris": len(tmp.data.polygons)}
    finally:
        purge("_tmp_export")


def gated_export(obj, filepath, accept, rotate_euler=None, weld=WELD_POSITIONAL):
    """Export only if `accept` passed, then re-verify the bytes and delete on failure.

    Three properties worth stating, because each one closes a real hole:

    - A failing variant leaves **no** file, and any stale file at that path from a
      previous run is removed, so a bad build cannot leave an old good-looking
      file behind for someone to pick up.
    - The file-level check parses what was just written, not the mesh in memory.
    - On file-level failure the file is deleted. There is an unavoidable window in
      which an unverified file exists on disk; deleting on failure closes it, and
      is simpler to reason about than write-to-temp-then-rename.
    """
    _need_bpy("gated_export")
    if not accept.ok:
        if os.path.exists(filepath):
            os.remove(filepath)
        return {"exported": False, "reason": "mesh checks failed",
                "failures": [c.name for c in accept.failures]}

    info = export_stl(obj, filepath, rotate_euler=rotate_euler)

    mesh_audit = _load_mesh_audit()
    report = mesh_audit.audit(filepath, weld, 0, "z", 45.0, 4)
    faults = mesh_audit.acceptance(report, {}, allow_multi_body=False)
    if faults:
        os.remove(filepath)
        return {"exported": False, "reason": "file checks failed",
                "faults": faults, "info": info}

    info["vertex_digest"] = report["vertex_digest"]
    info["volume"] = report["topology"]["volume"]
    return {"exported": True, "info": info}

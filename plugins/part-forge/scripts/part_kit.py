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
import sys
import tempfile

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


def inward_normals(poly):
    """Unit inward normal per vertex of a closed simple polygon, either winding.

    Winding is read from the signed area rather than assumed. A ring arriving from
    a profile generator carries whatever winding that generator used, and an offset
    applied the wrong way grows the part instead of hollowing it -- silently, since
    the result is still a valid closed ring.
    """
    n = len(poly)
    if n < 3:
        raise ValueError(f"inward_normals needs 3 or more points, got {n}")
    ccw = polygon_area(poly) > 0.0
    edge = []
    for i in range(n):
        au, av = poly[i]
        bu, bv = poly[(i + 1) % n]
        eu, ev = bu - au, bv - av
        ln = math.hypot(eu, ev)
        if ln < 1e-12:
            edge.append((0.0, 0.0))
            continue
        eu, ev = eu / ln, ev / ln
        edge.append((-ev, eu) if ccw else (ev, -eu))
    out = []
    for i in range(n):
        pu, pv = edge[(i - 1) % n]
        qu, qv = edge[i]
        su, sv = pu + qu, pv + qv
        ln = math.hypot(su, sv)
        out.append((qu, qv) if ln < 1e-12 else (su / ln, sv / ln))
    return out


def _ring_lerp(a, b, t):
    return [(au + (bu - au) * t, av + (bv - av) * t)
            for (au, av), (bu, bv) in zip(a, b)]


def _ring_at_z(rings, zs, z):
    """Linear interpolation of the ring stack at an arbitrary height."""
    if z <= zs[0]:
        return list(rings[0])
    if z >= zs[-1]:
        return list(rings[-1])
    for i in range(len(zs) - 1):
        if zs[i] <= z <= zs[i + 1]:
            span = zs[i + 1] - zs[i]
            return _ring_lerp(rings[i], rings[i + 1],
                              0.0 if span < 1e-12 else (z - zs[i]) / span)
    return list(rings[-1])


def offset_rings(rings, zs, wall, *, floor, ceiling):
    """Inset a ring stack `wall` PERPENDICULAR to the lofted surface, not in-plane.

    Hollowing a loft is the commonest operation any container part needs -- a bank,
    a vase, a housing, an enclosure -- and the obvious construction is wrong.

    Insetting each ring by `d` within its own plane leaves `d` of wall only where
    the surface is vertical. Where the surface slopes `alpha` off vertical the
    perpendicular wall is `d * cos(alpha)`. It is wrong *quietly*, because in-plane
    it is exact: on the part that produced this function the minimum in-plane
    distance between outer and inset ring measured 2.640 mm at every height, to
    three decimals, while the real wall on the upper dome was 1.60 mm.

    **The limit case is the one to remember, because nobody derives it.** On a 45
    degree cone, insetting `d` horizontally *and* `d` vertically reproduces the
    original surface exactly and leaves a wall of zero: with `r = R - z`, the inset
    gives `r = (R - d) - (z - d) = R - z`. The construction that feels obviously
    conservative is degenerate.

    The correction is a horizontal inset of `wall * sqrt(1 + m**2)` per ring vertex,
    where `m` is the surface's outward run per unit rise at that vertex, taken by
    finite difference along the vertex's own inward normal. Per vertex and not per
    ring, because on a non-circular section the slope varies with direction.

    `floor` and `ceiling` are keyword-only and have **no defaults**. A container's
    floor is usually not its wall thickness -- the part this came from carries
    bayonet ledges in a 6.0 mm floor under a 2.64 mm wall -- and letting the floor
    default to the wall inset was a second, independent defect in the same function.
    Omitting them is a TypeError at the call site, which is the only failure mode
    here that cannot reach a printer.

    Returns `(inset_rings, inset_zs)`, ready to hand to `loft_solid` as a cavity.
    """
    n = len(rings)
    if n != len(zs):
        raise ValueError(f"offset_rings: {n} rings but {len(zs)} heights")
    if n < 2:
        raise ValueError(f"offset_rings needs 2 or more rings, got {n}")
    width = len(rings[0])
    for i, r in enumerate(rings):
        if len(r) != width:
            raise ValueError(
                f"offset_rings: ring {i} has {len(r)} points, ring 0 has {width}; "
                f"every ring must carry the same vertex count so the loft closes"
            )
    for i in range(n - 1):
        if zs[i + 1] <= zs[i]:
            raise ValueError(
                f"offset_rings: heights must strictly increase, but z[{i}]={zs[i]} "
                f"and z[{i + 1}]={zs[i + 1]}"
            )
    if wall <= 0.0:
        raise ValueError(f"offset_rings: wall must be positive, got {wall}")
    if not zs[0] <= floor < ceiling <= zs[-1]:
        raise ValueError(
            f"offset_rings: need {zs[0]} <= floor < ceiling <= {zs[-1]}, got "
            f"floor={floor}, ceiling={ceiling}"
        )

    out_zs = sorted({float(floor), float(ceiling)}
                    | {float(z) for z in zs if floor < z < ceiling})
    step = max(1e-4, (zs[-1] - zs[0]) * 1e-3)
    out_rings = []
    for z in out_zs:
        outer = _ring_at_z(rings, zs, z)
        norms = inward_normals(outer)
        z_lo, z_hi = max(zs[0], z - step), min(zs[-1], z + step)
        lo, hi = _ring_at_z(rings, zs, z_lo), _ring_at_z(rings, zs, z_hi)
        dz = z_hi - z_lo
        ring = []
        for j in range(width):
            nu, nv = norms[j]
            # Outward run per unit rise, projected on this vertex's own normal.
            # Coordinate-free: no assumption that the section is centred anywhere.
            m = 0.0 if dz < 1e-12 else -(
                (hi[j][0] - lo[j][0]) * nu + (hi[j][1] - lo[j][1]) * nv) / dz
            d = wall * math.sqrt(1.0 + m * m)
            ring.append((outer[j][0] + d * nu, outer[j][1] + d * nv))

        a_out, a_in = polygon_area(outer), polygon_area(ring)
        if a_out == 0.0 or a_in * a_out <= 0.0 or abs(a_in) >= abs(a_out):
            raise ValueError(
                f"offset_rings: a {wall} mm perpendicular wall collapses the section "
                f"at z={z:.3f} (area {abs(a_out):.3f} -> {abs(a_in):.3f} mm^2). The "
                f"surface slopes too fast to hold this wall; thin the wall, or stop "
                f"the cavity below this height with `ceiling`."
            )
        for j in range(width):
            if not point_in_poly(ring[j], outer):
                raise ValueError(
                    f"offset_rings: inset vertex {j} at z={z:.3f} landed outside the "
                    f"outer ring; the section is too concave for a {wall} mm wall "
                    f"there. Reduce the wall or resample the profile."
                )
        out_rings.append(ring)
    return out_rings, out_zs


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

    def thickness_at(self, point, direction, max_dist=1.0e4, eps=1.0e-4,
                     on_surface_tol=1.0e-3):
        """Material thickness from a point **on the surface**, along `direction`.

        Starts just inside the surface so the first hit is the opposing wall.
        Reads a chord rather than a throat inside a fillet, so it is a screen for
        gross thin walls and not a certificate. Callipers on the printed part
        remain the authority.

        The precondition is now enforced, and returns `None` when it fails, because
        the unenforced version did not fail — it returned confident wrong numbers
        that read as real defects:

        - From the part's axis casting outward it returned 1.60 mm for a 2.64 mm
          wall. The first hit was a coin-slot wall at `x = SLOT_W/2 = 1.6`, and
          1.6 mm is a thoroughly plausible wall. It was investigated as a thin wall.
        - From 1 mm below the part casting up it returned exactly 1.0000 for a 6.0 mm
          floor: the distance from the origin to the first surface, which is the
          origin's own offset handed back. It would have returned 1.0000 for any
          geometry at all, including none.

        The second is the worse failure. A check that returns a constant regardless
        of the model is not weak, it is fabricated, and it presented as a legitimate
        failure twice.

        Both questions were really *"how wide is this void"*, asked with the
        measure-material tool. Use `raster` for a void; it cannot answer with a
        number it invented.
        """
        p = Vector(point)
        near = self.tree.find_nearest(p)
        if near is None or near[3] > on_surface_tol:
            return None
        d = Vector(direction).normalized()
        hit = self.cast(p + d * eps, d, max_dist)
        return None if hit is None else hit[3] + eps

    def raster(self, centre, direction, axis_u, axis_v, half_u, half_v,
               n_u=41, n_v=41, max_dist=1.0e4):
        """Cast a grid of parallel rays through a region; report what got through.

        This is how to measure an *opening* — a coin slot, a bore, a drain — rather
        than measuring the mesh beside it. It answers the physical question the part
        has to satisfy, "can the coin fit", and it answers `span_u is None` when the
        feature was never cut, which fails a gate instead of quietly passing one.

        Returns counts alongside the spans, deliberately. The spans are measured
        between the outermost *ray centres* that passed, so they understate the true
        aperture by up to one pitch — a bias toward failing a marginal part, which is
        the right direction, but not a number to quote as the dimension.

        **The station matters more than the resolution.** Aim the raster so that a
        ray missing the opening lands on solid material. If it can miss the part
        entirely, "nothing blocked it" and "it passed through the slot" become the
        same reading, which is `thickness_at`'s bug wearing a different hat.
        `all_clear` is set when every single ray passed, which nearly always means
        the raster was aimed past the part rather than through it.
        """
        cu, cv = Vector(axis_u).normalized(), Vector(axis_v).normalized()
        d = Vector(direction).normalized()
        c = Vector(centre)
        clear, tested = [], 0
        for i in range(n_u):
            su = -half_u + (2.0 * half_u * i / (n_u - 1)) if n_u > 1 else 0.0
            for j in range(n_v):
                sv = -half_v + (2.0 * half_v * j / (n_v - 1)) if n_v > 1 else 0.0
                tested += 1
                if self.cast(c + cu * su + cv * sv, d, max_dist) is None:
                    clear.append((su, sv))

        out = {
            "tested": tested,
            "clear": len(clear),
            "all_clear": bool(tested) and len(clear) == tested,
            "pitch_u": (2.0 * half_u / (n_u - 1)) if n_u > 1 else 0.0,
            "pitch_v": (2.0 * half_v / (n_v - 1)) if n_v > 1 else 0.0,
            "span_u": None, "span_v": None, "centre_u": None, "centre_v": None,
        }
        if not clear:
            return out
        us = [u for u, _ in clear]
        vs = [v for _, v in clear]
        out.update({
            "span_u": max(us) - min(us),
            "span_v": max(vs) - min(vs),
            "centre_u": (max(us) + min(us)) / 2.0,
            "centre_v": (max(vs) + min(vs)) / 2.0,
        })
        return out

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
    _triangulate_ngons(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _object_from_bmesh(name, bm)


def _triangulate_ngons(bm):
    """Fan-triangulate faces with more than four vertices, in place.

    A cap spanning a 96-point ring is a 96-gon. Blender's own bmesh calls the result
    impeccable — zero non-manifold edges, zero wire edges, zero duplicate positions —
    and `positional_topology` agrees at genus 0. The MANIFOLD boolean solver declines
    it anyway, in the full build sequence though not in isolation, which makes the
    trigger state-dependent and not purely the cap.

    That intermittency is the argument for doing this unconditionally rather than
    reacting to a failure: a declined solver and a working one are distinguishable
    only by `boolean`'s sign guard, and a class of input that provokes one sometimes
    is cheaper to remove than to detect. Quad side walls are left alone; adding
    triangles no solver objected to only costs file size.

    Adds no vertices, so any pinned vertex digest is unaffected by construction.
    """
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)


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
    _triangulate_ngons(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _object_from_bmesh(name, bm)


def hull_solid(name, rings):
    """Convex hull of a point cloud. Only valid when the result *is* convex.

    `convex_hull` returns the points it swallowed as `geom_interior` and leaves them
    in the bmesh. Deleting them matters: a vertex belonging to no face is invisible
    in the viewport, survives export as a loose vertex, and shows up downstream as a
    positional body with no volume -- which `mesh_audit` gates at `null_volume_bodies`
    and `loose vertices`. The version this kit was distilled from removed them and
    this one did not.
    """
    _need_bpy("hull_solid")
    bm = bmesh.new()
    for ring in rings:
        for co in ring:
            bm.verts.new(co)
    res = bmesh.ops.convex_hull(bm, input=bm.verts)
    interior = [g for g in res.get("geom_interior", []) if g.is_valid]
    if interior:
        bmesh.ops.delete(bm, geom=interior, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _object_from_bmesh(name, bm)


def _object_from_bmesh(name, bm):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


#: Which way a correct boolean moves the signed volume. Removing material cannot
#: grow a solid and adding material cannot shrink one, so the sign is a property
#: of the operation and not of the geometry.
VOLUME_SIGN = {"DIFFERENCE": -1, "UNION": +1, "INTERSECT": -1}


def boolean(target, cutter, operation, solver="MANIFOLD", keep_cutter=False):
    """Apply a boolean and raise unless the volume moved the way the operation requires.

    A boolean that silently does nothing is the worst outcome available: the part
    still looks plausible and is wrong. A boolean that silently does the *opposite*
    is worse, and it is the one that actually shipped. When a solver declines, the
    failed modifier still bakes, contributing the cutter as a second closed shell —
    so a DIFFERENCE comes back having *grown* by exactly the cutter's volume.

    Any guard phrased as "did something happen" is satisfied by that merge, accepts
    it on the first attempt, and never reaches the retry that would have worked. The
    magnitude test is necessary and was never sufficient; the sign is what says the
    right thing happened.
    """
    _need_bpy("boolean")
    if operation not in VOLUME_SIGN:
        raise ValueError(
            f"boolean: unknown operation {operation!r}; expected one of "
            f"{', '.join(sorted(VOLUME_SIGN))}"
        )
    want = VOLUME_SIGN[operation]

    before = mesh_volume(target)
    v_cutter = mesh_volume(cutter)
    trace = []
    for attempt in (solver, "EXACT"):
        noise = _apply_boolean(target, cutter, operation, attempt)
        after = mesh_volume(target)
        delta = after - before
        trace.append((attempt, after, delta, noise))
        if abs(delta) > NULL_VOLUME and delta * want > 0:
            if not keep_cutter:
                purge(cutter.name)
            return target

    raise RuntimeError(
        _boolean_failure(target, cutter, operation, before, v_cutter, trace)
    )


def _boolean_failure(target, cutter, operation, before, v_cutter, trace):
    """Say which of the two failures happened, because the fixes are different.

    "Changed nothing" and "changed the wrong way" have the same old message and
    opposite causes: the first means the cutter missed, the second means a solver
    declined and its geometry was merged in. Naming the merge signature — that the
    result equals target plus cutter — is what turns a multi-stage volume bisect
    into a first-read diagnosis.
    """
    last_delta = trace[-1][2]
    moved = any(abs(d) > NULL_VOLUME for _, _, d, _ in trace)
    lines = [
        f"boolean {operation} of {cutter.name} into {target.name} failed.",
        f"  target volume before  {before:14.6f}",
        f"  cutter volume         {v_cutter:14.6f}",
    ]
    for attempt, after, delta, _ in trace:
        lines.append(f"  after {attempt:<9s}       {after:14.6f}   (delta {delta:+.6f})")

    if not moved:
        lines.append("  Nothing moved on either solver: the cutter does not overlap "
                     "the target.")
    else:
        lines.append(f"  The volume moved the wrong way for a {operation}, which is "
                     f"never correct.")
        if abs((before + v_cutter) - trace[-1][1]) <= max(1e-6, abs(v_cutter) * 1e-6):
            lines.append("  The result equals target + cutter exactly. That is the merge "
                         "signature: the")
            lines.append("  solver declined and the failed modifier baked the cutter in "
                         "as a second shell.")
        elif last_delta * VOLUME_SIGN[operation] < 0:
            lines.append("  A cutter or target wound inside out produces this too — check "
                         "signed volumes.")

    noise = "\n".join(n.strip() for _, _, _, n in trace if n and n.strip())
    if noise:
        lines.append("  Blender said:")
        lines.extend(f"    {ln}" for ln in noise.splitlines() if ln.strip())
    return "\n".join(lines)


class _Captured:
    """Mutable holder so a caller can read fd-2 output after the block closes."""

    __slots__ = ("text",)

    def __init__(self):
        self.text = ""


def _capture_fd2(into):
    """Capture C-level stderr around a block. Returns a context manager.

    Blender reports a declined solver as `Cannot execute ... have non-manifold
    geometry` on the process's stderr, not through any Python API — `bpy` exposes
    no handle on it at all. A harness that does not read file descriptor 2 is
    discarding the only direct evidence of why a boolean failed, which is exactly
    what happened: six such warnings were emitted and none reached the exception.

    Degrades to a no-op if the descriptor cannot be duplicated, because losing the
    diagnostic is survivable and losing stderr is not.
    """
    import contextlib

    @contextlib.contextmanager
    def _cm():
        try:
            saved = os.dup(2)
        except (OSError, AttributeError):
            yield
            return
        # Not a `with`: the handle must outlive the yield, and the finally below
        # both restores fd 2 and closes it. SIM115 does not model that shape.
        tmp = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115
        try:
            sys.stderr.flush()
            os.dup2(tmp.fileno(), 2)
            yield
        finally:
            try:
                sys.stderr.flush()
            finally:
                os.dup2(saved, 2)
                os.close(saved)
            tmp.seek(0)
            into.text = tmp.read().decode("utf-8", "replace")
            tmp.close()

    return _cm()


def _apply_boolean(target, cutter, operation, solver):
    """Add, evaluate and bake one boolean modifier. Returns Blender's stderr chatter."""
    mod = target.modifiers.new(name="_bool", type="BOOLEAN")
    mod.operation = operation
    mod.object = cutter
    try:
        mod.solver = solver
    except TypeError:  # older builds lack this solver enum value
        mod.solver = "EXACT"
    cap = _Captured()
    with _capture_fd2(cap):
        _apply_modifiers(target)
    return cap.text


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


def weld_verts(obj, merge_dist=5.0e-3):
    """Weld coincident vertices and dissolve degenerate edges. Never reorients.

    Run between boolean stages. Coincident-but-distinct vertices accumulate across
    operations and the next boolean chokes on them. That half of the old `clean_mesh`
    was true and necessary; only the orientation pass welded to it was not.

    Named `weld_verts` rather than `weld` on purpose: `mesh_audit.weld` is a
    different operation on a different data structure, and `gated_export` already
    binds `weld` as a parameter name, so a module-level `weld` would be shadowed
    inside the one function most likely to want it.
    """
    _need_bpy("weld_verts")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_dist)
    bmesh.ops.dissolve_degenerate(bm, dist=merge_dist, edges=bm.edges)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def clean_mesh(obj, merge_dist=5.0e-3, recalc_normals=False):
    """Weld, reorient only when asked, and report the volume either side.

    **`recalc_normals` defaults to False, and that is a deliberate break with the
    previous behaviour.** `bmesh.ops.recalc_face_normals` orients every face outward
    from its own connected component. On a solid that is a repair. On a vessel it is
    silent corruption: a sealed cavity is a separate component whose faces must point
    *into* the surrounding material for the signed volume to come out as outer minus
    cavity, and recalc turns them the other way.

    Measured on a 20 mm cube with a concentric 14 mm cavity: 5256 mm^3 before,
    10744 mm^3 after — which is outer *plus* cavity, 8000 + 2744. The part is now
    solid to every consumer, and the next boolean treats the cavity as material.

    Nothing downstream catches it. `winding_flips` reads 0 on both sides, because a
    uniformly flipped component contains no disagreeing adjacent pair; `open_edges`,
    `over_edges`, `genus` and `bodies` are all unchanged. The single signal that moves
    is `inverted_bodies`, from 1 to 0 — so the corruption's only witness is the count
    it destroys, and a gate demanding `inverted_bodies == 0` actively prefers the
    corrupted mesh to the correct one.

    Pass `recalc_normals=True` only for a solid whose winding you have reason to
    doubt. Returns stats rather than the object: a repair that changes the artifact
    and reports nothing is the same failure in a smaller frame.
    """
    _need_bpy("clean_mesh")
    before = mesh_volume(obj)
    weld_verts(obj, merge_dist)
    if recalc_normals:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        bm.free()
    after = mesh_volume(obj)
    return {
        "volume_before": before,
        "volume_after": after,
        "volume_delta": after - before,
        "recalc_normals": recalc_normals,
    }


def mesh_volume(obj):
    """Signed volume by the divergence theorem, recentred and in float64.

    Delegates to `_group_volume` rather than repeating the sum, because the naive
    form -- mathutils vectors about the world origin -- is single precision and
    cancels badly. This function is the instrument behind `boolean`'s sign guard,
    which compares its output against `NULL_VOLUME` at 1e-6 mm^3; float32 epsilon on
    a part sitting tens of millimetres from the origin is comfortably above that, so
    the naive version put the guard's threshold below its own noise floor. A boolean
    that legitimately changed nothing could then produce a delta of arbitrary sign
    that cleared both tests, which is the exact failure the guard exists to catch.
    """
    _need_bpy("mesh_volume")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        return _group_volume(bm.faces)  # fans n-gons itself; no triangulate needed
    finally:
        bm.free()


def triangulate_and_purge(obj, null_volume=NULL_VOLUME, expect_components=1,
                          recalc_normals=False):
    """Triangulate, drop debris components, and assert nothing real was removed.

    `expect_components` is how many connected components the caller expects to
    survive: 1 for an ordinary solid, N for a plate of N coupons, and 1 + K for a
    vessel with K sealed cavities — a cavity is a component in its own right, with
    negative signed volume. Pass None to skip the count assertion.

    Declaring the count is worth strictly more than permitting any count. It catches
    a plug fused to its socket, which *lowers* the number, exactly as readily as it
    catches stray debris, which raises it. A boolean flag can only ever express one
    of those.

    `recalc_normals` defaults to False for the reason spelled out on `clean_mesh`.
    This function reoriented unconditionally too, which is the same defect one stage
    later and directly on the export path: a vessel that survived every earlier stage
    was solidified here, on its way to disk.

    `volume` is the sum over surviving components, so for a vessel it is the material
    volume — outer minus cavity — and is the number a mass estimate should use.
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

    if expect_components is not None and len(kept) != expect_components:
        bm.free()
        raise RuntimeError(
            f"triangulate_and_purge: expected {expect_components} component(s), found "
            f"{len(kept)} with volumes {[round(v, 6) for v, _ in kept]}. "
            f"A plate of N coupons wants expect_components=N; a vessel with a sealed "
            f"cavity wants 1 + K, the cavity being the negative-volume component."
        )

    vol_before = sum(v for v, _ in vols)
    for _, g in dropped:
        bmesh.ops.delete(bm, geom=list(g), context="FACES")
    if recalc_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    stats = {
        "triangles": len(bm.faces),
        "triangles_kept": sum(len(g) for _, g in kept),
        "components": len(groups),
        "kept_components": len(kept),
        "dropped_components": len(dropped),
        "dropped_faces": sum(len(g) for _, g in dropped),
        "volume": sum(v for v, _ in kept),
        "volume_dropped": sum(v for v, _ in dropped),
        "component_volumes": [round(v, 6) for v, _ in kept],
    }
    bm.free()

    # Each dropped component is individually under null_volume by construction, so
    # what is worth asserting is that they did not add up to something real - a part
    # shedding a thousand slivers has lost a feature, not debris.
    slack = max(1e-6, abs(vol_before) * 1e-9)
    if abs(stats["volume_dropped"]) > slack:
        raise RuntimeError(
            f"triangulate_and_purge dropped {stats['volume_dropped']:.6f} mm^3 across "
            f"{len(dropped)} component(s), above the {slack:.3e} tolerance; that is "
            f"geometry, not debris. Total before {vol_before:.6f}, kept "
            f"{stats['volume']:.6f}."
        )
    return stats


def _face_groups(bm):
    """Faces grouped into bodies the way a SLICER groups them: adjacency only
    across edges that have exactly two faces.

    An edge with four faces is not a join, it is a fault, so anything hanging off
    the solid through one of those is correctly seen as a separate body rather than
    as part of it. That is the whole reason for this convention rather than "share
    any edge": it is what makes null debris fall out as its own component instead of
    hiding inside the shell.

    The previous implementation here walked every `edge.link_faces` regardless of
    count, and its docstring said "by shared vertices" while doing neither. It
    therefore absorbed a back-to-back flap into the body across the very four-face
    edge that is this plugin's founding defect -- the one Bambu Studio refused to
    slice while the gate reported zero.
    """
    parent = list(range(len(bm.faces)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for e in bm.edges:
        if len(e.link_faces) == 2:
            ra, rb = find(e.link_faces[0].index), find(e.link_faces[1].index)
            if ra != rb:
                parent[rb] = ra
    groups = {}
    for f in bm.faces:
        groups.setdefault(find(f.index), []).append(f)
    return list(groups.values())


def _group_volume(faces):
    """Enclosed volume by the divergence theorem. Near zero for anything that does
    not enclose, which is exactly the discriminator the purge needs.

    Two details that are not fussiness, and that this function did not have until a
    real build tripped over both. The sum is taken about the component's **own
    centroid**, and in **float64**.

    Done the obvious way -- mathutils vectors about the world origin -- a
    back-to-back pair of triangles 23 mm out came back at 9.5e-06 mm^3 rather than
    zero, because `mathutils` is SINGLE precision and the two tetrahedra are ~60 mm^3
    each cancelling to nothing. 9.5e-06 is simply float32 epsilon at that magnitude.
    That is above `NULL_VOLUME`, so null debris read as a second solid body and
    aborted an otherwise correct build.

    Recentring removes the cancellation and, for a closed surface, changes nothing:
    the integral is translation-invariant. float64 removes the rest. The same pair
    then measures ~1e-15.
    """
    verts = {id(v): v for f in faces for v in f.verts}.values()
    n = len(verts)
    if not n:
        return 0.0
    ox = sum(float(v.co.x) for v in verts) / n
    oy = sum(float(v.co.y) for v in verts) / n
    oz = sum(float(v.co.z) for v in verts) / n
    total = 0.0
    for f in faces:
        vs = list(f.verts)
        ax = float(vs[0].co.x) - ox
        ay = float(vs[0].co.y) - oy
        az = float(vs[0].co.z) - oz
        for i in range(1, len(vs) - 1):
            bx = float(vs[i].co.x) - ox
            by = float(vs[i].co.y) - oy
            bz = float(vs[i].co.z) - oz
            cx = float(vs[i + 1].co.x) - ox
            cy = float(vs[i + 1].co.y) - oy
            cz = float(vs[i + 1].co.z) - oz
            total += (ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx)
                      + az * (bx * cy - by * cx)) / 6.0
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


def gated_export(obj, filepath, accept, rotate_euler=None, weld=WELD_POSITIONAL,
                 expect_solids=1, expect_cavities=0, expect=None,
                 wall_samples=0, build_axis="z", overhang_deg=45.0):
    """Export only if `accept` passed, then re-verify the bytes and delete on failure.

    Three properties worth stating, because each one closes a real hole:

    - A failing variant leaves **no** file, and any stale file at that path from a
      previous run is removed, so a bad build cannot leave an old good-looking
      file behind for someone to pick up.
    - The file-level check parses what was just written, not the mesh in memory.
    - On file-level failure the file is deleted. There is an unavoidable window in
      which an unverified file exists on disk; deleting on failure closes it, and
      is simpler to reason about than write-to-temp-then-rename.

    `expect_solids` and `expect_cavities` declare the shape of the artifact: one
    positive shell and no cavities for an ordinary part, N and 0 for a plate of
    coupons, 1 and K for a vessel. Both were previously fixed at 1 and 0 with no way
    to say otherwise, which made a plate and a hollow part equally unexportable —
    the hollow one being rejected as `inverted_bodies: got 1, want 0`, i.e. for the
    one property that proved it was built correctly.

    `expect`, `wall_samples`, `build_axis` and `overhang_deg` reach the file tier
    instead of being pinned here. `wall_samples` in particular defaulted to 0, which
    returns `{"available": False}` and disabled the file tier's only physical
    measurement at every call site in the plugin, with no caller able to turn it on.
    It still defaults to 0 because it is slow; the difference is that it is now a
    choice someone can make.
    """
    _need_bpy("gated_export")
    if not accept.ok:
        if os.path.exists(filepath):
            os.remove(filepath)
        return {"exported": False, "reason": "mesh checks failed",
                "failures": [c.name for c in accept.failures]}

    info = export_stl(obj, filepath, rotate_euler=rotate_euler)

    mesh_audit = _load_mesh_audit()
    report = mesh_audit.audit(filepath, weld, wall_samples, build_axis, overhang_deg, 4)
    faults = mesh_audit.acceptance(
        report, expect or {},
        expect_solids=expect_solids, expect_cavities=expect_cavities,
    )
    if faults:
        os.remove(filepath)
        return {"exported": False, "reason": "file checks failed",
                "faults": faults, "info": info}

    info["vertex_digest"] = report["vertex_digest"]
    info["volume"] = report["topology"]["volume"]
    info["bodies"] = report["topology"]["bodies"]
    info["cavities"] = report["topology"]["inverted_bodies"]
    return {"exported": True, "info": info}

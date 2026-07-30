#!/usr/bin/env python3
"""Measure the geometry facts that actually drive slicer settings.

Settings advice is only as good as its premises. "It has steep overhangs" or
"it's tall and tippy" are claims about the mesh, and this script turns them into
numbers so the recommendation can cite them instead of guessing from a filename.

Reports, as JSON: bounding box, volume, bed-contact area, overhang area split by
slope band, bridge candidates, tipping aspect ratio, and mesh watertightness.

Usage:
    inspect_model.py MODEL [MODEL ...] [--orient auto] [--pretty]

Supports STL (binary and ASCII), 3MF, and OBJ. Pure standard library; uses numpy
if present purely for speed on large meshes.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

# Slope is measured from the horizontal plane, matching Bambu Studio's
# "Threshold angle": 0 deg is a flat downward face, 90 deg is a vertical wall.
# Bands are chosen around the decisions they inform.
SLOPE_BANDS = [
    (0, 10, "flat_0_10", "bridging / needs support or is a bridge"),
    (10, 30, "shallow_10_30", "unprintable unsupported on most materials"),
    (30, 45, "moderate_30_45", "marginal; supportable by slowing overhang speed"),
    (45, 60, "steep_45_60", "normally fine with cooling"),
    (60, 90, "near_vertical_60_90", "no concern"),
]

BED_TOL = 0.05  # mm; a facet this close to z_min is touching the plate
BRIDGE_MIN_HEIGHT = 0.5  # mm above the plate before a flat-down face counts as a bridge


# ---------------------------------------------------------------------------
# loaders — each returns a flat list of triangles [((x,y,z),(x,y,z),(x,y,z)), ...]


def load_stl(path: Path) -> list:
    data = path.read_bytes()
    # An ASCII STL starts with "solid", but so do some binary files written by
    # sloppy exporters, so confirm against the declared triangle count instead.
    if len(data) >= 84:
        (count,) = struct.unpack("<I", data[80:84])
        if len(data) == 84 + count * 50:
            return _load_stl_binary(data, count)
    if data[:5].lower().startswith(b"solid"):
        return _load_stl_ascii(data.decode("utf-8", "replace"))
    raise ValueError(f"{path.name}: not a recognizable STL")


def _load_stl_binary(data: bytes, count: int) -> list:
    tris = []
    off = 84
    for _ in range(count):
        vals = struct.unpack_from("<12fH", data, off)
        tris.append((vals[3:6], vals[6:9], vals[9:12]))
        off += 50
    return tris


def _load_stl_ascii(text: str) -> list:
    tris, verts = [], []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("vertex"):
            verts.append(tuple(float(x) for x in line.split()[1:4]))
            if len(verts) == 3:
                tris.append(tuple(verts))
                verts = []
    return tris


def _safe_xml(data: bytes, label: str) -> bytes:
    """Refuse XML carrying a DTD before handing it to ElementTree.

    3MF files are routinely downloaded from model-sharing sites, so they are
    untrusted input. Entity declarations are the vector for both XXE file reads
    and billion-laughs expansion, and no legitimate 3MF needs a DTD, so the
    cheapest correct defense is to reject them outright rather than parse and hope.
    """
    head = data[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in data.lower():
        raise ValueError(
            f"{label}: XML declares a DTD/entities; refusing to parse untrusted markup"
        )
    return data


def load_3mf(path: Path) -> list:
    tris = []
    with zipfile.ZipFile(path) as zf:
        models = [n for n in zf.namelist() if n.endswith(".model")]
        if not models:
            raise ValueError(f"{path.name}: no .model part inside the 3MF")
        for name in models:
            root = ET.fromstring(_safe_xml(zf.read(name), f"{path.name}:{name}"))
            ns = {"c": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
            # `ns` is bound as a default so each .model part keeps its own
            # namespace; a late-binding closure would apply the last one to all.
            find = (
                (lambda el, tag, _ns=ns: el.findall(f".//c:{tag}", _ns))
                if ns
                else (lambda el, tag, _ns=None: el.findall(f".//{tag}"))
            )
            for mesh in find(root, "mesh"):
                pts = [
                    (float(v.get("x")), float(v.get("y")), float(v.get("z")))
                    for v in find(mesh, "vertex")
                ]
                for t in find(mesh, "triangle"):
                    try:
                        tris.append(
                            (
                                pts[int(t.get("v1"))],
                                pts[int(t.get("v2"))],
                                pts[int(t.get("v3"))],
                            )
                        )
                    except (IndexError, TypeError):
                        continue
    return tris


def load_obj(path: Path) -> list:
    pts, tris = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("v "):
            pts.append(tuple(float(x) for x in line.split()[1:4]))
        elif line.startswith("f "):
            idx = [int(tok.split("/")[0]) for tok in line.split()[1:]]
            idx = [i - 1 if i > 0 else len(pts) + i for i in idx]
            for k in range(1, len(idx) - 1):  # fan-triangulate n-gons
                tris.append((pts[idx[0]], pts[idx[k]], pts[idx[k + 1]]))
    return tris


LOADERS = {".stl": load_stl, ".3mf": load_3mf, ".obj": load_obj}


# ---------------------------------------------------------------------------
# geometry


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


# --------------------------------------------------------------------------- #
# narrow features — can this nozzle draw the detail that is in the file?
#
# A groove has two facing walls and the slicer must fit a perimeter on each. Below
# 2x the line width there is nowhere to put both, and the result is the ragged,
# over-extruded rim documented in failure-modes.md. The number that decides it is
# the gap between facing walls, and nobody has it: it is invisible in a bounding
# box, and a photograph cannot supply it.
#
# Three things make this harder than a 3D distance query, and each is a way to be
# confidently wrong:
#
#   1. It must be measured IN THE SLICING PLANE. A groove running at 45 deg to Z
#      has a perpendicular width W but an in-plane width W/cos(45) = 1.41 W, and
#      the slicer only ever sees the latter. A 3D nearest-surface query reports
#      the narrow number and condemns a groove that prints perfectly.
#   2. A chamfered or V-shaped groove tapers to zero width at its root, so the
#      minimum gap on any bevelled detail is ~0 and means nothing. The honest
#      metric is how much boundary length sits in the failing band, not the min.
#   3. The threshold is a function of line width, which comes from the preset.
#      The same model is fine at 0.42 mm and unprintable at 0.6.
#
# Direction is taken from the triangle's own normal projected to XY. STL normals
# point out of the solid by definition, so "which way is air" needs no contour
# assembly, no winding analysis, and no even-odd fill rule.
#
# A facet's normal alone says which way it faces, not whether that side is air.
# On one clean solid those are the same thing; on a model built from overlapping
# un-booleaned bodies they are not, and the buried facets a slicer would union
# away read as the two sides of an impossibly thin rib. `_is_interior` settles
# it with the nonzero winding rule -- the same fill rule the slicer uses -- and
# is asked only about a facet that is about to be counted, so clean parts pay
# almost nothing for it.
#
# The other precondition is consistent winding: a flipped facet turns "out" into
# "in" and would silently zero a real feature. That is cheap to detect from the
# edge bookkeeping `analyze` already does -- on a closed, consistently wound mesh
# every DIRECTED edge occurs exactly once -- so it is measured rather than
# assumed, and `_flags` withholds these numbers on any mesh that fails either
# precondition. A single flipped triangle in an otherwise watertight box is
# caught. part-forge's `mesh_audit.py` remains the fuller audit.
# --------------------------------------------------------------------------- #

NARROW_MAX_LAYERS = 120  # sampling budget; a full-height sweep is rarely needed
NARROW_SAMPLE_STEP = 0.3  # mm of boundary between probes
# cos(155 deg): the two sides of a slot are near-antiparallel. Loosening this
# starts admitting concave corners, whose width passes through zero by
# construction and would report a 0.00 mm minimum gap on any filleted part.
#
# Note what this does and does not reject, because it is easy to read as harsher
# than it is. The normals compared here are the XY projections, so a slot with
# vertical DRAFT is untouched: tilting both flanks in Z leaves their in-plane
# normals exactly antiparallel, and a 45-degree-drafted slot is still measured
# correctly, its area simply falling off as less of its depth sits under the
# threshold (120 -> 4 mm2 across 0 to 90 degrees of included draft, no cliff).
# What it rejects is a wedge in the CROSS-SECTION -- a corner, in plan view --
# which is the right call, because the cross-section is all the slicer sees.
PARALLEL_DOT = -0.9
# Below this the two surfaces are touching, not separated by a gap: a shared
# tessellation edge, a coincident facet, or the feather edge where a tapering
# face runs out. Measured on the saddle fixture, a hit distribution that
# otherwise piles up at the ray epsilon itself and drags the reported minimum
# to 0.000 mm -- a number that is alarming, meaningless, and not about printing.
TOUCH_EPS = 0.02  # mm
# How far outside a facet to stand when asking whether that side is really air.
# Must be far smaller than the narrowest feature worth reporting, so that
# stepping out of a genuine 0.3 mm slot never lands in the far wall.
INTERIOR_EPS = 0.001  # mm
HIST_BIN = 0.01  # mm; width histogram resolution, for re-scoring other nozzles
# Bambu's line width runs ~1.05x the nozzle. A model is called resolvable when
# under RESOLVABLE_PCT of its wall area falls below two line widths; a few
# percent is the feather edge every real part has where a face runs out.
NOZZLES = (0.2, 0.25, 0.4, 0.6, 0.8)
LINE_WIDTH_RATIO = 1.05
RESOLVABLE_PCT = 3.0


def _wall_facets(tris: list):
    """Triangles that can form a vertical wall, with normal and z-span precomputed.

    Done once rather than per plane. Recomputing a cross product for every
    triangle at every one of 120 heights is most of the cost of a naive sweep,
    and none of it depends on the height.
    """
    out = []
    for a, b, c in tris:
        n = _cross(_sub(b, a), _sub(c, a))
        mag3 = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if mag3 < 1e-12:  # zero-area triangle
            continue
        nxy = math.hypot(n[0], n[1])
        # Slope, not size. Testing the raw cross-product magnitude conflates
        # "nearly horizontal" with "small", so a tiny vertical sliver would be
        # discarded as a floor while a large almost-flat facet was kept as a wall.
        # Dividing by the full 3D magnitude first makes this an actual angle test.
        if nxy / mag3 < 1e-3:  # a floor or ceiling, never a wall
            continue
        zs = (a[2], b[2], c[2])
        out.append((a, b, c, n[0] / nxy, n[1] / nxy, min(zs), max(zs)))
    return out


def _slice_at(facets, z: float) -> list:
    """Cross-section at z as (x0, y0, x1, y1, nx, ny) with the outward normal."""
    segs = []
    for a, b, c, nx, ny, _, _ in facets:
        d = (a[2] - z, b[2] - z, c[2] - z)
        if (d[0] > 0 and d[1] > 0 and d[2] > 0) or (d[0] < 0 and d[1] < 0 and d[2] < 0):
            continue
        pts = []
        for (p, dp), (q, dq) in (((a, d[0]), (b, d[1])), ((b, d[1]), (c, d[2])), ((c, d[2]), (a, d[0]))):
            if (dp > 0) != (dq > 0) and dp != dq:
                t = dp / (dp - dq)
                pts.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
        if len(pts) != 2:
            continue
        (x0, y0), (x1, y1) = pts
        if math.hypot(x1 - x0, y1 - y0) < 1e-9:
            continue
        segs.append((x0, y0, x1, y1, nx, ny))
    return segs


def _interior_rows(segs, cell):
    """Bucket segments by the y bands they cross, for the winding query below."""
    rows = defaultdict(list)
    for s in segs:
        lo, hi = (s[1], s[3]) if s[1] <= s[3] else (s[3], s[1])
        for gy in range(int(lo // cell), int(hi // cell) + 1):
            rows[gy].append(s)
    return rows


def _is_interior(seg, rows, cell):
    """True when this facet is buried inside the solid.

    Without this there is no solid/air test at all, only "what does this facet
    face" -- and on a model assembled from overlapping un-booleaned bodies the
    buried facets a slicer would union away read as the two sides of an
    impossibly thin rib. A brick modelled as two boxes overlapping by 0.3 mm
    reported 25 % thin-wall surface that does not exist, and that mesh is
    watertight, so no manifold check catches it.

    The test is the nonzero winding rule, which is exactly the fill rule a
    slicer applies when it unions bodies. Step just outside the facet along its
    own normal and cast a ray to +X, adding +1 for each boundary crossed whose
    outward normal also points +X (leaving material) and -1 for each pointing
    -X (entering it). Air sums to zero. Inside one body sums to 1, inside two
    overlapping bodies sums to 2 -- nonzero either way, so the facet is buried
    and its "outside" is a lie.

    Asked lazily -- only about a facet that is about to be counted, and memoised
    per layer. On a clean part almost nothing is ever within a line width of
    anything, so this runs a few hundred times instead of once per segment per
    layer, and the containment test costs nothing on the parts that do not need it.
    """
    x0, y0, x1, y1, nx, ny = seg
    px = (x0 + x1) / 2 + nx * INTERIOR_EPS
    py = (y0 + y1) / 2 + ny * INTERIOR_EPS
    wind = 0
    for tx0, ty0, tx1, ty1, tnx, _tny in rows.get(int(py // cell), ()):
        # Half-open comparison: a ray through a shared vertex crosses the
        # boundary once, not twice and not zero times.
        if (ty0 > py) == (ty1 > py):
            continue
        if tx0 + (py - ty0) / (ty1 - ty0) * (tx1 - tx0) > px:
            wind += 1 if tnx > 0 else -1
    return wind != 0


def _cast(px, py, dx, dy, sx, sy, cands, max_dist):
    """Nearest wall PARALLEL to the source wall along a ray, or None.

    Parallelism, not mere visibility, is what makes this a slot measurement.
    Any concave corner -- every fillet, every chamfer, every V-groove root --
    has two surfaces whose separation passes through zero at the vertex. Accept
    whatever the ray happens to hit and the reported minimum gap on a smooth
    curved part is 0.00 mm, which is both meaningless and alarming.

    Two walls of a real slot are within a few degrees of antiparallel, so
    testing the hit normal against the SOURCE normal (not against the ray)
    rejects corner geometry while keeping genuine parallel-sided grooves. The
    ray direction alone then separates a gap from a wall thickness.
    """
    best = None
    best_seg = None
    for seg in cands:
        x0, y0, x1, y1, nx, ny = seg
        if nx * sx + ny * sy > PARALLEL_DOT:  # not a facing wall, just a corner
            continue
        ex, ey = x1 - x0, y1 - y0
        denom = dx * ey - dy * ex
        if abs(denom) < 1e-12:
            continue
        rx, ry = x0 - px, y0 - py
        t = (rx * ey - ry * ex) / denom
        if t <= TOUCH_EPS or t >= max_dist or (best is not None and t >= best):
            continue
        u = (rx * dy - ry * dx) / denom
        # Slightly outside [0,1]: a ray through the exact vertex shared by two
        # segments can land marginally past the end of both and be dropped by
        # each, losing a real hit. Overlapping instead is harmless -- the nearest
        # hit wins, so counting one twice changes nothing.
        if -1e-9 <= u <= 1.0 + 1e-9:
            best, best_seg = t, seg
    return (best, best_seg) if best is not None else None


def _narrow_features(tris: list, line_width: float, max_layers: int) -> dict:
    zs = [v[2] for t in tris for v in t]
    z_lo, z_hi = min(zs), max(zs)
    height = z_hi - z_lo
    if height <= 0:
        return {}
    n_layers = max(1, min(max_layers, int(height / 0.2)))
    # Midpoint rule: n slabs of equal thickness sampled at their centres, so the
    # probes account for exactly the full height. Sampling at height/(n+1) spacing
    # instead leaves the part n/(n+1) short -- a systematic under-report that a
    # fixture deriving its own expected value the same way can never catch,
    # because the bias then sits on both sides of the comparison and cancels.
    # The 1e-7 offset keeps a plane off any exact vertex, which is the one
    # degenerate case this scheme cannot resolve.
    step = height / n_layers
    planes = [z_lo + step * (i + 0.5) + 1e-7 for i in range(n_layers)]

    floor = line_width  # below one line width nothing can be drawn at all
    ceiling = 2.0 * line_width  # below two, two walls cannot both fit
    # Reported as wall AREA, not summed cross-section length. Length would scale
    # with how many layers were sampled, so the same part would score differently
    # at a different budget -- a number that moves when the measurement changes
    # and the part does not. Each probe stands for its share of the perimeter
    # times the slab thickness it represents, which is sampling-invariant.
    tally = {
        k: {"min": None, "unresolvable_mm2": 0.0, "ragged_mm2": 0.0, "z": []}
        for k in ("gap", "wall")
    }
    # Every hit also lands in a width histogram, so the same single pass can be
    # re-scored against a different nozzle afterwards. Only smaller nozzles are
    # answerable -- their band is a subset of the one already cast -- but that is
    # the direction the question always runs when detail is coming out ragged.
    hist = {k: defaultdict(float) for k in ("gap", "wall")}

    # Bucket facets by the planes they span. A triangle is short in z relative to
    # the part, so each plane ends up testing a small fraction of the mesh rather
    # than all of it -- the difference between seconds and half a minute on a
    # 27k-triangle part, with identical output.
    facets = _wall_facets(tris)
    buckets = defaultdict(list)
    for f in facets:
        lo = max(0, int((f[5] - z_lo) / step) - 1)
        hi = min(n_layers - 1, int((f[6] - z_lo) / step) + 1)
        for i in range(lo, hi + 1):
            buckets[i].append(f)

    # Anything at or beyond `ceiling` is discarded, so there is no reason to look
    # further than that -- and using it as the grid cell size too collapses the
    # candidate list from every segment within 3 mm to every segment within one
    # line-width pair. Same answer, a fraction of the work.
    cell = ceiling
    wall_area = 0.0
    for idx, z in enumerate(planes):
        segs = _slice_at(buckets.get(idx, ()), z)
        if len(segs) < 2:
            continue
        rows = _interior_rows(segs, cell)
        buried = {}  # memoised per layer; see _is_interior
        grid = defaultdict(list)
        for s in segs:
            x0, y0, x1, y1 = s[0], s[1], s[2], s[3]
            for gx in range(int(min(x0, x1) // cell), int(max(x0, x1) // cell) + 1):
                for gy in range(int(min(y0, y1) // cell), int(max(y0, y1) // cell) + 1):
                    grid[(gx, gy)].append(s)
        neighbourhood = {}  # gathered per cell, not per probe

        for x0, y0, x1, y1, nx, ny in segs:
            seg_len = math.hypot(x1 - x0, y1 - y0)
            # ceil, not int: int() lets a 0.5 mm segment be probed once, i.e. at
            # 0.5 mm spacing, so the advertised 0.3 mm resolution would be a
            # claim the code does not honour. Area is unaffected either way.
            n_probe = max(1, math.ceil(seg_len / NARROW_SAMPLE_STEP))
            probe_area = (seg_len / n_probe) * step
            for i in range(n_probe):
                wall_area += probe_area
                f = (i + 0.5) / n_probe
                px, py = x0 + f * (x1 - x0), y0 + f * (y1 - y0)
                gkey = (int(px // cell), int(py // cell))
                cands = neighbourhood.get(gkey)
                if cands is None:
                    cands = neighbourhood[gkey] = [
                        s
                        for ox in (-1, 0, 1)
                        for oy in (-1, 0, 1)
                        for s in grid.get((gkey[0] + ox, gkey[1] + oy), ())
                    ]
                # Outward is into air: the distance to the facing wall of a groove.
                # Inward is into solid: the thickness of a rib.
                for kind, (dx, dy) in (("gap", (nx, ny)), ("wall", (-nx, -ny))):
                    found = _cast(px, py, dx, dy, nx, ny, cands, ceiling)
                    if found is None:
                        continue
                    hit, hseg = found
                    # Only now is containment worth paying for: both the facet we
                    # stand on and the one we hit must actually border air, or
                    # this is two buried faces of overlapping bodies pretending
                    # to be a rib.
                    src = (x0, y0, x1, y1, nx, ny)
                    for s in (src, hseg):
                        if s not in buried:
                            buried[s] = _is_interior(s, rows, cell)
                    if buried[src] or buried[hseg]:
                        continue
                    rec = tally[kind]
                    rec["min"] = hit if rec["min"] is None else min(rec["min"], hit)
                    key = "unresolvable_mm2" if hit < floor else "ragged_mm2"
                    rec[key] += probe_area
                    rec["z"].append(z)
                    hist[kind][int(hit / HIST_BIN)] += probe_area

    out = {
        "line_width_mm": round(line_width, 3),
        "two_wall_floor_mm": round(ceiling, 3),
        "layers_sampled": len(planes),
        "sample_step_mm": NARROW_SAMPLE_STEP,
        # The resolution limit, stated so a null result can be read correctly.
        # Detail confined to a z band thinner than this can fall between planes
        # and report as nothing at all, which is indistinguishable from a clean
        # part unless the pitch is on the page next to it.
        "layer_pitch_mm": round(step, 3),
        "wall_area_mm2": round(wall_area, 1),
    }
    for kind, rec in tally.items():
        failing = rec["unresolvable_mm2"] + rec["ragged_mm2"]
        entry = {
            # An infimum, and on any tapered or chamfered feature it tends to the
            # touch epsilon by construction: a chamfer IS a gap that closes. Read
            # the areas to decide anything; this number only says such a place exists.
            "min_mm": round(rec["min"], 3) if rec["min"] is not None else None,
            "unresolvable_mm2": round(rec["unresolvable_mm2"], 2),
            "ragged_mm2": round(rec["ragged_mm2"], 2),
            # Self-normalising, so a feather edge on a big part reads as the
            # rounding error it is rather than as a defect.
            "pct_of_wall_area": round(100 * failing / wall_area, 2) if wall_area else 0.0,
        }
        if rec["z"]:
            # Each plane stands for its whole slab, so the affected band reaches
            # half a pitch beyond the outermost plane that saw it. Reporting the
            # plane heights alone understates it, and on a feature caught by a
            # single plane it would collapse to a zero-width range.
            entry["z_range_mm"] = [
                round(max(z_lo, min(rec["z"]) - step / 2), 2),
                round(min(z_hi, max(rec["z"]) + step / 2), 2),
            ]
        out[kind] = entry

    # Re-score the same measurement against every nozzle whose band the cast
    # already covers. This is what turns "19 % of your walls are too fine" into
    # "and a 0.4 nozzle is the wrong tool for this model", which is the sentence
    # the user actually needs.
    by_nozzle = {}
    for nozzle in NOZZLES:
        lw = round(nozzle * LINE_WIDTH_RATIO, 3)
        if lw > line_width + 1e-9:
            continue  # a wider band than was cast; no data, so no claim
        limit = 2.0 * lw
        failing = sum(
            area
            for k in ("gap", "wall")
            for b, area in hist[k].items()
            if (b + 0.5) * HIST_BIN < limit
        )
        by_nozzle[f"{nozzle:.2f}"] = round(100 * failing / wall_area, 2) if wall_area else 0.0
    out["pct_failing_by_nozzle"] = by_nozzle
    resolvable = [n for n, p in by_nozzle.items() if p < RESOLVABLE_PCT]
    out["smallest_resolvable_nozzle"] = min(resolvable, key=float) if resolvable else None
    out["resolvable_threshold_pct"] = RESOLVABLE_PCT
    return out


def analyze(tris: list, line_width: float = 0.42, narrow_layers: int = NARROW_MAX_LAYERS) -> dict:
    if not tris:
        raise ValueError("mesh contains no triangles")

    xs = [v[0] for t in tris for v in t]
    ys = [v[1] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    bbox = {
        "min": [min(xs), min(ys), min(zs)],
        "max": [max(xs), max(ys), max(zs)],
    }
    dims = [bbox["max"][i] - bbox["min"][i] for i in range(3)]
    z_min = bbox["min"][2]

    total_area = 0.0
    volume6 = 0.0
    bed_area = 0.0
    band_area = defaultdict(float)
    bridge_area = 0.0
    bridge_pts = []
    degenerate = 0
    edges = defaultdict(int)
    directed = defaultdict(int)

    for a, b, c in tris:
        n = _cross(_sub(b, a), _sub(c, a))
        mag = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if mag < 1e-12:
            degenerate += 1
            continue
        area = mag / 2.0
        total_area += area
        # Signed volume of the tetrahedron to the origin; sums to the enclosed
        # volume for a closed, consistently-wound mesh.
        volume6 += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )

        for p, q in ((a, b), (b, c), (c, a)):
            kp, kq = _key(p), _key(q)
            edges[tuple(sorted((kp, kq)))] += 1
            # Direction as well as adjacency. On a consistently wound closed
            # mesh the two triangles sharing an edge traverse it in opposite
            # directions, so every directed edge occurs exactly once. A second
            # occurrence means a neighbour is flipped -- which inverts "outward"
            # for that facet, and outward is the whole basis of the
            # narrow-feature measurement.
            directed[(kp, kq)] += 1

        nz = n[2] / mag
        if nz < 0:  # downward-facing: the only facets that can need support
            slope = math.degrees(math.acos(min(1.0, -nz)))
            for lo, hi, key, _ in SLOPE_BANDS:
                if lo <= slope < hi or (hi == 90 and slope >= 60):
                    band_area[key] += area
                    break
            zc = (a[2] + b[2] + c[2]) / 3.0
            if slope < 10:
                if zc <= z_min + BED_TOL:
                    bed_area += area
                elif zc >= z_min + BRIDGE_MIN_HEIGHT:
                    bridge_area += area
                    bridge_pts.extend([a, b, c])

    volume_mm3 = abs(volume6) / 6.0
    open_edges = sum(1 for count in edges.values() if count != 2)
    flipped_edges = sum(1 for count in directed.values() if count > 1)

    # The flat band lumps together three situations with opposite fixes: the face
    # resting on the plate (no action), a bridge anchored at both ends (tune
    # bridge flow/cooling), and a genuinely floating flat face (needs support).
    # Reporting them merged is what makes naive advice recommend supports for a
    # part whose "overhang" is just its own bottom.
    band_area["flat_0_10"] = max(0.0, band_area["flat_0_10"] - bed_area - bridge_area)
    floating_flat = band_area["flat_0_10"]

    downward = sum(band_area.values()) + bed_area + bridge_area
    bands = {}
    for _, _, key, meaning in SLOPE_BANDS:
        bands[key] = {
            "area_mm2": round(band_area[key], 2),
            "pct_of_downward": round(100 * band_area[key] / downward, 1)
            if downward
            else 0.0,
            "meaning": meaning,
        }
    bands["flat_0_10"]["meaning"] = (
        "floating flat face, excludes bed contact and bridges — needs support"
    )

    footprint_min = min(dims[0], dims[1])
    result = {
        "triangles": len(tris),
        "degenerate_triangles": degenerate,
        "watertight": open_edges == 0,
        "open_edges": open_edges,
        "winding_consistent": flipped_edges == 0,
        "flipped_edges": flipped_edges,
        "bbox_mm": {k: [round(v, 3) for v in val] for k, val in bbox.items()},
        "dims_mm": {
            "x": round(dims[0], 3),
            "y": round(dims[1], 3),
            "z": round(dims[2], 3),
        },
        "volume_cm3": round(volume_mm3 / 1000.0, 3),
        "surface_area_cm2": round(total_area / 100.0, 2),
        "bed_contact_area_mm2": round(bed_area, 2),
        "overhang_by_slope": bands,
        "support_needed_area_mm2": round(floating_flat + band_area["shallow_10_30"], 2),
        "bridge_area_mm2": round(bridge_area, 2),
        "tipping_aspect_ratio": round(dims[2] / footprint_min, 2)
        if footprint_min > 0.01
        else None,
        "narrow_features": _narrow_features(tris, line_width, narrow_layers),
    }

    if bridge_pts:
        bxs = [p[0] for p in bridge_pts]
        bys = [p[1] for p in bridge_pts]
        result["largest_bridge_extent_mm"] = {
            "x": round(max(bxs) - min(bxs), 2),
            "y": round(max(bys) - min(bys), 2),
        }

    result["flags"] = _flags(result)
    return result


def _key(p):
    # Quantize to 1 micron so float noise from the exporter does not split a
    # shared edge into two, which would fake a non-watertight mesh.
    return (round(p[0], 3), round(p[1], 3), round(p[2], 3))


def _flags(r: dict) -> list[str]:
    out = []
    if not r["watertight"]:
        out.append(
            f"MESH NOT WATERTIGHT ({r['open_edges']} open edges) — slicing may produce "
            "missing walls or phantom infill; repair before tuning settings"
        )
    if r["degenerate_triangles"]:
        out.append(f"{r['degenerate_triangles']} zero-area triangles")
    if r["support_needed_area_mm2"] > 1.0:
        out.append(
            f"{r['support_needed_area_mm2']} mm2 of unsupported faces below 30 deg (bed contact and "
            "bridges already excluded) — supports or a reorientation are in play"
        )
    if r["bridge_area_mm2"] > 1.0:
        ext = r.get("largest_bridge_extent_mm", {})
        span = max(ext.get("x", 0), ext.get("y", 0))
        out.append(f"{r['bridge_area_mm2']} mm2 of bridging, spanning up to ~{span} mm")
    if r["bed_contact_area_mm2"] < 100:
        out.append(
            f"only {r['bed_contact_area_mm2']} mm2 touching the plate — adhesion and warping risk"
        )
    if r["tipping_aspect_ratio"] and r["tipping_aspect_ratio"] > 4:
        out.append(
            f"aspect ratio {r['tipping_aspect_ratio']}:1 — tall and narrow, prone to ringing and knock-over"
        )
    dims = r["dims_mm"]
    if max(dims["x"], dims["y"]) > 325 or dims["z"] > 320:
        out.append("exceeds the H2D 325x320x325 single-nozzle envelope")
    nf = r.get("narrow_features") or {}
    lw, floor = nf.get("line_width_mm"), nf.get("two_wall_floor_mm")
    found = any((nf.get(k) or {}).get("pct_of_wall_area", 0) >= 1.0 for k in ("gap", "wall"))
    pitch = nf.get("layer_pitch_mm") or 0
    # Every narrow-feature number rests on the triangle normals meaning what STL
    # says they mean: outward, on one clean solid. An open or inconsistently
    # wound mesh breaks that, and so does a model assembled from overlapping
    # un-booleaned bodies -- interior facets the slicer would union away are read
    # here as the two sides of an impossibly thin rib. Reporting the figure
    # anyway, three lines under "MESH NOT WATERTIGHT", is how a measurement gets
    # quoted long after the caveat above it has scrolled away.
    if nf and not (r["watertight"] and r["winding_consistent"]):
        why = (
            f"{r['open_edges']} open edges"
            if not r["watertight"]
            else f"{r['flipped_edges']} edges traversed twice the same way, so some "
            "facet normals are inverted"
        )
        out.append(
            f"narrow-feature widths not reported ({why}): they assume outward normals "
            "on one clean solid — repair first, and use part-forge's mesh_audit.py to "
            "confirm body count and winding"
        )
        return out
    # A null result is only as good as the pitch that produced it. Detail living
    # in a thin z band on a tall part falls between planes and reports as a clean
    # sheet, which is the one failure direction that reads as good news.
    if nf and not found and pitch > 1.0:
        out.append(
            f"no narrow features seen, but cross-sections were sampled every {pitch} mm "
            f"— detail in a thinner z band than that would be missed; re-run with "
            "--narrow-layers raised before treating this as clean"
        )
    # The resolution verdict, before the per-feature detail: whether this nozzle
    # is the wrong tool for this model, and whether any nozzle is the right one.
    by_nozzle = nf.get("pct_failing_by_nozzle") or {}
    here = by_nozzle.get(f"{(lw or 0) / 1.05:.2f}")
    best = nf.get("smallest_resolvable_nozzle")
    if by_nozzle and here is not None and here >= RESOLVABLE_PCT:
        ladder = ", ".join(f"{n} mm -> {p}%" for n, p in sorted(by_nozzle.items()))
        if best is None:
            out.append(
                f"RESOLUTION: {here}% of wall area is finer than this nozzle can draw, and "
                f"no nozzle down to {min(by_nozzle, key=float)} mm clears "
                f"{nf['resolvable_threshold_pct']}% ({ladder}) — the detail is below what FDM "
                "resolves at this size. Scale the model up, or accept losing it; no setting "
                "recovers geometry the nozzle cannot draw"
            )
        else:
            out.append(
                f"RESOLUTION: {here}% of wall area is finer than this nozzle can draw. A "
                f"{best} mm nozzle brings it under {nf['resolvable_threshold_pct']}% ({ladder}) "
                "— but check its volumetric flow limit against the part's volume before "
                "committing, since a finer nozzle buys detail with time"
            )
    for kind, noun, fix in (
        # "groove wall", not "groove": both sides of a slot are probed, so the
        # figure is the wall area bounding the feature, about twice the area of
        # the feature itself. Naming it as the groove would overstate it 2x.
        ("gap", "groove/slot wall", "the ragged over-extruded rim in failure-modes.md"),
        ("wall", "rib/thin-wall surface", "dropped or crammed detail"),
    ):
        rec = nf.get(kind) or {}
        # Area in the failing band, not the minimum: a chamfered groove tapers
        # through zero and its min says nothing. And it must clear 1% of the
        # sampled wall area as well as an absolute floor -- every real part has
        # a few square millimetres of feather edge where a face runs out, and
        # flagging that as a defect is how a measurement loses its credibility.
        if rec.get("pct_of_wall_area", 0) < 1.0:
            continue
        total = nf.get("wall_area_mm2") or 1.0
        z = rec.get("z_range_mm")
        where = f", z {z[0]}–{z[1]} mm" if z else ""
        # The share is carried in the message because the absolute area cannot be
        # read without it. Under a few percent this is usually a face tapering out
        # to an edge, which is inherent to the shape and not a defect; a part whose
        # detail is genuinely too fine scores in the tens of percent.
        for key, band, consequence in (
            ("ragged_mm2", f"between {lw} and {floor} mm", f"too narrow for two walls, giving {fix}"),
            ("unresolvable_mm2", f"under {lw} mm", "below what this nozzle can draw at all"),
        ):
            v = rec.get(key, 0)
            if v > 1.0:
                out.append(
                    f"{v} mm2 of {noun} {band} wide ({100 * v / total:.1f}% of wall "
                    f"area{where}) — {consequence}"
                )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("models", nargs="+")
    ap.add_argument(
        "--pretty", action="store_true", help="human-readable summary instead of JSON"
    )
    ap.add_argument(
        "--line-width",
        type=float,
        default=0.42,
        help="outer wall line width the narrow-feature thresholds are judged "
        "against (default 0.42, the stock 0.4-nozzle value)",
    )
    ap.add_argument(
        "--narrow-layers",
        type=int,
        default=NARROW_MAX_LAYERS,
        help=f"cross-sections to sample for narrow features (default {NARROW_MAX_LAYERS}); "
        "raise it when fine detail sits in a thin z band",
    )
    args = ap.parse_args()

    results = {}
    for m in args.models:
        path = Path(m).expanduser()
        if not path.is_file():
            print(f"error: no such file: {path}", file=sys.stderr)
            sys.exit(1)
        loader = LOADERS.get(path.suffix.lower())
        if loader is None:
            print(
                f"error: unsupported format {path.suffix!r} (want .stl/.3mf/.obj)",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            results[str(path)] = analyze(
                loader(path), args.line_width, args.narrow_layers
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)

    if not args.pretty:
        print(json.dumps(results, indent=2))
        return

    for name, r in results.items():
        d = r["dims_mm"]
        print(f"\n{name}")
        print(
            f"  {d['x']} x {d['y']} x {d['z']} mm   {r['volume_cm3']} cm3   {r['triangles']} tris"
        )
        print(
            f"  bed contact {r['bed_contact_area_mm2']} mm2   aspect {r['tipping_aspect_ratio']}:1"
        )
        shown = [
            (k, b) for k, b in r["overhang_by_slope"].items() if b["area_mm2"] > 0.01
        ]
        if shown:
            print("  downward faces by slope from horizontal:")
            for key, band in shown:
                print(
                    f"    {key:<20} {band['area_mm2']:>9} mm2  ({band['pct_of_downward']}%)  {band['meaning']}"
                )
        else:
            print(
                "  downward faces: all bed contact — nothing overhanging in this orientation"
            )
        for f in r["flags"] or ["no geometry concerns detected"]:
            print(f"  ! {f}")


if __name__ == "__main__":
    main()

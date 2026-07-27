#!/usr/bin/env python3
"""Headless solid audit for 3D-printable parts. No Blender required.

Why this exists
---------------
Authoring a part needs Blender. *Verifying* it must not — otherwise every check
is hostage to a GUI session, and a mesh can only be trusted on the machine that
made it. This script re-derives the acceptance evidence from the exported file
alone, which is the artifact the slicer will actually read.

Dependency tiers (each degrades cleanly to the one below)
---------------------------------------------------------
  Tier 0  stdlib only        STL parse, positional weld, manifold/Euler/winding,
                             per-body signed volume, bbox, vertex digest.
  Tier 1  + trimesh          mass properties, centre of mass, inertia, convex-hull
                             ratio, ray-cast wall thickness, overhang area,
                             non-STL formats (OBJ/PLY/3MF/GLB).
  Tier 2  + pymeshlab        repair and Hausdorff comparison -> see mesh_repair.py
  Tier 3  + pyvista          section plots and offscreen renders -> mesh_render.py

Tier 0 is deliberately dependency-free and re-implements the checks rather than
delegating: an independent implementation catches bugs a shared one hides.

Usage
-----
    mesh_audit.py PART.stl
    mesh_audit.py PART.stl --json report.json --gate
    mesh_audit.py PART.stl --expect-file expect.json --gate
    mesh_audit.py A.stl --compare B.stl        # determinism / variant delta

Exit codes
----------
    0  audit ran; no faults (or --gate not given)
    1  --gate given and at least one fault or failed expectation
    2  could not read the input

The gate is positional: faults are collected, printed, and *then* decide the exit
code. A partial report of a bad mesh is more useful than an exception.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from collections import defaultdict

# ===========================================================================
#  TIER 0 - mesh reading (stdlib only)
# ===========================================================================

def read_stl(path):
    """Return a list of (v0, v1, v2) float triples. Handles binary and ASCII STL.

    Binary detection does not trust the 80-byte header text: some exporters write
    "solid ..." into it. The length check is authoritative.
    """
    with open(path, "rb") as fh:
        blob = fh.read()
    if len(blob) < 84:
        raise ValueError(f"{path}: too short to be an STL ({len(blob)} bytes)")

    n_declared = struct.unpack_from("<I", blob, 80)[0]
    if 84 + n_declared * 50 == len(blob):
        return _read_stl_binary(blob, n_declared)

    head = blob[:512].lstrip().lower()
    if head.startswith(b"solid"):
        return _read_stl_ascii(blob)

    # Trailing junk after a valid binary payload is common; accept it.
    if 84 + n_declared * 50 <= len(blob):
        return _read_stl_binary(blob, n_declared)
    raise ValueError(f"{path}: not a recognisable binary or ASCII STL")


def _read_stl_binary(blob, count):
    tris = []
    off = 84
    unpack = struct.Struct("<12fH").unpack_from
    for _ in range(count):
        f = unpack(blob, off)
        tris.append(((f[3], f[4], f[5]), (f[6], f[7], f[8]), (f[9], f[10], f[11])))
        off += 50
    return tris


def _read_stl_ascii(blob):
    tris, cur = [], []
    for line in blob.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] == "vertex":
            cur.append((float(parts[1]), float(parts[2]), float(parts[3])))
            if len(cur) == 3:
                tris.append(tuple(cur))
                cur = []
    return tris


def load_triangles(path):
    """Read any supported mesh into (triangles, loader_name).

    STL goes through the stdlib reader so Tier 0 stays dependency-free. Anything
    else needs trimesh.
    """
    if path.lower().endswith(".stl"):
        return read_stl(path), "stdlib"
    mesh = _trimesh_load(path)
    if mesh is None:
        raise ValueError(f"{path}: non-STL input requires trimesh (pip install trimesh)")
    return [tuple(map(tuple, t)) for t in mesh.triangles], "trimesh"


# ===========================================================================
#  TIER 0 - positional weld and the determinism digest
# ===========================================================================

def weld(tris, tol):
    """Collapse coincident vertices onto a grid of size `tol`.

    Returns (verts, faces, exact_verts, boundary_risk).

    `verts` are the snapped grid positions, which is what the reproducibility
    digest must hash: two runs that place a vertex 1e-9 mm apart have produced the
    same solid and must produce the same digest.

    `exact_verts` are the original coordinates of the first vertex seen in each
    cell. Volume and other metric quantities are computed from *these*, because
    snapping to a 1e-4 mm grid moves every vertex by up to 5e-5 mm, and integrated
    over a surface of ten thousand square millimetres that is a tenth of a cubic
    millimetre of spurious volume error - small, but systematic, and large enough
    to look like a real discrepancy when reconciling against a generator.

    `boundary_risk` counts coordinates sitting near a *rounding* boundary, i.e.
    where the scaled value is close to n + 0.5 and an insignificant perturbation
    would send it to the neighbouring cell. Two points closer than `tol` can then
    still land in different cells. A coordinate landing exactly on a grid multiple
    is the safest case, not the riskiest. If this count is non-zero, treat the
    unique-vertex count as approximate and re-run with a different `--weld`.
    """
    inv = 1.0 / tol
    index, verts, exact, faces = {}, [], [], []
    risk = 0
    band = 0.05  # how close to the .5 rounding boundary counts as at risk
    for tri in tris:
        ids = []
        for co in tri:
            key = []
            for c in co:
                scaled = c * inv
                key.append(int(math.floor(scaled + 0.5)))
                if abs(scaled - math.floor(scaled) - 0.5) < band:
                    risk += 1
            key = tuple(key)
            vid = index.get(key)
            if vid is None:
                vid = len(verts)
                index[key] = vid
                verts.append(tuple(k * tol for k in key))
                exact.append(tuple(co))
            ids.append(vid)
        faces.append(tuple(ids))
    return verts, faces, exact, risk


def vertex_digest(verts, places=4):
    """md5 over the *set* of welded vertices, order-independent.

    Re-running an unedited generator reproduces the same solid but not the same
    STL bytes: triangle emission order varies, and the diagonal chosen on a
    planar quad can flip. Hashing the sorted unique vertex set is therefore the
    only reproducibility claim worth making about a mesh. `md5` of the file is
    noise.

    The digest is self-consistent, not interoperable. It is defined over the
    snapped grid positions at `places` decimals, so it is comparable across runs
    of *this* tool at the same `--weld` and `--digest-places`, and it will not
    match a digest produced by a generator that hashes its own representative
    coordinates at a different precision. That is fine for the question being
    asked - "did my edit change the solid" - and it is worth knowing before
    someone tries to reconcile two digests that were never meant to agree.
    """
    fmt = "%%.%df" % places
    rows = sorted(",".join(fmt % c for c in v) for v in verts)
    h = hashlib.md5()
    for row in rows:
        h.update(row.encode())
        h.update(b"\n")
    return h.hexdigest()


# ===========================================================================
#  TIER 0 - topology
# ===========================================================================

def require_triangles(faces, who):
    """Raise a diagnosable error if `faces` is not all triangles.

    This module is triangles-only throughout, because STL is a triangle format and
    everything here was written against it. Nothing said so. The failure it produced
    was `ValueError: too many values to unpack (expected 3)` from a tuple unpack
    several frames deep, which names neither the requirement nor the offending face.

    Worth keeping even after every in-repo caller triangulates first. The people who
    reach this module with polygons are the ones writing a stage-by-stage diagnostic
    -- that is, people already debugging something else, for whom an opaque unpack
    error inside the trusted auditor is the most expensive possible answer.
    """
    for i, f in enumerate(faces):
        if len(f) != 3:
            raise ValueError(
                f"{who}: needs triangles; face {i} has {len(f)} vertices. "
                f"Run part_kit.triangulate_and_purge first, or "
                f"bmesh.ops.triangulate(bm, faces=bm.faces) on a copy."
            )


def topology(verts, faces, metric_verts=None):
    """Manifold, winding, Euler, and connected-body analysis.

    Connectivity comes from the welded ids; every *measured* quantity - area,
    volume - comes from `metric_verts`, the unsnapped coordinates, so the grid
    weld cannot perturb a number that will be compared against a design value.

    Definitions used, stated so a disagreeing tool can be reconciled:
      open edge      undirected edge used by exactly one face -> a hole
      over edge      undirected edge used by three or more faces -> self-touch
      winding flip   a *directed* edge traversed twice; on a consistently wound
                     closed surface every directed edge occurs exactly once
      degenerate     a triangle with a repeated vertex id or zero area

    `faces` must be triangles. See `require_triangles`.
    """
    require_triangles(faces, "topology")
    mv = verts if metric_verts is None else metric_verts
    undirected = defaultdict(int)
    directed = defaultdict(int)
    degenerate = []
    for fi, (a, b, c) in enumerate(faces):
        if a == b or b == c or a == c:
            degenerate.append(fi)
            continue
        for u, v in ((a, b), (b, c), (c, a)):
            directed[(u, v)] += 1
            undirected[(u, v) if u < v else (v, u)] += 1

    open_edges = [e for e, n in undirected.items() if n == 1]
    over_edges = [e for e, n in undirected.items() if n > 2]
    flips = sum(n - 1 for n in directed.values() if n > 1)

    # zero-area triangles that are not caught by repeated ids
    zero_area = []
    for fi, (a, b, c) in enumerate(faces):
        if fi in set(degenerate):
            continue
        if _tri_area(mv[a], mv[b], mv[c]) <= 0.0:
            zero_area.append(fi)

    bodies = _connected_bodies(faces, len(verts))
    body_stats = []
    for face_ids in bodies:
        sub = [faces[i] for i in face_ids]
        vs = {v for f in sub for v in f}
        es = {(min(u, v), max(u, v)) for f in sub for u, v in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0]))}
        vol = sum(_signed_vol(mv[a], mv[b], mv[c]) for a, b, c in sub)
        body_stats.append({
            "faces": len(sub),
            "verts": len(vs),
            "edges": len(es),
            "euler": len(vs) - len(es) + len(sub),
            "signed_volume": vol,
        })
    body_stats.sort(key=lambda b: -abs(b["signed_volume"]))

    return {
        "verts": len(verts),
        "faces": len(faces),
        "edges": len(undirected),
        "open_edges": len(open_edges),
        "over_edges": len(over_edges),
        "winding_flips": flips,
        "degenerate_faces": len(degenerate) + len(zero_area),
        "degenerate_repeated_id": len(degenerate),
        "degenerate_zero_area": len(zero_area),
        "bodies": len(bodies),
        "euler": sum(b["euler"] for b in body_stats),
        # Genus counts handles: one per through-hole. A closed orientable surface
        # has euler = 2 - 2g per body, so this is information about the shape, not
        # a defect - a bracket with two bolt holes is legitimately genus 2.
        "genus": (2 * len(bodies) - sum(b["euler"] for b in body_stats)) // 2,
        "body_detail": body_stats,
        "volume": sum(b["signed_volume"] for b in body_stats),
        "inverted_bodies": sum(1 for b in body_stats if b["signed_volume"] < 0),
        "null_volume_bodies": sum(1 for b in body_stats if abs(b["signed_volume"]) < 1e-9),
    }


def _connected_bodies(faces, n_verts):
    """Group faces into connected components by shared welded vertices."""
    parent = list(range(n_verts))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b, c in faces:
        union(a, b)
        union(b, c)
    groups = defaultdict(list)
    for fi, f in enumerate(faces):
        groups[find(f[0])].append(fi)
    return list(groups.values())


def _tri_area(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def _signed_vol(a, b, c):
    """Signed volume of the tetrahedron (origin, a, b, c) -- sums to the solid."""
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    ) / 6.0


def bounds(tris):
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for tri in tris:
        for co in tri:
            for i in range(3):
                if co[i] < lo[i]:
                    lo[i] = co[i]
                if co[i] > hi[i]:
                    hi[i] = co[i]
    return {
        "min": lo,
        "max": hi,
        "dims": [hi[i] - lo[i] for i in range(3)],
    }


def edge_lengths(verts, faces):
    require_triangles(faces, "edge_lengths")
    seen = set()
    lo, hi, total, n = math.inf, 0.0, 0.0, 0
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            if key in seen:
                continue
            seen.add(key)
            p, q = verts[u], verts[v]
            d = math.dist(p, q)
            lo = min(lo, d)
            hi = max(hi, d)
            total += d
            n += 1
    return {"min": 0.0 if n == 0 else lo, "max": hi, "mean": total / n if n else 0.0}


# ===========================================================================
#  TIER 1 - trimesh enrichment
# ===========================================================================

def _trimesh_load(path):
    try:
        import trimesh
    except ImportError:
        return None
    mesh = trimesh.load(path, force="mesh", process=False)
    return mesh if hasattr(mesh, "faces") else None


def trimesh_report(path, wall_samples, build_axis, overhang_deg):
    """Mass properties, ray-cast wall thickness, and overhang area.

    Returns {"available": False, "reason": ...} when trimesh is missing, so the
    caller can proceed on Tier 0 evidence instead of failing.
    """
    try:
        import numpy as np
        import trimesh  # noqa: F401
    except ImportError as exc:
        return {"available": False, "reason": f"{exc.name} not installed"}

    mesh = _trimesh_load(path)
    if mesh is None:
        return {"available": False, "reason": "trimesh could not produce a mesh"}

    out = {
        "available": True,
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "volume_mm3": float(mesh.volume),
        "area_mm2": float(mesh.area),
        "center_mass": [float(v) for v in mesh.center_mass],
        "centroid": [float(v) for v in mesh.centroid],
        "euler_number": int(mesh.euler_number),
        "body_count": int(mesh.body_count),
    }

    try:
        hull_v = float(mesh.convex_hull.volume)
        out["convex_hull_volume_mm3"] = hull_v
        out["solidity"] = float(mesh.volume / hull_v) if hull_v else None
    except Exception as exc:  # hull can fail on pathological input
        out["convex_hull_error"] = repr(exc)

    try:
        out["inertia"] = [[float(x) for x in row] for row in mesh.moment_inertia]
        out["principal_inertia"] = [float(v) for v in mesh.principal_inertia_components]
    except Exception as exc:
        out["inertia_error"] = repr(exc)

    out["wall_thickness"] = _wall_thickness(mesh, np, wall_samples)
    out["overhang"] = _overhang(mesh, np, build_axis, overhang_deg)
    return out


def _wall_thickness(mesh, np, samples):
    """Estimate minimum wall by shooting a ray inward from each sampled face.

    From a face centroid, step just inside the surface and cast along the inward
    normal; the first hit is the opposing wall, so the hit distance is the local
    thickness. This measures *material* thickness, not clearance, because rays
    start inside the solid.

    Blind spots worth knowing: a ray fired down the middle of a fillet reads the
    chord, not the throat, and a thin feature whose two faces are not opposed
    (a knife edge) reads long. Treat the result as a screen that catches gross
    thin walls, not as a certificate. Two-sided callipers on the printed part
    remain the authority.
    """
    if samples <= 0:
        return {"available": False, "reason": "skipped by --wall-samples 0"}
    faces = len(mesh.faces)
    if faces == 0:
        return {"available": False, "reason": "no faces"}
    step = max(1, faces // samples)
    idx = np.arange(0, faces, step)
    normals = mesh.face_normals[idx]
    origins = mesh.triangles_center[idx] - normals * 1e-4

    method = "trimesh intersector"
    try:
        locs, ray_ids, _ = mesh.ray.intersects_location(
            ray_origins=origins, ray_directions=-normals, multiple_hits=False
        )
        dist = np.linalg.norm(locs - origins[ray_ids], axis=1)
    except (ImportError, ModuleNotFoundError, ValueError, AttributeError) as exc:
        # trimesh's intersectors want rtree or embree. Neither is worth an install
        # step for a check this important, so fall back to a vectorised
        # Moller-Trumbore sweep that needs nothing beyond numpy.
        method = f"numpy Moller-Trumbore fallback ({type(exc).__name__}: {exc})"
        dist, ray_ids = _mt_first_hit(np, mesh.triangles, origins, -normals)

    if dist.size == 0:
        return {"available": False, "reason": "no ray hits"}
    keep = dist > 1e-6
    dist, ray_ids = dist[keep], ray_ids[keep]
    if dist.size == 0:
        return {"available": False, "reason": "all ray hits degenerate"}

    k = int(np.argmin(dist))
    return {
        "available": True,
        "metric": "opposing_surface_chord",
        "min_mm": float(dist[k]),
        "at_point": [float(v) for v in origins[ray_ids[k]]],
        "p01_mm": float(np.percentile(dist, 1)),
        "p05_mm": float(np.percentile(dist, 5)),
        "p50_mm": float(np.median(dist)),
        "below": {str(b): int((dist < b).sum()) for b in (0.5, 1.0, 2.0, 3.0)},
        "samples": int(dist.size),
        "faces_total": faces,
        "method": "inward ray cast from face centroid, first hit; " + method,
        "caveat": (
            "This is the distance to the opposing surface, which equals wall "
            "thickness only where the two surfaces bound a wall. A ray fired "
            "across a relief groove, a chamfer, a notch, or any surface feature "
            "narrower than the wall reads the feature, not the wall - so the raw "
            "minimum is routinely far below the structural wall and is NOT a "
            "thin-wall finding on its own. Read the distribution: a structural "
            "problem moves p05 and p50, while a surface feature shows up only in "
            "the minimum. Confirm either way with a section render."
        ),
    }


def _mt_first_hit(np, triangles, origins, directions, chunk=48):
    """Vectorised Moller-Trumbore. Returns (distances, ray_indices) for rays that hit.

    Chunked over rays because the intermediate is (rays x triangles x 3): the
    whole set at once would allocate gigabytes on a mesh of any size.
    """
    v0 = triangles[:, 0]
    e1 = triangles[:, 1] - v0
    e2 = triangles[:, 2] - v0

    best = np.full(len(origins), np.inf)
    for i in range(0, len(origins), chunk):
        o = origins[i:i + chunk]
        d = directions[i:i + chunk]
        pv = np.cross(d[:, None, :], e2[None, :, :])
        det = np.einsum("fj,rfj->rf", e1, pv)
        live = np.abs(det) > 1e-12
        inv = np.where(live, 1.0 / np.where(live, det, 1.0), 0.0)
        tv = o[:, None, :] - v0[None, :, :]
        u = np.einsum("rfj,rfj->rf", tv, pv) * inv
        qv = np.cross(tv, e1[None, :, :])
        v = np.einsum("rj,rfj->rf", d, qv) * inv
        t = np.einsum("fj,rfj->rf", e2, qv) * inv
        hit = live & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1.0 + 1e-9) & (t > 1e-9)
        best[i:i + chunk] = np.where(hit, t, np.inf).min(axis=1)

    ray_ids = np.nonzero(np.isfinite(best))[0]
    return best[ray_ids], ray_ids


def _overhang(mesh, np, build_axis, threshold_deg):
    """Downward-facing area that a slicer would flag as unsupported.

    `tilt_deg` is the angle between a face normal and the *downward* build axis:
    0 deg is a flat ceiling (fully unsupported), 90 deg is a vertical wall
    (fully supported). A face counts as an overhang when
    `tilt_deg < threshold_deg`, so the default 45 flags anything shallower than a
    45 deg slope. Slicer UIs phrase the same threshold as "support angle"; the
    numbers agree, the wording does not.
    """
    axis = {"x": 0, "y": 1, "z": 2}[build_axis]
    down = np.zeros(3)
    down[axis] = -1.0

    normals = mesh.face_normals
    areas = mesh.area_faces
    cos = normals @ down
    tilt = np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))
    flagged = tilt < threshold_deg

    result = {
        "build_axis": build_axis,
        "threshold_deg": threshold_deg,
        "definition": "tilt_deg = angle(face normal, -build_axis); overhang when tilt_deg < threshold_deg",
        "area_mm2": float(areas[flagged].sum()),
        "faces": int(flagged.sum()),
        "total_area_mm2": float(areas.sum()),
    }
    if flagged.any():
        centres = mesh.triangles_center[flagged]
        result["lowest_overhang_at"] = [float(v) for v in centres[int(np.argmin(centres[:, axis]))]]
        result["min_tilt_deg"] = float(tilt[flagged].min())

    bed = [i for i in range(3) if i != axis]
    result["bed_footprint_mm"] = [
        float(mesh.bounds[1][bed[0]] - mesh.bounds[0][bed[0]]),
        float(mesh.bounds[1][bed[1]] - mesh.bounds[0][bed[1]]),
    ]
    result["height_mm"] = float(mesh.bounds[1][axis] - mesh.bounds[0][axis])
    return result


# ===========================================================================
#  ACCEPTANCE
# ===========================================================================

# Structural faults are unconditional: no printable solid is exempt from these.
STRUCTURAL_GATES = (
    ("open_edges", 0, "holes in the surface -- the slicer has no inside to fill"),
    ("over_edges", 0, "edge shared by 3+ faces -- self-intersecting or coincident shells"),
    ("winding_flips", 0, "inconsistent face winding -- inside and outside are ambiguous"),
    ("degenerate_faces", 0, "zero-area or repeated-vertex triangles"),
    ("null_volume_bodies", 0, "a body enclosing no volume"),
)
# `inverted_bodies` is deliberately NOT in this list. A negative-volume shell is a
# cavity, which is a defect only when the caller did not ask for one -- see the body
# model on `acceptance`.


def acceptance(report, expect, allow_multi_body=False, *,
               expect_solids=None, expect_cavities=0):
    """Collect faults. Returns a list of {check, got, want, why} dicts.

    The body model, stated once because three separate gates read from it. A
    printable artifact is some number of **solids** -- closed shells with positive
    signed volume -- any of which may contain **cavities**, closed shells with
    negative signed volume that subtract from the material. So:

        bodies          = solids + cavities
        inverted_bodies = cavities

    Three shapes are legitimate and the gate must be able to tell them apart: a
    solid (1, 0), a plate of N coupons (N, 0), and a vessel with K sealed cavities
    (1, K).

    `expect_solids=None` leaves the count ungated, which is exactly what
    `allow_multi_body=True` has always meant and remains its translation. Declaring a
    number is strictly stronger than permitting any number: it catches a plug fused
    to its socket, which *lowers* the count, as readily as debris, which raises it.

    `expect_cavities` defaults to 0, so an ordinary part gates precisely as before.
    It exists because a correct vessel reports `inverted_bodies == 1`, and the old
    unconditional `inverted_bodies == 0` rejected it as "the solid is inside out" --
    while passing that same vessel once `clean_mesh` had flipped the cavity outward
    and quietly made it solid. The gate preferred the corrupted artifact to the sound
    one, which is the precise inversion this plugin exists to prevent.
    """
    faults = []
    topo = report["topology"]

    for key, want, why in STRUCTURAL_GATES:
        got = topo.get(key)
        if got != want:
            faults.append({"check": key, "got": got, "want": want, "why": why})

    n_bodies = topo["bodies"]
    n_cavities = topo["inverted_bodies"]
    n_solids = n_bodies - n_cavities

    if n_cavities != expect_cavities:
        faults.append({
            "check": "inverted_bodies", "got": n_cavities, "want": expect_cavities,
            "why": "a shell with negative signed volume is a cavity. With "
                   "expect_cavities=0 this means the solid is inside out; declare "
                   "--expect-cavities K for a vessel that should have K of them",
        })

    if expect_solids is not None:
        if n_solids != expect_solids:
            faults.append({
                "check": "solids", "got": n_solids, "want": expect_solids,
                "why": "positive-volume shells, cavities excluded. Too many means "
                       "debris or a part that failed to fuse; too few means two "
                       "parts fused into one",
            })
    elif not allow_multi_body and n_solids != 1:
        faults.append({
            "check": "bodies", "got": n_bodies, "want": 1,
            "why": "stray shells print as debris; pass --allow-multi-body, or "
                   "--expect-solids N for a plate of N coupons",
        })

    # Total signed volume was implied by the old unconditional inverted_bodies gate
    # and has to be asserted directly now that cavities are legal: a cavity larger
    # than the shell containing it is arithmetic, not geometry.
    if topo["volume"] <= 0.0:
        faults.append({
            "check": "volume_sign", "got": round(topo["volume"], 6), "want": "> 0",
            "why": "total signed volume is zero or negative -- the part encloses no "
                   "material, or a cavity exceeds the solid around it",
        })

    # Euler is NOT gated at 2. A through-hole adds a handle, so a plate with two
    # bolt holes is genus 2 and has euler = -2 by correct arithmetic. Gating at 2
    # would reject most real brackets - a gate that fails a sound part is exactly
    # as useless as one that passes a broken one.
    #
    # What *is* invariant for a closed orientable surface: euler = 2 - 2g per
    # body, so the total must be even and can never exceed 2 per body. Violating
    # either means the surface is not closed and orientable, whatever the edge
    # counts happened to say.
    n_bodies = topo["bodies"]
    euler = topo["euler"]
    if euler % 2 != 0:
        faults.append({
            "check": "euler_parity", "got": euler, "want": "even",
            "why": "a closed orientable surface has euler = 2 - 2g, always even; "
                   "an odd value means the surface is torn or non-orientable",
        })
    if euler > 2 * n_bodies:
        faults.append({
            "check": "euler_bound", "got": euler, "want": f"<= {2 * n_bodies}",
            "why": f"euler above 2 per body implies negative genus, which no "
                   f"closed surface has; the {n_bodies}-body count or the "
                   f"connectivity is wrong",
        })

    # Genus itself is reported, not gated, unless the caller declares what it
    # should be. Declaring it is worth doing: it counts through-holes, so an
    # expected genus catches a boolean that silently failed to punch one.
    if expect and "topology.genus" not in expect and "genus" in expect:
        expect = dict(expect)
        expect["topology.genus"] = expect.pop("genus")

    for name, spec in (expect or {}).items():
        faults.extend(_check_expectation(report, name, spec))
    return faults


def _check_expectation(report, name, spec):
    """Compare one dotted path in the report against an expectation."""
    got = _dig(report, name)
    if got is None:
        return [{"check": name, "got": None, "want": spec, "why": "path absent from report"}]

    if isinstance(spec, dict):
        want, tol = spec.get("value"), spec.get("tol", 0.0)
    else:
        want, tol = spec, 0.0

    if isinstance(want, bool) or isinstance(got, bool):
        ok = bool(got) == bool(want)
    elif isinstance(want, (list, tuple)):
        ok = len(got) == len(want) and all(abs(g - w) <= tol for g, w in zip(got, want))
    elif isinstance(want, (int, float)):
        ok = abs(got - want) <= tol
    else:
        ok = got == want

    if ok:
        return []
    return [{"check": name, "got": got, "want": want, "tol": tol,
             "why": "expectation from the parameter table did not hold"}]


def _dig(obj, dotted):
    for part in dotted.split("."):
        if isinstance(obj, dict):
            if part not in obj:
                return None
            obj = obj[part]
        elif isinstance(obj, (list, tuple)):
            try:
                obj = obj[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return obj


# ===========================================================================
#  REPORTING
# ===========================================================================

def audit(path, weld_tol, wall_samples, build_axis, overhang_deg, digest_places):
    tris, loader = load_triangles(path)
    verts, faces, exact, risk = weld(tris, weld_tol)
    return {
        "file": os.path.abspath(path),
        "bytes": os.path.getsize(path),
        "loader": loader,
        "triangles_raw": len(tris),
        "weld_tol": weld_tol,
        "weld_boundary_risk": risk,
        "vertex_digest": vertex_digest(verts, digest_places),
        "digest_places": digest_places,
        "topology": topology(verts, faces, metric_verts=exact),
        "bounds": bounds(tris),
        "edge_length": edge_lengths(exact, faces),
        "trimesh": trimesh_report(path, wall_samples, build_axis, overhang_deg),
    }


def render_text(report, faults):
    topo, tm = report["topology"], report["trimesh"]
    L = []
    add = L.append
    add(f"  file            {report['file']}")
    add(f"  triangles       {report['triangles_raw']}  ->  {topo['verts']} welded verts @ {report['weld_tol']} mm")
    add(f"  vertex digest   {report['vertex_digest']}   (compare this, never the file md5)")
    add(f"  bodies / euler  {topo['bodies']} / {topo['euler']}"
        f"   genus {topo['genus']}  ({topo['genus']} through-hole(s); pass --genus N to gate it)")
    add(f"  volume          {topo['volume']:.4f} mm^3")
    add("  dims (x,y,z)    " + " x ".join(f"{d:.3f}" for d in report["bounds"]["dims"]) + " mm")
    add(f"  edge length     min {report['edge_length']['min']:.5f}   max {report['edge_length']['max']:.3f} mm")
    add(f"  open / over     {topo['open_edges']} / {topo['over_edges']}")
    add(f"  winding flips   {topo['winding_flips']}")
    add(f"  degenerate      {topo['degenerate_faces']}")
    if report["weld_boundary_risk"]:
        add(f"  weld risk       {report['weld_boundary_risk']} coords near a grid boundary -- re-run with a different --weld to confirm counts")

    if tm.get("available"):
        add(f"  solidity        {tm.get('solidity', float('nan')):.4f}  (volume / convex hull)")
        add("  centre of mass  " + ", ".join(f"{v:.3f}" for v in tm["center_mass"]))
        wall = tm.get("wall_thickness", {})
        if wall.get("available"):
            b = wall["below"]
            add(f"  opposing chord  min {wall['min_mm']:.3f}   p05 {wall['p05_mm']:.3f}   "
                f"p50 {wall['p50_mm']:.3f} mm   ({wall['samples']} rays)")
            add(f"                  under 0.5/1/2/3 mm: {b['0.5']}/{b['1.0']}/{b['2.0']}/{b['3.0']} rays")
            add("                  NOT wall thickness where a groove, chamfer or notch is")
            add("                  narrower than the wall -- judge by p05/p50, confirm by section")
        else:
            add(f"  opposing chord  unavailable -- {wall.get('reason')}")
        oh = tm.get("overhang", {})
        add(f"  overhang        {oh['area_mm2']:.2f} mm^2 below {oh['threshold_deg']} deg tilt, build axis {oh['build_axis'].upper()}")
        add(f"  bed / height    {oh['bed_footprint_mm'][0]:.2f} x {oh['bed_footprint_mm'][1]:.2f} mm, {oh['height_mm']:.2f} mm tall")
    else:
        add(f"  tier 1          skipped -- {tm.get('reason')}  (pip install trimesh)")

    add("")
    if faults:
        add(f"  FAULTS ({len(faults)})")
        for f in faults:
            want = f.get("want")
            tol = f" +/- {f['tol']}" if f.get("tol") else ""
            add(f"    x {f['check']}: got {f['got']}, want {want}{tol}")
            add(f"      {f['why']}")
    else:
        add("  ACCEPTED - no faults")
    return "\n".join(L)


def compare(a, b):
    """Determinism / variant delta between two audits."""
    same = a["vertex_digest"] == b["vertex_digest"]
    va, vb = a["topology"]["volume"], b["topology"]["volume"]
    return {
        "vertex_digest_match": same,
        "verdict": (
            "identical solid (same vertex set)" if same
            else "different solid -- expected if a parameter changed, a defect if not"
        ),
        "a": {"file": a["file"], "digest": a["vertex_digest"], "volume": va,
              "verts": a["topology"]["verts"], "dims": a["bounds"]["dims"]},
        "b": {"file": b["file"], "digest": b["vertex_digest"], "volume": vb,
              "verts": b["topology"]["verts"], "dims": b["bounds"]["dims"]},
        "volume_delta_mm3": vb - va,
        "volume_delta_pct": (100.0 * (vb - va) / va) if va else None,
        "vert_delta": b["topology"]["verts"] - a["topology"]["verts"],
        "dim_delta_mm": [y - x for x, y in zip(a["bounds"]["dims"], b["bounds"]["dims"])],
    }


# ===========================================================================
#  CLI
# ===========================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Headless solid audit for 3D-printable parts (no Blender required).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Tier 0 needs only the standard library. Install trimesh for mass\n"
               "properties, wall thickness, overhang area, and non-STL formats.",
    )
    ap.add_argument("mesh", help="path to STL (or any trimesh-readable mesh)")
    ap.add_argument("--compare", metavar="OTHER", help="second mesh: report the delta and whether the solid is identical")
    ap.add_argument("--json", metavar="OUT", help="write the full report as JSON")
    ap.add_argument("--expect-file", metavar="JSON", help='expectations, e.g. {"topology.volume": {"value": 32953.0, "tol": 1.0}}')
    ap.add_argument("--expect", action="append", default=[], metavar="PATH=VAL[~TOL]",
                    help="inline expectation, repeatable: --expect topology.volume=32953~1.0")
    ap.add_argument("--gate", action="store_true", help="exit 1 if any fault or failed expectation")
    ap.add_argument("--allow-multi-body", action="store_true", help="do not fault on more than one shell")
    ap.add_argument("--expect-solids", type=int, default=None, metavar="N",
                    help="assert exactly N positive-volume shells, cavities "
                         "excluded. Stronger than --allow-multi-body: it also "
                         "catches two parts fused into one, which lowers the count")
    ap.add_argument("--expect-cavities", type=int, default=0, metavar="K",
                    help="number of sealed internal cavities the part should have "
                         "(default 0). A cavity is a shell with negative signed "
                         "volume; a vessel has one and is not inside out")
    ap.add_argument("--genus", type=int, default=None, metavar="N",
                    help="assert the number of through-holes (handles). Genus is "
                         "reported either way; gating it catches a boolean that "
                         "silently failed to punch a hole")
    ap.add_argument("--weld", type=float, default=1e-4, metavar="MM", help="positional weld tolerance (default 1e-4)")
    ap.add_argument("--digest-places", type=int, default=4, metavar="N", help="decimal places in the vertex digest (default 4)")
    ap.add_argument("--wall-samples", type=int, default=2000, metavar="N", help="rays for the wall-thickness screen (default 2000, 0 to skip)")
    ap.add_argument("--build-axis", choices=("x", "y", "z"), default="z", help="print build direction (default z)")
    ap.add_argument("--overhang-deg", type=float, default=45.0, metavar="DEG", help="overhang tilt threshold (default 45)")
    ap.add_argument("--quiet", action="store_true", help="suppress the text report")
    args = ap.parse_args(argv)

    try:
        report = audit(args.mesh, args.weld, args.wall_samples, args.build_axis,
                       args.overhang_deg, args.digest_places)
    except (OSError, ValueError) as exc:
        print(f"mesh_audit: {exc}", file=sys.stderr)
        return 2

    expect = {}
    if args.expect_file:
        try:
            with open(args.expect_file) as fh:
                expect.update(json.load(fh))
        except (OSError, ValueError) as exc:
            print(f"mesh_audit: --expect-file: {exc}", file=sys.stderr)
            return 2
    for item in args.expect:
        try:
            path, rhs = item.split("=", 1)
            val, _, tol = rhs.partition("~")
            expect[path] = {"value": _coerce(val), "tol": float(tol) if tol else 0.0}
        except ValueError:
            print(f"mesh_audit: bad --expect {item!r}; want PATH=VAL[~TOL]", file=sys.stderr)
            return 2

    if args.genus is not None:
        expect["topology.genus"] = {"value": args.genus, "tol": 0}

    faults = acceptance(report, expect, args.allow_multi_body,
                        expect_solids=args.expect_solids,
                        expect_cavities=args.expect_cavities)
    report["expect"] = expect
    report["faults"] = faults
    report["accepted"] = not faults

    if args.compare:
        try:
            other = audit(args.compare, args.weld, args.wall_samples, args.build_axis,
                          args.overhang_deg, args.digest_places)
        except (OSError, ValueError) as exc:
            print(f"mesh_audit: --compare: {exc}", file=sys.stderr)
            return 2
        report["comparison"] = compare(report, other)

    if not args.quiet:
        print(render_text(report, faults))
        if "comparison" in report:
            c = report["comparison"]
            print(f"\n  COMPARE vs {other['file']}")
            print(f"    digest match  {c['vertex_digest_match']}  -- {c['verdict']}")
            print(f"    volume delta  {c['volume_delta_mm3']:+.4f} mm^3 ({c['volume_delta_pct']:+.3f}%)")
            print(f"    vert delta    {c['vert_delta']:+d}")
            print("    dim delta     " + ", ".join(f"{d:+.4f}" for d in c["dim_delta_mm"]) + " mm")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=2, sort_keys=False)
        if not args.quiet:
            print(f"\n  report -> {args.json}")

    return 1 if (args.gate and faults) else 0


def _coerce(text):
    low = text.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    if "," in text:
        return [float(p) for p in text.split(",")]
    try:
        return float(text)
    except ValueError:
        return text


if __name__ == "__main__":
    sys.exit(main())

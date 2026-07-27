#!/usr/bin/env python3
"""gate-coupon-dish_gen.py -- a shelled vessel, built to be a regression fixture.

Run inside Blender (>= 4.2; developed against 5.2 LTS):

    blender --background --python-exit-code 1 --python gate-coupon-dish_gen.py
    # --python-exit-code is not optional: without it Blender returns 0 even when
    # this script raises, so a failed build looks like a success to the caller.

Output goes to this file's own directory unless DISH_OUT_DIR is set. Set it before
any experiment: a build that fails its own acceptance deletes the file at that path,
so a partially-failing regeneration DESTROYS the committed fixture rather than
merely overwriting it.

WHY THIS PART EXISTS
--------------------
`projects/shade-bar-mount/` is a solid. Every hollow-geometry defect this harness has
actually shipped -- the cavity `clean_mesh` turned inside out, the gate that rejected a
correct vessel as "inside out", the in-plane inset that leaves `wall * cos(alpha)` -- is
invisible on a solid part, and was therefore invisible to this repository's entire
regression net. This is the vessel that makes them visible.

It is a real dish and it prints, but its FEATURES were chosen for coverage, and
`FACTS.md` says so plainly rather than dressing them up as measured requirements.
Four properties are load-bearing; each catches a different failure if it moves:

  the 45-degree rim   a naive in-plane inset leaves 1.414 mm of a 2.000 mm wall
                      here. On a vertical wall cos(0) = 1 and the two constructions
                      are identical -- exactly how the defect stayed hidden until it
                      met a dome.
  the 6 mm floor      against a 2 mm wall. Letting the floor default to the wall
                      inset was a second, independent defect in the same function.
  the drain slot      an APERTURE: the specification is the opening, not the material
                      beside it. Measured by casting a raster through it, which
                      returns None when it was never cut.
  the sealed void     a shell with negative signed volume. A correct vessel reports
                      one, and the gate used to call that "inside out" while passing
                      the same part once its cavity had been flipped solid.

The void must be SEALED and separate from the bowl. An aperture that reaches a
cavity merges it into the outer shell -- one body, no negative volume -- so a vessel
with only an open bowl cannot exercise the cavity count at all. Hence two hollow
features.

Coordinate system
-----------------
    origin  centre of the base, on the bed
    +Z      up.  All material sits at Z >= 0.  Units: 1 Blender unit = 1 mm.
"""

import math
import os
import sys

import bmesh
import bpy  # noqa: F401  (imported so the failure outside Blender is legible)


def _load_part_kit():
    """Import the shipped kit from this file's own location, not the cwd."""
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.environ.get("PART_FORGE_SCRIPTS") or os.path.normpath(
        os.path.join(here, "..", "..", "plugins", "part-forge", "scripts"))
    if cand not in sys.path:
        sys.path.insert(0, cand)
    import part_kit
    return part_kit


pk = _load_part_kit()

# ---------------------------------------------------------------------------
# PARAMETERS -- everything below is derived from these.
# ---------------------------------------------------------------------------

PART_NAME = "GateCouponDish"

R_BASE = 30.0     # outer radius through the pedestal, mm
R_RIM = 42.0      # outer radius at the lip, mm
H_TOTAL = 18.0    # overall height, mm
Z_FLARE = 6.0     # where the wall stops being vertical, mm

WALL = 2.0        # bowl wall, measured PERPENDICULAR to the surface, mm
FLOOR_T = 6.0     # material under the bowl, mm.  Deliberately != WALL.

SLOT_W = 4.0      # drain slot width, mm -- the aperture that must be measured
SLOT_L = 12.0     # drain slot length, mm

VOID_R = 18.0     # radius to the sealed void's centre, mm
VOID_W = 6.0      # sealed void footprint, mm
VOID_H = 2.0      # sealed void height, mm
VOID_Z = 2.0      # its floor, mm.  Inside the pedestal: 0 < 2 and 4 < FLOOR_T.

SEG_RING = 96     # ring segments
SEG_LOFT = 24     # loft steps

#: (R_RIM - R_BASE) / (H_TOTAL - Z_FLARE) = 12/12, so the rim is at exactly 45
#: degrees.  Asserted in the acceptance list rather than trusted here.
RIM_SLOPE = (R_RIM - R_BASE) / (H_TOTAL - Z_FLARE)


def outer_radius(z):
    """The silhouette: a vertical pedestal, then a 45-degree flare."""
    if z <= Z_FLARE:
        return R_BASE
    return R_BASE + (z - Z_FLARE) * RIM_SLOPE


def ring_at(z, n=SEG_RING):
    r = outer_radius(z)
    return [(r * math.cos(2.0 * math.pi * i / n), r * math.sin(2.0 * math.pi * i / n))
            for i in range(n)]


def outer_rings():
    """Ring stack for the loft, with the profile's own breakpoint sampled exactly.

    Z_FLARE is added explicitly rather than left to the even steps. An even step
    can walk straight over a silhouette breakpoint, and the resulting dimension
    error reads as a real defect while being a sampling artifact -- which then gets
    "fixed" by loosening the tolerance that would have caught a real one.
    """
    zs = {H_TOTAL * i / SEG_LOFT for i in range(SEG_LOFT + 1)}
    zs.add(Z_FLARE)
    ordered = sorted(zs)
    return [ring_at(z) for z in ordered], ordered


def box(name, w, d, h, at):
    cx, cy, cz = at
    pts = [(cx - w / 2.0, cy - d / 2.0), (cx + w / 2.0, cy - d / 2.0),
           (cx + w / 2.0, cy + d / 2.0), (cx - w / 2.0, cy + d / 2.0)]
    return pk.prism(name, pts, lambda u, v: (u, v, cz), (0.0, 0.0, h))


def build():
    pk.scene_setup()
    pk.purge(PART_NAME, "cavity", "slot", "void")

    rings, zs = outer_rings()
    obj = pk.loft_solid(PART_NAME, rings, lambda i, u, v: (u, v, zs[i]))

    # The bowl. offset_rings insets PERPENDICULAR to the surface, so on the
    # 45-degree rim the horizontal inset is WALL*sqrt(2) and not WALL.
    cav_rings, cav_zs = pk.offset_rings(rings, zs, WALL, floor=FLOOR_T,
                                        ceiling=H_TOTAL)
    # Carry the top ring above the lip so the DIFFERENCE opens the bowl instead of
    # leaving a zero-thickness membrane exactly at z = H_TOTAL.
    cav_rings = cav_rings + [cav_rings[-1]]
    cav_zs = cav_zs + [H_TOTAL + 4.0]
    cavity = pk.loft_solid("cavity", cav_rings, lambda i, u, v: (u, v, cav_zs[i]))
    pk.boolean(obj, cavity, "DIFFERENCE", solver="EXACT")
    pk.weld_verts(obj)

    # The drain slot: through the floor, on the axis, clear of the sealed void.
    slot = box("slot", SLOT_W, SLOT_L, FLOOR_T + 4.0, (0.0, 0.0, -2.0))
    pk.boolean(obj, slot, "DIFFERENCE", solver="EXACT")
    pk.weld_verts(obj)

    # The sealed void: wholly inside the pedestal, opening onto nothing.
    void = box("void", VOID_W, VOID_W, VOID_H, (VOID_R, 0.0, VOID_Z))
    pk.boolean(obj, void, "DIFFERENCE", solver="EXACT")

    # Deliberately NOT recalc_normals=True. That call is what turns this part
    # solid, and `cavities` in the acceptance list is what proves it did not.
    pk.clean_mesh(obj)
    return obj


def mesh_triangles(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    out = [tuple(tuple(v.co) for v in f.verts) for f in bm.faces]
    bm.free()
    return out


def verify(obj):
    """Measure the part. Every number here comes off the mesh, not the table."""
    stats = pk.triangulate_and_purge(obj, expect_components=2)
    topo = pk.positional_topology(mesh_triangles(obj))
    a = pk.Acceptance(PART_NAME)

    a.exact("solids", topo["bodies"] - topo["inverted_bodies"], 1,
            "one printed shell")
    a.exact("cavities", topo["inverted_bodies"], 1,
            "the sealed void. A zero here means the cavity was flipped outward and "
            "the part is now solid -- the failure this fixture exists to catch")
    a.exact("open_edges", topo["open_edges"], 0)
    a.exact("over_edges", topo["over_edges"], 0)
    a.exact("winding_flips", topo["winding_flips"], 0)
    a.exact("degenerate_faces", topo["degenerate_faces"], 0)
    a.exact("genus", topo["genus"], 1,
            "the drain slot puts one handle through the dish. NOT the hole count: "
            "the sealed void adds none and a bowl open at the top adds none")
    a.at_least("volume", topo["volume"], 1.0)

    a.tight("rim_slope_is_45deg", RIM_SLOPE, 1.0,
            "the point of the rim: at 45 degrees a naive in-plane inset leaves "
            "wall*cos(45), a 29% error rather than the 2% a near-vertical wall hides")

    with pk.Probe(obj) as probe:
        # Wall on the sloped rim, cast along the TRUE surface normal. A radial cast
        # measures a longer chord and under-reports the very defect this checks.
        z_mid = (Z_FLARE + H_TOTAL) / 2.0
        r_mid = outer_radius(z_mid)
        hyp = math.hypot(1.0, RIM_SLOPE)
        n_r, n_z = -1.0 / hyp, RIM_SLOPE / hyp    # inward and downward along the wall
        worst = None
        for k in range(24):
            th = 2.0 * math.pi * k / 24
            p = (r_mid * math.cos(th), r_mid * math.sin(th), z_mid)
            d = (n_r * math.cos(th), n_r * math.sin(th), n_z)
            t = probe.thickness_at(p, d)
            if t is not None and (worst is None or t < worst):
                worst = t
        a.within("rim_wall_perpendicular", worst if worst is not None else -1.0,
                 WALL, 0.06,
                 "worst of 24 stations along the surface normal. An in-plane inset "
                 "would read 1.414 mm here")

        # Floor: from inside the bowl, straight down, well clear of the slot.
        floor_t = probe.thickness_at((12.0, 0.0, FLOOR_T), (0.0, 0.0, -1.0))
        a.within("floor_thickness", floor_t if floor_t is not None else -1.0,
                 FLOOR_T, 0.02,
                 "the floor is not the wall; defaulting it to the wall inset was a "
                 "defect in its own right")

        # The aperture, measured by what passes THROUGH it rather than by the mesh
        # beside it. Returns None if the slot never opened, which fails a gate.
        band = probe.raster((0.0, 0.0, H_TOTAL + 6.0), (0.0, 0.0, -1.0),
                            (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                            SLOT_W, SLOT_L / 4.0, n_u=161, n_v=21)
        a.exact("aperture_was_cut", 0 if band["span_u"] is None else 1, 1,
                "None means the slot never opened through the floor")
        a.exact("raster_hit_the_part", 0 if band["all_clear"] else 1, 1,
                "every ray passing means the raster was aimed past the dish, so "
                "'nothing blocked it' and 'it went through the slot' would be the "
                "same reading")
        span = band["span_u"] if band["span_u"] is not None else -1.0
        a.within("drain_aperture_w", span, SLOT_W, 2.0 * band["pitch_u"] + 1e-9,
                 "clear width through the floor. Biased low by up to one ray pitch "
                 "per side, never high")
        a.note("aperture_rays", f"{band['clear']}/{band['tested']} passed")

    a.note("triangles", stats["triangles"])
    a.note("component_volumes", stats["component_volumes"])
    a.note("material_volume_mm3", round(stats["volume"], 4))
    return a, stats, topo


def main():
    obj = build()
    a, stats, topo = verify(obj)
    print(a.render())

    out = os.environ.get("DISH_OUT_DIR") or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(out, "gate_coupon_dish.stl")
    res = pk.gated_export(obj, path, a, expect_solids=1, expect_cavities=1,
                          wall_samples=1500)
    print(f"\n  export  {res}")

    # What the generator measured, recorded beside what it produced. Deliberately
    # not the auditor's opinion: this is the generator's own representative, and
    # comparing it against mesh_audit's numbers is meaningless by design. Each is
    # worth comparing against its own history.
    import json
    report = {
        "part": PART_NAME,
        "built": "2026-07-26",
        "parameters": {
            "R_BASE": R_BASE, "R_RIM": R_RIM, "H_TOTAL": H_TOTAL,
            "Z_FLARE": Z_FLARE, "WALL": WALL, "FLOOR_T": FLOOR_T,
            "SLOT_W": SLOT_W, "SLOT_L": SLOT_L, "RIM_SLOPE": RIM_SLOPE,
            "VOID_R": VOID_R, "VOID_W": VOID_W, "VOID_H": VOID_H, "VOID_Z": VOID_Z,
            "SEG_RING": SEG_RING, "SEG_LOFT": SEG_LOFT,
        },
        "acceptance": a.as_dict(),
        "purge": stats,
        "topology": topo,
        "export": res,
    }
    with open(os.path.join(out, "verify_report.json"), "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True, default=str)
    return bool(res.get("exported"))


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

#!/usr/bin/env python3
"""Regression harness for the half of part_kit that needs Blender.

`smoke.sh` states in its own header that nothing in it needs Blender, and that is
the right contract for a gate meant to run anywhere. The consequence is that
`boolean`, `clean_mesh`, `weld_verts`, `triangulate_and_purge`, `gated_export` and
`Probe` -- every function that has ever produced a wrong artifact here -- had no
automated coverage at all. The pinned vertex digest does not help: it is a property
of committed bytes on disk, and `saddle_gen.py` does not import `part_kit`.

So this file is separate, opt-in, and slow, and it is where a defect that reaches a
printer gets caught. Run it after touching anything under the BLENDER SOLIDS,
MEASUREMENT or EXPORT banners:

    /Applications/Blender.app/Contents/MacOS/Blender -b -noaudio \
        --python .claude/scripts/kit_smoke.py

Exit status is 0 only if every assertion passed. Blender always exits 0 on its own,
so the status is written to KIT_SMOKE_STATUS in the environment's temp dir and the
wrapper reads it -- see `kit_smoke.sh`.
"""
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "plugins", "part-forge", "scripts"))

import part_kit as pk

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    mark = "ok  " if cond else "FAIL"
    line = f"  {mark}  {name}"
    if not cond and detail:
        line += f"\n        {detail}"
    print(line)


def raises(name, exc_type, fn, needle=""):
    try:
        fn()
    except exc_type as exc:
        if needle and needle.lower() not in str(exc).lower():
            check(name, False, f"raised {exc_type.__name__} but without {needle!r}: {exc}")
        else:
            check(name, True)
        return
    except Exception as exc:  # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}, wanted {exc_type.__name__}: {exc}")
        return
    check(name, False, f"did not raise {exc_type.__name__}")


def section(title):
    print(f"\n{title}")


# ---------------------------------------------------------------------------
#  Pure kernel -- no Blender needed, but a regression here breaks every part
# ---------------------------------------------------------------------------

def square(half, n_per_side=1):
    pts = []
    for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        pts.append((u * half, v * half))
    if n_per_side == 1:
        return pts
    dense = []
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        for k in range(n_per_side):
            t = k / n_per_side
            dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return dense


def cone_rings(radius_at_zero, height, n_ring=48, n_z=17):
    """A 45 degree cone: r = R - z, so dr/dz = -1 exactly."""
    rings, zs = [], []
    for i in range(n_z):
        z = height * i / (n_z - 1)
        r = radius_at_zero - z
        rings.append([(r * math.cos(2 * math.pi * j / n_ring),
                       r * math.sin(2 * math.pi * j / n_ring)) for j in range(n_ring)])
        zs.append(z)
    return rings, zs


section("geometry kernel -- inward normals")
ccw = square(10.0)
cw = list(reversed(ccw))
n_ccw = pk.inward_normals(ccw)
n_cw = pk.inward_normals(cw)
check("inward_normals points inward for CCW winding",
      all(pk.point_in_poly((p[0] + n[0] * 0.5, p[1] + n[1] * 0.5), ccw)
          for p, n in zip(ccw, n_ccw)))
check("inward_normals points inward for CW winding too",
      all(pk.point_in_poly((p[0] + n[0] * 0.5, p[1] + n[1] * 0.5), cw)
          for p, n in zip(cw, n_cw)))

section("geometry kernel -- offset_rings, the cos(alpha) defect")
R, H, WALL = 40.0, 30.0, 3.0
rings, zs = cone_rings(R, H)
inset, izs = pk.offset_rings(rings, zs, WALL, floor=6.0, ceiling=H - 2.0)

# On a 45 degree cone the naive in-plane inset of WALL leaves a wall of
# WALL*cos(45) = 0.707*WALL. A true perpendicular offset must move the ring
# horizontally by WALL*sqrt(2) instead.
z_mid = izs[len(izs) // 2]
outer_mid = pk._ring_at_z(rings, zs, z_mid)
inner_mid = inset[len(izs) // 2]
r_out = math.hypot(*outer_mid[0])
r_in = math.hypot(*inner_mid[0])
horizontal = r_out - r_in
want_h = WALL * math.sqrt(2.0)
check("45deg cone: horizontal inset is wall*sqrt(1+m^2), not wall",
      abs(horizontal - want_h) < 1e-6,
      f"got {horizontal:.6f}, wanted {want_h:.6f} (naive would be {WALL:.6f})")
check("45deg cone: the perpendicular wall really is `wall`",
      abs(horizontal / math.sqrt(2.0) - WALL) < 1e-6,
      f"perpendicular = {horizontal / math.sqrt(2.0):.6f}")

raises("offset_rings refuses to default the floor", TypeError,
       lambda: pk.offset_rings(rings, zs, WALL, ceiling=20.0))
raises("offset_rings refuses ragged ring widths", ValueError,
       lambda: pk.offset_rings([rings[0], rings[1][:-1]], [0.0, 1.0], WALL,
                               floor=0.1, ceiling=0.9),
       "vertex count")
raises("offset_rings refuses a non-increasing z", ValueError,
       lambda: pk.offset_rings([rings[0], rings[1]], [1.0, 1.0], WALL,
                               floor=1.0, ceiling=1.0),
       "increase")
raises("offset_rings refuses a wall that collapses the section", ValueError,
       lambda: pk.offset_rings(rings, zs, 60.0, floor=1.0, ceiling=H - 1.0))

floor_only, floor_zs = pk.offset_rings(rings, zs, WALL, floor=9.0, ceiling=H - 1.0)
check("offset_rings honours a floor thicker than the wall",
      abs(floor_zs[0] - 9.0) < 1e-9, f"cavity starts at {floor_zs[0]}")

section("geometry kernel -- boolean sign table is data, not prose")
check("VOLUME_SIGN covers exactly Blender's three operations",
      set(pk.VOLUME_SIGN) == {"DIFFERENCE", "UNION", "INTERSECT"})
check("DIFFERENCE and INTERSECT remove, UNION adds",
      pk.VOLUME_SIGN["DIFFERENCE"] < 0 and pk.VOLUME_SIGN["INTERSECT"] < 0
      and pk.VOLUME_SIGN["UNION"] > 0)

section("mesh_audit -- triangle precondition")
ma = pk._load_mesh_audit()
raises("topology names the offending face on quad input", ValueError,
       lambda: ma.topology([(0, 0, 0)] * 4, [(0, 1, 2, 3)]), "face 0 has 4")
raises("edge_lengths guards too", ValueError,
       lambda: ma.edge_lengths([(0.0, 0.0, 0.0)] * 4, [(0, 1, 2, 3)]), "triangles")

section("mesh_audit -- the body model")
VESSEL = {"topology": {
    "open_edges": 0, "over_edges": 0, "winding_flips": 0, "degenerate_faces": 0,
    "null_volume_bodies": 0, "bodies": 2, "inverted_bodies": 1, "euler": 4,
    "genus": 0, "volume": 5256.0,
}}
PLATE = dict(VESSEL); PLATE["topology"] = dict(VESSEL["topology"])
PLATE["topology"].update({"bodies": 10, "inverted_bodies": 0, "euler": 20,
                          "volume": 40000.0})
SOLID = dict(VESSEL); SOLID["topology"] = dict(VESSEL["topology"])
SOLID["topology"].update({"bodies": 1, "inverted_bodies": 0, "euler": 2,
                          "volume": 8000.0})

check("a correct vessel passes when it declares its cavity",
      ma.acceptance(VESSEL, {}, expect_solids=1, expect_cavities=1) == [],
      str(ma.acceptance(VESSEL, {}, expect_solids=1, expect_cavities=1)))
check("an undeclared cavity is still a fault",
      any(f["check"] == "inverted_bodies" for f in ma.acceptance(VESSEL, {})))
check("a plate passes with --expect-solids N",
      ma.acceptance(PLATE, {}, expect_solids=10) == [],
      str(ma.acceptance(PLATE, {}, expect_solids=10)))
check("a plate still fails without a declaration",
      any(f["check"] == "bodies" for f in ma.acceptance(PLATE, {})))
check("two coupons fused into one is caught by the exact count",
      any(f["check"] == "solids" for f in ma.acceptance(PLATE, {}, expect_solids=11)))
check("an ordinary solid gates exactly as before",
      ma.acceptance(SOLID, {}) == [], str(ma.acceptance(SOLID, {})))

NEG = dict(SOLID); NEG["topology"] = dict(SOLID["topology"])
NEG["topology"].update({"volume": -8000.0, "inverted_bodies": 1})
check("a wholly inverted solid is caught by volume_sign",
      any(f["check"] == "volume_sign"
          for f in ma.acceptance(NEG, {}, expect_solids=1, expect_cavities=1)))

# ---------------------------------------------------------------------------
#  Blender-dependent
# ---------------------------------------------------------------------------

if not pk.HAVE_BPY:
    print("\n  part_kit reports no bpy; the Blender tier did not run.")
else:
    import bmesh

    pk.scene_setup()

    def box(name, half, at=(0.0, 0.0)):
        pts = [(-half + at[0], -half + at[1]), (half + at[0], -half + at[1]),
               (half + at[0], half + at[1]), (-half + at[0], half + at[1])]
        return pk.prism(name, pts, lambda u, v: (u, v, -half), (0.0, 0.0, 2 * half))

    def tris_of(obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        out = [tuple(tuple(v.co) for v in f.verts) for f in bm.faces]
        bm.free()
        return out

    def hollow(name="vessel", outer=20.0, cav=14.0):
        o = box(name, outer / 2)
        c = box(name + "_cav", cav / 2)
        pk.boolean(o, c, "DIFFERENCE", solver="EXACT")
        return o

    section("blender -- loft_solid and prism emit no n-gons")
    ring = [(10 * math.cos(2 * math.pi * i / 96), 10 * math.sin(2 * math.pi * i / 96))
            for i in range(96)]
    lofted = pk.loft_solid("lofted", [ring, ring], lambda i, u, v: (u, v, i * 20.0))
    check("loft_solid caps are triangulated",
          max(len(p.vertices) for p in lofted.data.polygons) <= 4)
    pris = pk.prism("pris", ring, lambda u, v: (u, v, 0.0), (0.0, 0.0, 10.0))
    check("prism caps are triangulated",
          max(len(p.vertices) for p in pris.data.polygons) <= 4)
    pk.purge("lofted", "pris")

    section("blender -- boolean")
    raises("boolean rejects an unknown operation", ValueError,
           lambda: pk.boolean(box("b1", 5.0), box("b2", 2.0), "SUBTRACT"),
           "unknown operation")
    pk.purge("b1", "b2")

    far = box("far_t", 5.0)
    miss = box("far_c", 2.0, at=(100.0, 100.0))
    raises("a cutter that misses raises and says so", RuntimeError,
           lambda: pk.boolean(far, miss, "DIFFERENCE"), "does not overlap")
    pk.purge("far_t", "far_c")

    t = box("ok_t", 10.0)
    c = box("ok_c", 4.0)
    v0 = pk.mesh_volume(t)
    pk.boolean(t, c, "DIFFERENCE", solver="EXACT")
    check("an ordinary DIFFERENCE still succeeds",
          abs(pk.mesh_volume(t) - (v0 - 8.0 ** 3)) < 1.0,
          f"{pk.mesh_volume(t)} vs {v0 - 8.0 ** 3}")
    pk.purge("ok_t")

    # The failure that motivated VOLUME_SIGN had no assertion at all until now: a
    # boolean whose volume moves the WRONG WAY, which the old magnitude-only guard
    # accepted on the first attempt. A UNION whose cutter lies wholly inside the
    # target is the deterministic way to produce a no-op that must not be accepted --
    # the true delta is exactly zero, so anything the guard accepts here is noise.
    inner_t = box("inner_t", 10.0)
    inner_c = box("inner_c", 3.0)
    raises("a UNION that cannot add material raises rather than passing on noise",
           RuntimeError, lambda: pk.boolean(inner_t, inner_c, "UNION", solver="EXACT"),
           "does not overlap")
    pk.purge("inner_t", "inner_c")

    # Bodies must be grouped the way a SLICER groups them -- adjacency only across
    # edges carrying exactly two faces. An edge with four faces is a fault, not a
    # join, so a flap hanging off one is a separate body and must fall out of the
    # purge as debris. Grouping across any shared edge absorbs it into the shell
    # instead, which is this plugin's founding defect: the mesh Bambu Studio refused
    # while the gate reported zero.
    body = box("grouping", 5.0)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.edges.ensure_lookup_table()
    seam = next(e for e in bm.edges if len(e.link_faces) == 2)
    a, b = seam.verts
    # Two distinct tips at the same position: bmesh refuses a second face on the
    # same three vertices, and a real triangulator emits distinct-but-coincident
    # vertices anyway.
    co = (a.co.x, a.co.y, a.co.z + 3.0)
    bm.faces.new((a, b, bm.verts.new(co)))
    bm.faces.new((b, a, bm.verts.new(co)))
    n_groups = len(pk._face_groups(bm))
    four_faced = sum(1 for e in bm.edges if len(e.link_faces) == 4)
    bm.free()
    check("a flap on a four-face edge is a separate body, not part of the shell",
          n_groups == 2 and four_faced == 1,
          f"{n_groups} group(s) with {four_faced} four-face edge(s); grouping across "
          f"any shared edge would report 1 and hide the flap inside the solid")
    pk.purge("grouping")

    section("blender -- clean_mesh and weld_verts on a vessel")
    v = hollow("v1")
    before = pk.mesh_volume(v)
    stats = pk.clean_mesh(v)
    check("clean_mesh no longer solidifies a vessel",
          abs(pk.mesh_volume(v) - before) < 1e-6,
          f"{before} -> {pk.mesh_volume(v)}")
    check("clean_mesh reports the volume either side",
          {"volume_before", "volume_after", "volume_delta"} <= set(stats))
    check("clean_mesh default is recalc_normals=False", stats["recalc_normals"] is False)

    w = hollow("v2")
    bw = pk.mesh_volume(w)
    pk.weld_verts(w)
    check("weld_verts never touches orientation", abs(pk.mesh_volume(w) - bw) < 1e-6)

    r = hollow("v3")
    br = pk.mesh_volume(r)
    pk.clean_mesh(r, recalc_normals=True)
    check("recalc_normals=True is still available, and still destructive",
          abs(pk.mesh_volume(r) - br) > 1.0,
          "the escape hatch stopped doing the thing it is documented to do")
    pk.purge("v1", "v2", "v3")

    section("blender -- triangulate_and_purge")
    plate = box("plate", 5.0)
    for i, at in enumerate(((20.0, 0.0), (0.0, 20.0), (20.0, 20.0))):
        pk.boolean(plate, box(f"pb{i}", 5.0, at=at), "UNION", solver="EXACT")
    st = pk.triangulate_and_purge(plate, expect_components=4)
    check("a 4-body plate is accepted when declared", st["kept_components"] == 4)
    check("volume sums over kept components, not just the largest",
          abs(st["volume"] - 4000.0) < 1.0, f"got {st['volume']}")
    pk.purge("plate")

    plate2 = box("plate2", 5.0)
    pk.boolean(plate2, box("pb_x", 5.0, at=(20.0, 0.0)), "UNION", solver="EXACT")
    raises("a wrong component count still raises, and names both numbers",
           RuntimeError, lambda: pk.triangulate_and_purge(plate2, expect_components=1),
           "expected 1 component(s), found 2")
    pk.purge("plate2")

    ves = hollow("v4")
    stv = pk.triangulate_and_purge(ves, expect_components=2)
    check("a vessel survives the purge when it declares its cavity",
          abs(stv["volume"] - 5256.0) < 1.0, f"got {stv['volume']}")

    section("blender -- gated_export")
    acc = pk.Acceptance("vessel")
    acc.at_least("volume", pk.mesh_volume(ves), 1.0)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "vessel.stl")
        res = pk.gated_export(ves, path, acc, expect_solids=1, expect_cavities=1)
        check("a correct sealed vessel now reaches disk", res["exported"] is True,
              str(res.get("faults")))
        check("and the export reports its cavity count",
              res.get("info", {}).get("cavities") == 1)

        bad = pk.Acceptance("vessel")
        bad.at_least("volume", pk.mesh_volume(ves), 1.0)
        res2 = pk.gated_export(ves, os.path.join(d, "bad.stl"), bad,
                               expect_solids=1, expect_cavities=0)
        check("an UNdeclared cavity is still rejected", res2["exported"] is False)
        check("and the rejected file is not left on disk",
              not os.path.exists(os.path.join(d, "bad.stl")))
    pk.purge("v4")

    section("blender -- Probe honesty")
    p_obj = box("probe_box", 10.0)
    with pk.Probe(p_obj) as probe:
        on_surface = probe.thickness_at((-10.0, 0.0, 0.0), (1.0, 0.0, 0.0))
        check("thickness_at measures a real wall from the surface",
              on_surface is not None and abs(on_surface - 20.0) < 1e-2,
              f"got {on_surface}")
        check("thickness_at returns None from the part's axis",
              probe.thickness_at((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)) is None)
        check("thickness_at returns None from 1 mm below the part",
              probe.thickness_at((0.0, 0.0, -11.0), (0.0, 0.0, 1.0)) is None)
    pk.purge("probe_box")

    slotted = box("slotted", 10.0)
    pk.boolean(slotted, pk.prism("slot", [(-1.6, -6.0), (1.6, -6.0), (1.6, 6.0),
                                          (-1.6, 6.0)],
                                 lambda u, v: (u, v, -12.0), (0.0, 0.0, 24.0)),
               "DIFFERENCE", solver="EXACT")
    with pk.Probe(slotted) as probe:
        band = probe.raster((0.0, 0.0, 20.0), (0.0, 0.0, -1.0),
                            (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), 6.0, 4.0,
                            n_u=121, n_v=9)
        # The documented contract, not a guessed number: the span is measured
        # between outermost passing ray CENTRES, so it understates the true 3.2 mm
        # aperture by up to one pitch at each end and must never overstate it.
        lo_ok = 3.2 - 2.0 * band["pitch_u"]
        check("raster brackets the slot, biased low by at most one pitch per side",
              band["span_u"] is not None and lo_ok <= band["span_u"] <= 3.2 + 1e-9,
              f"span_u={band['span_u']}, allowed [{lo_ok:.3f}, 3.200]")
        check("raster reports coverage, so a miss cannot read as a pass",
              band["tested"] == 121 * 9 and not band["all_clear"])
    pk.purge("slotted")

    solid = box("no_slot", 10.0)
    with pk.Probe(solid) as probe:
        none_band = probe.raster((0.0, 0.0, 20.0), (0.0, 0.0, -1.0),
                                 (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), 4.0, 4.0,
                                 n_u=41, n_v=9)
        check("raster returns None when the feature was never cut",
              none_band["span_u"] is None and none_band["clear"] == 0)
    pk.purge("no_slot")


print(f"\n  {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("  FAILED: " + ", ".join(FAIL))
print("  KIT SMOKE " + ("CLEAN" if not FAIL else "DIRTY"))

status_path = os.environ.get("KIT_SMOKE_STATUS")
if status_path:
    with open(status_path, "w") as fh:
        fh.write("0" if not FAIL else "1")

#!/usr/bin/env python3
"""Wall shelf bracket - a runnable skeleton for a parametric printable part.

Copy this file, replace the geometry, keep the shape. The part it builds is
deliberately real rather than a demo cube: a rounded mounting plate, a shelf leg,
a gusset with analytically filleted tips, and two counterbored screw holes. It has
a load path worth checking and every construction idiom the skill describes.

Invocation
----------
Headless, which is how a build should be run:

    blender --background --python-exit-code 1 --python generator_template.py

`--python-exit-code 1` is NOT optional. Without it Blender exits 0 even when this
script raises, so a failed build reports success to every caller, CI included.

Live session, which is how a Blender MCP connection runs it:

    exec(open("generator_template.py").read())

In the live path `__file__` does not exist, so `out_dir()` resolves through an
environment variable and a NameError fallback.

Coordinate system
-----------------
    origin  centre of the plate's bottom edge, on the wall face
    +X      along the plate width
    +Y      away from the wall
    +Z      up
    1 Blender unit == 1 mm

Print orientation
-----------------
Authored in its print orientation, so no export rotation is applied. The shelf is
a cantilever loaded downward: bending puts the top of the shelf root in tension
along Y. With the part sitting on its own underside, layers stack in Z and that
tension lies *within* a layer rather than across the layer lines, which is where
FDM parts fail. The plate and gusset then rise as vertical walls, the bed contact
is the full shelf footprint, and nothing needs support.

The plate's own bending would run across layers, which is acceptable here only
because the plate is screwed flat to the wall and carries the reaction in shear
against the fasteners rather than in bending. Recheck that claim if the mounting
method changes.
"""

from __future__ import annotations

import json
import math
import os
import sys

try:
    import bpy
    import bmesh
    HAVE_BPY = True
except ImportError:          # importable outside Blender so the kernel is testable
    bpy = bmesh = None
    HAVE_BPY = False


#: Substituted by new_part.py with the plugin's scripts directory as it stood at
#: scaffold time. Left as a literal placeholder in the template itself, which is
#: how the search below knows to ignore it.
_SCAFFOLD_SCRIPTS = "{{PART_FORGE_SCRIPTS}}"


def _find_part_kit():
    """Locate part_kit.py: env var, then relative to this file, then cwd.

    Four cases have to work, and the fourth is the one that bites. A copy of this
    file scaffolded into a part project sits *outside* the plugin, so walking up
    from `__file__` cannot reach the plugin's scripts directory - which is why
    new_part.py bakes the path it used into `_SCAFFOLD_SCRIPTS`. The environment
    variable is still checked first, so moving or reinstalling the plugin does not
    strand a project that was scaffolded against the old location.
    """
    candidates = []
    for var in ("PART_FORGE_SCRIPTS", "CLAUDE_PLUGIN_ROOT"):
        root = os.environ.get(var)
        if root:
            candidates.append(root)
            candidates.append(os.path.join(root, "scripts"))
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.abspath(os.path.join(here, "..", "..", "..", "scripts")))
    except NameError:        # exec()'d: no __file__
        pass
    candidates.append(os.path.join(os.getcwd(), "scripts"))
    candidates.append(os.getcwd())
    if "{{" not in _SCAFFOLD_SCRIPTS:    # unsubstituted in the template itself
        candidates.append(_SCAFFOLD_SCRIPTS)

    for path in candidates:
        if os.path.isfile(os.path.join(path, "part_kit.py")):
            if path not in sys.path:
                sys.path.insert(0, path)
            return path
    raise ImportError(
        "part_kit.py not found. Set PART_FORGE_SCRIPTS to the plugin's scripts "
        f"directory. Looked in: {candidates}"
    )


_find_part_kit()
import part_kit as pk  # noqa: E402


# ===========================================================================
#  PARAMETERS  -  dimension bearing
# ===========================================================================
# Every value here is a dimension. Each cites the ledger section it comes from,
# so a number can be traced to the measurement that justifies it. Keep the sweep
# history in FACTS.md and leave a pointer, not a hundred lines of it here.

PART_NAME = "wall_bracket"

W_PLATE = 60.0        # mm   plate width, X                      - FACTS 3.1
H_PLATE = 50.0        # mm   plate height, Z                     - FACTS 3.1
T_PLATE = 5.0         # mm   plate thickness, Y                  - FACTS 3.2
R_CORNER = 5.0        # mm   plate corner radius, cosmetic       - design choice

D_SHELF = 30.0        # mm   shelf depth from the wall face, Y   - FACTS 4.1
T_SHELF = 5.0         # mm   shelf thickness, Z                  - FACTS 4.2

T_WEB = 4.0           # mm   gusset thickness, X                 - design choice
H_WEB = 24.0          # mm   gusset height up the plate, Z       - design choice
WEB_MARGIN = 4.0      # mm   gusset tip setback from shelf tip   - design choice
R_TIP = 3.0           # mm   gusset tip fillet radius            - FACTS 7c

HOLE_D = 4.5          # mm   M4 clearance through hole           - FACTS 2.3
CBORE_D = 8.5         # mm   M4 socket-head counterbore          - FACTS 2.3
CBORE_DEPTH = 2.5     # mm   counterbore depth from the free face - FACTS 2.3
HOLE_SIGNS = (-1.0, 1.0)   # one bore per entry, mirrored about x = 0
HOLE_DX = 40.0        # mm   hole centre spacing, X               - FACTS 2.1 MEASURED
#                            ^ fixed by the existing wall anchors. This is an
#                              input, never a derivation. See FACTS 2.1.
HOLE_Z = 38.0         # mm   hole centre height, Z                - FACTS 2.2 MEASURED

EDGE_MIN = 2.0        # mm   minimum material outside a counterbore
FLOOR_MIN = 1.5       # mm   minimum material under a screw head
T_WALL_MIN = 3.0      # mm   printable wall floor on the load path

LOAD_LBF = 10.0       # lbf  design load at the shelf tip         - FACTS 1.5
MATERIAL = "PETG"
SIGMA_ALLOW_BY_MATERIAL = {"PLA": 50.0, "PETG": 50.0}   # MPa, tensile yield
#   PLA and PETG coincide at 50 here; that is a coincidence in the source data,
#   not evidence the two behave alike. The guard below catches an unknown key and
#   does nothing about a plausible-but-wrong value.
SF_MIN = 8.0          # covers ~0.6x for infill, ~0.5x for creep, rest for spread

VARIANT_OFFSETS = (-2.0, 0.0, 2.0)   # mm, applied to D_SHELF


# ===========================================================================
#  PARAMETERS  -  empirical constants
# ===========================================================================
# NOT dimensions. These are mesh-robustness and tessellation tunables: changing
# one alters the mesh, never the design. Kept in their own block so a segment
# count is never mistaken for a design decision.

SEG_CIRCLE = 64       # facets per hole
SEG_CORNER = 12       # facets per plate corner arc
SEG_FILLET = 12       # facets per gusset tip fillet
MERGE_DIST = 5.0e-3   # mm   weld distance between boolean stages
WEB_BITE = 0.6        # mm   gusset overlap into plate and shelf, for the union
CUT_OVERRUN = 1.0     # mm   how far a cutter extends past the solid

DO_EXPORT = True


# ===========================================================================
#  DERIVE  -  every secondary value computed once
# ===========================================================================

def derive(d_shelf=None):
    """Compute every derived value and validate the parameter combination.

    Nothing downstream computes its own. A radius recomputed at three call sites
    will disagree at two of them after the next edit.

    The asserts run before any geometry exists, so a bad combination costs a
    second rather than a full build. Each message names the physical
    consequence, because an expression repeated back is not a diagnosis.
    """
    d_shelf = D_SHELF if d_shelf is None else float(d_shelf)

    if MATERIAL not in SIGMA_ALLOW_BY_MATERIAL:
        raise ValueError(
            f"no allowable stress recorded for {MATERIAL!r}; "
            f"known materials are {sorted(SIGMA_ALLOW_BY_MATERIAL)}"
        )
    sigma_allow = SIGMA_ALLOW_BY_MATERIAL[MATERIAL]

    l_web = d_shelf - T_PLATE - WEB_MARGIN
    r_hole = HOLE_D / 2.0
    r_cbore = CBORE_D / 2.0
    hole_x = HOLE_DX / 2.0

    # Gusset triangle in the (Y, Z) plane, root buried by WEB_BITE so the union
    # with the plate and shelf is an overlap rather than a coplanar butt joint.
    a = (T_PLATE - WEB_BITE, T_SHELF - WEB_BITE)
    b = (T_PLATE + l_web, T_SHELF - WEB_BITE)
    c = (T_PLATE - WEB_BITE, T_SHELF + H_WEB)
    set_b = _setback(b, a, c, R_TIP)
    set_c = _setback(c, b, a, R_TIP)
    len_bc = math.dist(b, c)

    arm = d_shelf - T_PLATE                       # worst case: load at the tip
    load_n = LOAD_LBF * pk.LBF_TO_N
    moment = load_n * arm                         # N*mm
    section_mod = W_PLATE * T_SHELF ** 2 / 6.0    # mm^3, plain rectangle
    sigma = moment / section_mod                  # MPa
    safety = sigma_allow / sigma

    assert d_shelf > T_PLATE + WEB_MARGIN + 2.0 * R_TIP, (
        f"shelf depth {d_shelf} mm leaves no room for the gusset between the "
        f"plate face and the shelf tip; the bracket would have no brace"
    )
    assert T_SHELF + H_WEB < H_PLATE - R_CORNER, (
        f"the gusset reaches z={T_SHELF + H_WEB} mm and would run out through "
        f"the rounded top of the {H_PLATE} mm plate"
    )
    assert hole_x + r_cbore + EDGE_MIN <= W_PLATE / 2.0, (
        f"the counterbore at x={hole_x} mm breaks out of the plate edge; only "
        f"{W_PLATE / 2.0 - hole_x - r_cbore:.2f} mm of material would remain"
    )
    assert HOLE_Z + r_cbore + EDGE_MIN <= H_PLATE, (
        f"the counterbore at z={HOLE_Z} mm breaks out of the top of the plate"
    )
    assert CBORE_DEPTH + FLOOR_MIN < T_PLATE, (
        f"a {CBORE_DEPTH} mm counterbore in a {T_PLATE} mm plate leaves "
        f"{T_PLATE - CBORE_DEPTH:.2f} mm under the screw head, below the "
        f"{FLOOR_MIN} mm floor; the head would pull through"
    )
    assert CBORE_D > HOLE_D, (
        f"the counterbore ({CBORE_D} mm) is no larger than the hole it is "
        f"meant to relieve ({HOLE_D} mm); the screw head would not seat"
    )
    assert min(T_WEB, T_SHELF, T_PLATE) >= T_WALL_MIN, (
        f"the thinnest section on the load path is "
        f"{min(T_WEB, T_SHELF, T_PLATE)} mm, under the {T_WALL_MIN} mm "
        f"printable floor; it would come out as a wall count, not a dimension"
    )
    assert set_b + set_c < len_bc, (
        f"the tip fillets consume {set_b + set_c:.2f} mm of a {len_bc:.2f} mm "
        f"gusset hypotenuse and would overlap, leaving no straight brace"
    )
    assert 2.0 * hole_x > CBORE_D + EDGE_MIN, (
        f"the two counterbores at {HOLE_DX} mm spacing would break into each other"
    )

    return {
        "D_SHELF": d_shelf, "L_WEB": l_web,
        "R_HOLE": r_hole, "R_CBORE": r_cbore, "HOLE_X": hole_x,
        "WEB_A": a, "WEB_B": b, "WEB_C": c,
        "SET_B": set_b, "SET_C": set_c, "LEN_BC": len_bc,
        "SIGMA_ALLOW": sigma_allow, "ARM": arm, "LOAD_N": load_n,
        "MOMENT": moment, "SECTION_MOD": section_mod,
        "SIGMA": sigma, "SF": safety,
        "Z_WEB_TOP": T_SHELF + H_WEB, "Y_WEB_TIP": T_PLATE + l_web,
        "N_HOLES": len(HOLE_SIGNS),
    }


def _setback(corner, toward_a, toward_b, r):
    """Distance from a corner to the tangent point of a radius-r fillet."""
    u1 = _unit(toward_a, corner)
    u2 = _unit(toward_b, corner)
    theta = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1])))
    return r / math.tan(theta / 2.0)


def _unit(to_pt, from_pt):
    d = (to_pt[0] - from_pt[0], to_pt[1] - from_pt[1])
    n = math.hypot(*d)
    return (d[0] / n, d[1] / n)


# ===========================================================================
#  BUILD PHASES
# ===========================================================================

def phase_plate(g):
    """Rounded mounting plate, extruded off the wall face along +Y."""
    profile = pk.rounded_rect(W_PLATE, H_PLATE, R_CORNER, SEG_CORNER, origin="corner")
    return pk.prism(
        PART_NAME, profile,
        lambda u, v: (u - W_PLATE / 2.0, 0.0, v),
        (0.0, T_PLATE, 0.0),
    )


def phase_shelf(g):
    """The horizontal leg, extruded up along +Z."""
    profile = pk.rounded_rect(W_PLATE, g["D_SHELF"], R_CORNER, SEG_CORNER, origin="corner")
    return pk.prism(
        "_tmp_shelf", profile,
        lambda u, v: (u - W_PLATE / 2.0, v, 0.0),
        (0.0, 0.0, T_SHELF),
    )


def phase_web(g):
    """Gusset triangle with analytically filleted tips, extruded along X.

    The root corner stays square and buried; the two tips are rounded because a
    knife edge prints badly and carries no load. Neither tip is a right angle,
    which is exactly why the fillet is solved rather than bevelled.
    """
    a, b, c = g["WEB_A"], g["WEB_B"], g["WEB_C"]
    profile = [a]
    profile += pk.tangent_fillet(b, _unit(a, b), _unit(c, b), R_TIP, SEG_FILLET)
    profile += pk.tangent_fillet(c, _unit(b, c), _unit(a, c), R_TIP, SEG_FILLET)
    return pk.prism(
        "_tmp_web", profile,
        lambda u, v: (-T_WEB / 2.0, u, v),
        (T_WEB, 0.0, 0.0),
    )


def phase_holes(g, obj):
    """Two counterbored through holes, cut along +Y.

    The bore uses a circumscribed polygon: a polygon drawn through the circle's
    points cuts *inside* it, so the hole would come out undersized by the sagitta
    and the screw would not pass.
    """
    for sign in HOLE_SIGNS:
        x = sign * g["HOLE_X"]
        through = pk.prism(
            "_tmp_through",
            pk.circumscribed_circle(x, HOLE_Z, g["R_HOLE"], SEG_CIRCLE),
            lambda u, v: (u, -CUT_OVERRUN, v),
            (0.0, T_PLATE + 2.0 * CUT_OVERRUN, 0.0),
        )
        pk.boolean(obj, through, "DIFFERENCE")

        cbore = pk.prism(
            "_tmp_cbore",
            pk.circumscribed_circle(x, HOLE_Z, g["R_CBORE"], SEG_CIRCLE),
            lambda u, v: (u, T_PLATE - CBORE_DEPTH, v),
            (0.0, CBORE_DEPTH + CUT_OVERRUN, 0.0),
        )
        pk.boolean(obj, cbore, "DIFFERENCE")
    return obj


def build(name=PART_NAME, d_shelf=None):
    """Assemble the part. Returns (object, derived dict)."""
    pk._need_bpy("build")
    g = derive(d_shelf)
    pk.purge(name, "_tmp_shelf", "_tmp_web", "_tmp_through", "_tmp_cbore")

    obj = phase_plate(g)
    obj.name = name
    obj.data.name = name

    pk.boolean(obj, phase_shelf(g), "UNION")
    pk.clean_mesh(obj, MERGE_DIST)

    pk.boolean(obj, phase_web(g), "UNION")
    pk.clean_mesh(obj, MERGE_DIST)

    phase_holes(g, obj)
    pk.clean_mesh(obj, MERGE_DIST)

    g["purge"] = pk.triangulate_and_purge(obj)

    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    return obj, g


# ===========================================================================
#  VERIFY  -  measure the mesh, never restate the parameter
# ===========================================================================

def verify(obj, g):
    """Measure the finished solid. Returns a plain dict; raises nothing."""
    v = {"params": {"D_SHELF": g["D_SHELF"], "W_PLATE": W_PLATE, "H_PLATE": H_PLATE,
                    "T_PLATE": T_PLATE, "T_SHELF": T_SHELF, "T_WEB": T_WEB,
                    "HOLE_D": HOLE_D, "CBORE_D": CBORE_D}}

    co = [tuple(vt.co) for vt in obj.data.vertices]
    lo = [min(c[i] for c in co) for i in range(3)]
    hi = [max(c[i] for c in co) for i in range(3)]
    v["bbox"] = {"min": lo, "max": hi, "dims": [hi[i] - lo[i] for i in range(3)]}

    tris = [tuple(tuple(obj.data.vertices[i].co) for i in p.vertices)
            for p in obj.data.polygons]
    v["topology"] = pk.positional_topology(tris)
    v["triangles"] = len(tris)

    with pk.Probe(obj) as probe:
        # Plate thickness at three stations, all clear of the holes.
        plate = []
        for x, z in ((0.0, 10.0), (-24.0, 45.0), (24.0, 12.0)):
            t = probe.thickness_at((x, 0.0, z), (0.0, 1.0, 0.0))
            if t is not None:
                plate.append(t)
        v["t_plate"] = {"min": min(plate), "max": max(plate), "samples": len(plate)}

        # Shelf thickness, measured up from the underside beyond the plate.
        shelf = []
        for x, y in ((0.0, g["D_SHELF"] - 3.0), (-20.0, T_PLATE + 6.0), (20.0, T_PLATE + 6.0)):
            t = probe.thickness_at((x, y, 0.0), (0.0, 0.0, 1.0))
            if t is not None:
                shelf.append(t)
        v["t_shelf"] = {"min": min(shelf), "max": max(shelf), "samples": len(shelf)}

        # Gusset thickness, measured across from its -X face.
        web = []
        for y, z in ((T_PLATE + 4.0, T_SHELF + 4.0), (T_PLATE + 8.0, T_SHELF + 6.0)):
            t = probe.thickness_at((-T_WEB / 2.0, y, z), (1.0, 0.0, 0.0))
            if t is not None:
                web.append(t)
        v["t_web"] = {"min": min(web), "max": max(web), "samples": len(web)}

        # Hole geometry, by circle fit on a full sweep. The nominal diameter is a
        # parameter; this is what the boolean actually delivered.
        v["holes"] = []
        tested = skipped = 0
        y_probe = (T_PLATE - CBORE_DEPTH) / 2.0
        fan_r = g["R_HOLE"] + 3.0
        for sign in HOLE_SIGNS:
            cx = sign * g["HOLE_X"]
            arc = probe.surface_arc((cx, y_probe, HOLE_Z), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
                                    fan_r, 0.0, 359.0, step_deg=3.0)
            expected = int(round(359.0 / 3.0)) + 1
            tested += len(arc)
            skipped += expected - len(arc)
            pts = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
                   for a, r in arc]
            cu, cv, rad, resid = pk.fit_circle(pts)
            v["holes"].append({"x_nominal": cx, "r": rad, "residual": resid,
                               "centre_err": math.hypot(cu, cv), "samples": len(pts)})
        v["hole_scan"] = {"tested": tested, "skipped": skipped}

    v["bending"] = {"arm": g["ARM"], "moment": g["MOMENT"], "sigma": g["SIGMA"],
                    "sf": g["SF"], "sf_required": SF_MIN,
                    "section_mod": g["SECTION_MOD"], "material": MATERIAL,
                    "note": "plain rectangular shelf section; ignores the gusset, "
                            "so the real margin is larger than reported"}

    v["volume_mm3"] = g["purge"]["volume"]
    v["mass_g_solid_petg"] = g["purge"]["volume"] * 1.27e-3
    v["bed_contact_mm2"] = _bed_contact_area(obj)
    v["purge"] = g["purge"]
    return v


def _bed_contact_area(obj, tol=1.0e-4):
    """Area of downward faces sitting on the bed plane. Print quality, not a gate."""
    z_min = min(vt.co.z for vt in obj.data.vertices)
    total = 0.0
    for p in obj.data.polygons:
        if p.normal.z < -0.9 and all(
                abs(obj.data.vertices[i].co.z - z_min) < tol for i in p.vertices):
            total += p.area
    return total


# ===========================================================================
#  ACCEPTANCE  -  the specification of record
# ===========================================================================

def acceptance(v, g):
    """Build the gate. Where this and the written brief disagree, this wins."""
    a = pk.Acceptance(PART_NAME)

    t = v["topology"]
    a.exact("open_edges", t["open_edges"], 0,
            "a hole in the surface; the slicer has no inside to fill")
    a.exact("over_edges", t["over_edges"], 0,
            "an edge shared by three or more faces once welded by position")
    a.exact("winding_flips", t["winding_flips"], 0,
            "inconsistent winding leaves inside and outside ambiguous")
    a.exact("degenerate_faces", t["degenerate_faces"], 0)
    # This bracket is a SOLID: one positive shell, no cavities. Both numbers below
    # are declarations about that shape, not universal constants. A plate of N
    # coupons declares N solids; a vessel declares 1 solid and K cavities, a cavity
    # being a shell with negative signed volume. See `mesh-verification-gate`.
    a.exact("solids", t["bodies"] - t["inverted_bodies"], 1,
            "positive-volume shells; stray ones print as debris")
    a.exact("cavities", t["inverted_bodies"], 0,
            "this part is solid, so a negative-volume shell means it is inside out")
    a.exact("euler_even", t["euler"] % 2, 0,
            "a closed orientable surface has euler = 2 - 2g, always even")
    # CAREFUL when adapting this line. Genus equals the hole count only for a solid
    # with bores through it. A hollow shell with two openings is a pipe -- genus 1 --
    # no matter how many holes it has, so a reader who copies `N_HOLES` into a vessel
    # gets a check that is confidently wrong about the shape it is guarding.
    a.exact("genus", t["genus"], g["N_HOLES"],
            "each through hole adds one handle; a genus below the hole count "
            "means a bore did not punch through, and a boolean silently did nothing")

    a.tight("bbox_x", v["bbox"]["dims"][0], W_PLATE)
    a.tight("bbox_y", v["bbox"]["dims"][1], g["D_SHELF"])
    a.tight("bbox_z", v["bbox"]["dims"][2], H_PLATE)
    a.tight("bbox_z_min", v["bbox"]["min"][2], 0.0)
    a.tight("bbox_y_min", v["bbox"]["min"][1], 0.0,
            "material behind the wall face would hold the plate off the wall")

    a.tight("t_plate", v["t_plate"]["min"], T_PLATE)
    a.tight("t_shelf", v["t_shelf"]["min"], T_SHELF)
    a.tight("t_web", v["t_web"]["min"], T_WEB)
    a.at_least("min_wall_load_path",
               min(v["t_plate"]["min"], v["t_shelf"]["min"], v["t_web"]["min"]),
               T_WALL_MIN,
               "below the printable floor the section becomes a wall count")

    for i, h in enumerate(v["holes"]):
        a.loose(f"hole{i}_radius", h["r"], g["R_HOLE"],
                "an undersized bore means the screw does not pass")
        a.at_most(f"hole{i}_residual", h["residual"], 0.15,
                  "the bore is not the circle it was cut as")
        a.at_most(f"hole{i}_centre_err", h["centre_err"], 0.10)

    a.at_least("bending_sf", v["bending"]["sf"], SF_MIN,
               "sustained load on a printed section needs margin for infill and creep")

    # Measured, printed, deliberately not enforced. Kept out of the tally so a
    # passing count is never mistaken for coverage.
    a.note("volume_mm3", v["volume_mm3"])
    a.note("mass_g_solid_petg", v["mass_g_solid_petg"],
           "solid-material upper bound; the slicer decides the real figure")
    a.note("bed_contact_mm2", v["bed_contact_mm2"],
           "first-layer adhesion; a print-quality signal, not a dimension")
    a.note("folded_or_dropped", v["purge"]["dropped_components"])
    a.coverage("hole_scan", v["hole_scan"]["tested"], v["hole_scan"]["skipped"],
               "rays that missed indicate the fan radius no longer sits in material")
    return a


# ===========================================================================
#  ORCHESTRATION
# ===========================================================================

def out_dir():
    """Env override, then this script's directory, then cwd for the exec() path."""
    env = os.environ.get("WALL_BRACKET_OUT_DIR")
    if env:
        os.makedirs(env, exist_ok=True)
        return env
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def variant_name(base, offset):
    """Derive the file name from the offset it was built at.

    Names written out by hand silently mislabel every export the moment the
    nominal default moves. `main()` asserts this function round-trips.
    """
    if abs(offset) < 1e-9:
        return f"{base}_d0"
    return f"{base}_d{offset:+g}".replace("+", "p").replace("-", "m")


def _offset_from_name(base, name):
    tag = name[len(base) + 2:]
    if tag == "0":
        return 0.0
    return float(tag.replace("p", "+").replace("m", "-"))


def main():
    if not HAVE_BPY:
        print("generator_template: not running inside Blender; nothing built.")
        return False

    pk.scene_setup()
    pk.purge("Cube", "Light", "Camera")

    directory = out_dir()
    results, exports, refused, stl = {}, {}, [], {}
    ok = True

    for offset in VARIANT_OFFSETS:
        name = variant_name(PART_NAME, offset)
        assert abs(_offset_from_name(PART_NAME, name) - offset) < 1e-9, (
            f"variant name {name!r} does not round-trip to its offset {offset}; "
            f"the exported files would be mislabelled"
        )

        obj, g = build(name=name, d_shelf=D_SHELF + offset)
        v = verify(obj, g)
        acc = acceptance(v, g)
        print(acc.render())
        results[name] = {**v, "acceptance": acc.as_dict()}

        path = os.path.join(directory, name + ".stl")
        if DO_EXPORT:
            res = pk.gated_export(obj, path, acc)
            if res["exported"]:
                exports[name] = res["info"]
                stl[name] = {"vertex_digest": res["info"]["vertex_digest"],
                             "volume": res["info"]["volume"],
                             "dims": res["info"]["dims"]}
                print(f"  exported  {path}  digest {res['info']['vertex_digest']}")
            else:
                refused.append({"name": name, **{k: res[k] for k in res if k != "info"}})
                print(f"  REFUSED   {name}: {res['reason']}")
        if not acc.ok:
            ok = False
        pk.purge(name)

    results["_exports"] = exports
    results["_refused"] = refused
    results["_stl"] = stl
    report_path = os.path.join(directory, "verify_report.json")
    with open(report_path, "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f"\n  report -> {report_path}")
    print(f"  verdict: {'ACCEPTED' if ok and not refused else 'REJECTED'}")
    return ok and not refused


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

#!/usr/bin/env bash
# Regression harness for the plugin scripts.
#
# There is no unit-test suite behind the ~5,000 lines of Python in plugins/, and
# the thing most likely to break them is a refactor that still runs. So this
# exercises the real entry points against the repo's one real fixture and pins
# the numbers that must not move.
#
# Every assertion here is a behaviour a caller depends on: an exit code a skill
# branches on, a JSON key a document quotes, or a digest whose whole purpose is
# to be identical run over run.
#
#   .claude/scripts/smoke.sh          # run everything, print a verdict
#   .claude/scripts/smoke.sh -v       # also echo each command
#
# Exit 0 when every check passes, 1 otherwise. Nothing here writes inside the
# repo, needs the network, or needs Blender.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PF="$ROOT/plugins/part-forge/scripts"
PT="$ROOT/plugins/print-tune-bambu/skills/print-tune-bambu/scripts"
FIXTURE="$ROOT/projects/shade-bar-mount"
VESSEL="$ROOT/projects/gate-coupon-dish"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

VERBOSE=0
[[ "${1:-}" == "-v" ]] && VERBOSE=1

PASS=0
FAIL=0
SKIP=0

# The digest is a property of bytes already on disk, so it is stable across
# runs, machines and Python versions. If this moves, the fixture STL changed --
# which is either the point of your commit or a bug, and never a surprise.
readonly EXPECT_DIGEST="a916d985268c8921fff6f15315bc8e74"
readonly EXPECT_VOLUME="32953.0289"

# The vessel fixture. A SOLID part cannot exercise a cavity, so the saddle above is
# blind to every hollow-geometry failure: a flipped cavity leaves bodies, open edges,
# winding flips and genus all identical, and moves only the signed volume and the
# cavity count. These are the numbers that move if one comes back.
readonly VESSEL_DIGEST="964be23728bc126c0f7c06eafca0ce6f"
readonly VESSEL_VOLUME="23924.4142"
readonly VESSEL_CAVITY_MM3="72.0"       # 6 x 6 x 2 sealed void, negative shell

ok()   { PASS=$((PASS + 1)); printf '  ok    %s\n' "$1"; }
# check <label> [detail]  -- consumes the exit status of the previous command.
# Written as an explicit branch so that a reporter which itself fails can never
# be mistaken for a failing assertion.
check() {
    if [[ $? -eq 0 ]]; then ok "$1"; else bad "$1" "${2:-}"; fi
}
bad()  { FAIL=$((FAIL + 1)); printf '  FAIL  %s\n         %s\n' "$1" "${2:-}"; }
skip() { SKIP=$((SKIP + 1)); printf '  skip  %s (%s)\n' "$1" "${2:-}"; }

# expect_exit <wanted> <label> <cmd...>
expect_exit() {
    local want="$1" label="$2"
    shift 2
    [[ $VERBOSE -eq 1 ]] && printf '       $ %s\n' "$*"
    local out
    out="$("$@" 2>&1)"
    local got=$?
    if [[ $got -eq $want ]]; then
        ok "$label"
    else
        bad "$label" "wanted exit $want, got $got -- $(printf '%s' "$out" | tail -1)"
    fi
}

echo
echo "part-forge smoke -- fixture $(basename "$FIXTURE")"
echo

# --------------------------------------------------------------------------- #
# 1. Help paths. A CLI whose --help needs an optional dependency installed is
#    broken for exactly the person trying to work out what to install.
# --------------------------------------------------------------------------- #
echo "help paths"
for s in mesh_audit mesh_render mesh_repair new_part; do
    expect_exit 0 "$s.py --help" python3 "$PF/$s.py" --help
done
expect_exit 0 "mesh_repair.py clean --help" python3 "$PF/mesh_repair.py" clean --help

# --------------------------------------------------------------------------- #
# 2. The audit gate on a known-good solid.
# --------------------------------------------------------------------------- #
echo
echo "acceptance gate"
expect_exit 0 "saddle_h0 accepted" \
    python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h0.stl" --gate --quiet
expect_exit 0 "saddle_h-2 accepted" \
    python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h-2.stl" --gate --quiet
expect_exit 0 "saddle_h+2 accepted" \
    python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h+2.stl" --gate --quiet

# A gate that cannot fail is not a gate. These two prove it still refuses.
expect_exit 1 "wrong genus is refused" \
    python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h0.stl" --genus 1 --gate --quiet
expect_exit 1 "impossible volume is refused" \
    python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h0.stl" \
    --expect topology.volume=1.0~0.001 --gate --quiet

# --------------------------------------------------------------------------- #
# 3. Error paths. Exit 2 means "could not read", and skills branch on it.
# --------------------------------------------------------------------------- #
echo
echo "error paths"
expect_exit 2 "missing file exits 2" \
    python3 "$PF/mesh_audit.py" "$FIXTURE/does_not_exist.stl"
head -c 50 "$FIXTURE/saddle_h0.stl" > "$TMP/truncated.stl"
expect_exit 2 "truncated STL exits 2" python3 "$PF/mesh_audit.py" "$TMP/truncated.stl"

# --------------------------------------------------------------------------- #
# 4. Determinism. The digest exists to be compared; if it is not reproducible
#    it carries no information at all.
# --------------------------------------------------------------------------- #
echo
echo "determinism"
python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h0.stl" --quiet --json "$TMP/a.json" >/dev/null 2>&1
python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h0.stl" --quiet --json "$TMP/b.json" >/dev/null 2>&1
if [[ -f "$TMP/a.json" && -f "$TMP/b.json" ]]; then
    read -r DA VA <<<"$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(d['vertex_digest'], round(d['topology']['volume'],4))" "$TMP/a.json")"
    DB="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['vertex_digest'])" "$TMP/b.json")"

    [[ "$DA" == "$DB" ]]
    check "digest reproduces across runs" "$DA != $DB"
    [[ "$DA" == "$EXPECT_DIGEST" ]]
    check "digest matches the pinned value" "fixture geometry moved: $DA != $EXPECT_DIGEST"
    [[ "$VA" == "$EXPECT_VOLUME" ]]
    check "volume matches the pinned value" "$VA != $EXPECT_VOLUME"
else
    bad "determinism" "--json produced no file"
fi

# --------------------------------------------------------------------------- #
# 4b. The vessel fixture. Its whole reason for existing is that a solid part
#     cannot fail the way a hollow one can: a flipped cavity keeps every
#     structural number identical -- bodies, open edges, winding flips, genus --
#     and changes only the signed volume and the cavity count.
#
#     The independent check is the load-bearing one. inspect_model.py shares no
#     code with mesh_audit, has its own STL loader, and sums signed tetrahedra
#     over every triangle. A correct sealed cavity contributes NEGATIVE volume,
#     so flipping it outward moves inspect_model's answer by twice the cavity --
#     144 mm^3 here. That is full detection of the worst defect in the ledger by
#     code that has never heard of bodies, cavities or the body model.
# --------------------------------------------------------------------------- #
echo
echo "vessel fixture"
python3 "$PF/mesh_audit.py" "$VESSEL/gate_coupon_dish.stl" --quiet \
    --json "$TMP/v.json" >/dev/null 2>&1
python3 "$PT/inspect_model.py" "$VESSEL/gate_coupon_dish.stl" >"$TMP/vi.json" 2>/dev/null
python3 - "$TMP/v.json" "$TMP/vi.json" "$VESSEL_DIGEST" "$VESSEL_VOLUME" \
         "$VESSEL_CAVITY_MM3" <<'PYEOF'
import json, sys
ma = json.load(open(sys.argv[1]))
im = list(json.load(open(sys.argv[2])).values())[0]
want_d, want_v, cav = sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
t = ma["topology"]
bad = []
if ma["vertex_digest"] != want_d:
    bad.append(f"digest {ma['vertex_digest']} != {want_d}")
if abs(t["volume"] - want_v) > 1e-3:
    bad.append(f"volume {t['volume']:.4f} != {want_v}")
if t["bodies"] - t["inverted_bodies"] != 1:
    bad.append(f"solids {t['bodies'] - t['inverted_bodies']} != 1")
if t["inverted_bodies"] != 1:
    bad.append(f"cavities {t['inverted_bodies']} != 1 -- the sealed void was lost")
if t["genus"] != 1:
    bad.append(f"genus {t['genus']} != 1")
# The independent opinion, and the one that catches a flipped cavity.
v_im = im["volume_cm3"] * 1000.0
if abs(v_im - want_v) > 0.5:
    flipped = abs(v_im - (want_v + 2.0 * cav)) < 0.5
    bad.append(f"inspect_model {v_im:.4f} != {want_v}"
               + (" -- exactly +2x the cavity: it was flipped outward" if flipped else ""))
if bad:
    print("; ".join(bad), file=sys.stderr)
    sys.exit(1)
PYEOF
check "vessel digest, cavity and genus hold" "the hollow fixture moved -- see stderr"

python3 - "$TMP/v.json" <<'PYEOF'
import json, sys
t = json.load(open(sys.argv[1]))["topology"]
vols = sorted(b["signed_volume"] for b in t["body_detail"])
sys.exit(0 if vols and vols[0] < 0 and abs(vols[0] + 72.0) < 1e-6 else 1)
PYEOF
check "the sealed void is still a negative shell of 72 mm^3" \
      "the cavity is gone, flipped, or resized"

# --------------------------------------------------------------------------- #
# 5. JSON contract. These keys are quoted by skills and by the sibling plugin;
#    renaming one is a breaking change that nothing else would catch.
# --------------------------------------------------------------------------- #
echo
echo "json contract"
MISSING="$(python3 -c "
import json,sys
d = json.load(open(sys.argv[1]))
need = ['file','vertex_digest','topology','bounds','trimesh','faults','accepted']
print(','.join(k for k in need if k not in d) or 'none')
" "$TMP/a.json" 2>/dev/null)"
[[ "$MISSING" == "none" ]]
check "mesh_audit --json carries its documented keys" "missing: $MISSING"

# --------------------------------------------------------------------------- #
# 6. Variant comparison, the mode used to review a design change.
# --------------------------------------------------------------------------- #
echo
echo "variant comparison"
expect_exit 0 "h0 vs h+2 compares" \
    python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h0.stl" \
    --compare "$FIXTURE/saddle_h+2.stl" --quiet --json "$TMP/cmp.json"
if [[ -f "$TMP/cmp.json" ]]; then
    python3 -c "
import json,sys
c = json.load(open(sys.argv[1])).get('comparison') or {}
sys.exit(0 if c and c.get('vertex_digest_match') is False else 1)" "$TMP/cmp.json"
    check "distinct variants report distinct digests" "comparison block missing or wrong"
fi

# --------------------------------------------------------------------------- #
# 7. Scaffolding, into a temp dir. new_part.py must find its templates through
#    the plugin, not through the caller's working directory.
# --------------------------------------------------------------------------- #
echo
echo "scaffolding"
expect_exit 0 "new_part scaffolds" \
    python3 "$PF/new_part.py" "Smoke Test Widget" --dir "$TMP/parts"
for f in FACTS.md PROJECT.md BUILD-BRIEF.md; do
    [[ -f "$TMP/parts/smoke-test-widget/$f" ]]
    check "scaffold wrote $f" "not created"
done
expect_exit 1 "scaffold refuses to overwrite" \
    python3 "$PF/new_part.py" "Smoke Test Widget" --dir "$TMP/parts"

# --------------------------------------------------------------------------- #
# 8. part_kit's pure-Python half must stay importable without Blender, because
#    that is what lets any of it be checked at all outside a bpy process.
# --------------------------------------------------------------------------- #
echo
echo "part_kit without blender"
python3 - "$PF" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import part_kit as pk

assert pk.HAVE_BPY is False, "bpy should be absent outside Blender"
area = pk.polygon_area(pk.rounded_rect(10, 6, 1.5, 8))
assert 57 < area < 59, f"rounded_rect area moved: {area}"
_, n = pk.weld_by_position([(0, 0, 0), (0, 0, 0.00005), (1, 1, 1)])
assert n == 2, f"positional weld merged wrong: {n}"
try:
    pk.Probe(None)
except RuntimeError:
    pass
else:
    raise AssertionError("bpy-dependent call should refuse without Blender")
PY
check "geometry kernel imports and computes" "see traceback above"

# --------------------------------------------------------------------------- #
# 9. Optional-dependency degrade paths. Exit 3 with a runnable uvx line is the
#    contract; a traceback is not.
# --------------------------------------------------------------------------- #
echo
echo "optional dependencies"
if python3 -c "import pyvista" 2>/dev/null; then
    skip "mesh_render degrades without pyvista" "pyvista is installed"
else
    expect_exit 3 "mesh_render degrades without pyvista" \
        python3 "$PF/mesh_render.py" "$FIXTURE/saddle_h0.stl" --views --out "$TMP/r"
fi
if python3 -c "import pymeshlab" 2>/dev/null; then
    skip "mesh_repair degrades without pymeshlab" "pymeshlab is installed"
else
    expect_exit 3 "mesh_repair degrades without pymeshlab" \
        python3 "$PF/mesh_repair.py" clean "$FIXTURE/saddle_h0.stl" "$TMP/c.stl"
fi

# --------------------------------------------------------------------------- #
# 10. The sibling plugin's model inspector reads the same file independently.
#     Its agreement with mesh_audit is the cross-check the repo is built on --
#     so it is asserted here in numbers. It used to be asserted in this comment
#     and nowhere else: the only check was that inspect_model exited 0, which it
#     would do while disagreeing about every quantity it measures.
#
#     The two share no code and do not even agree on method. inspect_model has
#     its own STL loader and quantises positions to 3 decimal places;
#     mesh_audit welds at 1e-4 mm. That the numbers still land on top of each
#     other is what makes the agreement evidence rather than tautology.
# --------------------------------------------------------------------------- #
echo
echo "narrow features"

# --------------------------------------------------------------------------- #
#     A ladder of pillars whose every gap and wall width is CHOSEN, so the
#     detector is checked against arithmetic rather than against another
#     estimate. The second assertion is the one that matters most: an X-shear
#     proportional to Z changes every 3D distance in the mesh and no in-plane
#     one, and the slicer only ever sees the in-plane width. A future
#     "optimisation" to a 3D nearest-surface query would still pass the first
#     check and fail this one.
# --------------------------------------------------------------------------- #
python3 - "$PT" <<'PY'
import struct, sys, tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import inspect_model as im

DEPTH, HEIGHT = 5.0, 20.0
WIDTHS = [1.0, 1.0, 1.0, 0.6, 1.0, 1.0, 1.0]
GAPS = [0.3, 0.5, 0.7, 0.9, 1.2, 2.5]


def box(x0, x1, y0, y1, z0, z1):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]
    return [(v[a], v[b], v[c]) for a, b, c in f]


def ladder(shear=0.0):
    tris, x = [], 0.0
    for i, w in enumerate(WIDTHS):
        tris += box(x, x + w, 0.0, DEPTH, 0.0, HEIGHT)
        x += w + (GAPS[i] if i < len(GAPS) else 0.0)
    return [tuple((p[0] + shear * p[2], p[1], p[2]) for p in t) for t in tris]


# Exact, not approximate: the midpoint rule accounts for the full height, so a
# gap is bounded by two faces of DEPTH x HEIGHT with no sampling shortfall. This
# value is arithmetic about the fixture and is deliberately NOT derived the way
# the code derives it -- an expected value computed by the same method as the
# measurement cannot detect a bias in that method, which is how a systematic
# n/(n+1) under-report survived the first version of this check.
face = DEPTH * HEIGHT
bad = []
flat = im.analyze(ladder())["narrow_features"]
for path, want in (
    ("gap.min_mm", 0.3), ("gap.unresolvable_mm2", 2 * face),
    ("gap.ragged_mm2", 4 * face), ("wall.min_mm", 0.6),
    ("wall.ragged_mm2", 2 * face), ("wall.unresolvable_mm2", 0.0),
):
    k, sub = path.split(".")
    got = flat[k][sub]
    if got is None or abs(got - want) > max(0.02, 0.002 * want):
        bad.append(f"{path} {got} != {want:.2f}")

# Total wall area is arithmetic too: each pillar has two DEPTH x HEIGHT faces
# and two width x HEIGHT faces. Pinning it catches a sampling change that
# rescales everything uniformly, which the ratios above would not notice.
want_area = sum(2 * DEPTH * HEIGHT + 2 * w * HEIGHT for w in WIDTHS)
if abs(flat["wall_area_mm2"] - want_area) > 0.5:
    bad.append(f"wall_area_mm2 {flat['wall_area_mm2']} != {want_area}")

# Shear tilts every wall: a 1.2 mm in-plane gap drops to 0.54 mm measured
# perpendicular. The slicer still sees 1.2, so these numbers must not move.
tilted = im.analyze(ladder(shear=2.0))["narrow_features"]
for k in ("gap", "wall"):
    for sub in ("min_mm", "unresolvable_mm2", "ragged_mm2"):
        if flat[k][sub] != tilted[k][sub]:
            bad.append(f"shear moved {k}.{sub}: {flat[k][sub]} -> {tilted[k][sub]}")

# A plain brick modelled as two overlapping boxes. There is no thin rib here --
# a slicer unions the bodies and sees one solid -- but the buried facets face
# each other across the overlap and read as one without a containment test.
# The mesh is watertight, so no manifold check catches it; only the winding rule
# does. Swept across overlaps that bracket the reporting band.
for overlap in (0.1, 0.3, 0.6, 0.8):
    brick = box(0, 10, 0, 10, 0, 10) + box(10 - overlap, 20 - overlap, 0, 10, 0, 10)
    r = im.analyze(brick)
    nf = r["narrow_features"]
    if not r["watertight"]:
        bad.append(f"overlap {overlap}: fixture stopped being watertight, test is void")
    for k in ("gap", "wall"):
        if nf[k]["unresolvable_mm2"] or nf[k]["ragged_mm2"]:
            bad.append(
                f"overlap {overlap}: invented {k} features "
                f"{nf[k]['unresolvable_mm2']}/{nf[k]['ragged_mm2']} mm2 in solid material"
            )

# The harder half of the same defect: faces that are COINCIDENT rather than
# overlapping. A 60 mm column with a 0.6 mm slot plugged everywhere except one
# 0.6 mm tall band -- the plugs' sides sit exactly on the slot walls. Without a
# containment test the plug's far face reads as the far wall of a full-height
# slot and the answer comes out 100x high, over the whole column.
def slotted(z0, z1):
    return (box(0, 4.7, 0, 10, z0, z1) + box(5.3, 10, 0, 10, z0, z1)
            + box(4.7, 5.3, 8, 10, z0, z1))


merged = slotted(0, 60) + box(4.7, 5.3, 0, 8, 0, 30) + box(4.7, 5.3, 0, 8, 30.6, 60)
g = im.analyze(merged)["narrow_features"]["gap"]
# Truth: 2 walls x 8 mm deep x 0.6 mm tall = 9.6 mm2, at z 30.0-30.6. The
# tolerance is one layer pitch of quantisation, not a licence for the 960 mm2
# over z 0-60 that this reported before the winding rule went in.
if not 6.0 <= g["ragged_mm2"] <= 14.0:
    bad.append(f"coincident-face slot: {g['ragged_mm2']} mm2, want ~9.6")
zr = g.get("z_range_mm") or [0, 60]
if zr[0] < 29.0 or zr[1] > 32.0:
    bad.append(f"coincident-face slot: z {zr}, want the band near 30.0-30.6")

# Both preconditions must actually gate the numbers, or the caveat in the skill
# is decorative. A single flipped triangle leaves the box closed, so this is not
# reachable through the watertight check -- only the directed-edge count sees it.
flipped = box(0, 10, 0, 10, 0, 10)
flipped[0] = (flipped[0][0], flipped[0][2], flipped[0][1])
rf = im.analyze(flipped)
if rf["winding_consistent"]:
    bad.append("a flipped triangle did not register as inconsistent winding")
if not rf["watertight"]:
    bad.append("flipped-triangle fixture stopped being watertight, test is void")
if not any("not reported" in f for f in rf["flags"]):
    bad.append("narrow features were still reported on an inconsistently wound mesh")
if im.analyze(box(0, 10, 0, 10, 0, 10))["flipped_edges"]:
    bad.append("a clean box reported flipped edges")

if bad:
    print("; ".join(bad), file=sys.stderr)
    sys.exit(1)
PY
check "groove and rib widths match an analytic ladder, survive shear, and are not invented inside overlapping solids" \
      "the narrow-feature detector disagrees with arithmetic -- see stderr above"

# The vessel fixture's sealed void is documented as 6 x 6 x 2, so its ceiling is
# one bridge of exactly 6 x 6 mm. Before clustering, this number was the bounding
# box of every bridge facet on the part at once -- fine on a fixture with one
# bridge, 8x overstated on a model with 1197 of them, and quoted straight into
# max_bridge_length.
python3 - "$PT" "$VESSEL" <<'PY'
import sys, pathlib
sys.path.insert(0, sys.argv[1])
import inspect_model as im

r = im.analyze(im.LOADERS[".stl"](pathlib.Path(sys.argv[2]) / "gate_coupon_dish.stl"))
ext = r.get("largest_bridge_extent_mm") or {}
bad = []
if r.get("bridge_count") != 1:
    bad.append(f"bridge_count {r.get('bridge_count')} != 1")
for axis in ("x", "y"):
    if abs(ext.get(axis, 0) - 6.0) > 0.01:
        bad.append(f"bridge extent {axis}={ext.get(axis)} != 6.0")
if bad:
    print("; ".join(bad), file=sys.stderr)
    sys.exit(1)
PY
check "the sealed void reads as one 6 x 6 mm bridge, not a whole-part bounding box" \
      "bridge clustering regressed -- see stderr above"

echo
echo "slice_check gcode features"

# --------------------------------------------------------------------------- #
#     `check` and `compare` need Bambu Studio's CLI, which this harness may not
#     have and must never require. The gcode parser behind `features` needs
#     nothing: it is text handling, it carries the branchiest logic in the file
#     -- relative versus absolute extrusion, G92 resets, retractions, travel
#     moves and inline comments, each of which silently corrupts a total when
#     mishandled -- and it is the evidence behind the "engraved detail prints
#     ragged" diagnosis. A synthetic plate pins every branch to a known number.
# --------------------------------------------------------------------------- #
cat >"$TMP/plate_1.gcode" <<'GCODE'
; HEADER_BLOCK_START
; total layer number: 2
; HEADER_BLOCK_END
M83
; CHANGE_LAYER
; Z_HEIGHT: 0.20
; FEATURE: Outer wall
G1 X10 Y10 E1.0
G1 X20 Y10 E2.0
G1 X30 Y10 F9000 ; travel, and a comment that must not parse as E
G1 E-0.8
; FEATURE: Gap infill
G1 X31 Y10 E0.5
; CHANGE_LAYER
; Z_HEIGHT: 0.40
; FEATURE: Gap infill
G1 X32 Y10 E0.25
; FEATURE: Outer wall
M82
G1 X35 Y10 E2.0
G92 E0
G1 X40 Y10 E3.0
G1 X50 Y10 E4.5
GCODE

expect_exit 0 "features reads a plate from its directory" \
    python3 "$PT/slice_check.py" features "$TMP"

python3 - "$PT" "$TMP/plate_1.gcode" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import slice_check as sc

f = sc.gcode_features(Path(sys.argv[2]))
bad = []


def want(name, key, exp):
    got = f.get(name, {}).get(key)
    if got is None or abs(got - exp) > 1e-6:
        bad.append(f"{name}.{key} {got} != {exp}")


# Outer wall: 1.0 + 2.0 relative; then absolute 2.0, a G92 that rezeroes the
# datum, then 3.0 and (4.5 - 3.0). The absolute run before the G92 is what makes
# the reset load-bearing -- without it last_e is already 0 and dropping the
# reset changes nothing, so the branch would be asserted but never exercised.
# The -0.8 retraction and the E-less travel must contribute nothing.
want("Outer wall", "mm", 9.5)
want("Gap infill", "mm", 0.75)
want("Outer wall", "blocks", 2)
want("Gap infill", "blocks", 2)
# z comes from ; Z_HEIGHT:, and both features span both layers.
want("Outer wall", "z_min", 0.20)
want("Outer wall", "z_max", 0.40)
want("Gap infill", "z_min", 0.20)
want("Gap infill", "z_max", 0.40)
if set(f) != {"Outer wall", "Gap infill"}:
    bad.append(f"unexpected features: {sorted(f)}")
# Gap infill is the whole point of the subcommand; if it ever stops being
# flagged, the diagnosis it supports goes quiet rather than wrong.
if "Gap infill" not in sc.DETAIL_RISK:
    bad.append("Gap infill dropped out of DETAIL_RISK")
if bad:
    print("; ".join(bad), file=sys.stderr)
    sys.exit(1)
PY
check "extrusion, blocks and z survive M82/M83, G92, retraction and comments" \
      "the feature parser miscounts -- see stderr above"

# `check` and `compare` need Bambu Studio's CLI and so cannot run here, but the
# reporting logic between the slicer and the reader is pure and is where the
# diagnostic surfacing lives. Gap infill is seconds of work and the whole
# diagnosis for ragged narrow detail, so it must appear even though ranking by
# time buries it -- that is the behaviour, not an incidental of the formatting.
python3 - "$PT" <<'PY'
import io, sys
from contextlib import redirect_stdout

sys.path.insert(0, sys.argv[1])
import slice_check as sc

result = {
    "return_code": 0, "layer_height": 0.2, "wall_loops": 2,
    "sparse_infill_density": 15,
    "sliced_plates": [{
        "total_predication": 1000.0,
        "filaments": [{"total_used_g": 12.5}],
        "feature_type_times": {
            "Sparse infill": 400, "Outer wall": 300, "Inner wall": 150,
            "Travel": 80, "Undefined": 40, "Brim": 20, "Top surface": 8,
            "Gap infill": 1.5, "Overhang wall": 0.5,
        },
        "warning_message": "",
    }],
}
s = sc.summarize(result)
bad = []
if s["grams"] != 12.5:
    bad.append(f"grams {s['grams']} != 12.5")
if not s["ok"] or s["seconds"] != 1000:
    bad.append(f"ok/seconds wrong: {s['ok']}/{s['seconds']}")

buf = io.StringIO()
with redirect_stdout(buf):
    sc.print_summary("fixture", s)
text = buf.getvalue()
# Ranked 8th and 9th by time, so both fall outside the top six.
for name in ("Gap infill", "Overhang wall"):
    if name not in text:
        bad.append(f"{name} was buried by the top-six cut")
    elif "(diagnostic)" not in text.split(name, 1)[1].split("\n", 1)[0]:
        bad.append(f"{name} shown but not marked diagnostic")
if "Sparse infill" not in text:
    bad.append("the ordinary top-six breakdown stopped being printed")
if bad:
    print("; ".join(bad), file=sys.stderr)
    sys.exit(1)
PY
check "diagnostic features are surfaced even when time-ranking buries them" \
      "print_summary dropped a feature that names a defect -- see stderr above"

echo
echo "cross-plugin agreement"
expect_exit 0 "inspect_model reads the fixture" \
    python3 "$PT/inspect_model.py" "$FIXTURE/saddle_h0.stl"

python3 "$PT/inspect_model.py" "$FIXTURE/saddle_h0.stl" >"$TMP/im.json" 2>/dev/null
python3 "$PF/mesh_audit.py" "$FIXTURE/saddle_h0.stl" --json "$TMP/ma.json" --quiet >/dev/null 2>&1
python3 - "$TMP/im.json" "$TMP/ma.json" <<'PY'
import json, sys
im = list(json.load(open(sys.argv[1])).values())[0]
ma = json.load(open(sys.argv[2]))
t = ma["topology"]
# inspect_model reports cm^3 and takes abs(); mesh_audit reports signed mm^3.
v_im = im["volume_cm3"] * 1000.0
v_ma = abs(t["volume"])
bad = []
if abs(v_im - v_ma) > 0.5:
    bad.append(f"volume {v_im:.4f} vs {v_ma:.4f} mm^3")
if im["triangles"] != ma["triangles_raw"]:
    bad.append(f"triangles {im['triangles']} vs {ma['triangles_raw']}")
if im["open_edges"] != t["open_edges"]:
    bad.append(f"open_edges {im['open_edges']} vs {t['open_edges']}")
if im["degenerate_triangles"] != t["degenerate_faces"]:
    bad.append(f"degenerate {im['degenerate_triangles']} vs {t['degenerate_faces']}")
d_im = [im["dims_mm"][k] for k in ("x", "y", "z")]
d_ma = ma["bounds"]["dims"]
if any(abs(a - b) > 1e-3 for a, b in zip(d_im, d_ma)):
    bad.append(f"dims {d_im} vs {d_ma}")
if bad:
    print("; ".join(bad), file=sys.stderr)
    sys.exit(1)
PY
check "inspect_model and mesh_audit agree on the same bytes" \
      "the two independent implementations disagree -- see stderr above"

# --------------------------------------------------------------------------- #
echo
printf '  %d passed, %d failed, %d skipped\n' "$PASS" "$FAIL" "$SKIP"
if [[ $FAIL -eq 0 ]]; then
    echo "  SMOKE CLEAN"
    exit 0
fi
echo "  SMOKE FAILED"
exit 1

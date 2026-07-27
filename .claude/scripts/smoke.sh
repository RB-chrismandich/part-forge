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
#     Its agreement with mesh_audit is the cross-check the repo is built on.
# --------------------------------------------------------------------------- #
echo
echo "cross-plugin agreement"
expect_exit 0 "inspect_model reads the fixture" \
    python3 "$PT/inspect_model.py" "$FIXTURE/saddle_h0.stl"

# --------------------------------------------------------------------------- #
echo
printf '  %d passed, %d failed, %d skipped\n' "$PASS" "$FAIL" "$SKIP"
if [[ $FAIL -eq 0 ]]; then
    echo "  SMOKE CLEAN"
    exit 0
fi
echo "  SMOKE FAILED"
exit 1

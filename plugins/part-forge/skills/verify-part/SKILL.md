---
name: verify-part
description: Audit an STL or mesh for printability without Blender - positional manifoldness, watertightness, wall thickness, overhang area, mass properties, and reproducibility digest. Use to check a file a slicer rejected, to compare two builds, or to verify a mesh from any source.
argument-hint: <mesh.stl> [--compare other.stl] [--expect key=val] [--render]
allowed-tools: Bash, Read, Glob, Skill
---

# Audit a mesh, outside the tool that made it

This runs on the exported file, in an implementation that shares nothing with any generator. It
answers the question a slicer will ask, which is not always the question the authoring tool
answered.

## Step 1 - resolve the input

Take the path from `$ARGUMENTS`. If none was given, glob for `*.stl`, `*.3mf`, `*.obj`, `*.ply`
under the current directory and `projects/`, list what you find, and ask which one. If the user
named a part rather than a file, find that part's exports.

## Step 2 - audit

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"
python3 "$S/mesh_audit.py" part.stl --gate --json part_audit.json
```

Tier 0 needs only the standard library. Tier 1 adds mass properties, ray-cast wall thickness,
and overhang area when trimesh is importable; if it is missing, the audit still runs and says
which checks were skipped rather than failing.

Useful flags:

- `--build-axis {x,y,z} --overhang-deg N` — overhang is measured against the build direction, so
  this must match how the part will actually be placed on the bed. Getting it wrong makes the
  overhang number meaningless.
- `--allow-multi-body` — only when several shells are genuinely intended. Otherwise the default
  fault is correct: stray shells print as debris.
- `--weld MM` — the positional weld tolerance, default 1e-4 mm. If `weld_boundary_risk` comes
  back non-zero, re-run at a different tolerance before trusting the unique-vertex counts.
- `--expect PATH=VAL~TOL` or `--expect-file expect.json` — assert against the parameter table,
  e.g. `--expect topology.volume=32953.0~1.0`.

## Step 3 - read the report against what matters

Report in this order, because this is the order in which problems disqualify a file:

1. **Faults.** Each with its measured value and the expectation. An open edge or an over-used
   edge means the slicer will refuse the file regardless of how good the geometry is.
2. **Bodies, Euler characteristic, and genus.** More than one body means the solid is not what
   it appears to be. Euler must be even and no more than 2 per body -- but it is *not* expected
   to equal 2: every through-hole adds a handle, so a plate with two bolt holes is genus 2 and
   has Euler -2 by correct arithmetic. Genus is reported; pass `--genus N` to assert the hole
   count, which catches a bore that silently failed to punch through.
3. **Minimum wall.** Against the design floor. Say where the minimum occurs, not only its value.
   The measurement is an inward-ray screen: it catches gross thin walls, and it reads a chord
   rather than a throat inside a fillet, so treat it as a screen and not a certificate.
4. **Overhang area, with the build axis stated.** A number without its axis is not a number.
5. **Dimensions and volume**, against the parameter table if one exists.
6. **Vertex digest.** The value to record and to diff later.

When the auditor and an upstream harness disagree, that disagreement is the finding. Do not
average them or pick the friendlier one — establish which is measuring the shipped artifact.

## Step 4 - compare, when asked

```bash
python3 "$S/mesh_audit.py" before.stl --compare after.stl
```

Read the digest match first. Identical digests mean the same solid, whatever the file bytes say —
triangle order and quad-diagonal choice vary run to run, so a file hash proves nothing. Different
digests are expected when a parameter changed and are a defect when nothing did.

Report the volume, vertex-count, and dimension deltas alongside, so a genuine change can be sized.

## Step 5 - render, when a scalar is not enough

If a wall or overhang number is marginal, or the geometry is being reviewed rather than gated,
render it. Section views reveal internal voids and inside-thinning walls that no exterior view
shows.

```bash
python3 "$S/mesh_render.py" part.stl --sections 8 --axis x
python3 "$S/mesh_render.py" part.stl --thickness --clip-below 3.0
python3 "$S/mesh_render.py" part.stl --overhang --build-axis z
```

This needs pyvista, which is not a requirement of the plugin. If it is absent the script prints
the `uvx` invocation that would work and exits 3; run that rather than installing anything into
the user's interpreter without asking.

## Step 6 - repair only when asked, and never silently

Do not repair a mesh as a convenience. A file that needs repair has a generator that produced
bad geometry, and fixing the output leaves the cause in place. Report the fault and its likely
source first.

If the user does want a repair — a mesh from an outside source with no generator behind it:

```bash
python3 "$S/mesh_repair.py" clean in.stl out.stl --json repair.json
```

It refuses to write when the volume moves by more than half a percent, because a repair that
changes the solid is not a repair. Report the before-and-after table, and re-audit the output.

## Notes

- Say which checks were skipped and why. An audit that silently ran at Tier 0 reads as a full
  audit.
- `--gate` sets the exit code. Use it in any loop over variants so a failure cannot scroll past.
- For the founding reason this tool exists outside Blender, load `mesh-verification-gate`.

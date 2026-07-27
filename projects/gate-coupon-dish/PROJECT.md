# Gate Coupon Dish -- Project Memory

**Status:** **Built and verified.** `gate-coupon-dish_gen.py` generates the part
parametrically; `gate_coupon_dish.stl` is committed and its geometry is pinned in
`.claude/scripts/smoke.sh`.
**Last reviewed:** 2026-07-26 (rebuilt headless against Blender 5.2.0 LTS)
**Owner:** chrismandich

**Read `FACTS.md` first, including its banner.** This part asserts nothing about the
physical world; every dimension in it is a coverage choice.

## 1. Purpose

Give the repository a **hollow** fixture.

The regression net was one solid part, `projects/shade-bar-mount/`, plus its pinned
vertex digest. A solid part cannot exhibit the failures that dominate this
harness's history: `clean_mesh` turning a cavity inside out, the gate rejecting a
correct vessel as "inside out", an in-plane inset leaving `wall * cos(alpha)`, and an
aperture measured by the material beside it rather than by what passes through.

Every one of those was found by hand, on a project living outside this repository. Not
one of them could have been caught here. This part closes that.

## 2. Current state of the model

| | |
|---|---|
| generator | `gate-coupon-dish_gen.py`, one artifact, 14 gated checks |
| artifact | `gate_coupon_dish.stl`, 8288 triangles, 84 x 84 x 18 mm |
| vertex digest | `964be23728bc126c0f7c06eafca0ce6f` |
| material volume | 23924.4142 mm^3 |
| body model | 1 solid, 1 cavity, genus 1 |
| sealed void | -72.0 mm^3, a separate negative shell |

Regenerate with:

```bash
blender --background --python-exit-code 1 --python gate-coupon-dish_gen.py
```

`--python-exit-code 1` is not optional: Blender exits 0 on an uncaught exception, so a
failed build otherwise reports success to every caller. Set `DISH_OUT_DIR` to a scratch
directory for any experiment -- a build that fails its own acceptance **deletes** the
file at the output path, so a partially-failing regeneration destroys the committed
fixture rather than merely overwriting it.

## 3. Findings

**3a. Two hollow features are required, not one.** An aperture that reaches a cavity
merges it into the outer shell, leaving one body and no negative volume. A vessel with
only an open bowl reports `inverted_bodies = 0` and cannot exercise `expect_cavities` at
all -- the check would pass while measuring nothing, which is the failure class the
whole harness exists to prevent. Hence the open bowl *and* the sealed pedestal void.

**3b. The rim angle is the experiment.** At 45 degrees the perpendicular and in-plane
constructions differ by 29%. On a vertical wall they are identical, so a straight-sided
fixture would have contained the check and proved nothing by it.

**3c. The wall probe must follow the surface normal.** A radial cast on a sloped wall
measures a longer chord and reads *thicker* than the truth, under-reporting precisely
the defect the check exists for. The generator casts along the meridional normal,
`(-1, slope) / hypot`, rotated into each station's azimuth.

**3d. The independent verifier is what makes this fixture evidence rather than
decoration.** `gated_export`'s two tiers both call `mesh_audit`, so they are one
implementation run twice -- real coverage of the export path, but not a second opinion.
`inspect_model.py` shares no code, carries its own STL loader, quantises positions to a
different tolerance, and sums signed tetrahedra over every triangle. A flipped cavity
moves its answer by exactly twice the void. `smoke.sh` pins that number, and it is the
only assertion here that a bug inside `mesh_audit` could not also silence.

## 4. The real design problem

There isn't one, and saying so plainly is part of the job. The design problem was
*choosing numbers that make defects loud*, and it is recorded in `FACTS.md` section 5.

The one genuine tension is that the part must stay printable. A fixture that could not
be printed would stop modelling the artifact class the harness protects -- so the rim
sits at the unsupported-overhang limit rather than past it, and the sealed void spans
6 mm, which bridges.

## 5. What this fixture may be used for

- Proving a change to `part_kit`'s hollow-geometry path did not regress. That is its job.
- Demonstrating the shell-and-open idiom; `construction-idioms.md` points here.

**Not** for any claim about a real requirement, tolerance or fit. It has none.

## 6. Next actions

- None outstanding. Built, gated, committed, pinned.
- If `part_kit.offset_rings`, `clean_mesh`, `triangulate_and_purge` or
  `mesh_audit.acceptance` change, rebuild and confirm the digest before assuming the
  change was safe. A moved digest here means real geometry moved: the digest is over the
  welded vertex set, not the bytes, so re-export noise cannot produce one.

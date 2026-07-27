---
name: mesh-verification-gate
description: Build and audit the acceptance gate that decides whether a generated solid may be exported. Use when a mesh passes every check but the slicer rejects it, when writing acceptance checks for a generator, when a mesh is reported watertight but is not, when choosing tolerances for geometric checks, when proving a generator is reproducible, or when auditing a verification harness for checks that pass without measuring anything.
---

# The gate that decides whether a solid ships

A harness reported `non-manifold edges 0` and printed 135 passing checks. The owner opened
the same file in Bambu Studio and got `Error: 2 non-manifold edges`.

Both were right. They were answering different questions.

**Blender counts faces per *topological* edge. A slicer reconstructs topology *by
position*.** Two vertices at the same coordinate but distinct in the authoring tool's data
structures are one vertex to the slicer, and the edges that meet there become one edge with
too many faces on it. The authoring tool's answer was true about its own data structure and
false about the file. The gate had passed for the project's entire history without ever
measuring what shipped.

Everything below follows from that.

## The four rules

**1. Gate on the exported bytes, read back from disk.** Not the in-memory mesh. Parse the
file the slicer will parse, and do it in code that shares not one line with the exporter —
an independent implementation catches the bugs a shared one hides.

**2. Weld by position before judging topology.** Reconstruct connectivity the way a consumer
will: exact coordinate match first, then a neighbour-cell union-find at a tolerance chosen
from the format's own precision floor. A binary STL stores float32, so its ulp near 50 mm is
a few times 1e-6 mm; a weld at 1e-4 mm sits comfortably above that noise and below any real
feature. Verify the choice is not load-bearing by sweeping it — if the answer moves with the
tolerance, the mesh is the problem, not the tolerance.

**3. Refuse and delete.** A variant that fails is not exported. If a stale file from a
previous run sits at that path, remove it, so a failing build can never leave an old
good-looking file behind for someone to pick up. When the file-level check fails *after*
writing, delete the file. There is an unavoidable window in which an unverified file exists
on disk; deleting on failure closes it, and is simpler to reason about than write-to-temp
then rename.

**4. Measure the mesh, never restate the parameter.** A check comparing `WRAP_DEG` to
`WRAP_DEG` proves the assignment operator works. Cast rays at the finished surface and gate
the number that comes back. In the worked example the nominal wrap was 170 deg and the
delivered wrap measured 177.9 to 194.3 deg across variants — the parameter never described
the part, and only measurement revealed it.

## Two tiers, two gates

| Tier | Runs where | Sees | Gates on |
|---|---|---|---|
| Mesh | inside the authoring tool, after the build | the finished in-memory solid | dimensions, fits, wall, structure |
| File | on the exported bytes, after writing | what the slicer sees | positional manifoldness, bodies, winding |

Both must pass. The mesh tier catches a part that is wrong; the file tier catches a part that
is right and unshippable. Neither substitutes for the other.

Run the mesh tier first so a dimensionally wrong variant never reaches export at all, then
export, then re-parse and run the file tier on what was actually written.

## The check inventory

Full list with tolerances and rationale: `references/check-inventory.md`. The structural
subset is unconditional — no printable solid is exempt. What a part may declare is its
*shape*, not whether it is checked:

| Check | Expected | Why it is not optional |
|---|---|---|
| open edges | 0 | a hole; the slicer has no inside to fill |
| over-used edges | 0 | three or more faces on one edge; the fault that shipped |
| winding flips | 0 | inside and outside are ambiguous |
| degenerate faces | 0 | zero area or repeated vertex |
| solids | the declared count, default 1 | positive-volume shells; too many is debris, too few is two parts fused |
| cavities | the declared count, default 0 | negative-volume shells; undeclared, it means the solid is inside out |
| Euler characteristic | even, and <= 2 per body | a closed orientable surface has `euler = 2 - 2g`; odd or above the bound means torn or non-orientable |
| genus | reported; gate it when known | counts through-holes; gating it catches a bore that silently failed to punch |
| total signed volume | > 0 | zero or negative means no material, or a cavity larger than its shell |
| null-volume bodies | 0 | a shell enclosing nothing |

### Three shapes, and the gate has to tell them apart

`bodies` is not the right primitive, and gating it at 1 was wrong in both directions. A shell
is **positive** if its signed volume is positive and **negative** — a cavity — if it is not,
so `bodies = solids + cavities`. Three shapes are legitimate:

| Shape | solids | cavities | example |
|---|---|---|---|
| solid | 1 | 0 | a bracket with bores |
| plate | N | 0 | ten clearance coupons on one bed |
| vessel | 1 | K | a bank, a housing, anything hollow |

Declare the shape. `--expect-solids N` and `--expect-cavities K`, or the same arguments on
`gated_export`. An exact count is strictly stronger than the old `--allow-multi-body`, which
survives as an alias meaning "do not gate the count": permitting any number catches debris
but not a plug fused to its socket, because fusing *lowers* the count.

**This gate previously preferred a corrupted part to a sound one, and that is the reason the
row above changed.** A correct vessel reports one negative shell, and the unconditional
`inverted_bodies == 0` rejected it as "the solid is inside out". Run `clean_mesh` with its
old unconditional `recalc_face_normals` and the cavity flips outward, the part becomes
silently solid — seven times the intended mass — and `inverted_bodies` reads 0, so the same
gate passes it. The one part that was built correctly was the one it refused.

On top of those sit the part-specific checks: envelope and bounding box, the mating
dimensions, minimum wall on the load path, clearance and drop-in fit, and the structural
safety factor. In the worked example that came to 55 checks per variant, 165 across three.

**Use two tolerance regimes and say which is which.** Tight — around 2e-3 mm — for
dimension-bearing geometry built from primitives, where any deviation is a bug. Loose —
around 0.05 mm — for form features that emerge from booleans and lofts, where the mesh
tessellation legitimately moves the surface. One blanket epsilon either passes real defects
or fails on tessellation noise. Groove-to-layer alignment in the worked example was gated at
1 micron, because that number is either exact or the feature is pointless.

## "Reported, not gated" is a category, and it must be labelled

Some quantities are worth measuring and wrong to enforce: the reproducibility digest,
overhang area, folded-face counts, sample coverage statistics. Print them, mark them
explicitly as reported rather than gated, and keep them out of the pass count.

The reason is not tidiness. A passing count reads as coverage. If a quantity is measured but
unenforced and that is not stated, a reader concludes it was checked. The worked example
names the category out loud at every site that uses it, and that convention is what lets
someone tell "passed" from "was never looked at".

## Reproducibility: the solid, not the file

Nine consecutive runs of unmodified source produced **nine distinct file digests**. Two
causes: triangle emission order varies because boolean and mesh operators hash by pointer,
and the diagonal chosen on an ambiguous planar quad can flip. Neither changes the solid.

The same nine runs produced **one digest per variant** from the sorted unique vertex set.

So: hashing the exported file to prove reproducibility carries no signal at all. Hash the
welded unique vertex set at reduced precision, report it, and diff *that* to answer "did my
edit change the solid". Report it, do not gate it — a legitimate parameter change is
supposed to move it.

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"

# audit one exported variant, gate the exit code
python3 "$S/mesh_audit.py" saddle_h0.stl --gate --json audit_h0.json

# did an edit change the solid, or only the triangle order?
python3 "$S/mesh_audit.py" before.stl --compare after.stl
```

`mesh_audit.py` is deliberately an *independent* implementation of the file tier, outside the
authoring tool: stdlib-only for the parse, weld, topology, and digest, with trimesh adding
mass properties, ray-cast wall thickness, and overhang area when present. Two tools agreeing
from different evidence is a much stronger claim than either alone. Its Tier 0 has no
dependencies for the same reason the in-tool gate has none — a gate that requires an install
step is a gate that gets skipped.

## How gates fail silently

Every one of these passed for a long time in the worked example. Audit for them by name.

- **The check measured the wrong invariant.** The founding case. Ask of every check: is this
  a property of the artifact, or of the tool that made it?
- **The check went vacuous.** A void-detection scan whose every sampled station takes an
  early-out branch reports success having tested nothing. It was disclosed rather than
  hidden, which is the right response, but a regression in exactly the mode it targets would
  not be caught. Report tested-versus-skipped counts so a check cannot quietly stop working.
- **A probe constant went stale.** A ray origin hard-coded at 20.0 mm was correct until a
  taper was added further out, after which it sampled air. Derive probe positions from the
  parameters they depend on.
- **One plane, forever.** Every ray fired at X=0, and X=0 was deliberately the centre of a
  ridge — so the sweep measured the ridge for the project's whole history and never the
  thinner groove floor beneath it. A second station found it. Ask which station is the
  *worst* case, not the convenient one.
- **A fix's side effect was never measured.** A corner-radius repair shipped dead-sharp
  corners and passed 165 checks across four iterations, while the file's own commentary
  argued the exclusion was correct. When a fix lands, measure what it changed, not only what
  it fixed.
- **The count grew and the coverage did not.** Adding checks in the plane you already sample
  raises the number and not the confidence.

## Documentation loses to code

The generator's own acceptance list is the specification of record. Where a written brief and
the executable check disagree, **the code wins** — which is precisely why the check has to be
worth that authority. Write the brief's acceptance section as a description of what the code
must measure, then make the code the thing that decides.

## Reference files

- `references/check-inventory.md` — every check with its expected value, tolerance regime,
  measurement method, and the failure it exists to catch.
- `references/positional-vs-topological.md` — the founding defect in full, why the two
  answers diverge, how to reconstruct slicer-side topology, and how to choose and validate
  the weld tolerance.

## Related

- `parametric-part-workflow` — Stage 6 is this gate.
- `blender-parametric-generator` — where the acceptance list lives and how the export is
  wired behind it.
- `/part-forge:verify-part` — run the audit on an existing mesh or STL, no Blender needed.
- `part-design-reviewer` agent — adversarial audit of a harness for the silent failures above.
- `print-tune-bambu` — the downstream slice check, a third independent line of evidence.

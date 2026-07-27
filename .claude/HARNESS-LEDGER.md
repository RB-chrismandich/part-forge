# Harness feedback ledger

Recommendations for the `part-forge` / `print-tune-bambu` plugin harness, raised while
*using* it rather than while reviewing it. This file is maintenance tooling for this
repository and is not shipped inside either plugin.

**What belongs here:** a defect or gap in the plugins' own scripts, skills, templates or
gates, found by building a real part with them. **What does not:** defects in a part
project. Those go in that project's `FACTS.md` section 7.

Each entry states what was expected, what happened, how it was found, and what would fix it.
Entries are never deleted; they are marked `FIXED`, `WONTFIX` or `SUPERSEDED` with a reason,
because a rejected recommendation is as useful to the next reader as an accepted one.

**Severity.** `high` = produces a wrong artifact while reporting success. `medium` = costs
real debugging time or hides a signal. `low` = ergonomics.

| # | Severity | Component | One line | Status |
|---|---|---|---|---|
| 1 | **high** | `part_kit.boolean` | any volume change counts as success, so a merged cutter reads as a completed cut | FIXED |
| 2 | medium | `part_kit.loft_solid` | n-gon caps make the default MANIFOLD solver fail, silently via #1 | FIXED |
| 3 | medium | `part_kit.positional_topology` | requires triangles, fails with an opaque unpack error on quads | FIXED |
| 4 | medium | `part_kit.Probe.thickness_at` | returns a plausible number when called from a non-surface point | FIXED |
| 5 | medium | `blender-parametric-generator` | no true-offset shell idiom; the obvious in-plane inset is wrong by cos(slope) | FIXED |
| 6 | **high** | `examples/generator_template.py`, fixtures | no hollow example, and no hollow fixture -- so nothing could catch #4, #5, #8 or #10 | FIXED |
| 7 | low | `new_part.py` templates | scaffolds section 3 and section 9 rows that can silently contradict each other | FIXED |
| 8 | **high** | `part_kit.clean_mesh` | `recalc_face_normals` turns any hollow part into a solid, silently | FIXED |
| 9 | medium | `gated_export`, `triangulate_and_purge` | hard-coded single-body assumption blocks any multi-part print plate | FIXED |
| 10 | **high** | `mesh_audit.acceptance` | the gate rejected a correct vessel and passed the corrupted one -- found while fixing #8 | FIXED |
| 11 | medium | `smoke.sh`, `saddle_gen.py` | nothing covered part_kit's Blender half, and the worked example is a fork of the kit | FIXED |
| 12 | **high** | `part_kit._face_groups` | grouped across four-face edges, hiding the flap debris this repo was founded on | FIXED |
| 13 | medium | `part_kit._group_volume`, `mesh_volume` | float32 about the world origin; the kit never took a precision fix the fixture already had | FIXED |
| 14 | medium | `smoke.sh` | the founding cross-implementation thesis was asserted in a comment and checked nowhere | FIXED |
| 15 | low | `part_kit.hull_solid` | leaves `geom_interior` vertices in the mesh; the version it was distilled from deletes them | FIXED |

Resolved 2026-07-26 on `emdash/harness-feedback-g2tdp`. part-forge 0.1.0 -> 0.2.0. Every
entry's resolution is recorded under its own heading below; #10 and #11 were raised during
that work and follow #9.

**Two of the ledger's own claims did not survive checking, and both changed the fix.** They
are recorded at the entries concerned: the argument for #8's safe default rests on
`winding_flips` catching an inverted cavity, and it does not; and #5's proposed signature
reproduces the second defect that same entry names. Neither weakens the entry -- #8 is if
anything worse than reported -- but a recommendation implemented verbatim would have been
wrong in both places.

---

## 1. `part_kit.boolean` treats any volume change as success -- `high`, FIXED

**Found:** 2026-07-26, building `projects/stormtrooper-helmet-piggy-bank`.

**Expected.** `boolean(target, cutter, "DIFFERENCE")` either removes material or raises. Its
own docstring is explicit about the risk it exists to manage: *"A boolean that silently does
nothing is the worst outcome available."*

**What happened.** The first `DIFFERENCE` of a cavity out of a helmet shell produced a solid
whose volume was **the exact sum of the two inputs** -- 820217.7 + 694257.9 = 1514475.7. The
cutter had been merged in as a second closed shell rather than subtracted. `boolean()`
returned normally. Six `Cannot execute ... have non-manifold geometry` warnings were emitted
by Blender to stderr and nothing in the harness read them.

**Mechanism.** `boolean()` retries across `(solver, "EXACT")` and accepts an attempt when:

```python
if abs(after - before) > NULL_VOLUME:
```

An absolute difference. When the MANIFOLD solver fails to execute, `_apply_modifiers` still
bakes the evaluated object, and the failed modifier contributes the cutter's geometry to the
result. The volume therefore *does* change -- it grows by the cutter's whole volume -- the
guard passes on the first attempt, and **the EXACT retry never runs.** The one solver that
would have worked is never reached, precisely because the broken one changed the number.

The guard tests that *something happened*. It needed to test that *the right thing happened*.

**Why it is `high`.** This is not a crash. It produces a mesh that is watertight, has zero
open edges, and passes several downstream checks. In this project the failure only surfaced
three stages later as `genus = -1`, and it took a stage-by-stage volume trace to attribute.
On a part whose acceptance list did not happen to include a genus check, it would ship.

**Fix.** Test the sign of the change against the operation, not its magnitude:

```python
EXPECTED = {"DIFFERENCE": -1, "UNION": +1, "INTERSECT": -1}
...
delta = after - before
if abs(delta) > NULL_VOLUME and delta * EXPECTED[operation] > 0:
    ...accept
```

A `DIFFERENCE` that increases volume is never correct and should fall through to the retry,
then raise. Worth adding to the raise message: the cutter's own volume, so a reader can see
at a glance that the result is `before + cutter` and recognise the merge signature.

**Resolved as proposed, both parts.** `VOLUME_SIGN` is module-level data, and the guard is
`abs(delta) > NULL_VOLUME and delta * VOLUME_SIGN[op] > 0` -- both halves, since the sign
alone would re-admit sub-tolerance noise pointing the right way. An unknown operation raises
`ValueError` rather than `KeyError`.

The message branches, because "nothing moved on either solver" and "moved the wrong way" have
opposite causes and opposite fixes. It prints the cutter's volume and every attempt's delta,
and when the result equals `target + cutter` within tolerance it names that as the merge
signature outright.

The secondary fix is in too. `_capture_fd2` redirects file descriptor 2 around the modifier
bake and attaches whatever Blender said to the exception -- `bpy` exposes no handle on it, so
reading the descriptor is the only way to recover it. It degrades to a no-op if the descriptor
cannot be duplicated: losing the diagnostic is survivable, losing stderr is not.

No currently-correct call was found that the sign table newly rejects. The two degenerate
cases -- a UNION whose cutter is already inside, an INTERSECT whose cutter contains the target
-- both give `delta == 0` and were already rejected by the magnitude test.

---

## 2. `loft_solid` emits n-gon caps the MANIFOLD solver rejects -- `medium`, FIXED

**Found:** 2026-07-26, same build.

**Expected.** A solid built by `loft_solid` is valid input to `boolean`, whose default solver
is `MANIFOLD`.

**What happened.** `loft_solid` caps each end with a single face spanning the whole ring:

```python
bm.faces.new(list(reversed(grid[0])))
bm.faces.new(grid[-1])
```

At `SEG_RING = 96` that is a 96-gon at each end. Blender's own `bmesh` reports the result as
impeccable -- 0 non-manifold edges, 0 non-manifold verts, 0 wire edges, 0 zero-area faces, 0
duplicate positions -- and `positional_topology` agrees: `bodies=1, euler=2, genus=0`. The
MANIFOLD solver rejects it anyway with `have non-manifold geometry`.

**Evidence.** Same two solids, four combinations:

| input | solver | result |
|---|---|---|
| n-gon caps | MANIFOLD | subtracted correctly *in isolation* |
| n-gon caps | EXACT | subtracted correctly |
| triangulated | MANIFOLD | subtracted correctly |
| triangulated | EXACT | subtracted correctly |

Note what this table does **not** say. In isolation every combination worked; the failure
only appeared in the full build sequence, which means the trigger is state-dependent and not
purely the cap topology. That is exactly why #1 matters more than this entry: the harness
should be robust to a solver that fails intermittently, and right now an intermittent solver
failure is indistinguishable from success.

**Fix.** Triangulate inside `loft_solid` and `prism` before returning, or fan-triangulate the
caps specifically. Cheap, removes a whole class of solver sensitivity. If that is unwanted,
`boolean()` should triangulate a working copy before handing it to the solver.

**Workaround in use.** The generator passes `solver="EXACT"` explicitly and asserts the
direction of the volume change itself, which is #1's fix implemented locally.

**Resolved, and this entry's own caveat is confirmed.** On Blender 5.2.0 LTS, MANIFOLD
subtracted a 96-gon-capped lofted cylinder correctly in isolation -- exactly as the table
above reports, and exactly why the entry is careful to say the trigger is state-dependent.

Triangulated anyway, in `_triangulate_ngons`, shared by `prism` and `loft_solid` and applied
to faces above four vertices so quad side walls are untouched. The reasoning is the
intermittency rather than a reproduction: a class of input that provokes a solver *sometimes*
is cheaper to remove than to detect, and detection here depends entirely on #1's sign guard.
Adds no vertices, so no pinned digest can move.

`boolean()` triangulating a working copy was the alternative and was not taken -- it pays the
cost on every boolean rather than once at construction, and leaves the n-gon in the object the
generator keeps handing to other things.

---

## 3. `positional_topology` fails opaquely on quad input -- `medium`, FIXED

**Found:** 2026-07-26, writing a stage-by-stage diagnostic.

**Expected.** Passing polygons to a topology auditor either works or says why not.

**What happened.**

```
File "mesh_audit.py", line 218, in topology
    for fi, (a, b, c) in enumerate(faces):
ValueError: too many values to unpack (expected 3)
```

The function requires triangles. Nothing in its signature, docstring or the calling wrapper
says so. In the generator this never bites, because `triangulate_and_purge` always runs
first -- which is exactly why it is easy to ship: the only callers who hit it are people
writing diagnostics, i.e. people already debugging something else.

**Fix.** Validate at the top of `positional_topology` and raise with the offending face:

```python
bad = next((i for i, f in enumerate(triangles) if len(f) != 3), None)
if bad is not None:
    raise ValueError(
        f"positional_topology needs triangles; face {bad} has {len(triangles[bad])} "
        f"vertices. Run triangulate_and_purge, or bmesh.ops.triangulate on a copy."
    )
```

**Resolved, at the frame that actually raises.** The guard went into `mesh_audit.py` as
`require_triangles`, called from `topology` and from `edge_lengths` -- which has the same
unpack and the same silence. The entry proposes putting it in `part_kit.positional_topology`,
but that is the wrapper; the traceback names `mesh_audit.py`, and a diagnostic written against
`mesh_audit` directly would have missed a guard placed upstream of it.

Kept deliberately even though, after #2, no in-repo path feeds an n-gon to the auditor. The
callers who reach this module with polygons are the ones writing a stage-by-stage diagnostic
-- people already debugging something else, for whom an opaque unpack error inside the
trusted auditor is the most expensive possible answer.

---

## 4. `Probe.thickness_at` is not honest about its precondition -- `medium`, FIXED

**Found:** 2026-07-26. Cost two false readings that both looked like real defects.

**Expected.** The docstring says *"Material thickness from a surface point along
`direction`"*, and its contract is that the caller supplies a point **on the surface**.

**What happened.** Called with points that were not on the surface, it returned confident
wrong numbers instead of `None`:

- From the part's axis `(0, 0, z)` casting outward, it returned `1.60` mm for a wall the
  model set at `2.64` mm. The ray's first hit was a coin-slot wall at `x = SLOT_W/2 = 1.6`,
  and `1.6` is a perfectly plausible wall thickness. It was read as a thin-wall defect and
  investigated as one.
- From `(x, y, -1.0)` casting up, it returned exactly `1.0000` for a floor modelled at `6.0`
  -- the distance from the ray origin to the bed plane. **Because the origin was 1 mm below
  the part, the check reported the origin offset back as a measurement**, and would have done
  so for any geometry whatsoever, including no geometry at all.

The second is the worse of the two: a check that returns a constant regardless of the model
is not a weak check, it is a fabricated one, and it read as a legitimate failure both times.

**Fix.** Two options, not exclusive:

1. Verify the precondition. Cast a short ray backwards from `point` first; if it does not
   immediately exit material, the point is not on the surface -- return `None` rather than a
   number.
2. Add a sibling `gap_at(point, direction)` for measuring a void, so the two intents are
   distinguishable at the call site. Both of the failures above were really "measure a void"
   questions being asked with the "measure material" tool.

**Related.** The reliable pattern that replaced both, and which is worth promoting into
`construction-idioms.md`: to measure an *opening*, cast a raster of parallel rays through it
and measure the width of the band that passes through, rather than measuring the mesh near
it. It answers the coin's question -- *can I fit* -- and it returns `None` when the feature
was never cut, which fails a gate instead of quietly passing one.

**Resolved: option 1 taken, option 2 declined, the "related" note promoted to the fix.**

`thickness_at` now verifies the precondition with `BVHTree.find_nearest` and returns `None`
when the point is not on the surface within tolerance. A backward ray was the suggestion; the
nearest-surface query answers the actual question ("is this point on the mesh") directly
rather than inferring it.

**`gap_at` was not built, deliberately.** It has `thickness_at`'s exact shape -- one origin,
one direction, one scalar -- so it would return a confident number from an origin the caller
misjudged, for precisely the reason `thickness_at` did. Shipping it would add a second
instance of the bug this entry exists to remove, and would let the ticket read as closed while
the idiom that actually worked stayed unwritten.

The raster is the API. `Probe.raster` sits beside `Probe.fan`, which already has the right
shape: it returns per-ray results and counts, not a scalar, so it cannot fabricate one. It
reports `span_u is None` when nothing got through, and `all_clear` when *everything* did --
which nearly always means the raster was aimed past the part rather than through it, and is
the same failure wearing a different hat. Documented in `construction-idioms.md` with the
station warning, since where to aim matters more than how many rays.

---

## 5. No true-offset shell idiom, and the obvious one is wrong -- `medium`, FIXED

**Found:** 2026-07-26. Cost one full build cycle and a `1.60` mm wall on a `2.64` mm nominal.

**Expected.** Hollowing a lofted solid is the single most common operation for any container
part -- a bank, a vase, a housing, an enclosure. `construction-idioms.md` covers profiles,
lofts, booleans, selective bevel, fillet mathematics and debris purge, but not this.

**What happened.** The obvious construction -- inset each ring in its own plane by the wall
thickness, and clamp the z range by the same amount -- is wrong wherever the surface is not
vertical, and it is wrong *quietly*, because in-plane it is exact. Verified numerically: for
this superellipse family the minimum in-plane distance between the outer ring and the inset
ring is `2.640` mm at every height, to three decimals. The perpendicular wall is not.

Where the surface slopes at `alpha` off vertical, the perpendicular wall is `d * cos(alpha)`.
On the upper dome that took a nominal 2.64 mm to a measured 1.60 mm.

**The limit case is the one to put in the docs, because it is not intuitive.** On a 45 degree
cone, insetting `d` horizontally *and* `d` vertically produces a surface **identical to the
original** and a wall of exactly zero. Radius `r = R - z`; inset gives
`r = (R - d) - (z - d) = R - z`. The construction that feels obviously conservative is
degenerate.

**Fix.** Add to `part_kit`:

```python
def offset_rings(rings, zs, d):
    """Rings offset `d` PERPENDICULAR to the lofted surface, not in-plane."""
```

computing the horizontal inset per ring vertex as `d * sqrt(1 + (dr/dz)**2)` by finite
difference, since `dr/dz` varies with direction on a non-circular section. A working
implementation is in `projects/stormtrooper-helmet-piggy-bank/..._gen.py` as `slope_inset()`
and `shell_rings()`, and should be lifted rather than rewritten.

**Also worth documenting separately:** the floor of a container is usually *not* the wall
thickness. Here it carries the bayonet ledges and is 6.0 mm against a 2.64 mm wall. Letting
`z_bottom` default to the wall inset was a second, independent defect in the same function.

**Resolved, with the proposed signature rejected.** `offset_rings(rings, zs, d)` as written
above carries this entry's own second defect: a single `d` cannot express a 6.0 mm floor under
a 2.64 mm wall, so implementing it verbatim ships the bug the entry names eleven lines later.

The signature is `offset_rings(rings, zs, wall, *, floor, ceiling)` -- keyword-only, and
**no default on either**. Omitting one is a TypeError at the call site, which is the only
failure mode in this area that cannot reach a printer.

Lifted the math, rewrote the plumbing, as recommended: `slope_inset` and `shell_rings` close
over `ring_at`, `H_TOTAL` and `PROFILE`, so a verbatim lift would have given `part_kit` a
function that works for one project's globals. The slope is taken along each vertex's own
inward normal rather than a radial distance, which drops the assumption that the section is
centred on the origin. Added the guards the original lacks: a ring-count raise, a
strictly-increasing-z raise, an inversion check, and a point-in-polygon check per inset vertex
for the concave case.

The 45 degree cone limit is now an assertion, not only prose: `kit_smoke.py` builds one and
checks that the horizontal inset is `wall * sqrt(2)` and the perpendicular wall is `wall`.

---

## 6. No hollow example, and no hollow fixture -- `high` (re-rated), FIXED

`examples/generator_template.py` builds a wall bracket: a solid assembled by unions with
holes cut through it. Every idiom it demonstrates is one this project could not use directly.

A container part needs shelling, an opening whose *aperture* is the specification rather than
its material, a cavity that must be reachable from more than one opening, and a genus
assertion that is not simply the hole count. All four are absent, and the last is a trap: the
template's `a.exact("genus", t["genus"], g["N_HOLES"])` is right for a plate with bores and
wrong for anything hollow. A hollow shell with two openings is a pipe -- genus 1 -- and a
reader adapting the template will reach for the hole count.

**Fix.** A second, smaller example, or a section in `construction-idioms.md` covering the
shell-and-open pattern with the genus reasoning spelled out.

**Resolved, and RE-RATED from `low` to `high`.** The documentation half was never the
important half. This entry was the only one whose fix produces *coverage* for the others, and
filing it under ergonomics was the mistake -- with it open, #4, #5, #8 and #10 were all "fixed"
with nothing in the repository able to notice them coming back.

Documentation, done: a shell-and-open section in `construction-idioms.md`, the aperture idiom
beside it, and the template now declares `solids` and `cavities` rather than `bodies`, with an
explicit warning at the genus line that genus equals the hole count only for a solid with
bores -- a vessel with two openings is genus 1 whatever its bore count.

**The fixture, done: `projects/gate-coupon-dish/`.** A shelled dish, 84 x 84 x 18 mm, exported,
committed, and pinned in `smoke.sh` at digest `964be23728bc126c0f7c06eafca0ce6f` and volume
23924.4142 mm^3. Four properties are load-bearing and each one is a different ledger entry:

| feature | value | catches |
|---|---|---|
| rim at exactly 45 degrees | slope 1.000 | #5 -- an in-plane inset reads 1.4142 of a 2.000 wall |
| floor thicker than the wall | 6.00 vs 2.00 | #5's second defect, the floor defaulting to the wall |
| drain slot through the floor | 4.0 mm aperture | #4 -- measured by what passes through it |
| sealed void in the pedestal | -72.0 mm^3 | #8 and #10 -- a negative shell that must stay negative |

**Two hollow features, not one, and this is the non-obvious part.** An aperture that reaches a
cavity merges it into the outer shell: one body, no negative volume. A vessel with only an open
bowl reports `inverted_bodies = 0` and cannot exercise `expect_cavities` at all -- the check
would pass while measuring nothing, which is the exact failure class this ledger is about. So
the bowl is open and the pedestal void is sealed, and they are kept apart geometrically.

**Proven to be able to fail**, which is the only thing that makes any of it worth committing:

| defect reintroduced | result | failing checks |
|---|---|---|
| `clean_mesh(recalc_normals=True)` | refused, no STL | `solids`, `cavities` |
| naive in-plane inset | refused, no STL | `rim_wall_perpendicular` read **1.4142** = 2.0*cos(45) |
| slot never cut | refused, no STL | `genus`, `aperture_was_cut`, `drain_aperture_w` |
| unmodified | exported | none |

And from the bytes alone, with the gate bypassed: a flipped cavity gives volume **24068.4142**,
which is the pinned value plus exactly twice the void, and `inspect_model.py` -- sharing no code
with `mesh_audit` -- independently reports 24068.0. That last number is the only assertion in
the set that a bug inside `mesh_audit` could not also silence, which is why `smoke.sh` pins it.

`repo_check.py`'s fixture check was globbing-generalised in the same change; it named
`shade-bar-mount` literally and is the only checker in the file that looks at `projects/` at
all, so without that edit the gate would have printed CONSISTENT without ever opening the new
directory.

---

## 7. Scaffolded templates can contradict themselves silently -- `low`, FIXED

`new_part.py` writes a `FACTS.md` whose section 3 invites an envelope row like *"must print
in one piece, no splitting, no glue seam"* and whose section 9 invites settled-scope rows for
decisions like the retrieval method. In this project those two were filled in as *one piece*
and *twist-lock plug* respectively -- and a twist-lock plug is a second printed piece by
definition. They contradicted each other from the moment both were written.

`repo_check.py` passed throughout, correctly: it is a structural gate and this is a semantic
contradiction. `plugin-drift-auditor` reconciles documents against artifacts, but there was
no artifact yet.

**Fix, if any.** Probably not a code fix. A line in `measured-facts-discipline` under *Things
that make the ledger worse* would cover it: **a row in section 3 that constrains the part
count, and a row in section 9 that chooses a mechanism, must be read against each other --
the envelope section is about the shell, not about the assembly.** Low value alone; recorded
because it is cheap and because the next reader will hit the same shape.

**Resolved as proposed, no code change.** Added to *Things that make the ledger worse* in
`measured-facts-discipline`, with one addition the entry does not make: the precedence rule
does not adjudicate this. `FACTS.md` beats `PROJECT.md` orders *files*, and both rows live
inside `FACTS.md`, so the contract returns no answer for the case that actually occurred. The
new line says which wins -- the envelope constrains the shell, not the assembly -- rather than
only noting that the two must be read together.

---

## 8. `clean_mesh` destroys hollow parts -- `high`, FIXED

**Found:** 2026-07-26, building the helmet's shell. Cost roughly half the debugging on this
project, and produced three separate symptoms that each looked like an unrelated bug.

**Expected.** `clean_mesh(obj, dist)` is documented as the thing to run between boolean
stages -- *"Coincident-but-distinct vertices accumulate across operations and the next boolean
chokes on them"* -- and that part is true and necessary.

**What happened.** It ends with:

```python
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
```

`recalc_face_normals` orients every face to point away from its own connected component. For
a solid that is a repair. For a **hollow** solid it is corruption: a cavity's surface must
face *inward*, into the material, and recalc turns it outward.

One call after hollowing the helmet, the signed volume went from **126326 to 1514548** -- the
outer solid plus the cavity, rather than minus it. The mesh remained manifold, watertight,
one body, zero open edges, zero winding flips by positional audit. Nothing looked wrong.

**Why it is `high`, and why it is worse than #1.** The next boolean treats the cavity as
material. In this build the slot cut then removed the entire cavity and produced a **solid**
helmet - 784795 mm3 of PLA instead of 110980 - which still passed most of the acceptance
list. The three symptoms it produced were:

- a 0.25 mm wall reading (the probe found a slot wall, not a shell)
- `slot_was_cut = 0` (there was no slot opening because there was no cavity to open into)
- `genus = 0` instead of 1

Each was investigated as its own defect. None of them named the cause. A part that is
*silently 7x heavier and completely solid* is the kind of thing that reaches a printer.

**Fix.** Split the two concerns, because only one of them is "cleaning":

```python
def weld(obj, merge_dist=5.0e-3):
    """Weld coincident vertices. Does not touch orientation."""
    ...remove_doubles, dissolve_degenerate...

def clean_mesh(obj, merge_dist=5.0e-3, recalc_normals=True):
    """...recalc_normals=False for any part with an internal cavity."""
```

Default `recalc_normals` to `False` if a compatibility break is acceptable, since the EXACT
boolean solver already emits consistent winding and `winding_flips` in the acceptance list is
what proves it. At minimum, the docstring must say that this function is unsafe for hollow
geometry -- currently nothing anywhere does.

**Related documentation gap.** `construction-idioms.md` says *"Weld between boolean stages"*
and points at `clean_mesh`. For any container part that advice is actively harmful.

**Resolved, and one premise corrected.** Reproduced exactly on a 20 mm cube with a 14 mm
concentric cavity: 5256 -> 10744 mm3, which is 8000 + 2744.

The correction matters, because it is the argument this entry uses to justify the safe
default. **`winding_flips` does not catch this.** It reads 0 before and 0 after. It counts a
directed edge traversed twice, which detects adjacent faces disagreeing; a uniformly flipped
component contains no such pair, so a wholly inverted cavity is invisible to it. `open_edges`,
`over_edges`, `genus` and `bodies` are all unchanged too. The only number that moves is
`inverted_bodies`, 1 -> 0 -- so the corruption's sole witness is the count it erases. See #10,
which is the other half of this and was found by measuring it.

The default is `recalc_normals=False` regardless, but on the stronger ground that no gate
catches the failure rather than that one does. `weld_verts` is the orientation-free weld;
`clean_mesh` returns the volume either side, because a repair that changes the artifact and
reports nothing is the same failure in a smaller frame.

**One site this entry did not name.** `triangulate_and_purge` ended with the same
unconditional `recalc_face_normals`, one stage later and directly on the export path. It is
under the same flag with the same default now. It was unreachable for a sealed cavity only
because the single-component raise in #9 rejected the part first -- so fixing #9 alone would
have armed it.

---

## 9. Single-body assumption blocks multi-part print plates -- `medium`, FIXED

**Found:** 2026-07-26, building the bayonet clearance ladder - five socket-and-plug pairs on
one plate, which is ten disjoint solids by design.

**Expected.** A plate of test coupons is an ordinary thing to generate. It is arguably the
*most* ordinary thing, since it is how any clearance, tolerance or bridging question gets
answered empirically, and this repository's whole method is to print the question.

**What happened.** Two independent hard-coded assumptions:

1. `triangulate_and_purge` raises outright:

   ```
   RuntimeError: triangulate_and_purge: expected 1 solid component, found 10
   with volumes [4640.889863, 4640.889735, ...]
   ```

   Note the volumes: five identical sockets and five plugs decreasing by rung. The ladder was
   entirely correct and the helper refused it.

2. `gated_export` then calls:

   ```python
   faults = mesh_audit.acceptance(report, {}, allow_multi_body=False)
   ```

   with the flag **hard-coded**, though `mesh_audit.acceptance` accepts it as a parameter and
   `mesh_audit.py`'s own CLI exposes it. A build whose 19 acceptance checks all passed was
   rejected with `file checks failed` and the STL deleted.

**Fix.** Thread the flag through rather than inventing new machinery:

```python
def gated_export(obj, filepath, accept, rotate_euler=None,
                 weld=WELD_POSITIONAL, allow_multi_body=False):
```

and give `triangulate_and_purge` an `expect_components=1` parameter, so a caller can say
`expect_components=10` and still get the debris purge and the volume assertion - which are
the valuable parts and are currently lost entirely when a caller works around it.

**Note on the workaround.** The ladder reimplements `gated_export`'s contract locally. That
is duplicated logic in a project script, which is exactly what `part_kit` exists to prevent,
and it will drift. Worth fixing upstream rather than leaving each project to copy it.

**Bonus, same area.** Gating `bodies` at an *exact expected count* turned out stronger than
`allow_multi_body` either way: it catches a plug fused to its socket as well as stray debris.
Worth promoting into `mesh-verification-gate` as the recommended check for plates.

**Resolved, taking the bonus as the main fix.** `triangulate_and_purge` gained
`expect_components`, `gated_export` gained `expect_solids` / `expect_cavities`, and
`mesh_audit.acceptance` gained the same pair with `--expect-solids` / `--expect-cavities` on
the CLI. `--allow-multi-body` survives as the weaker "do not gate the count" alias, so no
documented flag disappeared.

**A landmine inside the proposed fix.** `stats["volume"]` was `kept[0][0]` -- the *largest*
surviving component -- while the assertion below it compared that against `vol_before`, a sum
over all of them. Lifting the single-component raise without touching this converts a
correct-but-overzealous rejection into an incorrect one that fires on every legitimate plate,
with a more confusing message. It now sums over kept components, which is also the right
quantity for a mass estimate and for a vessel's material volume. The assertion was rewritten
to say what it actually means: the dropped total must be debris, not geometry.

**Also unpinned on the same two lines,** since threading one argument through a call while
leaving its neighbours hard-coded is how a pass count grows without coverage growing:
`gated_export` passed `wall_samples=0` -- which returns `{"available": False}` and disabled
the file tier's only physical measurement at every call site in the plugin, with no caller
able to turn it on -- and `expect={}`, which disabled every expectation against the written
bytes. Both are parameters now. `wall_samples` still defaults to 0 because it is slow; the
difference is that it is a choice somebody can make.

---

## 10. The gate preferred a corrupted vessel to a correct one -- `high`, FIXED

**Found:** 2026-07-26, while building a reproduction for #8. Not reported from a build,
because no build ever got far enough to see it -- #9 refused the part one stage earlier.

**Expected.** A correctly built hollow part passes the acceptance gate.

**What happened.** It does not, and never could. `gated_export` on a correct sealed vessel --
a 20 mm cube with a concentric 14 mm cavity, signed volume 5256 mm3, built entirely by the
plugin's own helpers -- returns:

```
{'exported': False, 'reason': 'file checks failed', 'faults': [
  {'check': 'inverted_bodies', 'got': 1, 'want': 0,
   'why': 'negative signed volume -- the solid is inside out'},
  {'check': 'bodies', 'got': 2, 'want': 1,
   'why': 'stray shells print as debris; pass --allow-multi-body if intended'}]}
```

`inverted_bodies` was in `STRUCTURAL_GATES`, gated unconditionally at 0, with **no escape
hatch of any kind** -- not a CLI flag, not a parameter. So #9's proposed fix, threading
`allow_multi_body` through, would have cleared the second fault and left the first. A vessel
would still have been unexportable, and the entry would have closed.

**Why it is `high`, and why it is the sharpest statement of #8.** A cavity has negative signed
volume *because it is correct*. Run #8's `recalc_face_normals` and the cavity flips outward:
the part silently becomes solid, seven times the intended mass -- and `inverted_bodies` reads
0, so this gate **passes it**.

The gate rejected the part that was built correctly and accepted the one that was destroyed,
using the same check, in the same direction, for the same reason. Every other structural
number agreed with it: `bodies`, `open_edges`, `over_edges`, `winding_flips` and `genus` are
identical either side of the corruption.

**Fix.** A stated body model rather than a patched row. A shell is positive (a *solid*) or
negative (a *cavity*), `bodies = solids + cavities`, and three shapes are legitimate: a solid
(1, 0), a plate of N coupons (N, 0), a vessel (1, K). `inverted_bodies` left
`STRUCTURAL_GATES` and became `expect_cavities`, defaulting to 0 so an ordinary part gates
exactly as before. Total signed volume is now asserted `> 0` directly -- it used to be implied
by requiring every body positive, and that implication is gone once cavities are legal.

**Note on the shape of this defect.** Three documented rows in
`mesh-verification-gate/SKILL.md` -- under a heading asserting the structural subset is
"unconditional, no printable solid is exempt" -- were each falsified by a different one of
#6, #8 and #9. Patched as three separate commits, the table would have ended up permitting N
bodies while still requiring every body positive, which blocks the exact cavity #8 exists to
make legal. `repo_check.py` cannot see that: it is a structural gate and this is a semantic
contradiction, which is #7's observation turned on the plugin's own documentation.

---

## 11. part_kit's Blender half had no coverage, and the worked example is a fork -- `medium`, FIXED

**Found:** 2026-07-26, establishing a baseline before changing anything.

**Expected.** The regression net covers the functions that produce artifacts.

**What happened.** Two independent gaps that compound.

`smoke.sh` states in its own header that nothing in it "writes inside the repo, needs the
network, or needs Blender". That is the right contract for a gate meant to run anywhere, and
the consequence is that `boolean`, `clean_mesh`, `triangulate_and_purge`, `gated_export` and
`Probe` -- every function in this ledger that has ever produced a wrong artifact -- had **zero
automated coverage**, before or after any fix here.

The pinned vertex digest does not close it. The digest hashes committed bytes on disk, and
`projects/shade-bar-mount/saddle_gen.py` **does not import `part_kit`**: it carries its own
inlined `prism`, `loft_solid`, `boolean`, `_apply_boolean`, `clean_mesh` and
`triangulate_and_purge`. The repository's one worked example is a fork of the kit. So a kit
fix does not reach it, a kit regression does not show up in it, and `CLAUDE.md` pointing
readers at it as the worked example is pointing them at code that still demonstrates all nine
defects.

**Fix, partial.** `.claude/scripts/kit_smoke.py` and `kit_smoke.sh`: 44 assertions, opt-in,
Blender-dependent, separate from `smoke.sh` so that script's portability contract is intact.
It asserts the fixed behaviour of #1 through #10, including the 45-degree-cone limit case and
the escape hatch on #8 still being destructive when asked for. Blender exits 0 regardless of
what happened inside it, so the verdict travels back through a status file.

**Resolved, and the conclusion is the opposite of the one this entry assumed.**

First, the premise was checked rather than believed: all three variants regenerate from
`saddle_gen.py` with **identical** vertex digests and volumes. The fixture is reproducible, so
any reconciliation is verifiable -- a moved digest has a named cause or the change is wrong.

Reconciling turned out to be mostly the wrong direction. Splitting the file in half settles it:

- The **verification** half -- `stl_triangles`, `stl_manifold`, `stl_acceptance` -- re-opens the
  exported bytes, rebuilds topology by position, and computes its own digest, sharing no code
  with `mesh_audit`. That is a third independent opinion on the artifact, which is the method
  this repository is built on. It must never be deduplicated, and it now carries a comment
  saying so, because it reads as obvious duplication to anyone who has not been told.
- The **construction** half is a producer, not a verifier, and the thesis says nothing in its
  favour. Only `boolean` was worth moving: the fixture's own guard accepted any boolean where
  the **vertex count** changed, which is #1 wearing a different disguise -- a declined solver
  bakes the cutter in, the count moves, the guard passes, and the EXACT retry never runs. It
  now delegates to `part_kit.boolean`. Verified digest-neutral on all three variants before
  landing. This is also what makes the pinned digest able to notice a kit regression at all,
  which is what this entry actually wanted.

Everything else stays forked, on evidence rather than caution:

- `clean_mesh` -- swapping it MOVES the digest. `part_kit.weld_verts` adds
  `dissolve_degenerate` at `merge_dist`, and the fixture's smallest legitimate edge is
  **0.0050583 mm** against a threshold of **0.005**: 1.2% of margin. It removed 14 vertices and
  0.0019 mm^3 of real material. Also, the saddle has no cavity, so its unconditional
  `recalc_face_normals` is a correct repair here -- aligning it to the kit's `False` default
  would need an explicit `True` just to preserve behaviour, which is dedupe making a call site
  worse.
- `triangulate_and_purge` -- the fixture's version is *ahead* of the kit's. See #12 and #13.
- `circumscribed_circle`, `rounded_rect`, `corner_fillet` -- deliberately divergent, and each
  divergence is load-bearing. `circumscribed_circle` is rotated 90 degrees so a flat facet
  lands at the trough's rest point rather than a tessellation valley.

**The remaining gap is now closed differently than proposed.** "Nothing compares the two
implementations" was the half of this entry that the thesis actually requires, and it needed no
reconciliation at all -- see #14.


---

## 12. `_face_groups` grouped across four-face edges -- `high`, FIXED

**Found:** 2026-07-26, while testing whether `saddle_gen.py` could be reconciled with the kit.

**Expected.** The purge separates debris from the solid the way a slicer would.

**What happened.** Swapping `part_kit.triangulate_and_purge` into the fixture generator aborted
the h+2 build:

```
RuntimeError: triangulate_and_purge: expected 1 component(s),
found 2 with volumes [32846.705386, 3e-05]
```

The fixture's own purge accepts the same mesh. Both use the same 1e-6 threshold, so the two
implementations disagreed about **connectivity**, not about size.

**Mechanism.** `part_kit._face_groups` walked every `edge.link_faces` regardless of how many
faces the edge carried -- and its docstring said "by shared vertices", which is a third thing it
also did not do. `saddle_gen._face_groups` unions only across edges with **exactly two faces**,
and documents why: an edge with four faces is not a join, it is a fault, so anything hanging off
the solid through one is a separate body.

**Why it is `high`.** The four-face edge is this repository's founding defect -- the "2
non-manifold edges" Bambu Studio refused while the generator reported zero. The kit's grouping
absorbed exactly that flap into the shell, so the purge could not see the one thing it exists to
find. The fixture's implementation, written first, already had it right; the kit was distilled
from that file and lost it on the way.

**Fix.** Ported `saddle_gen`'s union-only-across-two-face-edges grouping into `part_kit`, and
corrected the docstring. `kit_smoke.py` now builds a flap on a four-face edge and asserts it
comes out as a separate body.

---

## 13. The kit never took a precision fix the fixture already had -- `medium`, FIXED

**Found:** 2026-07-26, same investigation.

**What happened.** `part_kit._group_volume` and `mesh_volume` both summed
`a.dot(b.cross(c))` over **mathutils** vectors about the **world origin**. `mathutils` is single
precision. `saddle_gen._signed_volume` sums about each component's **own centroid** in float64,
and its docstring records exactly why: a back-to-back pair 23 mm out came back at 9.5e-06 mm^3
instead of zero, "enough to make null debris read as a solid body and abort the build".

`part_kit.py`'s own header says it was "distilled from a working shade-bar saddle generator".
This is a fix that existed in the original, was measured and written down there, and did not
survive the distillation.

**Fix.** Ported the recentred float64 kernel into `_group_volume`; `mesh_volume` now delegates
to it rather than keeping a second copy.

**Honest limit on the evidence.** A synthetic back-to-back flap cancels *exactly* even in
float32, so it does not discriminate, and a well-conditioned solid 1200 mm from the origin
measures to within 3.6e-12 -- six orders below `NULL_VOLUME`, not above it. The claim that this
routine's noise floor generally exceeds the guard's threshold is **not** supported. What is
supported is the specific documented case, and #12's abort. The fix is cheap and removes a class
of error; it is not the dramatic one it first looked like, and the regression test in
`kit_smoke.py` is #12's grouping assertion rather than a volume one, because that is the
assertion that actually discriminates.

---

## 14. The founding thesis was asserted in a comment -- `medium`, FIXED

**Found:** 2026-07-26.

**Expected.** `CLAUDE.md` states that `inspect_model.py` and `mesh_audit.py` overlap on purpose
so neither can validate the other's bug, and that this is the evidence the repository runs on.

**What happened.** `smoke.sh`'s "cross-plugin agreement" section says in a comment that "its
agreement with `mesh_audit` is the cross-check the repo is built on", and then checks that
`inspect_model` **exits 0**. Nothing anywhere compared a single number the two produce. Both
would have kept passing while disagreeing about every quantity they measure.

Citing the passing assertion count as evidence the thesis holds was citing a comment. That is
the plugin's own named failure -- a check that passes without measuring what it claims -- sitting
inside the harness that exists to catch it.

**Fix.** `smoke.sh` now compares volume, triangle count, open edges, degenerate triangles and
all three bounding-box dimensions between the two, on the same bytes. They agree. The agreement
is meaningful rather than tautological because the two disagree on method: `inspect_model` has
its own STL loader and quantises to 3 decimal places, `mesh_audit` welds at 1e-4 mm.

Verified by negative control -- fed `h0`'s inspection against `h+2`'s audit, the check fails on
volume and dimensions as it should.

---

## 15. `hull_solid` leaves interior vertices in the mesh -- `low`, FIXED

**Found:** 2026-07-26, same fork inventory.

`bmesh.ops.convex_hull` returns the points it swallowed as `geom_interior` and leaves them in
the bmesh. `saddle_gen.hull_solid` deletes them; `part_kit.hull_solid`, distilled from it, does
not. A vertex belonging to no face is invisible in the viewport, survives export, and reappears
downstream as a loose vertex -- which `mesh_audit` gates under `null_volume_bodies` and `loose
vertices`. Masked in the fixture only because its hull is consumed immediately by a boolean.

**Fix.** Deleted, matching the original.

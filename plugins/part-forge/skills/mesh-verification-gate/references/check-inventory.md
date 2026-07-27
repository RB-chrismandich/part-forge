# Check inventory

Every check a part gate should carry, grouped by tier. Each row names the failure it exists
to catch, because a check whose failure mode nobody can state is a check nobody can tell is
working.

The example column carries real measurements from the shade-bar saddle's `verify_report.json`
so the magnitudes are concrete. The check names are part-agnostic; the numbers are not.

## Tolerance regimes

One blanket epsilon either passes real defects or fails on tessellation noise. Three regimes
cover every check worth writing.

| Regime | Value | Applies to | Reasoning |
|---|---|---|---|
| tight | 2e-3 mm | dimension-bearing geometry built from primitives | the vertex was placed by arithmetic; any deviation is a bug, not noise |
| loose | 5e-2 mm | form features emerging from booleans and lofts | tessellation legitimately moves the surface; a tight bound fails on segment count |
| exact | 1e-3 mm | layer-pitched features | the groove lands on a layer boundary or the feature is pointless; measured error was 6.7e-07 mm |
| structural | equality | counts, flags, topology | 0 is 0; there is no tolerance on "how many holes" |

The regime belongs in the check declaration, not in a comment. `Acceptance.tight()` and
`Acceptance.loose()` in `scripts/part_kit.py` exist so the choice is visible at every call
site and auditable in one grep.

## Tier 1 - Structural, unconditional

No printable solid is exempt. These run on the **exported bytes** after positional welding,
not on the in-memory mesh. Run them again in the authoring tool if convenient, but the file
tier is the one that decides.

| Check | Expected | Regime | How measured | Failure it catches |
|---|---|---|---|---|
| open edges | 0 | structural | undirected edge used by exactly one triangle | a hole; the slicer has no enclosed volume to fill |
| over-used edges | 0 | structural | undirected edge used by three or more triangles | the fault that shipped: coincident shells or a self-touch |
| winding flips | 0 | structural | a directed edge traversed twice | inside and outside are ambiguous; normals cannot be trusted |
| degenerate faces | 0 | structural | repeated vertex id, or zero area after welding | slicers divide by the face normal |
| bodies / solids | 1 | structural | connected components over welded vertices | stray shells print as debris; `saddle_h+2` shipped 3 components until the purge dropped 2 |
| Euler characteristic | even, <= 2 per body | structural | V - E + F on welded topology | a closed orientable surface has euler = 2 - 2g; odd means torn or non-orientable |
| genus = (2*bodies - euler)/2 | reported; gate when the hole count is known | declared | derived from Euler | counts through-holes. Do NOT gate at genus 0: a plate with two bolt holes is legitimately genus 2 and euler -2. Gating euler at 2 rejects most real brackets, and a gate that fails a sound part is as useless as one that passes a broken one |
| signed volume | > 0 | structural | divergence theorem over triangles | negative means the solid is inside out |
| null-volume bodies | 0 | structural | per-body volume below 1e-6 mm^3 | a closed shell enclosing nothing |
| minimum edge length | > 2e-3 mm | tight | shortest welded edge | example 5.05e-3 mm; below the floor, slicers emit arc-fitting errors |
| loose vertices | 0 | structural | vertices in no face | harmless in the viewport, noise on export |
| loose edges | 0 | structural | edges in no face | same |
| purge volume delta | 0 | tight | volume before and after debris removal | a purge that changed the volume removed something real |

Note the deliberate duplication in the worked example's report: `non_manifold_edges` and
`topo_non_manifold_edges`, `shells` and `topo_shells`. Those pairs are the topological answer
and the positional answer recorded side by side. Keeping both is right; gating on the
topological one is the founding defect. See `positional-vs-topological.md`.

## Tier 2 - Envelope and dimension

Everything the part must physically be. All tight unless the surface came from a boolean.

| Check | Expected | Regime | How measured | Failure it catches |
|---|---|---|---|---|
| mounting face width | design value | tight | face selection, extent along the axis | example 76.19999695 against 76.2 |
| mounting face height | design value | tight | extent along the other axis | example 44.45000076 against 44.45 |
| mounting face planarity | 0 | tight | max absolute offset normal to the face | example 0.0; a bowed tape face bonds on its corners only |
| mounting face seated at origin | 0 | tight | minimum coordinate on the mount axis | example z_min 0.0; the datum must be where the model says |
| mounting face area | design value | loose | sum of selected face areas | example 3351.11 mm^2 = 5.194 in^2, the corner radii cost 1.1% of the nominal rectangle |
| overall height under cap | <= cap | tight | bounding box extent | example 44.45 against a 50.8 hard cap |
| bounding box within width | <= plate width | tight | bounding box | a feature that overhangs the mount is unmountable |
| bounding box floor | >= envelope bottom | tight | bounding box | example z_env_bot -5.7; the part must not foul what is below |
| projection from the mount plane | reported design value | loose | bounding box on the depth axis | example 45.35 mm; the silhouette, distinct from the moment arm |
| no material behind the mount plane | 0 | tight | maximum coordinate behind the datum | anything behind the tape plane prevents the part sitting flat |

## Tier 3 - Fit and clearance

The dimensions that decide whether the part mates with the thing it was built for. These are
the checks whose failure looks like success in the viewport.

| Check | Expected | Regime | How measured | Failure it catches |
|---|---|---|---|---|
| mating surface rest point | design value | tight | single ray at the seat | example -1.99997 against -2.0 |
| mating axis position, transverse | design value | tight | circle fit over a ray fan | example fit_y 31.74999975 against 31.75 |
| mating axis position, vertical | design value | tight | same fit | example fit_z 7.92481 against 7.925 |
| mating radius | design value | tight | same fit | example fit_r 9.92527 against 9.925 |
| circle-fit residual | < tight | tight | max deviation of any sample from the fitted radius | a good centre with a bad residual means the surface is not the arc it should be |
| fit sample count | >= design minimum | structural | count of rays that hit | example 79 samples; a fit over 4 points is not a fit |
| drop-in clearance | > 0 | tight | per-column ray against the analytic mating surface | example 0.39997 mm; a fillet that traps the part on assembly |
| delivered wrap angle | >= design floor | loose | ray sweep following the surface to the rim | example 187.1 measured against a 170.0 nominal, gated at >= 160 |
| chamfer or lead-in extent | design value | loose | ray fan to the distance discontinuity | example 0.788 mm both sides against 0.8 nominal |

The wrap row is the clearest instance of rule four. The nominal parameter was 170 deg. The
delivered wrap measured 179.95, 187.10 and 194.30 deg across the three variants. **The
parameter never described the part.** Only the measurement did, and the check gates the
measurement against a floor rather than against the parameter that named it.

## Tier 4 - Structural margin

| Check | Expected | Regime | How measured | Failure it catches |
|---|---|---|---|---|
| minimum wall on the load path | >= design floor | tight | radial ray fan, worst over all stations | example 3.4999976 against a 3.0 floor |
| wall sample count | >= design minimum | structural | rays that returned a hit | example 362 |
| angular span swept | >= expected | loose | extent of the sweep that hit | example 176.86 deg; a sweep that stopped early measured less than it claims |
| minimum wall per station | >= floor, each | tight | one figure per sampling station | example land 3.70000 at 28.14 deg, groove 3.49999 at 71.26 deg |
| bending safety factor | >= SF_MIN | loose | sigma = M*c/I at the worst station | example 36.48 against a required 8.0 |
| worst-section location reported | present | structural | the station that produced the minimum | a margin without a location cannot be re-checked after an edit |
| fillet radius, each | design value | loose | circle fit over the blend | example upper and lower reported separately |
| fillet centre offset | < loose | loose | fitted centre against analytic centre | a blend that drifted off its intended arc |
| fillet roundness | < loose | loose | r_max minus r_min over the fit | a blend that is an arc only on average |

The two-station wall check is the single most transferable row in this table. Every ray in
the original harness was fired in one plane, and that plane had been deliberately placed at
the centre of a ridge. It measured the ridge for the project's whole history. The groove
floor beside it, thinner and on the same load path, was first visited when a second station
was added -- and the groove is where the minimum actually is: 3.49999 mm against the land's
3.70000 mm.

## Tier 5 - Print-readiness

| Check | Expected | Regime | How measured | Failure it catches |
|---|---|---|---|---|
| layer-pitched feature count | planned == found | structural | edge detection along a marched depth profile | example planned 24, found 24 |
| layer-pitched feature depth | design value | tight | measured depth per feature | example 0.19999981 against 0.2 |
| layer-pitched feature width | design value | tight | measured width | example 0.39999987 against 0.4 |
| layer-pitched feature pitch | design value | tight | spacing between detected edges | example 1.0000 |
| layer alignment error | < 1e-3 mm | exact | distance from each edge to the nearest layer boundary | example 6.68e-07 mm; a half-layer phase error makes the feature a ridge instead of a groove |
| pitch is a whole number of layers | integer | structural | assert in derive(), before any geometry | catches the error at parameter time, for free |
| unsupported area | reported | note | face normals against the negative build axis | see Tier 6 -- measured, not gated |

## Tier 6 - Reported, not gated

Measured, printed, deliberately unenforced. **This tier must be visually distinct in the
report and excluded from the pass count.** A measured-but-unenforced quantity that is not
labelled reads as checked, and then a passing tally reads as a guarantee it never made.

| Quantity | Why measured | Why not gated |
|---|---|---|
| vertex-set digest | the only reproducibility claim worth making | a legitimate parameter change is supposed to move it |
| unsupported area | sizes the support burden and the scarring risk | the acceptable figure depends on orientation and material, not on geometry alone |
| folded faces | zero-thickness fins that no manifold check catches | example 107, of which 16 in the collar; disclosed as a residual, not a defect |
| sample coverage counts | proves the check looked at something | a low count is a warning about the harness, not about the part |
| purge statistics | components found, dropped, and the volume each carried | example h+2 found 3 components and dropped 2 carrying 0.0 mm^3 |
| moment arm and projection | the numbers a design review argues about | design outputs, not acceptance criteria |
| computed section properties | area, section height, section modulus | inputs to the safety factor, which is the gated quantity |

## Checks worth adding that this list did not have

Each of these is a gap the worked example exhibited, not a hypothetical.

**A coverage counter on every sampled check.** The void scan reported
`stations 61, tested 0` -- every one of the 61 sampled stations took an early-out branch, so
the check passed having measured nothing. It was disclosed rather than hidden, which is the
right response, but a regression in exactly the mode it targets would not be caught. Any
check that samples should report tested against skipped, and a check that tested zero should
announce itself as vacuous rather than as passing. `Acceptance.coverage()` in `part_kit.py`
does this by construction.

**A second sampling station wherever one plane was chosen.** If a check fires rays in a
single plane, that plane was chosen for a reason, and the reason is rarely "this is the worst
case". Add the station that is worst and gate on the minimum across both. When a feature is
periodic, sample at the crest and at the trough.

**Probe positions derived, never hard-coded.** A ray origin fixed at 20.0 mm was correct
until a taper was added further out, after which it sampled air and reported whatever the
fallback produced. Derive every probe position from the parameters that place the feature it
aims at, so adding geometry downstream cannot silently move the surface out from under the
ray.

**An assertion tying variant names to their offsets.** Names hard-coded as
`part_h-2 / part_h0 / part_h+2` against absolute values `0 / 2 / 4` encode a relationship to
the nominal default that nothing enforces. Changing the default silently mislabels every
exported file, and the label is what someone reads off the print. Assert
`value == nominal + offset` for each variant, or generate the names from the offsets.

**A post-fix delta check.** A corner-radius repair shipped dead-sharp corners and passed 165
checks across four iterations while the file's own commentary argued the exclusion was
correct. When a fix lands, diff the measured report against the previous run and require an
explanation for every quantity that moved, not only the one that was supposed to. The vertex
digest tells you whether the solid changed at all; the report diff tells you where.

**A check that the acceptance list itself grew in the right direction.** Adding checks in the
plane already sampled raises the count and not the confidence. Track which features have zero
checks against them, not only how many checks pass.

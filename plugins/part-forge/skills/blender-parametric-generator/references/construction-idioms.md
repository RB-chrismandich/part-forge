# Construction idioms

<!-- doc-type: reference -->
<!-- A lookup catalog of idioms keyed by the failure each prevents; readers arrive at one
     entry via search, not start-to-end, so this is a reference page, not an explanation. -->

Each entry states the failure it prevents before the technique, because the technique is
only memorable once the failure is. Working code for all of these is in
`examples/generator_template.py`; the helpers live in `scripts/part_kit.py`.

## Build profiles in 2D, then extrude or loft

**Failure prevented:** debugging a mesh instead of debugging a list.

A cross-section is a list of `(u, v)` tuples that ordinary arithmetic can produce, print,
plot, and assert against. Once it becomes a mesh it is a graph of vertex pointers, and a
wrong number is now a visual inspection problem. Keep every geometric decision in the 2D
layer, hand the finished polygon to `bmesh`, and the mesh layer stays dumb enough to trust.

The corollary is that the 2D layer must be importable without Blender, which is the whole
reason for the guarded `import bpy`. A profile function that can be exercised in a plain
interpreter can also be re-derived independently -- and independent re-derivation is how the
reference project confirmed its fillet mathematics to six decimal places.

Convention: profiles wound counter-clockwise, mapped into 3D by a caller-supplied `to3d`, so
the kernel holds no opinion about which axis is which.

## Circumscribe a bore, never inscribe it

**Failure prevented:** a hole the bolt does not fit through.

A regular n-gon whose vertices sit *on* a circle of radius `r` lies entirely inside that
circle except at the n contact points. Its edge midpoints fall short by the sagitta,
`r(1 - cos(pi/n))`. Cut a bore with that polygon and every flat is tight: at r = 2.25 mm and
n = 64 the bore is undersized by about 1.7 microns, which is nothing -- but at n = 16 it is
27 microns, and at n = 8 it is 0.17 mm, which is the difference between an M4 sliding
through and an M4 needing a drill.

Scale the radius so the polygon *contains* the circle:

```
r_poly = r / cos(pi / n)
```

Now the edge midpoints sit on the true circle and all the error is outside the intended
surface, where clearance lives anyway. `part_kit.circumscribed_circle` does this and offsets
the start angle by `pi/n` so a flat, not a vertex, faces the axes.

The same reasoning inverts for a **shaft**: a shaft cut with a circumscribed polygon is
oversized and will not enter its mating bore. Inscribe shafts, circumscribe bores, and write
down which one a given call is producing.

## Loft by hand for non-convex profiles; hull only when the result is convex

**Failure prevented:** a convex hull quietly filling in the concavity that was the point.

`bmesh.ops.convex_hull` is fast and robust and will happily swallow a C-section, a trough,
or anything with a re-entrant corner, returning a solid that passes every manifold check and
is the wrong shape. Use it only where the answer is genuinely convex -- a flared collar
between two convex rings, for instance.

Everything else gets stitched: quad each pair of adjacent rings, cap the ends, recalculate
normals. `part_kit.loft_solid` does this and raises when the rings differ in vertex count,
because unequal rings cannot close and the alternative to raising is a torn surface that
reports as boundary edges several stages later, far from the cause.

Equal ring counts are a real constraint on profile generation. A profile built from arcs
whose segment counts depend on radius will silently change vertex count between stations.
Fix the segment counts per feature, not per radius.

## Solve tangent fillets analytically; do not bevel a structural blend

**Failure prevented:** a ledge everywhere the junction is not square.

`bmesh.ops.bevel` cuts a constant-width chamfer along an edge. Where two surfaces meet at
90 deg that approximates a fillet; where they meet at 50 deg it does not, and the result is
a visible step with a stress concentration at its root -- precisely at the junction that
needed the blend.

For a corner at `P` where two surfaces leave along unit directions `u1` and `u2` separated by
angle `theta`, with bisector `b = unit(u1 + u2)`:

```
centre        = P + (r / sin(theta/2)) * b
tangent point = P + (r / tan(theta/2)) * u      for each of u1, u2
setback       = r / tan(theta/2)
```

The arc from one tangent point to the other is the fillet. Nothing here assumes a right
angle; at `theta = 90 deg` the setback collapses to `r`, which is the familiar case and a
useful sanity check.

Two things to assert. First, `theta` must not be degenerate -- at 0 or 180 deg no finite arc
exists, and `part_kit.tangent_fillet` raises rather than returning nonsense. Second, the
setbacks must fit: for two fillets on the same edge, `setback_1 + setback_2 < length`, or the
arcs overlap and consume the segment between them. Acute corners are where this bites,
because the setback grows without bound as `theta` falls. In the worked template a 3 mm
radius at a 48.7 deg corner sets back 6.63 mm -- more than twice the radius.

## Convex erosion is a 45-degree flare

**Failure prevented:** a taper that needs support, or a support-free taper computed twice.

Inset a convex polygon by `d` on every edge and sweep it a distance `d` along the sweep axis,
and the surface generated makes exactly 45 deg with that axis. Since 45 deg is also the
steepest overhang most FDM printers bridge unsupported, matching the erosion to the travel
satisfies the shape requirement and the printability requirement with one operation and one
number.

Growing faster than 1:1 asks the printer to bridge. Growing slower is free. So a collar
should shed at most 1 mm of radius per 1 mm of build travel, and the check for that is the
same arithmetic that produced it.

`part_kit.erode_convex` returns an empty list when the erosion consumes the profile. Check
for that rather than lofting an empty ring -- an empty ring is a `bmesh` error several frames
from its cause.

## Booleans: overlap, retry, and verify the volume moved the RIGHT WAY

**Failure prevented:** a boolean that silently does nothing, and the worse one that silently
does the opposite.

The worst boolean outcome is not a crash. It is a modifier that reports success, changes
nothing, and leaves a part that looks plausible and is wrong. The modifier will not tell you;
the volume will.

But the volume only tells you if you ask it the right question. This guard is not enough:

```
before = volume(target)
apply(solver)
if abs(volume(target) - before) > NULL_VOLUME:  accept        # WRONG
```

When a solver declines -- and MANIFOLD declines intermittently, on input that every other
tool calls perfect -- the failed modifier still bakes, and it contributes the cutter's
geometry as a second closed shell. So a DIFFERENCE comes back having **grown** by exactly the
cutter's volume. `abs()` is satisfied, the first attempt is accepted, and the EXACT retry
that would have worked is never reached. The broken solver is preferred *because* it moved
the number.

Removing material cannot grow a solid. The sign is a property of the operation:

```
EXPECTED = {"DIFFERENCE": -1, "UNION": +1, "INTERSECT": -1}
delta = after - before
if abs(delta) > NULL_VOLUME and delta * EXPECTED[operation] > 0:  accept
```

Keep both halves. Magnitude alone accepts the merge; sign alone re-admits sub-tolerance noise
pointing the right way.

`part_kit.boolean` does this, and its failure message distinguishes the two causes because
their fixes are opposite: "nothing moved on either solver" means the cutter missed, while a
result equal to `target + cutter` is the merge signature and means the solver declined. It
also captures Blender's stderr around the modifier bake and attaches it. Blender reports
`Cannot execute ... have non-manifold geometry` on file descriptor 2 and exposes it through
no Python API at all; six such warnings were emitted during the build that produced this
section and not one reached the exception.

Prefer an **overlap** to a coplanar butt joint. Two solids meeting exactly face-to-face give
the solver a degenerate case it may resolve into coincident-but-distinct vertices -- which is
the precise ingredient of the positional-versus-topological defect the whole plugin exists
around. Bury the joining feature by a fraction of a millimetre and the case disappears. The
template's gusset uses a 0.6 mm bite into both the plate and the shelf for exactly this
reason.

Apply the modifier through the depsgraph rather than an operator. Operator calls depend on
context that does not exist in `--background`, and the depsgraph path works identically in
both invocation modes.

## Weld between boolean stages -- but never recalculate normals on a vessel

**Failure prevented:** the third boolean failing because of debris from the first, and the
much worse one where the cleanup step silently fills the part in.

Each boolean leaves coincident-but-distinct vertices along its seams. They accumulate, and a
later operation chokes on geometry that looks clean in the viewport. A `remove_doubles` at a
few microns between stages costs nothing and keeps every stage seeing a tidy input.

Pick the weld distance well below the smallest real feature and well above float noise. Both
the reference and the template use 5e-3 mm. Record the range swept -- the reference tried
0.005 through 0.08 mm and found the outcome flat across all of it, which is worth writing
down so nobody repeats the experiment.

**The trap is what usually travels with the weld.** `bmesh.ops.recalc_face_normals` orients
every face outward from its own connected component. On a solid that is a repair. On a
vessel it is destruction: a sealed cavity is a separate component whose faces must point
*into* the surrounding material, and recalc turns them out.

Measured on a 20 mm cube with a concentric 14 mm cavity:

| stage | signed volume | what it means |
|---|---|---|
| after the cavity is cut | 5256 mm3 | 8000 - 2744, correct |
| after recalc | 10744 mm3 | 8000 + 2744, solid |

Nothing downstream sees it. `open_edges`, `over_edges`, `bodies` and `genus` are all
unchanged, and `winding_flips` reads **0 on both sides** -- a uniformly flipped component
contains no disagreeing adjacent pair, so the check that sounds like it covers orientation
does not cover this. The only number that moves is `inverted_bodies`, from 1 to 0, which is
to say the corruption's sole witness is the count it erases.

So `part_kit.clean_mesh` takes `recalc_normals` and it defaults to **False**, and
`part_kit.weld_verts` is the weld with no orientation pass at all. Reach for `weld_verts`
between stages. Pass `recalc_normals=True` only for a solid whose winding you actively
doubt, and read the volumes `clean_mesh` returns rather than assuming a repair was free.

The same call sat at the end of `triangulate_and_purge`, one stage later and directly on the
export path, and is now under the same flag with the same default.

## Shell a loft by offsetting PERPENDICULAR to the surface, never in-plane

**Failure prevented:** a 2.64 mm wall that measures 1.60 mm, and is exact in the plane you
checked it in.

Hollowing a loft is the commonest thing a container part needs -- a bank, a vase, a housing,
an enclosure -- and the obvious construction is wrong everywhere the surface is not vertical.

Inset each ring by `d` within its own plane, clamp the z range by the same `d`, and the
in-plane distance between outer and inner ring is exactly `d` at every height. Verified
numerically on the part that produced this section: 2.640 mm at every height, to three
decimals. The **perpendicular** wall, which is the one that gets printed, is `d * cos(alpha)`
where `alpha` is the surface's tilt off vertical. On the upper dome that was 1.60 mm.

**The limit case is the one to remember, because nobody derives it.** On a 45 degree cone,
insetting `d` horizontally *and* `d` vertically reproduces the original surface exactly and
leaves a wall of zero:

```
outer:  r = R - z
inner:  r = (R - d) - (z - d) = R - z          identical, wall = 0
```

The construction that feels obviously conservative is degenerate. Nothing about it looks
wrong, and every in-plane measurement of it agrees that the wall is there.

The correction is a horizontal inset of `d * sqrt(1 + m^2)` per ring vertex, where `m` is the
surface's outward run per unit rise at that vertex. Per **vertex**, not per ring: on a
non-circular section the slope varies with direction around the ring, so a single scalar per
height is already the wrong shape. `part_kit.offset_rings` takes it by finite difference
along each vertex's own inward normal, which needs no assumption about where the section is
centred.

**A container's floor is not its wall.** The part this came from carries bayonet ledges in a
6.0 mm floor under a 2.64 mm wall, and letting the floor default to the wall inset was a
second, independent defect in the same function. So `offset_rings` takes `floor` and
`ceiling` as keyword-only arguments with **no defaults**: omitting one is a TypeError at the
call site, which is the only failure mode in this area that cannot reach a printer.

It also refuses a wall that inverts the section, and refuses one whose inset vertices land
outside the outer ring -- the concave case, where a uniform offset self-intersects.

## Measure an opening with a raster, not with the mesh beside it

**Failure prevented:** a check that reports the ray origin's own offset back as a
measurement.

To ask whether a coin fits a slot, cast a grid of parallel rays through the slot and measure
the band that gets through. Do not measure the material near it.

The tempting alternative is a single ray and a single number, and it fails in a way that
reads exactly like a real defect. `thickness_at` called from a point that was not on the
surface returned 1.60 mm for a 2.64 mm wall -- the first hit was a slot wall at
`x = SLOT_W/2 = 1.6`, a thoroughly plausible thickness. Called from 1 mm below the part it
returned exactly 1.0000 for a 6.0 mm floor: the origin's own offset, which it would have
returned for any geometry whatsoever, including none.

A check that returns a constant regardless of the model is not a weak check. It is a
fabricated one, and it presented as a legitimate failure twice.

`part_kit.Probe.raster` returns counts beside the spans, and the counts are the honest part:

- `span_u is None` means **no ray got through** -- the feature was never cut. That fails a
  gate, where a scalar would have quietly returned something.
- `all_clear` means every ray passed, which nearly always means the raster was aimed past
  the part rather than through it. Aim it so a ray that misses the opening lands on solid
  material; otherwise "nothing blocked it" and "it went through the slot" are the same
  reading, which is the original bug wearing a different hat.
- The spans run between outermost passing ray **centres**, so they understate the true
  aperture by up to one pitch per side. Biased toward failing a marginal part, which is the
  right direction, but not a number to quote as the dimension.

The station matters more than the resolution. Pick where to aim before picking how many rays.

## Selective bevel: name the rules, and know what clamping costs

**Failure prevented:** a comment that lies, and a claim of cleanliness that is not true.

A cosmetic round-over is a bevel over a filtered edge set -- filtered by dihedral angle,
minimum edge length, adjacent face area, and proximity to features that must stay sharp.

**Name the rules; never number them in prose.** The reference carries a call-out about a
header reading "four rules" above a filter that tested six. A count in a comment is a claim
that rots the moment anyone adds a case, and unlike code it is never exercised.

`clamp_overlap=False` is often necessary, because clamping silently shrinks the radius
wherever geometry is tight and produces a bevel that varies without saying so. Turning it off
gets the requested radius and admits the possibility of self-intersecting spikes where
adjacent bevels collide. The reference ships with 36 such residual vertices at its final
settings -- measured, disclosed in the ledger, and judged acceptable, rather than eliminated
or hidden. Guard the operation with a bounding-box growth assertion so a bevel that explodes
is caught, and report the residual count instead of implying zero.

## Purge debris, then assert the volume did not move

**Failure prevented:** a cleanup step that deletes real geometry.

Booleans generate tiny disconnected shells. Dropping connected components below a volume
floor is right; doing it without checking is not, because the same code that removes a
0.0001 mm3 speck will remove a 400 mm3 feature if the component analysis is wrong.

Compute the total before, drop, compute after, and require that the difference equals the
volume of what was intentionally dropped. Report the dropped count and volume separately so
"removed three specks" and "removed a boss" are distinguishable in the log.

`part_kit.triangulate_and_purge` takes `expect_components`, and **declaring the number is
worth more than permitting any number.** It used to hard-code 1, which refused a plate of ten
test coupons -- the most ordinary thing this repository builds, since printing the question
is how any clearance gets answered -- and refused a vessel, whose sealed cavity is a
component in its own right with negative volume.

Pass 1 for a solid, N for a plate of N coupons, and 1 + K for a vessel with K cavities. An
exact count is strictly stronger than a permissive flag in both directions: it catches stray
debris, which raises the number, *and* a plug fused to its socket, which lowers it. A boolean
`allow_multi_body` can only ever express one of those.

`volume` in the returned stats sums over surviving components, so for a vessel it is the
material volume and is the number a mass estimate should use.

## Tessellation counts are empirical constants, and some are landmines

**Failure prevented:** re-running an experiment somebody already ran.

Segment counts, weld distances, bevel filter fractions and boolean solver choices are
mesh-robustness tunables, not dimensions. Keep them in their own labelled block so nobody
reads a segment count as a design decision, and record for each one the range swept and what
failed at the edges. A comment recording a negative result -- "0.005 through 0.08 all behave
identically", "below 12 segments the bore is measurably undersized" -- saves the next person
the sweep.

### Landmine parameters

Some tunables are **non-monotonic**: the value works, the value plus one works, and something
between them fails. The reference documents this for its round-over radius, root fillet
radius, and minimum-edge fraction, calling out specific failing values by number.

Three consequences worth internalising:

- A tunable that behaves at three sampled values has not been shown to behave between them.
- Changing one requires re-sweeping **every variant**, not just the nominal build. The
  reference's corner defect passed on all three variants for four iterations.
- Bisection does not work on a non-monotonic parameter. Sweep it.

Record the landmines by value in the ledger. "Do not set this to 1.0" is only useful if
somebody wrote down that 1.0 was tried.

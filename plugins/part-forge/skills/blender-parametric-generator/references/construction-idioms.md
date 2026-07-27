# Construction idioms

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

## Booleans: overlap, retry, and verify the volume moved

**Failure prevented:** a boolean that silently does nothing.

The worst boolean outcome is not a crash. It is a modifier that reports success, changes
nothing, and leaves a part that looks plausible and is wrong. The modifier will not tell you;
the volume will.

```
before = volume(target)
apply(solver)
if abs(volume(target) - before) <= NULL_VOLUME:  retry with EXACT, then raise
```

`part_kit.boolean` does this and raises with both volumes in the message, because the usual
cause is a cutter that does not actually reach the target.

Prefer an **overlap** to a coplanar butt joint. Two solids meeting exactly face-to-face give
the solver a degenerate case it may resolve into coincident-but-distinct vertices -- which is
the precise ingredient of the positional-versus-topological defect the whole plugin exists
around. Bury the joining feature by a fraction of a millimetre and the case disappears. The
template's gusset uses a 0.6 mm bite into both the plate and the shelf for exactly this
reason.

Apply the modifier through the depsgraph rather than an operator. Operator calls depend on
context that does not exist in `--background`, and the depsgraph path works identically in
both invocation modes.

## Weld between boolean stages

**Failure prevented:** the third boolean failing because of debris from the first.

Each boolean leaves coincident-but-distinct vertices along its seams. They accumulate, and a
later operation chokes on geometry that looks clean in the viewport. A `remove_doubles` at a
few microns between stages costs nothing and keeps every stage seeing a tidy input.

Pick the weld distance well below the smallest real feature and well above float noise. Both
the reference and the template use 5e-3 mm. Record the range swept -- the reference tried
0.005 through 0.08 mm and found the outcome flat across all of it, which is worth writing
down so nobody repeats the experiment.

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
"removed three specks" and "removed a boss" are distinguishable in the log. `part_kit.
triangulate_and_purge` raises when more than one substantial component survives, since that
means the part is not one solid.

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

# Positional versus topological: the defect this plugin is built around

## The incident

A parametric saddle generator ran its acceptance harness and printed:

```
non_manifold_edges   0
boundary_edges       0
shells               1
euler                2
...
135 [PASS], 0 [FAIL]
```

The owner opened the exported `saddle_h0.stl` in Bambu Studio and got:

```
Error: 2 non-manifold edges
```

Three facts about this are worth more than the fix.

**It was found by the owner, not by the process.** The harness had no mechanism that could
have caught it, because the harness and the slicer were not measuring the same object.

**It had been true for the file's entire history.** Every previous run had also passed, and
every previous STL had also been unsliceable. The pass count had never carried information
about the property it appeared to certify.

**Neither tool was wrong.** Both computed a correct answer to the question they were asking.
The questions differed.

## Why both answers are correct

**Blender counts faces per topological edge.** An edge is an entry in a mesh data structure.
Two vertices that share a coordinate but are separate entries produce separate edges, each
with its own face count. Ask "how many edges have a face count other than two" and the
answer is zero, truthfully.

**A slicer reconstructs topology by position.** It receives a triangle soup -- an STL carries
no connectivity at all, only three coordinates per triangle -- and rebuilds adjacency by
matching coordinates. Vertices at the same point become one vertex. The edges that met there
become one edge, and its face count is the sum.

So the same geometry has two different edge counts, and only one of them describes what will
be manufactured.

### Worked illustration

Take four triangles meeting along a seam from `A = (10, 0, 0)` to `B = (10, 5, 0)`. Suppose a
boolean produced two vertex pairs at those coordinates rather than one, so the mesh holds
`A1, A2` and `B1, B2`, each pair coincident to the last bit.

In the authoring tool:

```
edge A1-B1   faces {T1, T2}    -> count 2, manifold
edge A2-B2   faces {T3, T4}    -> count 2, manifold
non-manifold edges: 0
```

After a consumer welds by position, `A1` and `A2` become one vertex, `B1` and `B2` become one
vertex, and the two edges become one:

```
edge A-B     faces {T1, T2, T3, T4}   -> count 4, non-manifold
non-manifold edges: 1
```

Nothing moved. No coordinate changed. The count changed because the question changed. Two
such seams in the shipped file gave the slicer's "2 non-manifold edges".

This is also why the defect is invisible in the viewport. The surface renders as a closed
solid because it is one, geometrically. What is broken is a property that only exists once
somebody merges by position -- and the first thing that does so is the slicer.

## Reconstructing what the consumer sees

Two passes, in this order.

**Exact match first.** Hash the coordinate triple. Identical float bit patterns are the
common case, because most coincidence comes from an operator emitting the same computed
value twice, not from two independent computations landing nearby. This pass is O(n) and does
most of the work.

**Then a 27-neighbour-cell union-find.** Quantise each coordinate onto a grid of size `tol`
and bucket by cell. For each cell, test its members against the members of all 27 cells in
the surrounding 3x3x3 block, and union any pair within `tol`. The 27-cell neighbourhood is
what makes the result independent of where the grid happens to fall: a pair straddling a cell
boundary lands in adjacent cells and still merges. A naive single-cell bucket would miss
exactly those pairs, and they are not rare -- a grid boundary is as likely to fall between
two coincident points as anywhere else.

Union-find rather than a merge list because coincidence is transitive: three points within
`tol` pairwise must all become one vertex, and merging them pairwise in the wrong order
otherwise leaves two.

`weld_by_position()` in `scripts/part_kit.py` and `weld()` in `scripts/mesh_audit.py` are two
implementations of this, on purpose. The generator gates on one; the external audit uses the
other. Two implementations agreeing from different code is a materially stronger claim than
one implementation agreeing with itself.

## Choosing the weld tolerance

A binary STL stores coordinates as float32. Near 50 mm the spacing between representable
values is a few times 1e-6 mm. That is the noise floor: two points intended to be identical
can differ by that much purely from the write, with no defect present.

The smallest real feature in a printed part is orders of magnitude larger. A 0.2 mm layer, a
0.4 mm extrusion width, a 0.05 mm tolerance band -- all are at least 500 times the float32
noise. So there is a wide band with nothing in it, and **1e-4 mm sits in the middle of that
band**: a hundred times above the representation noise, and a thousand times below the
smallest thing a printer can produce.

The value being defensible on paper is not the same as it being safe in practice. Sweep it:

| weld tolerance | over-used edges | open edges | bodies |
|---|---|---|---|
| 0 (exact match only) | flat | flat | flat |
| 1e-6 mm | flat | flat | flat |
| 1e-5 mm | flat | flat | flat |
| 1e-4 mm | flat | flat | flat |
| 1e-3 mm | flat | flat | flat |
| 5e-3 mm | flat | flat | flat |

**A flat sweep is the evidence that the tolerance is not load-bearing.** The answer does not
depend on the parameter, so the parameter is not deciding the verdict -- the geometry is.

The converse is the useful diagnostic. **If the answer moves with the tolerance, the mesh is
the problem, not the tolerance.** A mesh whose body count drops from 3 to 1 somewhere between
1e-5 and 1e-3 has features separated by a distance no printer can resolve and no reviewer
intended, and picking the tolerance that produces the desired answer is choosing a verdict
rather than measuring one. Report the sweep, do not tune it.

## The grid-quantisation caveat

`mesh_audit.py` reports `weld_boundary_risk`: the number of coordinates sitting near a
*rounding* boundary -- where the grid-scaled value falls within 0.05 of `n + 0.5`, so an
insignificant perturbation would send it into the neighbouring cell. Note the direction: a
coordinate landing exactly on a grid multiple is the safest case, not the riskiest.

Grid rounding is deterministic and cheap, which is exactly what a reproducibility digest
needs, and its known weakness is that two points closer than `tol` can still land in
different cells. The 27-neighbour pass handles that for the topology reconstruction. The
digest path does not do the neighbour pass, because a digest must be a pure function of the
coordinates and nothing else.

So the counter is a disclosure rather than a fix. A non-zero `weld_boundary_risk` means the
unique-vertex count is approximate; re-run at a different tolerance and confirm the count is
stable before drawing any conclusion from it. Reporting the risk beats silently rounding and
hoping, which is the same failure this whole document is about.

## Reproducibility: hash the solid, not the file

Nine consecutive runs of unmodified source produced **nine distinct file digests**.

Two causes, both benign and neither fixable at reasonable cost:

- **Triangle emission order varies.** Boolean and mesh operators iterate over hash tables
  keyed by pointer identity, and allocation addresses differ between processes. The same
  triangles come out in a different order.
- **Ambiguous quad diagonals tie-break differently.** A planar quad can triangulate along
  either diagonal. Both are correct; the choice depends on iteration order, which is the
  first cause again.

Neither changes the set of vertices, the volume, or any measurement. The solid is identical
and the bytes are not.

The same nine runs produced **one digest per variant** from the sorted unique welded vertex
set, at reduced precision. Identical every time.

The conclusions:

- **`md5` of a shipped STL carries no signal at all.** It will differ between two runs of
  identical source, and it can coincide for two meshes that differ in triangle order alone.
  It answers no question anyone has.
- **The vertex-set digest is the reproducibility claim worth making.** Diff it to answer "did
  my edit change the solid, or only the tessellation".
- **Report it, never gate it.** A legitimate parameter change is supposed to move it. A gate
  on the digest would fail every intentional edit and would have to be updated by hand, which
  makes it a changelog with a failure mode rather than a check.

State the claim precisely when documenting a part: re-running the unedited generator
reproduces the same solid -- identical unique vertex set, volume, and measurements -- but not
the same STL bytes.

## Auditing any gate: three questions

Generalised past meshes entirely. For every check in a harness:

1. **Name the artifact the check touches.** In-memory data structure, exported file,
   intermediate representation, or the physical part. Be specific; "the model" is not an
   answer.
2. **Name the consumer whose question it answers.** The slicer, the printer, the mating part,
   the person installing it, a downstream script.
3. **Confirm those are the same.** If the check touches an in-memory structure and the
   consumer reads a file, the check is measuring a proxy, and the proxy has to be shown
   faithful before its passing means anything.

The saddle harness failed question 3 for its entire history, and every other property it
measured was fine. A gate can be thorough, well-written, and comprehensively wrong about the
one thing that ships.

A fourth question is worth asking whenever a check has passed for a long time without ever
failing: **what would have to break for this to go red?** If the answer is hard to construct,
the check may already be vacuous. See the coverage counter in `check-inventory.md`.

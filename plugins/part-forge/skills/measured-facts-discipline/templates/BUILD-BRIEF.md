# Build Brief -- <PART NAME>

**Hand this file to <agent> as the task. It is self-contained: it assumes no prior
conversation.**

That property is easy to lose by accident and is the whole value of the file. No phrase in
this brief may point outside it -- no "the profile discussed above", no "the corrected value",
no "as agreed". A reader who was not present must be able to build the part from this file
alone, and a second reader must be able to do it independently, so the two results can be
compared.

---

## Your task

Write `<part>_gen.py`, a parametric generator that builds this part from the parameter table
below, verifies it against the acceptance checks, and exports only what passes.

Deliver the script, the saved scene, the accepted mesh files, and the verification report.
The script is a deliverable in its own right, not scaffolding: every dimension that turns out
wrong must be a one-number edit and a re-run, not a remodel.

## Context -- why this part exists

<Two or three paragraphs. What is physically wrong; what already exists that this must work
with; what this part is therefore required to do, in verbs. Name what this part does NOT have
to do and why -- a part asked to do less gets smaller and stronger.>

<State the load and where it comes from. State whether the part is loaded in bending, shear,
tension, or compression, because that decides the print orientation.>

## Parameters

Place these at the top of the script as named constants, one per line, each carrying its
units and its source in a trailing comment. Nothing downstream may recompute a derived value
independently -- derive once, into one structure, and read from it everywhere.

| Param | Meaning | Value | Units | Source |
|---|---|---|---|---|
| `W_PLATE` | <meaning> | <value> | mm | `FACTS.md` 3.1 |
| `H_PLATE` | <meaning> | <value> | mm | `FACTS.md` 3.2, hard cap `<n>` |
| `T_PLATE` | <meaning> | <value> | mm | `FACTS.md` 4.3 |
| `D_<FEATURE>` | <meaning> | <value> | mm | `FACTS.md` 5.1 -- **CONFIRMED <date>** |
| `Y_<FEATURE>` | <meaning> | <value> | mm | `FACTS.md` 6.4 -- **MEASURED INPUT, NOT A DESIGN CHOICE** |
| `T_WALL` | Minimum structural wall on the load path | <value> | mm | design choice |
| `CLEAR` | Radial clearance to the mating part | <value> | mm | design choice |
| `LOAD_LBF` | Design load | <value> | lbf | `FACTS.md` 1.5 |
| `MATERIAL` | Filament | `"<PETG>"` | -- | `FACTS.md` 7f |
| `SF_MIN` | Required bending safety factor | <value> | ratio | covers infill knockdown and creep |

**Mark measured inputs as measured.** Any dimension fixed by hardware outside this project
must be labelled so in the table, and must not carry a formula. A derived lower bound answers
"how close could this sit", which is a different question, and using it as the value has
already cost one rebuild on this class of part.

### Empirical constants -- mesh-robustness tunables, not dimensions

These do not describe the part. They exist because boolean, bevel and loft operations have
failure modes that no formula predicts, and each value below was found by sweeping. Keep them
in a separate block so a reader never mistakes one for a dimension.

| Constant | Value | What it guards | Notes |
|---|---|---|---|
| `WELD_PRE_ROUND` | <value> mm | Vertex weld before the round-over | swept <range>; <flat / non-monotonic> |
| `ROUND_MIN_EDGE_FRAC` | <value> | Anti-spike bound on the bevel | swept; landmine values at <list> |
| `SEG_*` | <value> | Tessellation density | chosen for <tolerance> mm chord error |

Record negative results here. A swept range in which every value failed identically is worth
more than a bare final number, because it stops the next person re-running the experiment.

## Coordinate system

State it rather than assuming it. Every ray, probe and assertion in the acceptance list
depends on it.

- **1 unit = 1 mm.** Scene units metric with `scale_length = 0.001`; the exporter is told
  `use_scene_unit=False, global_scale=1.0` so raw coordinates are written directly and are not
  scaled twice.
- Origin at **<the named physical feature -- e.g. the centre of the plate's bottom edge, on the
  mounting face>**.
- `+X` <meaning -- e.g. along the bar axis>.
- `+Y` <meaning -- e.g. away from the wall>.
- `+Z` <meaning -- e.g. up>.
- The finished object carries an **identity transform**. The coordinate system is baked into
  vertex data, not held in the object's location or rotation.

## Geometry

One subsection per feature, in build order. Give the construction logic and the formula, not
a description of the result.

### <Feature 1 -- e.g. the plate>

<How it is built: profile, extrusion, radius. Give the formula for anything computed.>

### <Feature 2 -- e.g. the cradle>

<Same. Where a profile choice has alternatives, state which was chosen and why the
alternative was rejected -- a U-trough places the mating centre at exactly `D/2` above the rest
point, whereas a 90 deg V places it at `0.707*D`, coupling the height to the diameter.>

### <Feature 3 -- e.g. the structural fillet>

<Give the tangent construction generally, not assuming right angles. For a corner at point P
with surfaces leaving along unit directions u1 and u2 separated by angle theta: the arc centre
is at `P + (r / sin(theta/2)) * b` along the bisector b, and the tangent points are at
`P + (r / tan(theta/2)) * u`. Nothing is assumed to be a right angle.>

### Form -- cosmetic features

<Anything not load-bearing, marked as such, so a later reader knows it may be removed without
structural consequence.>

## Constraints

Each one is a number, and each one becomes a gate in the acceptance list. A constraint that
cannot be expressed as a number is a preference.

1. Mounting face is exactly **<w> x <h> mm**, planar, at <coordinate>.
2. Overall height **<= <cap> mm**.
3. Minimum wall on the load path **>= `T_WALL`**, measured at the *thinnest* station.
4. Bending safety factor **>= `SF_MIN`** at the worst section.
5. Watertight: zero open edges, zero over-used edges, zero degenerate faces, one body,
   Euler characteristic even and `<= 2`. It is **not** expected to equal 2 unless the part
   has no through-holes: each hole adds a handle, so `euler = 2 - 2g`. State the expected
   genus here -- `<g>` through-holes -- and gate on it, which also catches a bore that
   silently failed to punch through.
6. No material behind the mounting plane.
7. <Feature clearance -- e.g. the mating part can drop in without the fillet forming a trap.>

**Do not verify these in the authoring tool's in-memory mesh and stop there.** The gate must
parse the exported binary file back off disk, weld vertices **by position**, reconstruct
topology independently, and **refuse and delete** any variant that fails. An authoring tool
counts faces per topological edge; a slicer reconstructs topology by position. Both answers
can be correct while only one describes the file that ships.

## Print orientation

<State the orientation.> The reason, not just the instruction: the part is loaded in bending
in the **<plane>** plane. Printed <the naive orientation>, that bending would pull directly
across layer lines at <the location>, which is where FDM parts fail. Oriented <as specified>,
the bending is carried **within** layers. <Note whether it also prints without supports.>

If the orientation rotates the part's axes relative to the model, say which model axis becomes
the build axis, because any layer-aligned feature depends on it.

## Deliverables

Exact filenames, in this directory:

- `<part>_gen.py` -- the generator, including its own acceptance list.
- `<part>.blend` -- the saved scene, written after export so it reflects post-cleanup state.
- `<part>.stl` -- <or the variant set: `<part>_<v1>.stl`, `<part>_<v2>.stl`, `<part>_<v3>.stl`>.
- `verify_report.json` -- measured-versus-expected for every check, every variant, plus the
  list of variants refused and the vertex-set digest of each accepted file.

Write `verify_report.json` unconditionally, including on failure. A failing run's report is
the most useful artifact it produces.

## Unverified assumptions -- flag these, do not hide them

Every value below could be wrong, and the part's failure mode if it is wrong is stated. A
brief that hides its assumptions produces a part whose failure has no explanation.

| Assumption | Value used | If wrong, the part... | Hedged by |
|---|---|---|---|
| <assumption> | <value> | <specific failure> | <variant set / not hedged> |

State what the hedge does **not** cover. A three-variant set spaced 2 mm apart covers a 2 mm
error and covers nothing about a 10x unit misreading -- if that is the real error, all three
are scrap.

## Acceptance checks -- run these and report actual numbers

Report the measured value beside the expected value for every check. A bare "PASS" is not a
report.

**The generator's own `acceptance()` list is the specification of record. Where this brief and
that list disagree, the code wins** -- which is only safe because the code is checked against
the artifact rather than against itself.

Two tolerance regimes, stated rather than blanket:

- **Tight, <tol> mm** -- dimension-bearing and primitive geometry, where the value is placed
  directly by a parameter.
- **Loose, <tol> mm** -- boolean-, loft- and bevel-derived form features, where the surface is
  the output of an operation rather than a placement.

Checks to report:

| # | Check | Expected | Tolerance |
|---|---|---|---|
| 1 | Mounting-face width, height, planarity, position | <values> | tight |
| 2 | Overall bounding box within envelope | <values> | tight |
| 3 | Minimum wall on the load path, at **two or more stations** | `>= T_WALL` | tight |
| 4 | Bending safety factor at worst section | `>= SF_MIN` | -- |
| 5 | Positional manifold on the **exported file**: open edges, over edges, degenerate, bodies, winding | 0/0/0/1/0 | exact |
| 5b | Euler parity and bound, and genus against the hole count | even, `<= 2`; genus `<g>` | exact |
| 6 | <Feature dimension, measured off the finished mesh> | <value> | loose |
| 7 | Vertex-set digest per accepted file | -- | **reported, not gated** |

**Measure off the finished mesh, never assume from the parameter.** A parameter states an
intent; the delivered geometry is what the acceptance list must interrogate. If a parameter is
named `WRAP_DEG`, the wrap that ships still has to be measured, because booleans and chamfers
move it.

**Sample the worst station, not the convenient one.** A probe fired in a single plane measures
that plane forever. If a groove floor is thinner than the land beside it, one sweep down the
land centre will pass indefinitely.

**Derive probe positions from the parameters they depend on.** A literal coordinate in a
verification harness is a future stale value: a probe hard-coded at 20.0 mm kept passing after
a later feature grew the part past it.

## Do not

- Do not derive a dimension that hardware outside this project already fixes. Measure it.
- Do not verify manifoldness only in the authoring tool's data structures.
- Do not export a variant that failed its gate, and do not leave a stale file from a previous
  run at that path -- delete it, so a failing variant can never ship an old good-looking file.
- Do not hash the exported file to prove reproducibility. Triangle order and quad-diagonal
  choice vary run to run; compare the unique vertex set instead.
- Do not add a check without asking what it does not measure.
- Do not delete a superseded value from `FACTS.md`. Strike it through and correct beneath.
- Do not <part-specific prohibition>.

---
name: blender-parametric-generator
description: Write a Blender Python script that generates a printable part from a parameter table. Use when building a part as code rather than by hand-modelling, when a mesh has no construction history and needs rebuilding, when a design must produce dimensional variants cheaply, when booleans or bevels produce non-manifold results, or when setting up units, transforms, print orientation, and STL export for a generated solid.
---

# The generator is the deliverable

A hand-modelled mesh answers one question. A generator answers "what if the bore is 25 mm
and not 22" for the cost of one number and a re-run, which is the only thing that makes a
variant set affordable and a wrong measurement survivable.

The script is therefore a first-class artifact, shipped alongside the mesh. The mesh is
disposable output.

## Shape of the file

Six regions, in this order. The order is not cosmetic — each one may only read from the ones
above it.

```
1  Module docstring    invocation lines, coordinate system, units, design intent
2  Parameters          named constants, each citing the FACTS.md section it comes from
3  derive()            every secondary value computed once, plus the invariant asserts
4  Geometry kernel     pure-Python 2D math, no bpy
5  Build phases        named functions that emit the solid
6  Verify / export     the acceptance list, then the gate, then main()
```

### Guard the import so the kernel is testable

The worked example puts `import bpy` at module scope, which makes its several hundred lines
of pure-Python polygon math unimportable — and therefore untestable — outside a running
Blender process. Do not inherit that. Guard it:

```python
try:
    import bpy
    import bmesh
    HAVE_BPY = True
except ImportError:          # importable outside Blender for kernel unit tests
    bpy = bmesh = None
    HAVE_BPY = False
```

The 2D kernel — hulls, offsets, clipping, tangent-fillet solves — is ordinary geometry. Being
able to test it in a plain interpreter, and to re-derive its numbers independently, is worth
the four lines.

### Parameters carry their provenance, not their history

Each constant gets its units and the ledger section it came from:

```python
D_BAR   = 19.05    # mm  bar diameter, 3/4 in - FACTS 5, CONFIRMED by owner 2026-07-25
H_DROP  = 2.0      # mm  rest point below the plate edge - FACTS 6.1, STILL UNVERIFIED
Y_BAR   = 31.75    # mm  bar centre depth - FACTS 6.4, MEASURED INPUT, NOT A DESIGN CHOICE
T_WALL  = 3.0      # mm  minimum structural wall on the load path
```

That third comment is doing real work. It marks a value that must not be recomputed from a
formula, because something physical fixes it. See `measured-facts-discipline`.

Keep the decision history in `FACTS.md`, not here. The worked example carries 100-plus-line
sweep logs inline above single constants, which is valuable evidence in the wrong file: the
script grew to roughly three and a half times its executable logic and a reader must scroll
past experiment data to reach the next parameter. Leave a one-line pointer instead.

Separate **dimension-bearing parameters** from **empirical constants** — weld distances,
bevel filter fractions, tessellation counts. The second group are mesh-robustness tunables,
not dimensions; they belong in their own block, labelled as such, so nobody reads a segment
count as a design decision.

### derive() is the only place secondary values are computed

One function, called once, returning a dict whose keys mirror the constant naming. The rule
worth stating in its docstring: **nothing downstream computes its own.** A radius recomputed
in three places will disagree in two of them after the next edit.

`derive()` is also where parameter combinations are validated, before any geometry exists:

```python
assert H_PLATE <= H_PLATE_CAP, f"H_PLATE {H_PLATE} exceeds the {H_PLATE_CAP} mm envelope cap"
assert gap_eff > CLEAR,        f"effective gap {gap_eff:.3f} leaves no clearance"
assert 160.0 <= WRAP_DEG <= 180.0, f"WRAP_DEG {WRAP_DEG} outside the specified range"
assert abs(RIB_PITCH / LAYER_H - round(RIB_PITCH / LAYER_H)) < 1e-9, \
    "rib pitch must be a whole number of layers or the grooves will not land on layer lines"
```

Bare asserts are useless at 2 a.m. Every message names the physical consequence. Failing here
costs a second; failing after a twelve-second build and a boolean cascade costs the session.

## Construction idioms

Techniques, tradeoffs, and the failure each one avoids: `references/construction-idioms.md`.
The load-bearing ones:

- **Profiles in 2D, then extrude or loft.** Build the cross-section as a polygon list with
  ordinary math, then hand it to `bmesh`. Debugging a list of points beats debugging a mesh.
- **Analytic tangent fillets, not bevels, on structural blends.** A bevel that assumes a
  right angle leaves a ledge wherever the junction is not 90 deg, and real junctions are not.
  Solve the tangent circle: for a corner at `P` with surfaces leaving along unit directions
  `u1`, `u2` separated by `theta`, the arc centre sits at `P + (r / sin(theta/2)) * b` along
  the bisector `b`, with tangent points at `P + (r / tan(theta/2)) * u`. Assume nothing is a
  right angle.
- **Convex erosion is a 45-degree flare.** Eroding a convex profile by `d` per unit of travel
  produces exactly a 45-degree taper — which is also the overhang the printer can manage
  unsupported, so the two constraints can be satisfied by one operation.
- **Booleans need a retry and a *signed* volume check.** Run the fast solver, fall back to
  the exact one, and accept only when the volume moved the way the operation requires —
  removing material cannot grow a solid. A boolean that silently does nothing produces a part
  that looks plausible and is wrong; a declined solver bakes the cutter in as a second shell,
  which grows the volume and satisfies any guard that only asks whether something changed.
- **Weld between boolean stages, but do not recalculate normals.** Coincident-but-distinct
  vertices accumulate across operations and the next boolean chokes on them, so use
  `weld_verts`. `recalc_face_normals` travels with the weld out of habit and turns any sealed
  cavity inside out, silently making a hollow part solid — `clean_mesh` now defaults
  `recalc_normals=False` for that reason.
- **Shell a loft perpendicular to the surface.** An in-plane inset leaves `d * cos(alpha)` of
  wall wherever the surface slopes, and on a 45-degree cone leaves exactly zero. Use
  `offset_rings`, and give the floor its own thickness.
- **Name filter rules, never number them.** A header reading "four rules" sat above a filter
  that tested six. Numbering a list in prose creates a claim that rots.
- **Purge debris, and assert the volume did not move.** Drop connected components below a
  volume floor, then check total volume is unchanged. A purge that alters volume removed
  something real.

## Units, transforms, orientation

- Set the scene to metric with `scale_length = 0.001` so one Blender unit is one millimetre,
  and state that in the docstring. Then tell the exporter `use_scene_unit=False,
  global_scale=1.0`, otherwise the scale is applied twice.
- **Bake the part's coordinate system into vertex data and leave the object transform at
  identity.** A rotation carried on the object is a rotation the exporter may or may not
  apply, and a baked-in 90-degree X rotation is the classic signature of an imported mesh
  nobody can reason about.
- Export from a **disposable copy**. Rotate it into print orientation by transforming vertex
  data, drop its minimum to the bed, centre it in the other two axes, write, then discard.
  The canonical object never moves.
- **Print orientation is a structural decision, so justify it in the docstring.** If the load
  puts the part in bending, orient so the bending is carried *within* layers rather than
  across them, because across layer lines is where FDM parts fail. In the worked example that
  meant printing on its side rather than face-down, which also removed the supports.
- If the orientation rotation makes one part axis the build axis, then any layer-aligned
  feature — grooves pitched to layer height — depends on that rotation. Say so at both sites.

## Invocation, and the exit code that is not optional

```bash
blender --background --python-exit-code 1 --python part_gen.py
```

**`--python-exit-code 1` is not optional.** Without it Blender exits 0 even when the script
raises, so a failed build reports success to every caller, CI included.

Support two modes and make the difference explicit in the docstring: headless as above, and
in a live session via `exec(open("part_gen.py").read())` — the second is how a Blender MCP
connection runs it. In the live path `__file__` does not exist, so resolve the output
directory with an environment-variable override and a `NameError` fallback.

Accept variant overrides as keyword arguments on `derive()` and the build function rather
than mutating module constants, so one process can build a whole variant set without state
leaking between builds.

Derive variant *names* from their offsets and assert the relationship. Names hard-coded as
`part_h-2 / part_h0 / part_h+2` against absolute values `0 / 2 / 4` silently mislabel every
exported file the moment the nominal default changes.

## Export is gated, and the gate deletes

Build, verify the mesh, and only then export. Re-parse the file just written and verify it
positionally; on failure, remove it. Never leave a rejected variant on disk, and remove any
stale file at the path a failing variant would have occupied. `mesh-verification-gate` has
the full contract.

## Things that make a generator worse

- **`import bpy` at module scope.** Costs you all unit testing of the geometry math.
- **Recomputing a derived value at its point of use.** It will drift.
- **A bare `assert x > 0`.** Say what it means physically.
- **Blanket `except Exception`.** The two excepts worth having are a solver-enum fallback and
  the `__file__` lookup; everything else should propagate.
- **Sweep logs inline above constants.** Put them in the ledger; leave a pointer.
- **Ad-hoc ray fans copy-pasted per feature.** Ten variations of "cast a fan, fit a circle,
  compare" is ten places to fix a bug. Use `${CLAUDE_PLUGIN_ROOT}/scripts/part_kit.py`.
- **A tessellation count tuned until a boolean stopped failing, with no note.** The next
  person will retune it. Record the range you swept and what failed.

## Reference files

- `references/construction-idioms.md` — profile building, lofting, booleans, selective bevel,
  fillet mathematics, debris purge, and the failure each idiom prevents.
- `references/invocation-and-export.md` — the two invocation modes, exit codes, output
  directory resolution, unit and transform handling, print orientation, and the export copy.
- `examples/generator_template.py` — a runnable skeleton with the six regions, the bpy guard,
  a derive with asserts, a build phase, an acceptance list, and the gated export wired up.

## Related

- `measured-facts-discipline` — where parameter provenance comes from.
- `mesh-verification-gate` — the acceptance list and the export gate in detail.
- `fdm-structural-design` — wall thickness, orientation, and the load models.
- `${CLAUDE_PLUGIN_ROOT}/scripts/part_kit.py` — the shared measurement and construction
  helpers: the pure-Python geometry kernel, `Probe`, and `Acceptance`.
- `/part-forge:gen-part` — run a generator and report the gate result.

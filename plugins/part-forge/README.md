# part-forge

Two things go wrong when you design a functional part to print. You build something whose
every dimension is self-consistent and which fits everywhere except the room — one number was
never measured, and the model has no way to notice. Or you build something that passes every
check you wrote and the slicer refuses it anyway, because the checks measured a property of
your modelling tool rather than a property of the file that ships.

`part-forge` is the process that makes both of those expensive to reach by accident: measured
reality in one ledger that governs, the part as a parametric generator rather than a mesh you
pushed by hand, and an acceptance gate that reads the exported bytes back off disk and deletes
anything that fails.

## Why it is built this way

A generator once reported `non-manifold edges: 0` and **135 checks passing** across three
variants. Bambu Studio opened the same file and said `Error: 2 non-manifold edges`.

Both were correct. Blender counts faces per *topological* edge; a slicer reconstructs topology
*by position*. Two vertices at the same coordinate that Blender considers distinct are one
vertex to the slicer, and the edges around them stop being manifold. The harness had never
been wrong — it had been answering a different question than the one that decided whether the
part could be printed, and it did so for the entire history of the file until a real slicer
disagreed.

Every design decision here follows from that: verification runs on the artifact that ships,
by position, in an implementation that shares no code with the thing that produced it.

## What it installs

### Skills

| Skill | Purpose |
|---|---|
| `parametric-part-workflow` | The eleven-stage process from physical problem to 30-day re-check. Start here. |
| `measured-facts-discipline` | The facts ledger: confidence tags, per-fact template, supersession protocol, physical measurement procedures. |
| `blender-parametric-generator` | Writing the generator: parameter blocks, single-source derivation, construction idioms, units, transforms, export. |
| `mesh-verification-gate` | The acceptance harness: positional weld, check inventory, tolerance policy, refuse-and-delete contract, determinism digest. |
| `fdm-structural-design` | Bending and adhesive models, wall thickness on the load path, print orientation, the 45° rule as a design constraint. |
| `/part-forge:new-part` | Scaffold a part directory: three documents plus a generator skeleton wired to the verification kit. |
| `/part-forge:gen-part` | Run a generator headlessly, verify, and export behind the gate. |
| `/part-forge:verify-part` | Audit an existing mesh or STL with no Blender involved. |

### Agents

| Agent | Purpose |
|---|---|
| `part-design-reviewer` | Adversarial review of a generator plus its verify report. Hunts vacuous checks, stale probes, single-station ray fans, and expectations that restate a parameter instead of measuring the mesh. |
| `facts-auditor` | Epistemic audit of the facts ledger. Finds untagged numbers, derivations standing in for measurements, unhonoured open items, and lists everything the model depends on that nobody measured. |

### Scripts

| Script | Purpose |
|---|---|
| `mesh_audit.py` | Headless solid audit — manifoldness by position, per-body Euler and volume, wall thickness, overhang area, determinism digest, expectation gating. |
| `mesh_render.py` | Section slices, orthographic views, thickness and overhang heatmaps as PNGs — for eyes and for multimodal review. |
| `mesh_repair.py` | Cleaning, repair, decimation, and Hausdorff comparison between variants. |
| `new_part.py` | Directory scaffolder behind `/part-forge:new-part`. |
| `part_kit.py` | The reusable Blender geometry and measurement library the generator skeleton builds on. |

## Installing

Try it locally without installing:

```bash
claude --plugin-dir /path/to/part-forge/plugins/part-forge
```

Install from this repository's marketplace:

```
/plugin marketplace add /path/to/part-forge
/plugin install part-forge@part-forge
```

## Prerequisites

**Blender 4.2 or newer** — 5.2 LTS is what this was developed against. On macOS the binary
lives inside the app bundle at `/Applications/Blender.app/Contents/MacOS/Blender`; the `.app`
path alone will not run a script. Blender is needed to *author* a part. It is deliberately not
needed to verify one.

**python3** for the scripts. Nothing in the verification path requires a virtual environment.

**trimesh** — optional but recommended, and already present in this environment. Without it
`mesh_audit.py` still performs every topology, volume, and determinism check using only the
standard library. With it you additionally get mass properties, centre of mass, inertia,
convex-hull solidity, ray-cast wall thickness, overhang area, and non-STL formats.

**pyvista** and **pymeshlab** are fetched on demand with `uvx` when you ask for renders or
repairs. They are never required, and nothing in the gate depends on them.

The tiering is not incidental. A gate that runs inside Blender's bundled Python must not
acquire an install step, so the shipped checks are dependency-free and the richer libraries
serve as independent cross-checks.

| Tier | Requires | Gives you |
|---|---|---|
| 0 | standard library only | STL parse, positional weld, manifold and winding checks, per-body Euler and signed volume, bounding box, vertex digest |
| 1 | `trimesh` | mass properties, centre of mass, inertia, solidity, ray-cast wall thickness, overhang area, OBJ/PLY/3MF/GLB |
| 2 | `pymeshlab` | repair, cleaning, decimation, Hausdorff distance between variants |
| 3 | `pyvista` | section plots, orthographic renders, thickness and overhang heatmaps |

## The shape of the workflow

Measured reality lives in `FACTS.md`, and that file governs — the model conforms to it, never
the reverse. `PROJECT.md` carries status and the decision log. `BUILD-BRIEF.md` is a
self-contained task packet: it assumes no prior conversation and can be handed to a fresh
agent as the entire task. The generator turns the brief's parameter table into a solid and
gates its own export. `verify_report.json` is the evidence.

Precedence is strict: `FACTS.md` beats `PROJECT.md` beats the generator beats the mesh. Where
prose documentation and an executable check disagree about what is verified, the code is what
runs, so the code is the specification of record.

## Quick start

```
/part-forge:new-part shade-bar-mount
```

Scaffolds `projects/shade-bar-mount/` with the three documents and a generator skeleton. Then:

1. Fill in `FACTS.md`. Tag every number. List what you do not know yet in the blocker
   section — the process is built to proceed with known unknowns, not to pretend they are
   known.
2. Take the blocking measurements. The skill carries procedures for the ones that are awkward:
   circumference-over-π for a mounted bar, printed go/no-go gauges for a diameter you cannot
   reach, cross-checking a second independent number to settle ambiguous units.
3. `/part-forge:gen-part` — builds, verifies, and exports only what passes.
4. `/part-forge:verify-part projects/shade-bar-mount/saddle_h0.stl` — audits the exported
   bytes independently of the tool that wrote them.
5. Hand off to `print-tune-bambu` for slicing, then dry-fit before committing adhesive.

## What this deliberately does not do

**It does not slice.** Settings, materials, and verifying by slicing belong to
`print-tune-bambu`, a sibling plugin in the same marketplace with its own reference set and
its own wiki mirror. `part-forge` stops at an accepted solid. Install both and the pipeline
is continuous:

```
/plugin install part-forge@part-forge
/plugin install print-tune-bambu@part-forge
```

The handoff runs both ways. `print-tune-bambu` reads `verify_report.json` when one exists,
so it quotes the wall thickness measured at the *worst* station rather than re-deriving it —
and its `inspect_model.py` overlaps `mesh_audit.py` on purpose, because two implementations
agreeing from different evidence is the entire premise of this plugin. When they disagree,
that disagreement is the finding.

**It does not choose your material.** It will tell you the safety factor a stated allowable
stress produces, and it will refuse to guess the allowable.

**It does not do CAD-grade surfacing.** No NURBS, no class-A surfaces, no draft analysis.
Functional parts with measurable dimensions.

**It does not author meshes by hand.** If the answer is "nudge those vertices", this is the
wrong tool. The premise is that a part worth printing twice is worth expressing as a script,
because then a dimension that turns out wrong costs one number and a re-run instead of a
remodel.

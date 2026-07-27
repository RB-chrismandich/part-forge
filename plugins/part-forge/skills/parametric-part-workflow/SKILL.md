---
name: parametric-part-workflow
description: Run the end-to-end process for designing a functional 3D-printable part — bracket, mount, saddle, adapter, spacer, jig, enclosure, replacement clip. Use when a physical problem needs a printed solution, when a part must fit something that already exists, when a design depends on dimensions nobody has measured yet, or when deciding whether to edit an existing mesh or rebuild it parametrically. Establishes the facts ledger, the generator script, the acceptance gate, and the install follow-up.
---

# Designing a printable part that actually fits

Two failure modes end these projects, and neither one looks like failure while it is
happening.

The first is a beautiful part that does not touch the thing it was meant to support.
Every dimension in the model is self-consistent; one of them was never measured. The
model cannot detect this, because the model has no access to the room.

The second is a part that passes every check and still gets rejected by the slicer. The
checks were real. They measured the wrong invariant — an in-memory property of the
authoring tool rather than a property of the file that ships.

The process below exists to make both of those expensive to reach by accident. Its
organising rule: **measured reality lives in one file, that file governs, and the model
conforms to it — never the reverse.**

## Before anything else: three questions

Answer these out loud before touching geometry. Guessing any of them wastes a build.

1. **What does the part actually have to do?** Not "hold the bar" — *push up*, or *capture*,
   or *locate laterally*. Parts that are asked to do less get smaller and stronger. A
   support that only pushes up needs no retention lip; discovering that after modelling the
   lip is a rebuild.
2. **What already exists that this must conform to?** Existing hardware fixes dimensions
   that are then *not yours to choose*. Those are inputs, not derivations. See the trap in
   Stage 3.
3. **Which numbers are actually known?** Distinguish stated, inferred, and unknown from the
   start. This is the whole content of Stage 1.

## The stages

Each stage has an entry condition, one artifact, and an exit gate. Skipping the gate is
what causes the failures above.

### Stage 1 — Build the facts ledger

Create `FACTS.md` in the part's own directory and record every real-world constraint with a
confidence tag on every number. Enumerate what is still unknown as an explicit blocker
list. Nothing downstream may pretend an unknown is known.

Load the **measured-facts-discipline** skill for the tagging vocabulary, the per-fact
template, the supersede protocol, and the physical measurement procedures (paper-strip
diameter, printed go/no-go gauges, unit-disambiguation by cross-check).

*Exit gate:* every number carries a tag, and the unknowns are listed separately from the
knowns.

### Stage 2 — Decide: edit the existing mesh, or rebuild parametrically

If a draft or scanned mesh exists, this is a real decision and it deserves a recorded
reason. Rebuild parametrically when any dimension is still open, because then a wrong guess
costs one number and a re-run instead of a remodel. Edit in place only when the geometry is
already correct and the change is genuinely local.

A traced or generated mesh — all triangles, no construction history, degenerate edges,
visibly faceted curves — is almost never worth editing. Salvage the one or two dimensions
it got right, write them into `FACTS.md`, and rebuild.

*Exit gate:* the route is chosen and justified in writing, not defaulted into.

### Stage 3 — Write the build brief

Write `BUILD-BRIEF.md` as a **self-contained task packet**: it assumes no prior
conversation and can be handed to a fresh agent as the entire task. It carries the
parameter table, the construction logic, the constraints as gates, the acceptance checks,
the deliverables, the print orientation, and an explicit *Do not* list.

Two rules earn their own emphasis here:

- **Never substitute a theoretical minimum for a measured value when something outside your
  control fixes it.** The canonical failure: a mounting depth was derived as
  `plate_thickness + radius + gap`, correctly called "a floor, not a target" — and then used
  as the value. The real number, set by pre-existing brackets nobody had measured, was
  **1.98x** larger. The part could not reach what it was built to support. A floor is only
  the answer if the world happens to sit at the minimum, and the world rarely does.
- **Keep unverified assumptions in a visible section.** A brief that hides its assumptions
  produces a part whose failure has no explanation.

*Exit gate:* a reader with no context could build the part from this file alone.

### Stage 4 — Close the blocking measurements

Hand the owner the specific procedures, not a request to "measure it". Where a dimension
cannot be measured with tools on hand, print a cheap physical gauge — a comb of notches at
candidate sizes — and convert the question into something that can be held. Minutes of print
time buys an answer that no amount of reasoning does.

*Exit gate:* every dimension that decides whether the part works is measured, or explicitly
hedged by Stage 8's variant set.

### Stage 5 — Write the generator

The script is the deliverable, alongside the mesh. Parameters at the top as named
constants, each annotated with the `FACTS.md` section it comes from; derived values computed
in one place from those parameters; construction in named phases.

Load the **blender-parametric-generator** skill for the construction idioms, the parameter
table conventions, unit and transform handling, and how to keep the script re-runnable.

*Exit gate:* changing one parameter and re-running produces a correct variant with no other
edits.

### Stage 6 — Gate the export on verification

The generator's own acceptance list is the specification of record. Where prose
documentation and the executable check disagree, **the code wins** — so the check must be
worth trusting.

The gate must be *positional* and must run on the **exported file, read back from disk**.
Verifying in the authoring tool's in-memory mesh and stopping there is the defect that
shipped: an authoring tool counts faces per topological edge, while a slicer reconstructs
topology by position. Both answers were correct; they answered different questions, and the
part was rejected in the slicer after 135 checks passed. A variant that fails must be
**refused and deleted**, not exported with a warning.

Load the **mesh-verification-gate** skill for the check inventory, tolerances, the
positional weld, the reproducibility digest, and the refuse-and-delete contract.

*Exit gate:* the acceptance list passes on bytes read back from disk, and
`${CLAUDE_PLUGIN_ROOT}/scripts/mesh_audit.py` — an independent implementation outside the
authoring tool — agrees.

### Stage 7 — Check the structure and the printability

Confirm the load path is thick enough at its *thinnest* section, that the print orientation
carries bending within layers rather than across them, and that the overhangs are ones the
printer can actually bridge.

Load the **fdm-structural-design** skill for the bending and adhesive models, the 45-degree
rule used as a design constraint rather than a slicer setting, and the orientation
reasoning.

*Exit gate:* safety factor and minimum wall reported as numbers, not adjectives.

### Stage 8 — Hedge what is still open with a variant set, honestly

When one binding unknown survives Stage 4, print a *set* bracketing the plausible range
rather than a single guess. State what the hedge does **not** cover: a set of three
variants spaced 2 mm apart does nothing about a 10x unit misreading, and if that is the real
error then all three are scrap. A hedge whose limits are unstated reads as more coverage
than it is.

*Exit gate:* the variant spacing and its blind spot are both written down.

### Stage 9 — Slice, print, dry-fit

Hand off to the slicer. The `print-tune-bambu` skill covers settings, material choice, and
verifying by slicing when that toolchain is present. Dry-fit before committing adhesive or
fasteners.

### Stage 10 — Re-check over time

Some criteria cannot be checked before printing. Adhesive creep is the usual one: it is a
30-day question, not a peak-strength question. Schedule the re-check and record the result.

### Stage 11 — Write the as-built numbers back

Update `FACTS.md` with what the finished part actually measures, and retire the reference
draft. The ledger is built to be reopened.

## Artifacts, and what each one is for

| File | Role | Governs |
|---|---|---|
| `FACTS.md` | measured reality, confidence-tagged, with its own defect history | everything |
| `PROJECT.md` | status, plan, and the decision log | the model, not the facts |
| `BUILD-BRIEF.md` | stateless task packet handed to a fresh agent | the generator |
| `<part>_gen.py` | the parametric generator plus its acceptance gate | the exported mesh |
| `verify_report.json` | measured-vs-expected evidence for every variant | the export decision |
| `<part>.stl` | output, and the only artifact the slicer reads | nothing |

Precedence runs left to right: `FACTS.md` beats `PROJECT.md` beats the script beats the mesh.

## Things that make the outcome worse

- **Deriving a dimension that something else already fixes.** Measure it. A formula that
  produces a plausible number will be believed.
- **Deleting a wrong fact.** How the ledger was wrong is the most useful thing in it.
  Strike through, correct beneath, keep both.
- **Trusting a check that never touched the shipped artifact.** Passing counts prove the
  harness ran, not that the part is sound.
- **Hashing the exported file to prove reproducibility.** Triangle emission order and quad
  diagonal choice vary run to run; the file digest changes while the solid does not. Compare
  the vertex-set digest instead.
- **Optimising the section with the loudest stress number.** Check its share of the total
  first: a root fillet that cuts root stress several-fold can move total compliance by 7%
  if the root carries 6% of it.
- **Fixing one defect without measuring what the fix changed.** The corner-radius repair
  that shipped dead-sharp corners passed 165 checks for four iterations, and the file's own
  commentary argued the exclusion was correct.
- **Letting the acceptance list grow without asking what it does not measure.** Every ray
  fired in one plane measures that plane forever.

## Reference files

- `references/stage-checklist.md` — the stages as a copy-paste checklist with entry
  conditions, artifacts, and gates in one table.
- `references/document-set.md` — what belongs in `FACTS.md` vs `PROJECT.md` vs
  `BUILD-BRIEF.md`, with the precedence rules and section skeletons.
- `references/worked-example.md` and `references/worked-example-structural.md` — the shade-bar
  saddle traced through all eleven stages, including each defect that was found and how.

## Related skills and commands

- `/part-forge:new-part` — scaffold a part directory with all three documents and a
  generator skeleton.
- `/part-forge:gen-part` — run a generator, verify, and export behind the gate.
- `/part-forge:verify-part` — audit an existing mesh or STL without Blender.
- `measured-facts-discipline`, `blender-parametric-generator`, `mesh-verification-gate`,
  `fdm-structural-design` — the four depth skills this workflow delegates to.
- `print-tune-bambu` — downstream slicing and material settings.

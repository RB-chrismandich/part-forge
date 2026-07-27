# <PART NAME> -- Project Memory

**Status:** <Draft / Parameterized / Built and verified / Printed / Installed / Closed.>
<One sentence on what exists right now: which files are saved, which are RAM-only, what has
been exported.>
**Last reviewed:** <YYYY-MM-DD> (<how -- e.g. via blender-mcp against the live session>)
**Owner:** <name>

> **Measured reality lives in [`FACTS.md`](./FACTS.md) -- that file governs.** This file
> describes the model and the plan. Where they disagree, `FACTS.md` wins.

That pointer is the whole relationship between the two files. This document may contain
numbers read off the model; `FACTS.md` may not. A value back-filled from the mesh into
`FACTS.md` to make the two agree is the most damaging edit available in this project.

---

## 1. Purpose

<One or two sentences: what the part is, in verbs. State what it is an addition to rather than
a replacement for, if that is the case, because it changes what the part has to do.>

<Envelope and load in one line: plate envelope <w> x <h>; total load < <n> lb.>

## 2. Current state of the model

<Which application and version. Which objects exist. Whether the file has been saved.>

| Property | Value |
|---|---|
| Scene file path | <path, or **empty -- never saved**> |
| Scene units | Metric, `scale_length = <n>`, display unit **<unit>** |
| Mesh objects | <n> (`<name>`) |
| Materials | <n> -- <name>, <description> |

### `<object name>` -- the part

| Metric | Value |
|---|---|
| Bounding dimensions | **<x> x <y> x <z>** mm |
| Topology | <n> verts / <n> edges / <n> tris (<n> quads, <n> n-gons) |
| Watertight? | **<Yes/No>** -- <n> non-manifold edges, <n> boundary edges, <n> loose verts, <n> shells |
| Volume | <n> mm3 |
| Surface area | <n> mm2 |
| Object transform | loc <...>, rot <...>, scale <...> |
| Modifiers | <none / list> |

### Provenance signals

<If the mesh was imported, traced or generated rather than modelled, say so and give the
evidence: generated object names, colour-hash material names, 100 percent triangles, uneven
edge density, a baked-in 90 deg rotation from an axis-convention conversion. A mesh with no
construction history cannot be edited parametrically, and that fact decides section 5.>

## 3. Findings

Findings are kept after they are resolved or dropped. A finding that was raised and deleted
invites the same finding next month.

### 3.1 Resolved by <what resolved them -- e.g. the <date> photo set>

- **<Finding>** -- <how it was resolved, with the number.>

### 3.2 Blocking -- resolve before further modelling

1. **<Finding.>** <Consequence if ignored.> See `FACTS.md` <n>.
2. **<Finding.>** <Consequence.> See `FACTS.md` <n>.

### 3.3 Withdrawn

- ~~**<Finding.>**~~ Withdrawn -- <reason it was wrong.> <What is true instead.>

Withdrawing a finding is evidence about the review process and is worth keeping. State what
made the original wrong, not just that it was.

### 3.4 Should fix

<Numbered, each with the mechanism and whether it disappears as a side effect of another
change.>

### 3.5 Housekeeping

<Naming, origin placement, transforms, material names. Low stakes, but a bad starting state
for export or printing.>

## 4. The real design problem

<The constraint that actually decides whether the part works, separated from the constraints
that merely decide whether it fits. State it with numbers.>

<Where an earlier analysis was wrong, strike it through and correct beneath. If the correction
inverts the conclusion rather than adjusting it, say so.>

| Load | <Quantity> | <Quantity> | <Quantity> |
|---|---|---|---|
| <n> lb | <value> | <value> | <value> |
| <n> lb | <value> | <value> | <value> |

**Before optimising the section with the loudest stress number, compute its share of the
total.** A headline stress ratio is a local claim; compliance and deflection are global. And
compare a deflection budget against whatever else is also deflecting, not against zero.

## 5. GOAL -- committed

> **<One sentence. What gets built, printed, installed, and verified -- and the property that
> makes it maintainable, e.g. modelled parametrically from `FACTS.md` so any dimension that
> turns out wrong is a one-number edit and a reprint, not a remodel.>**

### 5.1 Route: <(a) edit the existing mesh / (b) rebuild parametrically>

<What the existing draft contributes that is worth keeping -- often exactly one dimension.>

<What must change regardless.>

<The cost argument. The decision turns on how many times the geometry will have to change:
when any dimension is still `[OPEN]`, the answer is "more times than expected".>

**Decision: <route>.** <What that makes cheap that was previously expensive.>

<What happens to the old draft -- kept as visual reference until dry-fit, then dropped.>

### 5.2 Parameter table -- the model's entire input

| Param | Meaning | Value | Source |
|---|---|---|---|
| `<NAME>` | <meaning> | **<value>** | `FACTS.md` <n> |
| `<NAME>` | <meaning> | **<value> -- MEASURED INPUT** | `FACTS.md` <n> -- not derived |
| ~~`<NAME>` derived~~ | ~~= <formula>~~ | **superseded** -- see the measured row above | this assumption cost a rebuild |

Keep superseded rows, struck through, with what they cost. The annotation is the cheapest
possible form of the lesson.

Derived: <state the derived quantities and the one place they are computed. Nothing downstream
computes its own.>

> **Correction (supersedes <section>'s "<claim>").** <What the earlier figure conflated, and
> what the floor-versus-target distinction actually is.>

> **<Profile or approach> changed from <A> to <B>.** <Why A was recommended under the earlier
> assumptions, what changed to remove A's virtue, and what A's cost is now that it is exposed.
> A decision invalidated by a later decision -- both recorded.>

### 5.3 Success criteria, in priority order

1. **<The part does its job.>** <The failure that a beautiful part can still have.>
2. **<It stays put.>** <Over what period, under what load.>
3. **It fits the envelope.** <Numbers.>
4. **It fits the mating part.** <Without slop or forcing.>
5. **It is printable and sound.** Watertight, no degenerate geometry, `>= <n>` mm wall on the
   load path, oriented so layer lines do not run across <the loaded section>.
6. **It is reproducible -- as a *solid*, not as a *file*.** Script plus scene plus mesh in this
   repo, every dimension traceable to `FACTS.md`. Note the limit precisely: re-running the
   unedited script reproduces the same solid -- identical unique vertex set, volume and
   measurements -- but **not the same file bytes**. Triangle emission order and the diagonal
   chosen on planar quads both vary run to run, so a file digest carries no signal. Compare the
   vertex-set digest the run prints.

Only <which criterion> cannot be checked before printing. Everything else is a property of the
model.

### 5.4 Variant strategy

<Which dimensions remain uncertain, and the bracketing set. State the spacing.>

**What this hedge does not cover:** <the error class it is blind to, and the consequence if
that is the real error.>

### 5.5 Non-goals

<What this part explicitly does not do, and who or what does it instead. Non-goals prevent
scope returning through the back door as a "should fix".>

## 6. Next actions

**Blocked on the owner** (`FACTS.md` <n>, <n>):

1. <Measurement, with its named procedure.>
2. <Measurement, with its named procedure.>

**Can start now, unblocked** -- the parametric rebuild does not wait on the measurements,
because the measurements are *inputs* to it:

3. <Action.>
4. <Action.>
5. Write the generator against the 5.2 parameter table, with the assumed values as defaults.
6. Generate, verify positionally on the exported file, confirm <the key dimensions>.

**After the measurements land:**

7. Update <params>, re-run, export the 5.4 variant set.
8. Dry-fit, then commit <adhesive/fasteners>. Re-check at 24 h and 30 days.
9. Record the as-built numbers back into `FACTS.md` and retire <the draft>.

---

_<Where the section 2 and section 3 measurements came from, when, and by what method. State
the uncertainty of any sampled figures.>_

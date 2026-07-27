# Stage checklist

The eleven stages, their entry conditions, their single artifact, and the gate that must
hold before the next stage begins. A stage without a gate is a stage that gets skipped
silently, which is why every row has one.

| Stage | Entry condition | Artifact | Exit gate | Load |
|---|---|---|---|---|
| 0. Scope the problem | A physical annoyance exists and is described in words | An owner statement of what the part must *do* (push up / capture / locate / space / adapt) | The verb is settled. "Support the bar" is not a verb; "push up at mid-span, retention already handled by the end brackets" is | `parametric-part-workflow` |
| 1. Build the facts ledger | Problem scoped; photos, an owner spec, or a reference object in hand | `FACTS.md` with a confidence tag on every number | Every number carries a tag, and `[OPEN]` items are enumerated separately as blockers | `measured-facts-discipline` |
| 2. Route decision | A draft, scan, or traced mesh may already exist | A recorded decision in `PROJECT.md`: edit in place, or rebuild parametrically | The choice is justified in writing against the cost of re-deriving under still-open dimensions | `parametric-part-workflow` |
| 3. Write the build brief | Parameter table drafted from `FACTS.md` | `BUILD-BRIEF.md`, self-contained | A reader with no prior context could build the part from this file alone | `measured-facts-discipline` |
| 4. Close blocking measurements | Blocking unknowns identified in Stage 1 | Measurement procedures executed; `FACTS.md` rows upgraded to `[MEASURED]` or `[STATED] CONFIRMED` with a date | Every dimension that decides whether the part *works* is measured, or explicitly deferred to Stage 8's hedge | `measured-facts-discipline` |
| 5. Write the generator | Parameters confirmed enough to produce a first solid | `<part>_gen.py`: parameters at top with `FACTS.md` citations, one `derive()`, named construction phases | Changing one parameter and re-running produces a correct variant with no other edit | `blender-parametric-generator` |
| 6. Gate the export | A solid builds without raising | `acceptance()` list, `verify_report.json`, and only-on-pass exported files | The positional check passes on bytes **read back from disk**, and an independent implementation outside the authoring tool agrees | `mesh-verification-gate`, `/part-forge:gen-part` |
| 7. Structure and printability | Export gate green | Reported safety factor, minimum wall on the load path, overhang area, chosen orientation with its reason | Numbers, not adjectives. A safety factor is a ratio; "strong enough" is not a gate | `fdm-structural-design` |
| 8. Hedge what is still open | One binding unknown survived Stage 4 | A variant set bracketing the plausible range | The spacing **and its blind spot** are both written down | `parametric-part-workflow` |
| 9. Slice, print, dry-fit | Variants accepted | Sliced job; printed part; dry-fit result | The part physically contacts and fits what it was built for, before any adhesive or fastener is committed | `print-tune-bambu` |
| 10. Re-check over time | Part installed | An observation at 24 h and at 30 days | The criterion that cannot be checked before printing -- creep, loosening, fatigue -- has actually been checked | -- |
| 11. Write back the as-built | Install verified over time | `FACTS.md` updated with measured reality; reference draft retired | None. This closes the loop, and the ledger stays open for the next correction | `measured-facts-discipline` |

## Where projects actually stall

Three stages absorb nearly all of the cost when they are skipped, and each fails in a way
that looks like progress at the time.

### Stage 1, skipped by tagging nothing

The mechanism is that an untagged number is indistinguishable from a measured one a week
later. Confidence is carried in the head of whoever wrote it down, and heads do not survive
a context switch.

The shade-bar consequence: the bar diameter entered the project as an estimate of about
22 mm with a range of 19 to 25 mm, derived from a photo. It was used as though it were
known. The confirmed value was 19.05 mm -- **2.95 mm too large**, which on a cradle radius is
the difference between seating and rattling. The estimate was not wrong because the
reasoning was sloppy; it was wrong because a two-step inference chain (measure the hook's
outer width, subtract an *assumed* wall thickness) had been labelled the strongest evidence
available, while the single direct read of the inner opening -- 18 to 19 mm, and closest to
correct -- was discounted for looking imprecise. A tag on each line would have shown that
the "strong" number depended on a guess and the "weak" number did not.

### Stage 4, skipped by deriving instead of measuring

The mechanism is that a formula always returns a plausible number, and a plausible number
is believed. Nothing in the model can tell the difference between a dimension that was
measured and one that was computed from a lower bound.

The shade-bar consequence: bar-centre depth was derived as
`T_plate + D_bar/2 + GAP` = 16.0 mm and correctly described in the brief as "a floor, not a
target" -- and then used as the value. The real depth, fixed by pre-existing end brackets
that nobody had put a ruler to, was 31.75 mm: **1.98 times** the floor. A mid-span support
that reaches 16 mm toward a bar sitting at 31.75 mm does not partially work. It never
touches the bar, and it cost a full rebuild. The parameter table now carries the annotation
`this assumption cost a rebuild` on the superseded row, which is the cheapest possible form
of the lesson.

### Stage 6, skipped by verifying in the authoring tool

The mechanism is that an in-memory mesh and an exported file are different objects, and the
question "is this manifold" has different correct answers for each. An authoring tool counts
faces per *topological* edge. A slicer discards the authoring tool's data structures entirely
and reconstructs topology *by position*. Two vertices at the same coordinate are one vertex
to the slicer and two to the authoring tool.

The shade-bar consequence: the owner opened `saddle_h0.stl` in Bambu Studio and got
`Error: 2 non-manifold edges` while the generator's own run reported `non-manifold edges 0`
and 135 checks passing. Both numbers were correct. They answered different questions, and
the one that mattered was never asked. The fix was structural rather than numeric -- the gate
now parses the binary STL back off disk, welds by position, and refuses *and deletes* any
variant that fails -- and it is the check that stopped a bad part being printed.

The general form is worth stating plainly, because it recurs in every one of this project's
defect sections: **a gate that passes without measuring what ships is not a gate.** Passing
counts prove the harness executed. They do not prove the artifact is sound.

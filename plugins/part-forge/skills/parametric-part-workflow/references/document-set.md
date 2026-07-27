# The document set and its precedence

A part project carries three markdown documents and one script. They are not three views of
the same content; each has a different relationship to the truth, and confusing them is how
a measured number gets overwritten by a modelled one.

## The precedence rule

    FACTS.md  >  PROJECT.md  >  <part>_gen.py  >  <part>.stl

Read left to right: where any two disagree, the one on the left governs and the one on the
right is the thing that must change.

The reason is asymmetric authority. `FACTS.md` records properties of the physical world,
which the project cannot alter -- a bar is the diameter it is. Everything to its right
records decisions the project *did* make, and decisions are revisable. A model that
disagrees with a measurement is a wrong model; a measurement that disagrees with a model is
still a measurement. Reversing the precedence, even once, converts the ledger from evidence
into a record of what was convenient to believe.

The mesh sits at the far right and governs nothing. It is an output. This matters more than
it sounds: the strongest temptation in a long project is to treat a shipped STL as a
reference for "what the part is", and to measure the next revision against it. The
generator, not the mesh, is the definition.

## FACTS.md -- measured reality

Purpose, stated in the original:

> Single source of truth for **real-world constraints**. Nothing here is inferred from the
> Blender model; the model conforms to this file, never the reverse.

### Section skeleton

| Section | Contents |
|---|---|
| Header | Title, the contract sentence above, the confidence legend, a "last updated / sources" line |
| 1 | The job -- what the part must do, in verbs |
| 2 | Mounting or attachment method |
| 3 | Space envelope, as specified by the owner |
| 4 | Existing hardware, explicitly marked reference-only |
| 5..6 | One section per dimension family that has to be measured |
| 7, 7a, 7b, ... | Defect history: one lettered sub-section per defect class found, each kept permanently |
| 8 | Measurements still needed -- the blocker list |
| 9 | Resolved scope -- what is settled and no longer open to relitigation |

### What must never go in it

Anything read off the model. A dimension measured in the authoring tool is a property of a
decision, not of the world, and belongs in `PROJECT.md`. The single most damaging edit
possible to this file is a number back-filled from the mesh to make the two agree.

Also excluded: deletions. Corrections are made by striking through the wrong text and
writing the correction beneath it, both visible. The original states the reason directly --
"Nothing is deleted, because how this file was wrong is the point of the file."

### On the 83 percent

In the worked example, sections 7 through 7j -- pure defect history -- run 709 of 857 lines,
**83 percent of the file**. The sections describing the physical object occupy roughly 130.

That ratio invites a natural objection: the document has stopped being a spec sheet and
become a build diary, and it should be pruned back to the facts. The objection is wrong, and
understanding why is the point of the whole method.

Every one of those sub-sections records a defect that *passed every check that existed at the
time*. Section 7i records a mesh that satisfied 135 assertions and was refused by the
slicer. Section 7h records four consecutive iterations in which 165 checks passed while the
part shipped with dead-sharp corners, and in which the file's own commentary argued that the
exclusion was correct. Section 7e records a measurement that could not see past its own
probe cone, so the geometry never moved and only the number did.

None of that is derivable from the current state of the part. The current parameter values
tell a reader what the answer is; the defect history tells a reader which questions the
harness is bad at asking. The second is what prevents the next defect, and it is available
nowhere else. A pruned `FACTS.md` would be shorter, cleaner, and would have lost the only
content that generalizes.

The practical test for whether a section earns its place: if a future change could
reintroduce this defect, and the reader would have no way to know the defect class exists,
the section stays.

## PROJECT.md -- the plan and the decision log

Purpose: describe the model and the plan, and record why each design decision went the way
it did. It defers explicitly, in its own header, to the facts file -- "Measured reality lives
in FACTS.md; that file governs. This file describes the model and the plan. Where they
disagree, FACTS.md wins."

### Section skeleton

Status / owner / last-reviewed header, then: purpose; current state of the model; findings
split into blocking, should-fix, housekeeping, and withdrawn; the committed goal as one
sentence; the route decision with its reasoning; the parameter table; success criteria in
priority order; the variant strategy; non-goals; next actions split by who is blocking.

### What must never go in it

Unmeasured numbers presented as constraints. If a value belongs in the parameter table it
must cite a `FACTS.md` section, and if no such section exists the value is a design choice
and should say so.

Withdrawn findings are kept, marked withdrawn, with the reason. A finding that was raised
and then dropped is evidence about the review process; deleting it invites the same finding
to be raised again next month.

## BUILD-BRIEF.md -- the task packet

Purpose, stated in the original:

> Hand this file to Claude as the task. It is self-contained: it assumes no prior
> conversation.

### Why it must be stateless

The brief is the one document whose value depends entirely on a property that is easy to
lose by accident.

A brief written mid-conversation absorbs the conversation. It says "the profile discussed
above", "the corrected value", "as agreed" -- and each of those is a pointer into a context
that will not exist when the file is next opened. The reader is then a fresh agent, or the
same person six weeks later, and the pointer resolves to nothing. What follows is not a
clean failure. The reader fills the gap with the most plausible interpretation, builds
something coherent, and the divergence is invisible until the part is in hand.

Statelessness is also what makes the brief *portable*, and portability is what makes the
generator re-derivable. A brief that can be handed to a fresh agent can be handed to a
second one independently, and the two results compared -- which is how the worked example
validated its fillet mathematics, by having the derivation re-implemented from scratch
outside the authoring tool and checking that every figure reproduced to six decimals. That
cross-check is impossible if the brief only makes sense to someone who was present.

Concretely, statelessness means: no pronouns referring outside the file; every parameter
carries its value, its units, and its source; every constraint is a number; the coordinate
system is stated rather than assumed; and the *Do not* list is written out, because the
things a fresh reader will reasonably try are exactly the things a present reader already
knows to avoid.

### Section skeleton

Framing line; your task; context -- why this part exists; parameters, with empirical
mesh-robustness constants kept in a clearly separate subsection from dimensions; coordinate
system; geometry, feature by feature, with formulas; constraints as numeric gates; print
orientation with its reason; deliverables by exact filename; unverified assumptions;
acceptance checks; *Do not*.

### What must never go in it

Status, history, or narrative. The brief is not a place to record what was tried; that is
`FACTS.md`. A brief that grows a history section stops being a task packet and becomes a
second, competing project file.

## The generator and the mesh

The generator holds the parameter table, the single derivation, the construction phases, and
the acceptance list. The acceptance list is the specification of record: the original states
it as "`saddle_gen.py`'s own `acceptance()` list is the specification of record -- 55 checks
per variant, 165 across the three, every one comparing a *measured* number against an
expected one", and then resolves the precedence question directly -- **where the brief and
the code disagree, the code wins.**

That rule is only safe because the code is checked against the world rather than against
itself. Prose describes intent; the executable check is the actual gate; and the gate is
worth trusting only when it measures the artifact that ships. The three claims are load
bearing together and worthless individually.

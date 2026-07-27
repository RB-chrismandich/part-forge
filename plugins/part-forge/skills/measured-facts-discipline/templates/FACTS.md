# <PART NAME> -- Facts & Actuals

Single source of truth for **real-world constraints**. Nothing here is inferred from the
model; the model conforms to this file, never the reverse.

**Confidence legend** -- every number in this file carries one of these tags. An untagged
number is a defect.

- `[STATED]` -- asserted directly by the owner. Treat as true.
- `[MEASURED +/-tol]` -- measured directly, with the instrument named. e.g.
  `[MEASURED +/-0.05 mm, digital callipers]`, `[MEASURED +/-0.3 mm, paper strip]`.
- `[PHOTO +/-tol]` -- derived from an image with a scale reference. **Carries real error.
  Confirm before printing.**
- `[DERIVED from N.N]` -- follows from other facts in this file. Carries **no independent
  authority**: it is only as good as the weakest fact it depends on, and it must never be
  used where the real value is fixed by something outside this project's control.
- `[OPEN]` -- not yet known. **Blocks anything that depends on it.** Listed in section 8.

**Status words used in prose.** These are not fact tags; they mark what happened to a fact or
a section over time.

| Word | Meaning |
|---|---|
| `CONFIRMED` | An estimate has been upgraded by direct measurement or owner statement. Carries a date. |
| `SUPERSEDED` | Replaced by a later fact. The original text stays, struck through, with a pointer to what replaced it. |
| `WITHDRAWN` | A finding that was raised and is no longer claimed. The reason stays. |
| `REFUTED` | A specific claim disproven by a later fact. Names the fact that disproved it. |
| `FIXED` | A defect section whose defect has been corrected. The history stays. |
| `DONE` | A section-8 blocker that has been closed. |
| `reported, not gated` | A quantity the harness measures and prints but does not fail on. Marks the difference between "passed" and "was never looked at". |

**Last updated:** <YYYY-MM-DD>
**Sources:** <n photos, owner spec of YYYY-MM-DD, direct measurement of YYYY-MM-DD, ...>

**Nothing is deleted from this file, because how this file was wrong is the point of the
file.** Corrections strike through the wrong text and write the correction beneath it, both
visible.

---

## 1. The job

What the part must **do**, in verbs. Not "support X" -- *push up*, *capture*, *locate
laterally*, *space apart*, *adapt*. A part asked to do less gets smaller and stronger.

| # | Fact | Confidence |
|---|---|---|
| 1.1 | **<What is wrong with the current situation.>** | `[STATED]` -- owner, <date> |
| 1.2 | **<What existing hardware already does part of the job.>** | `[STATED]` -- owner, <date> |
| 1.3 | **<What that existing hardware does NOT do.>** | `[PHOTO +/-tol]` |
| 1.4 | **Therefore this part only has to <verb>.** | `[DERIVED from 1.2-1.3]` |
| 1.5 | Total load: **<n> lb / <n> N**. | `[STATED]` -- owner, <date> |

Mark the single most consequential fact in this section explicitly. Downstream decisions that
rest on a *structural* fact survive a later arithmetic correction; decisions resting on a
number do not.

## 2. Mounting method

| # | Fact | Confidence |
|---|---|---|
| 2.1 | Attachment is **<adhesive / screwed / clamped / friction>**. | `[STATED]` -- owner, <date> |
| 2.2 | Substrate is **<material>**. | `[OPEN]` |

Adhesive mounts fail by creep over weeks, not by peak strength at install. If 2.1 is
adhesive, the product's **long-term static** rating governs, not its headline number.

## 3. Space envelope -- owner spec

| # | Fact | Value | Confidence |
|---|---|---|---|
| 3.1 | Max width | **<n> mm / <n> in** | `[STATED]` -- owner, <date> |
| 3.2 | Max height | **<n> mm / <n> in** (hard cap) | `[STATED]` -- owner, <date> |
| 3.3 | Max projection | **<n> mm / <n> in** | `[OPEN]` |

Dual units on every dimension. A value that is exactly a round imperial figure
(76.2 mm = 3.000 in) is evidence the source was imperial, and that is worth knowing.

## 4. Existing hardware -- reference only, not the part being built

Measurements of what is already installed. This section informs the design and constrains it;
none of it is a target to match.

| # | Fact | Confidence |
|---|---|---|
| 4.1 | <Overall dimension of the existing item.> | `[PHOTO +/-tol]` |
| 4.2 | <A dimension this part must clear or conform to.> | `[PHOTO +/-tol]` |

**Anything fixed by this hardware is an input to the new part, not a derivation.** See
section 8: measure it.

## 5. <Primary dimension family> -- e.g. the bar diameter

| # | Fact | Value | Confidence |
|---|---|---|---|
| 5.1 | <Dimension> | **<n> mm** | `[OPEN]` -> upgrade on measurement |

### How to settle it exactly, with the tools on hand

State the procedure, its **error budget**, and what it can **discriminate**. A procedure
without those two is not yet a procedure.

1. <Step.>
2. <Step.>
3. <Result formula.>

Error budget: reading <X> to <tol> gives <dimension> to about <tol>.
Discriminability: the candidate values are <a>, <b>, <c> -- far enough apart that even a
sloppy measurement is decisive.

### Evidence lines considered

| Route | Reading | Steps of inference | Weakest step |
|---|---|---|---|
| <Direct read of the dimension> | <value> | 1 | <what makes it noisy> |
| <Indirect: measure A, subtract assumed B> | <value> | 2 | **B is itself a guess** |

A chain is at best as good as its weakest link, and the weak link is usually the invisible
one. Prefer one noisy direct measurement over two clean inferences.

## 6. <Placement dimension family> -- the sleeper requirement

The dimension that decides whether the part *does its job* rather than whether it *fits*.
Usually the one nobody thinks to measure.

| # | Fact | Value | Confidence |
|---|---|---|---|
| 6.1 | <Placement dimension> | **<n> mm** | `[OPEN]` |

**Unit note on 6.1.** When a stated value has ambiguous units, resolve it by cross-check: find
a second, independently-derived number that should coincide under the correct reading, and
test agreement. Re-run the cross-check if any input to it later changes.

**6.x is a constraint, not a design choice.** If this dimension is fixed by hardware outside
this project, a value derived from this part's own geometry answers a different question
("how close *could* it sit") and the world has no obligation to sit at the minimum.

---

## 7. <Original analysis section> -- SUPERSEDED by 7f (kept as defect history)

Sections 7 and 7a, 7b, ... are the **defect history**. One lettered sub-section per defect
class found. They are permanent. In the reference project these sections grew to 83 percent
of the file, and that is the file working as designed: the parameter values say what the
answer is, while the defect history says which questions the harness is bad at asking. Only
the second generalizes.

**Nothing is deleted, because how this file was wrong is the point of the file.**

### The claim-by-claim retraction table

When a section is superseded wholesale, head it with a table separating what is wrong from
what governs now, so a reader who lands mid-file is not misled by the surviving prose.

| Claim below | Status |
|---|---|
| "<quoted claim>" | **wrong** -- <reason>, see 7f.1 |
| "<quoted claim>" | **wrong divisor** -- <what it divided by instead>, see 7f.2 |
| "<quoted claim>" | **refuted** -- see 6.4 |
| "<quoted claim>" | **inverted** -- <the opposite is true>, see 7f.2 |

### The strike-through-and-correct pattern

~~<The original wrong text, struck through in full. Do not shorten it -- a reader must be able
to see exactly what was believed and how confidently.>~~

**Corrected <YYYY-MM-DD>.** <The correct statement, with the number that replaced the wrong
one and the measurement or reasoning that produced it.>

When the correction *inverts* rather than adjusts the original, say so plainly:

~~<Original conclusion.>~~

**That is backwards, and it is the reason the rest of this correction exists.** <The inverted
conclusion, with the two errors that combined to produce the original.>

### 7a. <Defect title> -- <STATUS> <date>

**What was believed:** <the claim>
**What is true:** <the measurement>
**How it hid:** <which check passed anyway, and why it was answering a different question>
**Defect class:** <gate measured the wrong invariant / check went vacuous / probe constant
stale / sampled one station forever / fix side effect unmeasured / conclusion inverted>
**What now catches it:** <the specific check added, and what it measures>

### 7b. <Next defect> -- <STATUS> <date>

<Same shape.>

### 7x. <A known residual, recorded and deliberately not fixed> -- OPEN

Some defects are correctly left alone. Record the decision as an explicit numbered judgement
so the next reader does not re-open it:

1. The fix would not achieve the stated goal, because <reason>.
2. It touches the artifact-producing path to change nothing about the artifact.
3. It needs new machinery that would itself be unchecked.
4. Nothing downstream reads the property.
5. The actual underlying need is already met, more cheaply, by <what>.

`reported, not gated` -- the harness prints <quantity> every run so a reader can see it, and
does not fail on it.

---

## 8. Measurements still needed

The blocker list. Nothing downstream may treat any of these as known. Strike through and mark
`DONE` with the value and date when closed.

1. **<Dimension>** -- <why it blocks, which section depends on it>. Procedure: <named
   method>. `[OPEN]`
2. ~~**<Dimension>**~~ -- **DONE**, <value>, see section <n>.

Each entry names the procedure, not just the quantity. "Measure the bar" is not an
instruction; "wrap a paper strip, mark the overlap, measure mark to mark, divide by pi" is.

## 9. Resolved scope

What is settled and no longer open to relitigation. A decision that keeps being re-argued
belongs here with its reason.

| # | Settled | Reason |
|---|---|---|
| 9.1 | <Decision> | `[STATED]` -- owner, <date> |
| 9.2 | <Decision> | `[DERIVED from 1.4]` |

---

_All values tagged `[PHOTO]` carry the stated error and must be confirmed before committing to
a print. Values tagged `[DERIVED]` inherit the uncertainty of every fact they depend on._

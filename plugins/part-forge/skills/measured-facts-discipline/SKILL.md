---
name: measured-facts-discipline
description: Record and maintain the measured-reality ledger a physical design depends on. Use when writing or auditing a FACTS.md, when a dimension is estimated from a photo rather than measured, when a fact turns out wrong and must be corrected without erasing it, when deciding whether a number is measured or merely derived, or when a design needs a physical measurement procedure — bar diameter, bore, spacing, or a printed go/no-go gauge.
---

# The facts ledger

A model is internally consistent by construction. That is exactly why it cannot tell
whether it fits the room. The only defence is a separate document that holds what is
*actually true of the world*, written down with how well it is known, and given authority
over the model rather than derived from it.

The contract, stated on the ledger's own first line:

> Single source of truth for real-world constraints. Nothing here is inferred from the
> model; the model conforms to this file, never the reverse.

That direction is the whole point. A ledger that gets updated to match the model has
become a description of the model and has stopped being evidence.

## Tag every number

A number with no confidence tag is indistinguishable from a guess six weeks later, and
will be treated as fact by whoever reads it next. Five tags cover every case:

| Tag | Meaning | How much weight it carries |
|---|---|---|
| `[STATED]` | asserted directly by the owner | treat as true |
| `[MEASURED +/-tol]` | measured, with the instrument named | true within the stated band |
| `[PHOTO +/-tol]` | scaled off an image | carries real error; **confirm before printing** |
| `[DERIVED from N.N]` | follows from other facts | no independent authority; inherits their error |
| `[OPEN]` | not yet known | blocks everything downstream of it |

The tolerance belongs *inside* the tag, not in a separate column — value, units, and error
band are one token, so they cannot drift apart. `[PHOTO +/-3 mm]` is a complete statement;
"about 51 mm" is not.

The per-fact row:

```
| N.N | **Fact statement, value in dual units** | `[TAG +/-tol]` - source, date |
```

Give dual units whenever the source spec is imperial. A part whose plate is "76.2 mm" is
harder to sanity-check than one whose plate is "76.2 mm / 3.000 in", where the round number
in the second column tells you which one the world actually chose.

## `[DERIVED]` is the dangerous tag

A derived number looks like a measurement, reads like a measurement, and is believed like a
measurement. It is only as good as its weakest input, and that input is often an assumption
nobody wrote down.

**The rule that matters most in this skill: never derive a dimension that something outside
your control already fixes. Measure it.**

The canonical failure. A mounting depth was derived as
`plate_thickness + radius/2 + gap` = 16.0 mm. The brief was even honest about it, calling
the result "a floor, not a target". Then the floor was used as the value. The real depth was
set by brackets that had been on the wall for years and that nobody had measured: **31.75 mm,
1.98x the derived figure.** The part could not reach the thing it existed to support. The
parameter table now carries the annotation `this assumption cost a rebuild`.

The generalisation: a formula gives you the minimum the geometry permits. The world sits at
that minimum only by coincidence.

A second trap, subtler. Prefer the direct read over the longer chain even when the chain
looks better evidenced. A diameter inferred from *hook outer width minus assumed wall
thickness* used two clean, well-lit measurements and was treated as the strongest line of
evidence. It was 2.95 mm wrong, because the wall thickness in the middle was itself a guess.
The discounted direct read of the inner opening — dismissed as foreshortened — was closest
to correct. **Each inference step silently imports its own assumptions; a two-step chain
built on measurements is weaker than a one-step read that looks imprecise.**

## Correcting a fact without erasing it

> Nothing is deleted, because how this file was wrong is the point of the file.

Mechanism: strike the wrong text in place, put the correction immediately beneath it, and
keep both visible.

```markdown
~~Tape face 76.19 x 44.45 mm, 92.7% filled -> 4.86 in2 of adhesive contact.~~

**Corrected.** The face is 76.2 x 44.45 = 3387.1 mm2, and the acceptance report measures the
rounded-corner face at 3351.1 mm2 = 5.194 in2 on every run - 98.9% filled, not 92.7%.
```

When a correction invalidates several claims at once, a retraction table beats prose,
because it separates *what is wrong* from *what governs now* claim by claim:

| Claim below | Status |
|---|---|
| "4.86 in2 of adhesive contact" | **wrong** - and the tape face is not the bond either, see 7f.1 |
| "avg shear 1.03 psi" | **wrong divisor** - divides by the face, not the bond, see 7f.2 |
| "deleting the hook halves every number above" | **refuted** - see 6.4 |
| "at under 10 lb the adhesive is comfortable" | **inverted** - peel is the binding constraint |

That last row is worth studying. The original conclusion was not merely imprecise, it was
backwards, and the load number that seemed to settle the question did not settle it.

Separate a decision from the numeric argument made in its support. When the argument falls,
check whether the decision falls with it — often it does not. The choice to build a saddle
rather than a hook survived the refutation of the moment-arm claim that had been offered for
it, because the decision actually rested on a different fact entirely.

Status words used in running prose, beyond the five tags: **CONFIRMED** (upgraded from
estimate to owner-verified, with who and when), **SUPERSEDED by N.N** (as a section header,
section kept as history), **WITHDRAWN** (a finding retracted), **REFUTED** (a specific claim
disproven by a later fact), **FIXED** *date* (a defect resolved), **DONE** (a blocker
closed), and **reported, not gated** (measured and printed, deliberately not enforced).

## Defect history is content, not debt

In the worked example, sections 7a through 7j — the record of how the generator was wrong
and how each wrongness was found — grew to **709 of 857 lines, 83% of the file**. That is
the file working as designed. A ledger that stays short across several build iterations is
not clean; it is discarding the only evidence that shows which checks can be trusted.

Each defect entry should answer three things: what was believed, how it hid, and what
finally caught it. The third is the reusable part.

## Measuring things

Procedures, error budgets, and when to print a gauge instead of measuring:
`references/measurement-procedures.md`.

The short version. **Paper strip beats callipers on a mounted bar**: wrap, mark the overlap,
lay flat, measure mark-to-mark for circumference C, divide by pi. Reading C to 1 mm gives
diameter to about 0.3 mm — and the candidate sizes are far enough apart (3/4 in gives
C ~ 60 mm, 7/8 in ~ 70 mm, 1 in ~ 80 mm) that even a sloppy reading is decisive. Quote the
error budget and the discriminability check alongside any procedure; a method whose
resolution is not stated cannot be trusted to settle anything.

**When a dimension cannot be measured with what is on hand, print the question.** A flat
comb with semicircular notches at the candidate sizes, each labelled, converts an argument
into something that can be tried against the real object. Minutes of print time.

**When units are ambiguous, disambiguate by cross-check.** An owner writing "2 at the base"
cannot mean metres. Find a second, independently derived number that should coincide under
the correct reading and test the agreement: at 2 mm the bar centre landed within 0.83 mm of
where an existing draft independently put it, which it would not have under 2 cm or 2 in.
Then re-validate the cross-check if any input to it later changes.

## Things that make the ledger worse

- **An untagged number.** It will be read as fact.
- **Deleting a wrong fact.** The correction is more valuable than the fact ever was.
- **A `[DERIVED]` value standing in for something the world already decided.** Measure it.
- **A correction that says what is wrong but not what governs now.** The next reader has to
  redo the reasoning.
- **Relative dates.** "Last week" is unresolvable in a file that lives for months.
- **Updating the ledger to match the model.** The direction of authority is the contract.
- **A tolerance quoted without the instrument.** `+/-0.1 mm` from a tape measure is fiction.
- **Letting `[OPEN]` items sit outside the blocker list.** An unknown that is not enumerated
  gets treated as known by whoever builds next.
- **An envelope row and a settled-scope row that contradict each other.** Section 3 constrains
  the *shell*; section 9 chooses *mechanisms*. "Must print in one piece, no glue seam" and
  "retrieval by twist-lock plug" were both written into one ledger, and a twist-lock plug is a
  second printed piece by definition — they disagreed from the moment the second was written.
  Read the two sections against each other, and when they collide the envelope loses: it is a
  claim about the shell, not about the assembly. The precedence rule does not settle
  this. `FACTS.md` beats `PROJECT.md` orders *files*, and both of these live in the same file,
  so nothing in the contract adjudicates it and no structural gate can — `repo_check.py` was
  correctly silent throughout, because this is semantics.

## Reference files

- `references/measurement-procedures.md` — physical procedures with error budgets, gauge
  design, unit disambiguation, and what each instrument can honestly resolve.
- `references/correction-protocol.md` — the supersede, withdraw, and refute patterns with
  full worked examples, and the five-point test for when *not* to chase a known defect.
- `templates/FACTS.md`, `templates/PROJECT.md`, `templates/BUILD-BRIEF.md` — fill-in
  skeletons with the legend, the section numbering, and the table formats already in place.

## Related

- `parametric-part-workflow` — the process this ledger anchors; Stage 1 and Stage 4.
- `facts-auditor` agent — audits an existing ledger for untagged numbers, derived values
  standing in for measurements, unenumerated blockers, and missing defect history.
- `/part-forge:new-part` — scaffolds all three documents from the templates above.

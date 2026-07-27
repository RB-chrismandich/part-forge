# Correction protocol

> Nothing is deleted, because how this file was wrong is the point of the file.

A ledger exists to be wrong in public. Its value is not the facts it currently holds -- those
could be a table -- but the record of which beliefs failed, how they hid, and what caught
them. That record is what tells a future reader which parts of the current state to trust.

## Strike through, correct beneath, keep both

The mechanism is deliberately low-tech, because it has to survive being read by someone in a
hurry six months from now.

```markdown
~~Measured from the draft: tape face 76.19 x 44.45 mm, 92.7% filled -> 4.86 in2
of adhesive contact.~~

**Corrected.** The tape face is 76.2 x 44.45 = 3387.1 mm2, and the acceptance report
measures the rounded-corner face at 3351.1 mm2 = 5.194 in2 on every run - 98.9%
filled, not 92.7%.
```

Three properties make this work. The wrong text stays visible, so a reader who remembers the
old number recognises it and knows it was retracted rather than wondering whether they are
looking at a different fact. The correction sits immediately beneath, so there is no hunting.
And the correction states the new value *and* where it came from, so it is itself auditable.

Never edit a wrong number in place. An in-place edit destroys the only evidence that the
number was ever in doubt, and the next person will trust it exactly as much as a number that
was right the first time -- which is precisely the wrong amount.

## The claim-by-claim retraction table

When one correction invalidates several downstream claims, prose loses track. A table
separates what is wrong from what governs now, claim by claim, so nothing is silently carried
forward:

| Claim below | Status |
|---|---|
| "4.86 in2 of adhesive contact" | **wrong** - and the tape face is not the bond either, see 7f.1 |
| "avg shear 1.03 psi" | **wrong divisor** - divides by the face, not the bond, see 7f.2 |
| "deleting the hook halves every number above" | **refuted** - see 6.4 |
| "at under 10 lb the adhesive is comfortable" | **inverted** - peel is the binding constraint |

Read the four verdicts as a taxonomy, because they call for different responses:

- **wrong** - the value is incorrect; replace it.
- **wrong divisor** - the arithmetic is sound and the input is not. Every result computed the
  same way is also wrong, so this verdict obliges a sweep rather than a fix.
- **refuted** - a specific claim disproven by a later fact. The claim goes; whatever rested on
  it needs re-examining.
- **inverted** - the conclusion is not merely imprecise, it points the other way. The most
  dangerous verdict, because the original reasoning usually looked sound and the correction
  reads as a reversal rather than a refinement.

That last row is worth dwelling on. The original text concluded the adhesive was "comfortable,
not marginal" on the strength of a newly obtained load figure. Peel was the binding constraint
the whole time -- 12.5 psi against 1.67 psi of shear -- and the load number that appeared to
settle the question did not touch it. A number arriving does not automatically resolve the
question it seems to address.

## The status words

| Word | Applies to | Means |
|---|---|---|
| `CORRECTED` | a value | the number was wrong; the right one is below |
| `SUPERSEDED by N.N` | a section | still true as history, no longer governing; see the named section |
| `WITHDRAWN` | a finding or concern | raised, investigated, and no longer held |
| `REFUTED` | a specific claim | disproven by a later fact, which is named |
| `FIXED <date>` | a defect | resolved in the artifact, with the date it landed |
| `DONE` | a blocker | the measurement was taken or the question answered |
| `OPEN` | a question | deliberately unresolved, with the reason |
| `reported, not gated` | a measurement | measured and printed, deliberately not enforced |

Two distinctions that get blurred. **SUPERSEDED is not WITHDRAWN**: a superseded section was
right when written and has been overtaken, so it stays as history; a withdrawn finding was
never right. And **FIXED is not DONE**: FIXED belongs to a defect in the artifact, DONE to an
item on the blocker list. Conflating them produces a punch-list that looks complete while
defects remain.

Every one of these carries a date and, where a person decided, a name.

## Separate a decision from the argument offered for it

When an argument falls, check whether the decision falls with it. Often it does not, and
re-litigating a sound decision because its supporting arithmetic was wrong is its own kind of
waste.

The worked case. The choice to build a **saddle rather than a hook** was argued partly on the
grounds that deleting the hook curl would halve the moment arm. That claim was later refuted:
the arm is fixed by the existing end brackets and deleting the curl does not move it.

The decision survived unchanged. It rested on a different fact entirely -- that the end
brackets already capture the bar, so the mid-span part has no retention job to do -- and that
fact was untouched. The ledger records this explicitly: the conclusion "is unaffected: it
rests on 1.4, not on any number in this section."

The discipline: when recording a decision, name the fact it actually rests on, separately
from any numeric argument used to illustrate it. Then a later refutation of the illustration
is a local edit instead of a reopened decision.

The inverse also happens. A decision can survive its stated reason and still be wrong for a
reason nobody wrote down. Naming the load-bearing fact makes both cases checkable.

## Attribute owner-authorised trades

Some corrections are not discoveries but **decisions with a cost**, and those need a name
attached.

A round-over radius was reduced from 1.0 to 0.5 mm to fix a print-quality defect. That is not
a free improvement: the smaller radius eats less into the load-bearing wall, but it also
delivers less of the stress relief the larger radius was there for. The ledger records it as
**"`ROUND_R` 1.0 -> 0.5 (owner's decision, iteration 6)"**.

The attribution matters because a trade applied silently is indistinguishable from a bug
later. A reader finding 0.5 where the design rationale argues for 1.0 has to reconstruct
whether it was chosen or drifted. With the attribution, they know it was chosen, by whom, and
at which iteration -- and can go and ask.

Rule: anything that trades one stated goal against another gets an attribution. Anything that
merely corrects an error does not need one.

## The five-point test for when NOT to chase a defect

Not every known wrongness should be fixed. The determinism case is the model: raw exported
file bytes were not reproducible run to run, this was fully understood, and the deliberate
decision was to record it and leave it.

Apply all five. Chase the defect unless every one is satisfied:

1. **Would the fix actually achieve the stated goal?** Imposing a deterministic triangulation
   order would not have made the files byte-identical, because the emission order has other
   nondeterministic inputs. A fix that does not reach the goal is not a partial fix.
2. **Does the fix touch the artifact-producing path to change nothing about the artifact?**
   The change would have run inside the code that generates the shipped solid, to alter a
   property of the file that is not the solid. Risk to the deliverable, no benefit to it.
3. **Does it need new, unchecked machinery?** A deterministic tie-break needs a canonical
   vertex ordering, which is new code on the critical path with no existing test coverage.
   New unverified machinery guarding an already-understood non-problem is a bad trade.
4. **Does anything downstream read the property?** No slicer, no check, and no person reads
   the file hash. A property nobody consumes cannot cause a failure.
5. **Is the underlying need already met more cheaply?** The actual need was "tell me whether
   my edit changed the solid", and the vertex-set digest answers it exactly, at no cost.

When all five hold, record the defect with its analysis and mark it `OPEN, deliberately`. That
is a different state from `OPEN` and from silence, and the distinction is the point: a reader
finds a known issue with a reasoned decision attached, not an oversight and not a gap.

Write the five answers down. A decision not to fix something is exactly as reviewable as a
decision to fix it, and considerably harder to reconstruct later.

## The closing rule

A ledger with no defect history, after several build iterations, is not a clean ledger. It is
one that is deleting its evidence.

In the worked example the defect sections grew to 709 of 857 lines -- 83% of the file. That
ratio is the file working as designed. The short sections at the front say what is true; the
long sections behind them say how much to trust it, which checks have already failed silently,
and which classes of error this project has actually made. A reader who has only the first
part has facts without calibration.

If a ledger is staying short across iterations, the question is not "why is it so tidy" but
"where did the corrections go".

# Worked example, continued: structural analysis through delivery

Stages 7 through 11 of the shade-bar mid-span saddle case study. Stages 0
through 6 -- scoping, the facts ledger, the parametric rebuild, and the
verification-gate defect -- are in `worked-example.md`. Source files live at
`projects/shade-bar-mount/`.

## Stage 7 -- the structural analysis, and an inverted conclusion

The adhesive analysis was written, believed, and then found to be backwards.

The original conclusion read: "at under 10 lb the adhesive is comfortable, not marginal. My
earlier concern about peel being the governing risk was based on an unknown load; with the
real number it is not the binding constraint."

`FACTS.md` 7 strikes that through and replies: "**That is backwards, and it is the reason the
rest of this correction exists.** Peel *is* the binding constraint." At the confirmed moment
arm, a single tape strip sees **12.5 psi of peel against 1.67 psi of shear**. Two errors had
combined: the bonded area had been taken as the whole plate face rather than the actual strip
footprint, overstating it by 73 percent, and the shear figure divided by that same wrong
area. The load number did not dispose of the peel concern, because peel and shear do not
scale together.

The mechanism worth carrying forward: peel is a *bending* problem on the bond, so with
section modulus `S = b*h^2/6` the peel stress scales as **1/h^2** in bonded height. That is
why coverage matters more than intuition suggests, and it is quantified -- backing the top
strip off by 0.098 in costs `(1.750/1.652)^2 = 1.12`, a **12 percent peel penalty across the
entire bond**, whereas notching around a 5 mm2 void in a 3387 mm2 bond costs **0.15 percent**.
Coverage wins on the numbers.

Bond configurations compared:

| Bond | Area | Shear | Peel |
|---|---|---|---|
| One strip, 1.00 in | 3.00 in2 | 1.67 psi | 12.5 psi |
| One full strip plus one trimmed to 0.75 in | 5.25 in2 | 0.95 psi | 4.1 psi |
| Two full strips, plate height 50.8 mm | 6.00 in2 | 0.83 psi | 3.1 psi |

### The fillet that optimised the wrong section

A root fillet was enlarged from R8 to R16 to cut stress where the cradle meets the plate. The
root stress does fall hard. `FACTS.md` 7d then asks what fraction of the arm's total creep
compliance the root actually carries, using a weighted compliance integral
`integral (yL - y)^2 * sigma^(n-1) / I dy` evaluated at Norton exponent n = 3 to 5:

| Region | R_ROOT = 8 | R_ROOT = 16 |
|---|---|---|
| Root, Y < 15 | 19.1% | 6.2% |
| Mid | 4.4% | 4.1% |
| Trough wall, Y > 21 | **76.5%** | **89.7%** |

Total arm creep compliance falls only **15 percent at n=3 and 7 percent at n=5** from R8 to
R16 -- "not the 5 to 10x the root stress ratio suggests". The section that dominates is the
cradle wall, which the root fillet cannot reach.

A related finding from `BUILD-BRIEF.md`: total tip deflection is about **10 micrometres**,
against **46 to 253 micrometres** contributed by the compliant tape layer underneath.
Stiffening the plastic further is "optimising the wrong component by an order of magnitude".

**Lesson.** Before optimising the section with the loudest stress number, compute its share
of the total. A headline stress ratio is a local claim; compliance and deflection are global
ones, and only the global ones describe the part. And compare a deflection budget against
whatever is *also* deflecting, not against zero.

## Stage 7, continued -- the fix whose side effect nobody measured

`FACTS.md` 7h runs 209 lines and is a two-act story.

Act one: the plate's corner bevel could not fit its own edges and produced spikes. Act two:
the fix shipped the plate's four corners **dead sharp** -- no round-over at all.

The damning sentence: "Every one of the **165 checks passed**, on every variant, for four
iterations. It is the same class as 7i and 7c -- a property nobody measured -- except that
here **the file's own commentary argued for the exclusion**."

That last clause is the part worth internalising. The prose had described the fix as taking
"the corner arcs whole", which sounded correct and was never checked against what "whole"
meant on the physical part. The rationalisation preceded the verification and then substituted
for it.

**Lesson.** A fix changes more than the defect it targets. Enumerate what the fix touches and
add a check for each, before the fix is accepted. Be most suspicious where the reasoning is
most fluent: a confident sentence explaining why something is fine is not a measurement, and
reads more like one than a gap does.

## Stage 8 -- an honest hedge

Two dimensions remained uncertain enough to matter, so the first print was a set rather than
a part: three variants at `H_DROP` of **0, 2 and 4 mm** -- nominal 2 mm, bracketed by plus and
minus 2 mm.

What makes this a good hedge is the paragraph stating its limits. `BUILD-BRIEF.md` records
that the variant set does **not** hedge against a 10x unit misreading; if the owner's "2 at
the base" meant 2 cm rather than 2 mm, then all three STLs are scrap. A 2 mm bracket covers a
2 mm error. It covers nothing about a 20 mm one.

**Lesson.** State a hedge's coverage *and* its blind spot in the same place. Three variants
reads as thoroughness; three variants spaced 2 mm apart reads as what it is. An unstated limit
is claimed coverage.

## Stages 9 to 11 -- the criteria that only time can check

Success criteria, in the priority order `PROJECT.md` 6.3 assigns them: the sag is gone ("a
beautiful part that doesn't contact the bar is a failure"); it stays up, with no adhesive
creep or peel over 30 days under continuous load; it fits the envelope; it fits the bar; it is
printable and sound; it is reproducible as a solid rather than as a file.

Only the second cannot be checked before printing. Everything else is a property of the
model. Adhesive failure under sustained load is a creep problem measured in weeks, not a
peak-strength problem measured at install -- which is why the plan schedules a re-check at 24
hours and at 30 days, and why the material section specifies verifying the chosen product's
*long-term static* rating rather than its headline strength.

Stage 11 writes the as-built numbers back into `FACTS.md` and retires the reference draft.
The ledger stays open.

## Defect taxonomy

Every defect in this project belongs to one of five classes. All five share a shape: the check
that would have caught it either did not exist or was not asking about the artifact.

| Defect class | How it hid | What would have caught it |
|---|---|---|
| **Gate measured the wrong invariant** | The harness asserted topological manifoldness on the in-memory mesh; the slicer reconstructs topology by position. 135 checks passed and Bambu Studio refused the file (7i) | Parse the exported bytes back off disk, weld by position, reconstruct topology independently -- and refuse *and delete* on failure. Never share code with the producer |
| **Check silently went vacuous** | `_assert_root_is_solid` still runs, but on current geometry every sampled station takes an early-out branch, so it passes without testing anything. Disclosed rather than hidden | Report the count of stations actually *tested*, not just the pass/fail. A check that reports `tested: 0` is visibly not a check |
| **Probe constant went stale** | `FACE_PROBE_X` was hard-coded at 20.0 mm. A later feature (`FLARE_TIP`) grew the part past it, and the probe began sampling the wrong place while continuing to pass | Derive probe positions from the parameters they depend on -- the constant is now computed as `W_SADDLE/2 + FLARE + FLARE_TIP + 2.0`. A literal in a verification harness is a future stale value |
| **Ray fired in one plane forever** | Every wall-thickness ray was cast in the X=0 plane, and X=0 is deliberately the centre of a *land*. One sweep "would have measured the land forever and never looked at the groove" -- the groove floor being the thinner section | Sample the geometry at the station that is *worst*, not the one that is convenient. The harness now sweeps two X stations, land and groove floor, and gates on the minimum |
| **Fix's side effect never measured** | The corner-bevel repair shipped dead-sharp corners through four iterations and 165 passing checks, while the file's own prose argued the exclusion was correct (7h) | Enumerate what a fix touches and add a check per item before accepting it. Treat confident prose about why something is fine as an unverified claim |
| **Conclusion inverted, arithmetic sound** | The adhesive analysis used the plate face as the bonded area, overstating it by 73 percent, and divided shear by the same wrong figure. Every step was correct given the input | State each input's provenance beside the result. Compare independently-derived quantities -- peel and shear scale differently, and agreement between them was never checked |

The through-line, and the reason `FACTS.md` keeps all of this: passing counts prove the
harness ran. Only a check that touches the shipped artifact proves the part is sound.

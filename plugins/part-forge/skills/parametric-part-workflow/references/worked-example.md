# Worked example: the shade-bar mid-span saddle

The canonical case study for this workflow, traced through all eleven stages. Source files
live at `projects/shade-bar-mount/` -- `FACTS.md`, `PROJECT.md`, `BUILD-BRIEF.md`,
`saddle_gen.py`, `verify_report.json`.

The part is a 3M-taped mid-span support that lifts a sagging window-shade bar back to level.
It is small, cheap, and low-load -- under 10 lb -- which is exactly why it is instructive: the
project failed repeatedly for reasons that had nothing to do with difficulty. Every failure
was an epistemic failure. A number nobody had measured, or a check that measured the wrong
thing.

## Stage 0 -- scoping the verb

The existing end brackets already capture the bar. The mid-span part therefore only has to
**push up** -- it needs no retention lip, no capture geometry, and no fasteners, since it is
taped.

`FACTS.md` 1.4 records this inference, tagged as derived from 1.2 and 1.3, and annotates it:
"1.4 is the most consequential fact in this file." It is worth pausing on why a single-line
inference earns that status. It deleted a hook curl, removed a 2 mm-thick tip that would have
been marginal in FDM plastic, removed an overhang that complicated printing, and pulled the
moment arm inward. One correctly scoped verb removed four downstream problems.

The numeric argument attached to it -- that deleting the hook would halve every load number --
was later **refuted** (`FACTS.md` 6.4, because the arm is fixed by the end brackets and not by
this part's geometry). The decision survived anyway. `FACTS.md` 7 states the separation
explicitly: "The mid-span part should be a saddle, not a hook. That conclusion is unaffected:
it rests on 1.4, not on any number in this section."

**Lesson.** Record a decision's justification separately from the incidental numbers argued
in its support. When the numbers turn out wrong, a decision resting on a structural fact
survives; a decision resting on arithmetic has to be re-litigated.

## Stage 1 -- the facts ledger and the diameter estimate

`FACTS.md` opens with a three-tag legend: `[STATED]` asserted by the owner and treated as
true, `[PHOTO +/-]` derived from a ruler in a photograph and carrying real error, `[OPEN]`
not yet known.

Bar diameter began as `[PHOTO]`: approximately **22 mm, range 19 to 25 mm**. The confirmed
value (`FACTS.md` 5.1, `[STATED]`, owner, 2026-07-25) is **19.05 mm** -- one plain 3/4 inch.
The estimate was **2.95 mm too large**.

`FACTS.md` 5 draws two lessons from the miss, and they point in opposite directions from what
intuition suggests:

1. The evidence line that looked *strongest* was the one that misled. It measured the
   existing bracket's hook outer width -- two well-lit, crisply defined edges -- and subtracted
   an assumed wall thickness to get the inner diameter. The measurement was good. The
   subtraction imported a guess, silently, and the chain was reported with the confidence of
   its strongest link rather than its weakest.
2. The evidence line that was *discounted* was closest to correct. A direct read of the
   hook's inner opening gave 18 to 19 mm and was dismissed as foreshortened by the camera
   angle.

**Lesson.** A two-step inference is at best as good as its weakest step, and the weak step is
usually the invisible one. Prefer a single noisy direct measurement over a chain of clean
ones. When recording an inferred value, tag what it was inferred *from*, so the chain is
auditable later -- this is why the template carries `[DERIVED from N.N]` as a distinct tag
rather than folding derivations into `[PHOTO]`.

## Stage 2 -- route (b), rebuild parametrically

A draft existed: `obj_0`, a **4,642-triangle** traced mesh with no construction history,
degenerate zero-length edges, roughly 84 vertices coincident within 0.1 mm, and visibly
faceted curves. Its provenance markers -- generated object name, a colour-hash material name,
100 percent triangles, uneven edge density, a baked-in 90 deg X rotation from a Y-up
conversion -- all indicated an import, not modelled geometry.

`PROJECT.md` 6.1 records the decision to rebuild rather than edit, and the reasoning is a cost
argument rather than an aesthetic one. The draft contributed exactly one thing worth keeping:
a plate footprint of 76.19 x 44.45 mm, which is 3.000 x 1.750 inches exactly. That is a
rounded rectangle -- seconds to recreate. Everything else had to change.

Against keeping it: editing a triangle soup means pushing vertices by hand, and every "what
if the bar is 25 mm and not 22 mm" question means doing it again. Going parametric made
height and diameter variants cost one number and a re-run, which is what made the Stage 8
variant strategy affordable at all.

**Lesson.** The route decision is really a question about how many times the geometry will
have to change. When any dimension is still `[OPEN]`, the answer is "more times than
expected", and parametric wins on that ground alone.

## Stage 3 -- the brief, and the rebuild that a derivation cost

This is the most expensive lesson in the corpus.

Bar-centre depth from the tape plane, `Y_BAR`, was derived in the brief as
`T_plate + D_bar/2 + GAP` = **16.0 mm**. The brief described that figure correctly, in its own
words, as "a floor, not a target". And then it was used as the value.

The real depth is **31.75 mm** (1.250 in), measured at an end bracket. That is **1.98 times**
the floor.

`FACTS.md` 6.4 states the mechanism: "The bar's depth is fixed by the existing end brackets;
a mid-span support must reach exactly that far or it never touches the bar. `BUILD-BRIEF.md`
derived it as `T_plate + D_bar/2 + GAP` = 16.0 mm and called that 'a floor, not a target' --
true, but the floor is only the answer if the end brackets happen to hold the bar at the
minimum, which nobody had checked."

A part that reaches 16 mm toward a bar sitting at 31.75 mm does not fit badly. It does
nothing at all. The parameter table in `PROJECT.md` 6.2 now carries the superseded row struck
through with the annotation **"this assumption cost a rebuild"**, and the replacement row is
labelled `MEASURED INPUT` -- with the generator's own comment reinforcing it as
"MEASURED INPUT, NOT A DESIGN CHOICE".

**Lesson.** When a dimension is fixed by something outside the project's control, it is an
input and must be measured. A lower bound computed from the part's own geometry answers a
different question -- "how close *could* this sit" -- and the world has no obligation to sit at
the minimum. The generalized rule: a formula whose inputs are all under one's own control
cannot produce a fact about anything that is not.

## Stage 4 -- closing the measurements

Three techniques, each cheap, each converting an argument into an observation.

**Paper strip, for a diameter that cannot take callipers.** `FACTS.md` 5 gives the procedure:
wrap a paper strip tightly around the bar and mark where it overlaps itself; lay it flat and
measure mark to mark for circumference C; diameter is C / 3.1416. What makes it a good
procedure is not the arithmetic but the two sentences that follow it -- an error budget
("reading C to 1 mm gives diameter to about 0.3 mm") and a discriminability check
(3/4 in gives C about 60 mm, 7/8 in about 70 mm, 1 in about 80 mm; "these are far enough
apart that even a sloppy measurement is decisive").

**A printed go/no-go gauge, for a dimension with a small candidate set.** A flat comb with
semicircular notches at **19.0, 20.6, 22.2, 23.8 and 25.4 mm**, each labelled with embossed
text, tried against the bar. Minutes of print time converts an open question into an answer
that can be held. Once the diameter was confirmed the gauge was retired as a deliverable
(`BUILD-BRIEF.md`, struck through) but kept buildable behind a flag "if the confirmation is
ever doubted".

**Cross-check agreement, for an ambiguous unit.** The owner wrote a drop of "2 at the base",
which cannot be metres. `FACTS.md` 6.1 reads it as 2 mm and validates the reading
independently: at a 2 mm drop with the confirmed 19.05 mm bar, the bar centre lands within
**0.83 mm** of where the existing draft already places it. Two descriptions derived by
unrelated routes agree, and they would not agree if the intent were 2 cm or 2 in. The file
then re-runs the cross-check after the diameter was corrected, to confirm the conclusion does
not depend on the since-changed number.

**Lesson.** A measurement procedure is incomplete without its error budget and a statement
of what it can discriminate. And when units are ambiguous, look for a second number that
should coincide under the correct reading -- agreement between independent derivations is
stronger evidence than either derivation.

## Stages 5 and 6 -- the harness, and the defect it could not see

The generator grew an acceptance list of **55 checks per variant, 165 across the three
variants**, each comparing a measured number against an expected one. `BUILD-BRIEF.md` names
that list the specification of record and resolves conflicts in its favour: where the brief
and the code disagree, the code wins.

Then the owner opened `saddle_h0.stl` in Bambu Studio.

`FACTS.md` 7i records it: "**Found by the owner, in Bambu Studio, not by us.**
`saddle_h0.stl` -- *'Error: 2 non-manifold edges'* -- while our own run reported
`non-manifold edges 0` and 135 `[PASS]`. Both were correct. They were answering different
questions."

The mechanism, stated in the same section: "**Blender counts faces per *topological* edge. A
slicer reconstructs topology *by position*.**" Two vertices at identical coordinates are two
vertices to the authoring tool and one vertex to the slicer. An edge that is shared by two
faces topologically can be shared by three positionally. Every assertion in the harness was
true of the in-memory mesh; none of them was a claim about the file.

`FACTS.md` 7i then places the defect in a class: "It is the same class as the inverted
acceptance check 4 and the bevel that silently ran at zero offset -- **a gate that passes
without measuring what ships** -- and it is the one that stopped the part being printed."

The fix was structural. `BUILD-BRIEF.md` now specifies: "Do not verify this in `bmesh` and
stop there... The gate must parse the binary STL from disk after writing it, weld by
position, and **refuse and delete** any variant that fails." The generator implements it as a
second, independent tier -- `stl_triangles()` reads the file bytes, `_weld_ids()` welds by
coordinate, `stl_manifold()` reconstructs slicer-style topology, and a failing file is
`os.remove`d rather than shipped with a warning. The docstring states the discipline that
makes it worth having: it "must not share a single line of code with the thing that produced
them."

**Lesson.** Verify the artifact that ships, with an implementation that shares no code with
the producer. Both halves matter. Re-checking the same data structure with the same helper
functions reproduces the same blind spot at greater length.

## Stage 6, continued -- what reproducibility can honestly claim

`FACTS.md` 7j records a second finding, and resolves it by declining to fix it.

Nine consecutive runs of unmodified source produced **nine distinct raw file digests**. Two
causes: triangle emission order varies because boolean and bmesh operators iterate
pointer-hashed structures, and the diagonal chosen when triangulating a planar quad is a
tie-break that can flip. Neither changes the solid.

Over the same nine runs, the **unique vertex set digest was identical every time** -- one
digest per variant.

The file states the conclusion bluntly: "**Hashing raw STL bytes carries no signal at all**...
The **unique vertex set** is the invariant that does hold, and the run now prints its digest
for every variant. **Reported, never gated.**"

The decision not to impose a deterministic diagonal is recorded as an explicit five-point
judgement, and it generalizes into a template for when *not* to chase a known defect: the fix
would not achieve the stated goal; it touches the artifact-producing path to change nothing
about the artifact; it requires new machinery that would itself be unchecked; nothing
downstream reads the property; and the actual underlying need is already met more cheaply.

**Lesson.** Reproducibility claims must name the invariant they hold over. "The same solid"
is checkable; "the same file" is not, and asserting it produces a check that fails for
reasons carrying no information. Separately: `reported, not gated` is a category worth naming
in the harness output, so a reader can distinguish "passed" from "was never looked at".

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

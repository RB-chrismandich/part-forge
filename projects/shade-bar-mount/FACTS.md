# Shade Bar Mount — Facts & Actuals

Single source of truth for **real-world constraints**. Nothing here is inferred from the Blender
model; the model conforms to this file, never the reverse.

**Confidence legend**
- `[STATED]` — asserted directly by the owner. Treat as true.
- `[PHOTO ±]` — derived by me from a ruler in a photo. **Carries real error. Confirm before printing.**
- `[OPEN]` — not yet known.

Last updated: 2026-07-25 · Sources: 5 photos in `~/Downloads/3d-bar/` + owner spec

---

## 1. The job

| # | Fact | Conf |
|---|---|---|
| 1.1 | The shade bar **sags at mid-span** under the weight of a wide shade panel. | `[STATED]` |
| 1.2 | This part is a **mid-span anti-sag support**. It does **not** replace the end brackets. | `[STATED]` |
| 1.3 | The **end brackets capture the bar**, so it cannot lift out. | `[STATED]` |
| 1.4 | Therefore this part only has to **push the bar up**. It needs no retention, no capture, no hook curl. | derived from 1.2–1.3 |
| 1.5 | Total load is **light, < 10 lb**. A single mid-span support carries a fraction of that — call it ~5 lb design case. | `[STATED]` |

> **1.4 is the most consequential fact in this file.** See §7 — superseded for its numbers, which
> are in §7f.2, but still the place its consequence is argued.

## 2. Mounting method

| # | Fact | Conf |
|---|---|---|
| 2.1 | **3M-taped (adhesive/VHB).** No screws, no drilling. | `[STATED]` |
| 2.2 | The existing bracket is also adhesive-mounted — grey foam tape visible on its back plate. | photo |
| 2.3 | Mount surface is the **vertical face of a dark painted header/fascia band** below the ceiling. | photo |
| 2.4 | Substrate material and finish (metal? painted MDF? drywall?) | `[OPEN]` — decides 3M product choice |

## 3. Space envelope — owner spec

| # | Fact | Conf |
|---|---|---|
| 3.1 | **Plate: 3 in wide × no more than 2 in (50.8 mm) tall — a hard ceiling, not a target.** | `[STATED]` |
| 3.2 | Rationale for the height cap: a shorter plate can be **stuck higher or lower on the band**, so plate height buys installation adjustability. Shorter is better. | `[STATED]` |
| 3.3 | Vertical face physically available ≈ 2 in / 50 mm. | `[PHOTO ±5 mm]` |
| 3.4 | Horizontal room is generous; vertical room is the tight axis. | `[STATED]` |
| 3.5 | Obstructions below/beside the band (track, cassette, valance return) | `[OPEN]` |

## 4. The existing end bracket (reference only — not the part being built)

| # | Fact | Conf |
|---|---|---|
| 4.1 | Flat back plate with adhesive, **J/C-hook curling forward and up**. Captures the bar. | photo |
| 4.2 | Overall depth (back face → hook tip) ≈ **51 mm / 2 in**. | `[PHOTO ±3 mm]` |
| 4.3 | Back plate thickness ≈ **5–6 mm**. | `[PHOTO ±2 mm]` |
| 4.4 | Hook **outer** width ≈ 33–35 mm; **inner** cradle ≈ **19–24 mm**. | `[PHOTO ±3 mm]` |
| 4.5 | Sits in a taller vertical pocket than the new location offers. | `[STATED]` |

## 5. The shade bar — diameter estimate

**CONFIRMED: 3/4 in = 19.05 mm.** `[STATED]` — owner, 2026-07-25. This supersedes the
photo-derived estimate below; the estimate is kept only to show how far off it was.

The old estimate read ≈22 mm (range 19–25 mm), i.e. **2.95 mm too large**, and it ranked
7/8 in and 1 in as most likely. The true value sits at the very bottom of the estimated
range. Two lessons for the next unmeasured dimension: the "strongest" evidence line below
(hook outer width minus assumed wall thickness) was the one that misled, because the wall
thickness was itself a guess; and the direct read of the hook's inner opening (≈18–19 mm),
which was discounted as foreshortened, was the closest to correct.

Superseded estimate, and how it was reached:

| Evidence | Reads as | Weight |
|---|---|---|
| Existing hook outer width ≈33–35 mm minus ~5.5 mm walls each side | ≈22–24 mm inner | **Strongest** — two independent edges, both well-lit |
| Direct read of hook inner opening, bracket-in-hand photo | ≈18–19 mm | Moderate — hook is foreshortened, ruler zero is off-part |
| Direct read of hook inner opening, in-situ photo | ≈21–23 mm | Moderate |
| Blender draft cradle = 18 mm | ≈18 mm | **Discount this.** The model was scaled to make its plate exactly 3.000 in, so the cradle is a *consequence* of that scaling, not an independent measurement. |

Standard sizes inside the range: 3/4 in (19.05), 7/8 in (22.2), **1 in (25.4)**.

### How to settle it exactly, with the ruler already on hand

**Paper-strip method** — better than calipers for a mounted bar:
1. Wrap a strip of paper tightly around the bar, mark where it overlaps itself.
2. Lay it flat, measure mark-to-mark = circumference **C**.
3. Diameter = **C ÷ 3.1416**.

Reading C to 1 mm gives diameter to ~0.3 mm. Sanity check: 3/4 in bar → C ≈ 60 mm; 7/8 in → C ≈ 70 mm; 1 in → C ≈ 80 mm. These are far enough apart that even a sloppy measurement is decisive.

| # | Fact | Conf |
|---|---|---|
| 5.1 | Diameter = **19.05 mm (3/4 in)** | `[STATED]` — confirmed by owner 2026-07-25 |
| 5.2 | Round cross-section | photo, high confidence |
| 5.3 | Does the bar rotate in use (roller) or is it static? | `[OPEN]` — affects whether the saddle should be low-friction |

## 6. Height placement — the sleeper requirement

A drop-in mid-span support **only kills sag if its cradle sits at the right height.** Too low and the
bar never touches it and the sag persists; too high and it pushes a visible hump into the bar.

| # | Fact | Conf |
|---|---|---|
| 6.1 | **The bar's rest point sits ≈ 2 mm below the bottom edge of the wall plate.** | `[STATED]`, unit **assumed** — see note |
| 6.2 | Bar centre height at an **end bracket**, measured down from a reference visible at mid-span (e.g. top edge of the header band) | `[OPEN]` — still needed to place the plate on the wall |
| 6.3 | Current mid-span sag depth | `[OPEN]` — nice to have; confirms the fix worked |
| 6.4 | **Bar centre sits ≈ 1.25 in (31.75 mm) forward of the mounting surface**, giving 0.875 in of back clearance behind a 3/4 in bar. | `[STATED]` — owner, 2026-07-25 |

> **6.4 is a constraint, not a design choice, and the first build got it wrong.** The bar's depth is
> fixed by the existing end brackets; a mid-span support must reach exactly that far or it never
> touches the bar. `BUILD-BRIEF.md` derived it as `T_plate + D_bar/2 + GAP` = 16.0 mm and called
> that "a floor, not a target" — true, but the floor is only the answer if the end brackets happen
> to hold the bar at the minimum, which nobody had checked. The real value is **1.98× that**.
> `saddle_gen.py` now takes `Y_BAR` as an explicit measured input; set it to `None` only to fall
> back to the theoretical minimum. Consistent with §4.2's ≈51 mm-deep end bracket.

> **Unit note on 6.1.** The owner wrote "~2m below the base", which cannot be metres. Read as
> **2 mm**. Supporting evidence: at 2 mm drop with the **confirmed 19.05 mm** bar (§5), the bar
> centre lands −2 + 19.05/2 = **7.53 mm** above the plate's bottom edge — within **0.83 mm** of where
> the existing draft already puts it (6.7 mm). The two independent descriptions agree, which they
> would not if the intent were 2 cm or 2 in. (This argument was first written against the retired
> 22 mm estimate, where the two landed 9.0 and 6.7 mm apart — an agreement of 2.3 mm. Confirming the
> diameter tightened it, so the reading survives the `D_BAR` correction instead of depending on it.)
> **Confirm before printing.** If it is 2 cm, the bar hangs clear below the plate and the saddle arm
> grows by ~18 mm.

Note this is a *relative* dimension — rest point referenced to the plate's own bottom edge — which
is exactly right. It makes the part self-contained and pushes the absolute-height problem out to
installation, where §3.2's adjustability handles it.

## 7. Load path — SUPERSEDED by §7f.2 (kept as defect history)

> **Everything in this section is draft-era.** It was written against the first model — before
> `D_BAR` was confirmed (§5), before the moment arm was measured (§6.4), and before the adhesive
> product was chosen (§7f). **For the numbers that govern, go to §7f.2**: bonded area, shear and
> peel for each of the three strip layouts, at the confirmed 31.75 mm arm. Four claims below are
> wrong and are struck in place. Nothing is deleted, because how this file was wrong is the point
> of the file.
>
> | Claim below | Status |
> |---|---|
> | "4.86 in² / 3138 mm² of adhesive contact" | **wrong**, and the tape face is not the bond either — §7f.1 |
> | "Avg shear 1.03 psi" | **wrong divisor** — divides by the tape face, not the bond — §7f.2 |
> | deleting the hook "halves every number in the table above" | **refuted** — §6.4 |
> | "at < 10 lb the adhesive is comfortable, not marginal" | **inverted** — peel is the binding constraint, §7f.2 |
>
> Worth keeping straight, because it decides which lesson to draw: the *measurement* here was good
> and the *prediction* was not. The draft measured the cradle **32 mm** forward of the tape plane;
> the owner later confirmed **31.75 mm** (§6.4) — **0.25 mm out**, better than most of this file's
> photo reads. What failed was the prediction that deleting the hook would pull that arm back to
> ~15 mm. It did not move at all, because the arm is not this part's to choose: the end brackets
> fix where the bar is.

~~Measured from the draft: tape face **76.19 × 44.45 mm = 3.000 × 1.750 in exactly**, 92.7% filled
(rounded corners) → **4.86 in² / 3138 mm² of adhesive contact**.~~

**Corrected.** The tape face is 76.2 × 44.45 = **3387.1 mm²**, and the acceptance report measures
the rounded-corner face at **3351.1 mm² = 5.194 in²** on every run — **98.9% filled**, not 92.7%.
A 92.7% fill needs corner radii of ~17 mm: the missing area of a rounded rectangle is (4 − π)r², so
0.073 × 3387.1 = 247 mm² gives r = 17.0. `R_CORNER` is **6**, which leaves 99.1% before the
round-over. 92.7% is a draft-era number describing a draft-era outline. And the face is **not the
bond**: with one 414H-ST strip the bonded area is 3.00 in², with the recommended full-plus-trimmed
pair 5.25 in² (§7f.1). Cradle centre 32 mm (1.26 in) forward of the tape plane — **confirmed at
31.75 mm, §6.4**.

| Load case | Tipping moment | Peel force at top edge | ~~Avg shear~~ |
|---|---|---|---|
| 5 lb (likely) | 6.3 in·lbf | 3.6 lbf | ~~1.03 psi~~ |
| 10 lb (worst case) | 12.6 in·lbf | 7.2 lbf | ~~2.06 psi~~ |

The moment column survives the correction — 5 lbf × 1.250 in = 6.25 ≈ 6.3 in·lbf — precisely
because the 32 mm arm was *measured*. **The shear column does not.** It divides the load by the
tape face, which nothing is stuck to. Divided by the actual bond it is **1.67 psi** on one strip
and **0.95 psi** on the recommended pair (§7f.2).

~~**Conclusion: at < 10 lb the adhesive is comfortable, not marginal.** My earlier concern about
peel being the governing risk was based on an unknown load; with the real number it is not the
binding constraint.~~

**That is backwards, and it is the reason the rest of this correction exists.** Peel *is* the
binding constraint. At the confirmed arm a single strip sees **12.5 psi** of peel against
**1.67 psi** of shear (§7f.2) — the earlier concern was right and the load number did not dispose
of it. An installer who reads this section and stops fits one strip, which is precisely the 12.5 psi
case. Still verify against the chosen 3M product's *long-term static* rating (creep, not peak
strength, is what fails adhesive mounts over months) — that sentence was right and still applies.

**What §1.4 changes:** because the end brackets already capture the bar, the hook curl is dead
weight. Deleting it:

- ~~cuts the moment arm from 32 mm toward ~15 mm — **halves every number in the table above**~~
  — **refuted by §6.4.** The arm is fixed by the existing end brackets, not by this part's
  features, so it is 31.75 mm with or without a curl. Nothing halved.
- removes the ~2 mm-thin hook tip, the draft's weakest section
- removes the overhang that makes the part awkward to print
- shortens projection, so the part intrudes less into the window

The mid-span part should be a **saddle, not a hook**. That conclusion is unaffected: it rests on
§1.4, not on any number in this section.

## 7a. As-built wrap — `WRAP_DEG` does not describe the part

Found 2026-07-25 while adding the mouth chamfer, which needs to know where the cradle actually ends.

`WRAP_DEG = 170` clips the cradle disc at `Z_CUT`. The convex hull that forms the arm then drags
anchor A0 — at Z = 11.81 mm, well above `Z_CUT` = 7.06 mm — over the top of that clip and swallows
it, so **the flat top the clip made never reaches the finished part.** What really terminates the
trough is where the arm's sloping upper face crosses the trough circle:

| | Off vertical | At |
|---|---|---|
| Front (+Y) arm rim | **87.6°** | Y = 41.67, Z = 7.51 |
| Back (−Y) arm rim | **99.9°** | Y = 21.97, Z = 9.63 |
| Delivered wrap | **187.5°** | vs. 170 nominal, vs. a 160–180 brief |

> **Corrected 2026-07-25.** This table read 100.6° / 188.2°; the brief was swept to the measured
> figures and FACTS was not. 100.6° is §7b's *upper corner* θ, copied into the wrong row — the run's
> `wrap` line prints **99.9°** for the back rim — and 188.2 was just 87.6 + 100.6 carrying that
> error forward. The coordinates follow from the report's own fitted trough (axis Y = 31.7500,
> Z = 7.9248, R = 9.9253): Y = 31.75 − 9.9253·sin 99.9° = 21.97, Z = 7.9248 − 9.9253·cos 99.9° =
> 9.63. The same formula reproduces the front rim at 41.67 / 7.51 to the decimals shown, which is
> how the coordinates were checked.
>
> These three numbers are the nominal `H_DROP` = 2 variant. **Read them off the acceptance report,
> not off this table** — the run prints all three variants and they are not close: delivered wrap
> **180.2° / 187.5° / 194.9°** at `H_DROP` 0 / 2 / 4. Quoting one figure for "the part" is what put
> the wrong number here.

**This is not a defect and needs no fix.** The excess wrap sits behind the bar's rearmost tangent —
trough back at Y = 21.83, bar back at Y = 22.23 — so it cannot block a vertical drop-in. That is
measured directly every run (`bar drop-in clearance`, 0.400 mm) rather than inferred from an angle.
The 160–180° rule was always a proxy for "the bar must still go in"; the proxy was wrong about this
part while the thing it stood for was fine.

`mouth_rim()` now measures both rims off the envelope, and every consumer — the chamfer's start
angle, the wall-thickness sweep, the reported wrap — takes those numbers instead of `WRAP_DEG`.

## 7b. As-built corner angles — neither junction is 90°

Found 2026-07-25 while replacing the root blend with a true tangent fillet. Both corners are
measured off the envelope every run, not assumed, because the assumption was wrong in both cases.

| Corner | Surfaces | θ (void) | Material interior | Radius |
|---|---|---|---|---|
| **Upper** | arm's top face → plate's **front** face | **100.6°** (98.1 / 100.6 / 103.1 for `H_DROP` 0/2/4) | 259.4° | `R_ROOT` **13.5**; ceiling 16.89 / 17.72 / 18.63 for `H_DROP` 0/2/4 |
| **Lower** | cradle's underside → plate's **bottom** face | **131.6°** (identical for all three variants) | 228.4° | `R_ROOT_LOW` **5.0**, 5.21 available |

The lower radius is set by the `a1 → a2` hull edge, which Z = 0 crosses at 2/3 of its length.
At `ROOT_BLEND` = 1.5 that left **1.0035 mm** to the `a2` vertex and capped the blend at
1.0035 · tan(131.634°/2) = **2.2346 mm**. `ROOT_BLEND` = 3.5 lengthens it to 2.34 mm and the full
5.0 mm is delivered. Past the cap the blend would be tangent to nothing and would bulge below the
`a2` vertex into open air, so the run prints both the asked-for and the carried value.

## 7c. The round-over needs a bound in both directions

Found 2026-07-25, and it had been latent since the round-over was written.

`round_edges` must run with `clamp_overlap` **off** — on, a single 0.005 mm boolean sliver clamps the
whole operation to zero offset and silently produces an identical part. Off, an offset bevel slides
each vertex along the intersection of its adjacent face planes, and where two of those planes are
nearly parallel that direction is nearly undefined. The tangent fillets introduced exactly such
faces, and the failure was silent in the worst way:

| Guard | H_DROP = 0 result |
|---|---|
| neither bound | bounding box grew **8.3 mm**; STL shipped 3.9 mm wider than the plate |
| fold bound only | envelope exact, but a spurious bevel face cut through the arm at Y = 8.5 → **bending SF 0.49** |
| both bounds | envelope exact, **SF 46.6** at the right section, 525 edges rounded |

All thirty of the original acceptance checks passed in the first row. Nothing was looking at the
bounding box, and the one structural check that could have caught the second row is fired at X = 0
where the damage happened to miss it on two of the three variants.

Three things changed as a result: `round_edges` asserts its own envelope cannot grow by more than the
bevel radius; it skips edges folded past `ROUND_ANGLE_MAX` or whose adjoining faces are smaller than
`ROUND_MIN_FACE · R²`; and the part's X and Z extents are acceptance checks in their own right.

For **this** runaway the discriminator has to be **face area, not edge length**. Dropping edges
shorter than the radius was the obvious first try: it does not prevent the runaway on its own
(5.8 mm growth remained), and 32 of the edges it drops are on the plate's perimeter chain, which
tears the corner arcs — a chain beveled in some segments and not others reads as a chewed edge, not
a soft one. The two populations separated cleanly by adjoining-face area instead: real edges carried
0.27 mm² and up, the fillets' tangency seams 0.003–0.08 mm², and the cut at 0.03 mm² dropped
**none** of the perimeter chain.

> **Those area figures are the `ROUND_R` = 1.0 measurement and the separation they describe no
> longer exists.** The cut is `ROUND_MIN_FACE_FRAC · R²`, so at `ROUND_R` = 0.5 it is **0.0075 mm²**,
> and the smallest adjoining face anywhere in the target set is now **0.0657 mm²** — the plate's
> corner arcs, which are *real* edges sitting inside the old 0.003–0.08 seam band. Re-measured on all
> three variants at both radii, with every other rule applied and also with the length rule disabled:
> **the face-area rule excludes nothing at all.** The seams it was written for are taken first by the
> fillet-footprint rule. It is a live backstop, not a discriminator, and the 0.27 mm² figure should
> not be quoted as current.

There **is** an edge-length bound as well now (`ROUND_MIN_EDGE_FRAC`, §7h). It was described here as
"set at half the radius, not at the radius, which puts it in a gap in the target set's length
spectrum so it drops whole chains and never part of one." **That was true of `ROUND_R` = 1.0 and is
not true now.** At `ROUND_R` = 0.5 the bound is 0.25 mm; it still lands in a gap, but a 0.0122 mm one
between two unrelated features rather than between two populations, and it leaves **40 sub-0.25 mm
fragments of the corner-arc chain** unrounded between rounded links — a chain cut in parts. Measured
spectrum and the reasoning are in §7h.

## 7d. Neither blend is load-bearing — measured, ~180 builds

The governing section is **not** the root. It is the cradle's back wall under the bar at
Y = 26.52, and it is several millimetres beyond the fillet's furthest tangent point:

| | `R_ROOT` 8 | 12 | 14 | 16 |
|---|---|---|---|---|
| bending SF @ Y = 26 | 42.33 | 42.33 | 42.33 | 42.33 |
| root stress | 0.525 MPa | 0.411 | 0.367 | 0.330 |
| plate panel above the fillet | 0.769 MPa | — | — | 0.556 |
| tip deflection | 10.0 µm | 9.2 µm | — | 8.7 µm |
| drop-in / projection / wall / wrap | \- | unchanged | unchanged | unchanged |

> **The absolute figures in that table are a snapshot of the `R_ROOT` sweep and are stale; what it
> demonstrates is not.** 42.33 has not matched the build for a long time. The current one measures
> **36.4808** at the nominal `H_DROP` = 2, and **41.3633 / 33.0439** at `H_DROP` 0 / 4. It read
> **44.0616 / 49.0959 / 40.3036** while `ROUND_R` was 1.0 — `R_OUT` pays for the round-over up front,
> so halving the radius took 0.5 mm off the cradle's back wall, which *is* the governing section, and
> the section modulus fell with it (§7h). The row earns its place by showing SF is *invariant* across
> `R_ROOT`, and that survives the absolute value moving; the absolute value belongs to the acceptance
> report's `bending safety factor` check, which measures it on all three variants every run. Take it
> from there, not from here.

Bending SF is bit-identical to 5 significant figures at every radius, and drop-in clearance
(0.40000 mm) and projection (45.348 mm at `ROUND_R` 0.5; 45.849 mm at 1.0) never move at all across
the `R_ROOT` sweep — the fillet is unioned *before* the
trough is cut, so anything that strays forward of `Y_AXIS − R_BAR` is simply trimmed away. Tip
deflection is ~10 µm against **46–253 µm** contributed by the tape layer underneath, so stiffening
the plastic is optimising the wrong component by an order of magnitude.

The upper blend earns its keep on the **plate panel** (−28% stress as its top edge climbs from
Z = 18.0 to 24.6) and on peak tape peel (−6%) — not on strength. Cost: +3% volume.

**The creep argument for it does not hold, and this is worth recording because it is the obvious
one to reach for.** The root's own creep rate does fall hard: root stress 0.483 → 0.369 (R12) →
0.287 MPa (R16), so with a Norton exponent of 3–5 the rate at that spot drops to 0.21× or 0.074×.
But the root is not where creep deflection comes from. Weighting the compliance integral
`∫ (yL−y)² σⁿ⁻¹ / I dy` over the measured sections splits it, at n = 3:

| region | R_ROOT = 8 | R_ROOT = 16 |
|---|---|---|
| root, Y < 15 | 19.1% | 6.2% |
| mid | 4.4% | 4.1% |
| **trough wall, Y > 21** | **76.5%** | **89.7%** |

Total arm creep compliance therefore falls only **15% (n=3) / 7% (n=5)** from R8 to R16 — not the
5–10× the root stress ratio suggests. The sustained-load hot spot is the cradle wall at Y ≈ 26, the
same section that governs short-term stress, and no root fillet reaches it. If creep ever matters,
thicken that wall or shorten the moment arm.

A cove *scooped out* of the arm's underside, which is one reading of the sketch, is the opposite
trade: −824 mm³, +29% deflection, +11% peak stress, +79% creep compliance, at stations already at
SF 80–170. The version built instead adds material by lengthening the hull edge.

## 7e. The mouth-rim measurement could not see past its own cone

Found 2026-07-25 when `R_ROOT` was raised. `verify()` located the outer end of the mouth ramp by
taking the last ray hit inside a cone of `R_OUT + 1` = 15.125 mm from the trough axis. That worked
only while nothing else lived in the sector past the rim. At `R_ROOT` = 14 the root fillet does:
its material sits 13.5–15.1 mm from the trough axis at 94–95°, *inside* the cone, so the sweep
walked off the cradle onto the fillet and reported the mouth 1.5° wider than the envelope allows.

Every functional number — wall, wrap, chamfer, drop-in — was bit-identical. Only the measurement
moved, which is the failure mode this file exists to prevent.

The fix follows the ramp instead of trusting a cone. Along the ramp the hit distance changes
smoothly, about **0.01 mm per 0.05° step**; leaving it is a cliff — **2.7 mm** at `R_ROOT` = 14,
**7.8 mm** at 8. The sweep now breaks on the cliff, so it cannot wander onto a neighbouring feature
no matter what is built next to it. With that in place the `mouth ramp` failures disappear entirely
and the ceiling on `R_ROOT` becomes mesh robustness instead.

Both were verified by independent re-derivation outside Blender (a 20-agent review panel
re-implemented `derive` → `saddle_profiles` → `upper_corner`/`lower_corner` from scratch and
reproduced every figure above to six decimals).

## 7f. Material and adhesive — PRODUCT CHOSEN 2026-07-25 (substrate still `[OPEN]`)

Both were `[OPEN]` and both were raised as critical by the CDDL clarification gate: every
structural figure in the brief (bending SF — 44.0 when this was written at `ROUND_R` 1.0, **36.48**
now, §7h — root stress in MPa, 10 µm deflection, a Norton creep exponent) requires a modulus and an
allowable that no document supplied.

- **Material: PETG.** `[STATED]` — owner. `SIGMA_ALLOW` = 50 MPa already covers it, so no code
  change; what changes is that the assumption is now pinned. Chosen over PLA for creep under
  sustained dead load and for the ~80 °C glass transition against a dark, solar-gaining band.
- **Adhesive: 3M Scotch Extreme Mounting Strips 414H-ST**, 1 × 3 in (25.4 × 76.2 mm) per strip.
  `[STATED]` — owner.
  > **This does not close §2.4.** The product was chosen before the substrate that §2.4 says
  > *decides* it is known. On the dark painted band of §2.3 the bond is to the **paint film**, not
  > to whatever is behind it, and paint-to-substrate adhesion is the plausible long-term failure
  > path for a sustained overhead load. §2.4 and §8 item 3 stay `[OPEN]` deliberately; this is a
  > recorded acceptance of risk, not a resolution.

### 7f.1 The strip geometry does not match the plate, and the reported area is not the bond

| | mm | in |
|---|---|---|
| plate tape face | 76.2 × 44.45 = 3387 mm² | 3.00 × 1.75 = 5.25 in² |
| one strip | 25.4 × 76.2 = 1935 mm² | 1.00 × 3.00 = 3.00 in² |

The strip **length** equals the plate **width** exactly — both 3.000 in. The plate's 1.75 in height
takes **one** strip, leaving 0.75 in bare; **two** need 2.00 in and overhang by 6.35 mm.

So the acceptance report's `adhesive 3351 mm² = 5.19 in²` is the tape **face**, not the bonded
area. With one strip the real bond is **3.00 in²** — the report overstates it by **73%**. The line
is report-only and is now labelled as such; it was never a gate.

### 7f.2 Trim the second strip — better than raising `H_PLATE`

Peel is a bending problem, so it goes as the **square** of bonded height (`S = b·h²/6`), while
shear goes only as the area. At the confirmed 31.75 mm moment arm and 5 lb:

| bond | area | shear | **peel** |
|---|---|---|---|
| one strip, 1.00 in | 3.00 in² | 1.67 psi | **12.5 psi** |
| one full + one **trimmed to 0.75 in** | 5.25 in² | 0.95 psi | **4.1 psi** |
| two full strips, `H_PLATE` = 50.8 | 6.00 in² | 0.83 psi | **3.1 psi** |

Trimming a strip reaches the full tape face **with no change to the part**, and takes peel down 3×.
Raising `H_PLATE` buys a further 25% and costs a re-sweep of the empirical constants plus a taller
part. Trim the strip; leave `H_PLATE` alone. Superseded recommendation follows.

### 7f.3 Superseded: `H_PLATE` 44.45 → 50.8

`H_PLATE_CAP` = 50.8 mm is exactly 2.000 in — **exactly two strips edge to edge**, 6.00 in² of
bond, double the current one-strip area, with the second strip placed high where the peel moment
is greatest. `H_PLATE` presently sits 6.35 mm *below* its own documented cap.

Of everything examined this session this is the largest available improvement to the interface
that actually fails. It is recorded as a recommendation and **not** applied: it changes the part's
headline dimension and how much of the header band it covers, which is the owner's call. Note it
would also require re-sweeping the empirical fillet constants (see BUILD-BRIEF, Parameters).

## 7g. Known residual — folded faces

The round-over makes them and nothing gates them. Measured on the current build (`ROUND_R` = 0.5) at
the nominal `H_DROP` = 2: **107 edges folded past 170°** across the part (zero-thickness fins),
**16 of them** in the lower collar's runout. The other two variants are different parts and do not
give the same count — **133 / 22** at `H_DROP` = 0 and **104 / 16** at 4 — so for the variant you are
actually printing, read the run's `folds` line rather than this paragraph. They are manifold,
watertight and inside the envelope, so every acceptance check passes.

**The count is not monotone in anything, including `ROUND_R`, and this paragraph has gone stale
twice.** Trajectory, all three variants as `H_DROP` 2 / 0 / 4:

| build | folds (2 / 0 / 4) | collar (2 / 0 / 4) |
|---|---|---|
| before `ROUND_MIN_EDGE_FRAC` (§7h), `ROUND_R` 1.0 | 302 / 315 / 278 | — |
| with it, as first recorded, `ROUND_R` 1.0 | 117 / 114 / 114 | 17 / 16 / 16 |
| `ROUND_R` 1.0, as measured at iteration 6 | **125 / 121 / 110** | 13 / 13 / 10 |
| `ROUND_R` 0.5 (current) | **107 / 133 / 104** | 16 / 22 / 16 |

The middle two rows are the same setting: 117/114/114 had already drifted before this iteration
touched anything — iteration 4's in-Blender triangulation (§7i) changed the edge population the
count is taken over. **Halving the radius improved two variants and made `H_DROP` = 0 worse**
(121 → 133). Of the change, +14 per variant is new and is in the plate's four corner-arc regions,
where `ROUND_R` 1.0 had **zero** folds past 170° for the plain reason that it was not beveling them
at all (§7h); everything outside those regions improved. Quote the run, not a remembered number.

Recorded here because it is the defect-history file and this class had been living only in a
scratch note. Trajectory of the **collar** group: 78 fins before the round-over was taught to leave
the tangent fillets alone, 0 after, then 15–17 once the fillet stations were re-matched to the flare
and the tip cap was closed, then 10–13 at `ROUND_R` 1.0 as measured at iteration 6, and **16 / 22 / 16**
now (`H_DROP` 2 / 0 / 4). The remainder sit at the plate's top corners, around the witness notch and
— new since `ROUND_R` went to 0.5 — on the corner arcs themselves.

Root cause of the collar group: the saddle body is the convex hull of only **two** rings, so its
section between them is a Minkowski blend, while the fillet is solved per station from an eroded
profile. The two agree at the endpoints and drift in between. Fixing it properly means computing
the true interpolated section rather than re-eroding.

## 7h. The plate's four corners — spikes (2026-07-25), then dead sharp (2026-07-26)

Two defects in the same place, the second created by the fix for the first. Read both halves before
touching `ROUND_R` or `ROUND_MIN_EDGE_FRAC`.

### 7h.1 The original defect — a bevel that could not fit its edges (ROUND_R 1.0)

`R_CORNER` 6.0 over `SEG_CORNER` 24 makes the plate's corner arcs out of **0.393 mm** links; at the
time `ROUND_R` was **1.0 mm**. Measured on the 124 corner-arc edges the round-over was then
targeting: they fold at 82.7–90.0°, so the slide the bevel must make along each adjoining face,
`R·tan(φ/2)`, was **0.880–0.999 mm** — a **2.2×–2.5× overrun** on a 0.393 mm link. With
`clamp_overlap` necessarily off (§7c) each link's bevel interpenetrates both its neighbours, and the
chain comes back as a row of spikes. On the nominal build that was **236 of the part's 418** spike
vertices (normal cone > 150° with every incident edge < 1.5 mm).

Fixed by `ROUND_MIN_EDGE_FRAC` = 0.5: `round_edges` skips any edge shorter than half the bevel
radius. Swept, all three variants, acceptance checks run at every point. **This whole sweep is a
`ROUND_R` = 1.0 measurement** — the fractions below meant 0.0/0.3/0.4/… × 1.0 mm, and none of its
PASS/FAIL verdicts reproduce at `ROUND_R` = 0.5 (see 7h.4):

| `ROUND_MIN_EDGE_FRAC` | rounded edges | spikes (0 / 2 / 4) | folds (0 / 2 / 4) | verify |
|---|---|---|---|---|
| 0.0 (before) | 378 / 375 / 378 | 433 / 418 / 382 | 315 / 302 / 278 | PASS |
| 0.3 | 316 / 319 / 322 | 263 / 259 / 245 | 147 / 230 / 146 | **FAIL** — 10 non-manifold, 9 boundary |
| 0.4 | 238 / 239 / 244 | 195 / 201 / 177 | 119 / 122 / 113 | **FAIL** — 2 shells |
| 0.42 | 238 / 239 / 244 | 195 / 201 / 177 | 119 / 122 / 113 | **FAIL** — 2 shells |
| 0.45 | 238 / 238 / 244 | 195 / 174 / 177 | 119 / 131 / 113 | **FAIL** — 10 non-manifold, 9 boundary |
| 0.48 | 144 / 140 / 140 | 193 / 190 / 179 | 114 / 117 / 114 | PASS (same target set as 0.5) |
| **0.5 (chosen)** | 144 / 140 / 140 | **193 / 190 / 179** | **114 / 117 / 114** | **PASS** |
| 0.6 | 139 / 136 / 136 | 179 / 179 / 168 | 97 / 100 / 97 | PASS, but see below |
| 0.7 | 139 / 136 / 136 | 179 / 179 / 168 | 97 / 100 / 97 | PASS, but see below |
| 1.0 | 126 / 124 / 124 | 161 / 165 / 130 | 91 / 98 / 85 | **FAIL** — 3 shells |

Every failure above is on the **nominal** `H_DROP` = 2 build; the other two variants pass at every
swept value, which is why a sweep that only looks at one variant, or only at spike counts, picks the
wrong number.

The threshold has to land in a **gap** in the target set's length spectrum, or it leaves a chain
beveled in some links and not others — the chewed edge of §7c, and at 0.3 and 0.45 that is not
cosmetic, it tears the mesh open. Measured spectrum on the nominal build **at `ROUND_R` = 1.0**:
corner arcs top out at 0.3951, the collar's loft seams are a 96-edge spike at 0.4623, three
stragglers sit just above that spike on the flare-tip end-cap rims at 0.4486, 0.4641 and 0.4644, and
the shortest link of any chain that reads as a visible round-over is 0.5062 (the plate's top edge),
then 0.5833 (the notch), 0.777, 0.945, 1.253, 1.389. Half the radius sits in the **0.4644–0.5062**
gap, 0.0419 mm wide — re-confirmed at iteration 6, and the same two bounds on all three variants —
and it takes the corner arcs and the collar seams whole while keeping the side, top, bottom and notch
chains **100% intact**.

> **"Takes the corner arcs whole" is the sentence that hid the second defect.** It is true, and what
> it means on the part is that the plate's four corners were left square. §7h.3.

0.6 and 0.7 score better on the counts and still pass, and were **rejected on the render**: they
drop four edges that 0.5 keeps, and on the nominal all four are at the witness notch — the two
0.5062 stubs of the top edge at the notch shoulders and the two 0.5833 flanks of the V — so the top
edge comes back with a 0.5 mm square ear standing proud at each shoulder where the round-over stops.
On `H_DROP` = 0 they drop a **fifth**, which is why that row reads 144 → 139 where the other two read
140 → 136, and it is **not** at the notch: a 0.5168 link on the −X flare-tip end cap, at X = −21.5,
Y = 7.16, Z = 4.17 → 4.68, where the cap rim meets the plate's swell. Dropping it leaves one sharp
link in an otherwise rounded cap rim — the same chewed chain as the notch ears, on a far less
conspicuous feature — so it points the same way as the four without adding to the case. The notch is
what decided it.

#### 7h.2 The 0.4644 / 0.5168 tip-cap question, settled by measurement

Two paragraphs above described a −X tip-cap link two different ways — 0.4644 with a 0.4641 mirror,
and 0.5168 with a 0.7654 mirror — and it was left open whether one of them was wrong. Instrumented
at `ROUND_R` = 1.0, dumping every flare-tip rim edge in the round-over target set with its X mirror:

**They are two different links on the same cap, both real, and both sentences stand.** Every rim link
in question radiates from the *same* vertex at (±21.5, 7.1637, **4.1672**):

| variant | cap | link | runs to Z | length | positional mirror |
|---|---|---|---|---|---|
| all three | −X | downward | 3.7029 | **0.4644** | yes — the +X 0.4641, 0.00015 mm off exact |
| all three | +X | downward | 3.7031 | **0.4641** | yes — the −X 0.4644 |
| `H_DROP` = 0 only | −X | upward | 4.6839 | **0.5168** | **no** |
| `H_DROP` = 0 only | +X | upward | 4.9324 | **0.7654** | **no** |
| `H_DROP` = 2 only | −X | upward | 4.6157 | 0.4486 | **no** |

So: 0.4644 *is* the longest edge below the 0.50 cut and its +X mirror *is* 0.4641 — those two are a
genuine mirror pair, 0.00015 mm from exact. The 0.5168 is a **different link**, running the other way
off the shared vertex, and it is 0.0168 mm *above* the same cut, which is why 0.6/0.7 drop it and 0.5
does not. The one word that was loose is "mirror" for the 0.5168 ↔ 0.7654 pair: they start at
mirrored vertices and end **0.2485 mm apart in Z**, so they are the corresponding link on each cap
and not a positional mirror. That difference *is* the tessellation asymmetry the paragraph was
describing, so the conclusion was right and only the word was wrong. The 0.4486 straggler is
`H_DROP` = 2 only and has no counterpart at all.

#### 7h.3 The second defect — the corners then shipped DEAD SHARP (found 2026-07-26)

`ROUND_MIN_EDGE_FRAC · ROUND_R` at 0.5 × 1.0 is **0.50 mm**, which is *above* every 0.393 mm
corner-arc link. The rule therefore took the **entire** corner-arc chain out of the target set. That
is stated above as taking the arcs "whole", which is accurate and reads as a clean win — and nothing
in this file or in the script ever said what it meant on the part: **the plate's four corners had no
round-over at all**, and the perimeter round-over ran the straight edges and stopped dead at eight
tangent points. Every one of the 165 checks passed, on every variant, for four iterations. It is the
same class as §7i and §7c — a property nobody measured — except that here the file's own commentary
argued *for* the exclusion.

Measured on the finished mesh, in the four corner-arc regions (`|X| > 32.1`, plate Z bands), on the
nominal `H_DROP` = 2 (the other two are within one edge of these at both radii):

| | `ROUND_R` 1.0 | `ROUND_R` 0.5 |
|---|---|---|
| edges in the four corner regions | 456 | 1416 |
| folded 80–100° — the square corner itself | **120** | **38** |
| folded 30–40° / 20–30° / 10–20° — round-over creases | 20 / 16 / **0** | 84 / 129 / **247** |
| folded past 170° — zero-thickness fins | **0** | 14 |

At 1.0 the entire crease population in those regions is 164 edges: 120 square corners, 40 shallow
creases from the *straight* edges' bevels running in, 4 at ~145°, and **nothing at all between 40°
and 80°, nothing in 10–20°, and nothing above 145°**. That is a chain of 90° links with no round-over
on it. At 0.5 the square creases are mostly gone and the population has moved into the shallow
buckets a 3-segment round-over makes.

**Fix: `ROUND_R` 1.0 → 0.5** (owner's decision, iteration 6). `ROUND_MIN_EDGE_FRAC` is unchanged at
0.5; the bound it computes falls to **0.25 mm**, which is *below* 0.393, so the arcs re-enter the
target set on their own. Measured, all three variants: the corner-arc chain contributes **68**
full-length 0.3926 mm links to the target set at both radii — **0 of 68 rounded at `ROUND_R` 1.0, 68
of 68 at 0.5.**

Whole-part before/after, `H_DROP` **2 / 0 / 4**, all figures re-measured at iteration 6:

| | `ROUND_R` 1.0 | `ROUND_R` 0.5 |
|---|---|---|
| plate-perimeter spikes (\|model X\| > 31) | 46 / 46 / 46 | **36 / 36 / 36** |
| total spike vertices | 103 / 106 / 89 (**298**) | 94 / 111 / 94 (**299**) |
| folds past 170° | 125 / 121 / 110 (356) | 107 / 133 / **104** (344) |
| round-over target set / rounded | 375 / 140 · 378 / 144 · 378 / 140 | 374 / 330 · 376 / 328 · 380 / 336 |
| bending SF (gate ≥ 8.0) | 44.06 / 49.10 / 40.30 | **36.48 / 41.36 / 33.04** |
| min wall on load path (gate ≥ 3.0) | 4.000 | **3.500** |
| projection | 45.849 | 45.348 |
| acceptance | 165 PASS / 0 FAIL | 165 PASS / 0 FAIL |

**Read that table honestly, in both directions.**

- **Folds get worse on `H_DROP` = 0** — 121 → 133 — while the other two improve. The total falling
  356 → 344 hides it. See §7g: +14 of the change on *every* variant is new fins inside the corner
  regions, which is what beveling a chain that was previously untouched buys you.
- **Total spikes are flat** (298 → 299). Only the *plate-perimeter* group moved, and its composition
  changed completely rather than shrinking: at `ROUND_R` 1.0 those 46 came from the bevels on the
  *straight* perimeter edges reaching into the corner region beside a sharp corner; at 0.5 the 36 are
  the corner arcs' own mild interpenetration. Control, measured: `ROUND_R` 0.5 with
  `ROUND_MIN_EDGE_FRAC` = 1.0 — i.e. the same 0.50 mm cut, arcs excluded again — gives **0 / 0 / 0**
  perimeter spikes, 53 / 70 / 49 total and folds 65 / 95 / 66. Square corners are measurably the
  *cleaner* mesh. Rounded-with-mild-overrun is a deliberate trade, not a free win.
- **The arcs are still overrun by their own bevel.** At `ROUND_R` 0.5 the slide `R·tan(φ/2)` is
  0.440–0.500 mm against a 0.393 mm link — a 1.1×–1.3× overrun, where 1.0 gave 2.2×–2.5×. The
  interpenetration is mild, not absent, and the residual 36 perimeter spikes and 14 corner-region fins
  are exactly that.
- **The structure paid for it.** `R_OUT` = `R_TROUGH` + `T_WALL` + `ROUND_R` + `RIB_DEPTH`, so the
  cradle's back wall — the governing section — lost 0.5 mm, min wall went 4.000 → 3.500 and bending SF
  44.06 → 36.48. Both clear their gates (`T_WALL` 3.0, `SF_MIN` 8.0) with room, and 3.500 is still
  `T_WALL` + `ROUND_R` by construction, but this was not a cosmetic-only change and should not be
  recorded as one.

#### 7h.4 Where the threshold lands now, re-measured

`ROUND_MIN_EDGE_FRAC` = 0.5 at `ROUND_R` = 0.5 is a **0.25 mm** cut. It *is* still in a gap, and the
gap is the same on all three variants — but it is a thin, incidental gap between two unrelated
features, not the separation between two populations that 0.50 mm sat in:

| | `ROUND_R` 1.0 | `ROUND_R` 0.5 |
|---|---|---|
| cut | 0.50 mm | 0.25 mm |
| longest edge below it | 0.4644 (−X tip-cap rim) | **0.2491** (mouth rim, X = ±12.5) |
| shortest edge above it | 0.5062 (plate top edge) | **0.2613** (long half of a split corner-arc link) |
| gap width | 0.0419 mm | **0.0122 mm** |
| clearance below the cut | 0.0356 mm | **0.0009 mm** |
| target-set edges below / above (nominal) | 235 / 140 | 44 / 330 |

Both bounds are identical on `H_DROP` 0, 2 and 4. But 0.2491 and 0.2613 belong to different features,
the spectrum is dense on both sides, and the cut clears the edge below it by **0.9 µm** — a hair, not
a plateau. **The claim that this threshold "drops whole chains and never half of one" is no longer
true.** Of the 44 edges below the cut on the nominal (48 / 44 on `H_DROP` 0 / 4): **40 are sub-0.25 mm
fragments of the corner-arc chain itself**, left where boolean seams inserted extra vertices into it,
2 are on a flare-tip cap, and 2 are the 0.2491 mouth-rim pair. The chain is cut in parts. What saves
it in practice is that a 0.5 mm bevel slides ~0.5 mm along the chain from each neighbour, which is
longer than every one of those fragments (0.014–0.24 mm), so they are overrun rather than left
standing proud — which is why the corners read rounded and the perimeter spike count fell rather than
rose.

**The 0.6 / 0.7 rejection argument does not survive the radius change, and 0.5 is not re-derived.**
At `ROUND_R` 1.0 those fractions meant 0.60 / 0.70 mm and landed on the witness-notch chain, which is
what rejected them. At `ROUND_R` 0.5 they mean 0.30 / 0.35 mm and the notch chain (0.5062 / 0.5833) is
nowhere near them. Re-swept at `ROUND_R` = 0.5, all three variants, full acceptance at every point:

| `ROUND_MIN_EDGE_FRAC` | cut | perimeter spikes | folds (2 / 0 / 4) | verify |
|---|---|---|---|---|
| 0.3 | 0.15 mm | 53 | 116 / 143 / 110 | PASS |
| 0.48 | 0.24 mm | 36 | 102 / 129 / 97 | PASS |
| **0.5 (shipped)** | **0.25 mm** | **36** | **107 / 133 / 104** | **PASS** |
| 0.6 | 0.30 mm | 28 | 111 / 138 / 106 | PASS |
| 0.7 | 0.35 mm | 26 | 113 / 140 / 103 | PASS |
| 1.0 | 0.50 mm | 0 | 65 / 95 / 66 | PASS (corners square again) |

None of the `ROUND_R` 1.0 failure modes reproduce — no non-manifold at 0.3, no 2-shell at 0.4, no
3-shell at 1.0. **`OPEN`: 0.5 is held because iteration 6 was scoped to move `ROUND_R` only. It is no
longer demonstrably the best fraction at this radius** — 0.6 and 0.7 beat it on perimeter spikes and
lose to it on folds, and what they trade away is whole corner-arc segments going back to square. If
`ROUND_R` stays at 0.5, this fraction deserves its own sweep with a render, not just counts.

Where the spikes were at `ROUND_R` 1.0, before → after `ROUND_MIN_EDGE_FRAC` (nominal): plate corner
arc **236 → 44**, plate side edge 60 → 60, collar runout toe 55 → **23**, other 47 → 43, notch
11 → 11, plate bottom 9 → 9. The side-edge group was untouched because its links are 1.389 mm and the
only threshold that would take them was above the radius, which failed `shells`. Two figures moved as
a consequence and both were the geometry being read correctly rather than a regression: projection
45.830 → **45.849 mm** (the arm tip is no longer nibbled by the bevel) and, on `H_DROP` = 0,
`mouth ramp +Y` 86.15 → **86.50°**. Those are `ROUND_R` 1.0 numbers; at 0.5 projection is 45.348 mm.

## 7i. The harness validated a property the shipped file did not have — FIXED 2026-07-25

**Found by the owner, in Bambu Studio, not by us.** `saddle_h0.stl` — *"Error: 2 non-manifold
edges"* — while our own run reported `non-manifold edges 0` and 135 `[PASS]`. Both were correct.
They were answering different questions.

**Blender counts faces per *topological* edge. A slicer reconstructs topology *by position*.**
STL has no vertex identity — it is a triangle soup, and the slicer welds it by coordinate. Two
edges that Blender holds as distinct objects at identical coordinates therefore read manifold in
Blender and non-manifold in the slicer. Every manifold, boundary and shell check in this file had
been topological since it was written, so `non-manifold edges 0` had been true and useless all
along. It is the same class as the inverted acceptance check 4 and the bevel that silently ran at
zero offset — a gate that passes without measuring what ships — and it is the one that stopped
the part being printed.

**Mechanism.** The flare-tip cap taper and a trough-cylinder facet are both n-gons, and they share
a run of **ten near-collinear vertices** — a 0.287 mm polyline lying on the cylinder at
r = 9.9250–9.9264 against `R_TROUGH` 9.925. Every interior vertex of that run carries exactly two
edges and two faces, so it holds no shape. The **exporter triangulates each n-gon independently**,
and both clipped the *same ear* off the shared run: the same three vertices emitted twice with
opposite winding. That pair is a back-to-back flap enclosing nothing (areas 1.56e-5 and
2.50e-5 mm²). Its own edges have two faces each and read manifold; the edge it shares with the body
gets 2 body + 2 flap = **4**. Two ears, two non-manifold edges. The nominal variant only — the
other two put the cap elsewhere relative to the trough.

Measured on the broken file, welded positionally and split into connected components:

| component | triangles | volume mm³ | note |
|---|---|---|---|
| body | 25196 | 33531.5060 | watertight, euler 2, genus 0, winding consistent |
| flap 1 | 2 | 0.0000 | 0.042 × 0.028 × 0.030 mm |
| flap 2 | 2 | 0.0000 | 0.047 × 0.031 × 0.040 mm |

**So the shape was never wrong.** The solid carried 100.000% of the volume and was already
watertight. Retuning `FLARE_TIP` or reshaping the cap would have moved real geometry to chase null
debris — strictly worse than doing nothing. `FLARE_TIP` stays at 4.0.

**Fix, two parts.** *Triangulate inside Blender before export*, so the measured mesh, the `.blend`
and the shipped file are one mesh and the exporter has no independent choice left to make. Over
324 build/parameter combinations Blender's topological count then equals the file's positional
count every time. *Then purge components enclosing nothing* (< 1e-6 mm³) as a backstop, asserting
exactly one survives with its volume unchanged; more than one component with real volume raises,
rather than keeping the largest piece and calling it the part.

The purge is a precise instrument, not a blunt one. Swept over `FLARE_TIP` 3.00–5.00 × three
variants, it fired at exactly the 2 combinations that were broken, 2 faces each, and dropped
**zero** faces at the other 25. Without the fix the same field failed at 6 of 27, confirming the
non-monotonicity recorded in §7d.

**`SIGMA_ALLOW`-adjacent precision bug found on the way.** `_signed_volume` via `mathutils`
returned **9.5e-06 mm³** for a zero-volume flap instead of zero — single precision, two ~60 mm³
tetrahedra cancelling 23 mm from the origin. Enough to make null debris read as a solid body and
abort the build. Now float64 about each component's own centroid; the same pair measures ~1e-15.

**Second live instance of the same class, fixed with it.** The `shells` check was topological and
read **1** on a mesh that positionally contained **3**. Acceptance now gates on positional
non-manifold, boundary and shell counts plus degenerate-face and Euler checks — 8 per variant,
parsed from the binary STL on disk after it is written, by code sharing nothing with what wrote it.
A variant that fails is refused *and* its file deleted: a loud failure that leaves the bad STL as
the newest file in the directory is how this reached the owner in the first place. Weld tolerance
1.0e-4 mm, chosen between a float32 ulp of 7.6e-6 at the largest coordinate and the closest
genuinely distinct vertex pair at 0.005048 mm (`MERGE_DIST` 5.0e-3 guarantees nothing closer
survives) — an empty two-and-a-half-decade band. Verified non-load-bearing: 0 through 5e-3 give
identical counts on all three files; 1e-2 is where it breaks.

After: 165 `[PASS]`, 0 `[FAIL]`, and all three files watertight, one body, euler 2, zero positional
non-manifold edges — confirmed independently with `trimesh`, which is a cross-check only and not a
runtime dependency (the shipped gate runs in Blender's bundled Python and must not acquire an
install step).

**The parameter space was never as treacherous as we thought.** Re-sweeping after the fix, with
every point built across all three variants:

| parameter | previously recorded | re-measured after §7i |
|---|---|---|
| `R_ROOT` 12.0–15.0 @ 0.25 | 12.0, 14.25, 14.75 fail — "mesh robustness, not monotonic" | **12.0–14.5 all clean.** 14.75 / 15.0 fail `mouth ramp -Y` (95.45° / 95.65° vs 89.1–93.7°) — a monotonic *geometric* bound, mesh clean |
| `ROOT_BLEND` 2.0–4.5 @ 0.5 | 2.5 non-manifold, 3.0/3.5/4.0 clean | **2.5–4.5 all clean.** 2.0 fails Euler = 1 |
| `FLARE_TIP` 3.0–5.0 @ 0.25 | — | 26 of 27 clean; purge fires at exactly the 2 broken combinations, drops 0 faces at the other 25 |

Most of the recorded "landmines" were this same null-debris class, so the non-monotonic
mesh-robustness bound on `R_ROOT` was an artifact of the exporter, not a property of the geometry.
It had been steering the design away from radii that were never unsafe.

**Open, at two values we do not ship.** `FLARE_TIP` = 3.0 on `H_DROP` = 0, and `ROOT_BLEND` = 2.0,
both fail the new Euler check with **euler = 1** — odd, therefore impossible for a closed
orientable surface — while every edge carries exactly two faces. That signature is a *single-vertex
pinch*: two sheets meeting at a point, which no edge-based test can see. Both are pre-existing,
both were invisible to every check this file had before today, and neither affects a shipped value.
Worth its own iteration if either value is ever wanted.

## 7j. The generator is not byte-reproducible — `OPEN`, recorded not fixed

**Two runs of identical, unedited source produce different STL bytes.** Found by iteration 5b,
re-verified at iteration 6 by running the unmodified script **nine consecutive times** and hashing
all three variants after every run:

| digest | what it covers | result over 9 runs × 3 variants |
|---|---|---|
| `md5` of the file bytes | everything | **9 distinct digests per variant. Never once repeated.** |
| `md5` of the sorted triangle multiset | which triangles exist, winding kept | 1 digest for `saddle_h0` and `saddle_h+2`; **2 for `saddle_h-2`** (8 runs one way, 1 the other) |
| `md5` of the sorted **unique vertex set**, `.9g` per coordinate | where the surface is | **1 digest per variant. Identical every run.** |

Two independent causes, and the first alone is enough to break byte equality:

1. **Triangle emission order is nondeterministic.** The boolean and `bmesh` operators hash on pointer
   identity, so the order faces end up in varies between processes. This shuffles the whole file and
   moves the raw `md5` on every run of every variant. It changes nothing about the solid.
2. **The diagonal chosen on some planar quads flips run to run.** `triangulate_and_purge` calls
   `bmesh.ops.triangulate(..., quad_method='BEAUTY')`; on a quad whose two diagonals score equal
   within float noise the tie is broken by internal ordering, which is pointer-derived. Caught in the
   act at iteration 6 on `saddle_h-2`, run 9 of 9: **10 triangles differed, 5 quads, over an
   identical 20-vertex set** — same four corners, other diagonal, same surface, different triangle
   multiset. They sit on the layer-aligned relief grooves, at file coordinates X = 16.3631 / 16.6208,
   Y = 1.1033 / 1.3011, Z pairs (30.8, 31.4), (32.8, 33.4), (37.8, 38.4), (42.8, 43.4), (44.8, 45.4).
   Iteration 5b saw the same class on `saddle_h+2` at (19.1032, 15.9586) / (19.3329, 15.7289), Z =
   28.8 … 46.8 — the specific quads move with the geometry; the defect does not.

**Consequences, stated plainly.**

- A shipped STL **cannot** be reproduced byte-for-byte from its source. If you re-run the script and
  `diff` the file against the one in the repo, it will differ, and that difference means nothing.
- **Hashing raw STL bytes carries no signal at all** — not for "did my edit change the part", not for
  "is this the file we verified", not for provenance. Every use of a raw `md5` in this project's
  history that appeared to prove something was proving only that two files were written by the same
  process.
- The **unique vertex set** is the invariant that does hold, and the run now prints its digest for
  every variant (`geometry  vertex-set md5 …`, from `stl_manifold`). Reported, never gated. Compare
  *that* across runs. For an edit that is supposed to be geometry-neutral it must not move; for one
  that moves geometry it must.
- All 165 checks pass on either outcome, and both causes have therefore been shipping unnoticed for
  a long time. Volume, envelope, watertightness, one body, Euler 2 and every measured dimension are
  invariant to both — this is a *provenance* defect, not a geometry defect.

**Judgement: do NOT impose a deterministic diagonal now.** `OPEN`, deliberately, with reasons:

1. **It would not achieve the stated goal.** Cause 1 shuffles the file independently of cause 2.
   Fixing the diagonal alone leaves the raw `md5` moving on every run, so the part-fix buys nothing
   measurable while inviting exactly the false confidence this project keeps being bitten by —
   "reproducibility fixed", raw hash still moving. Byte reproducibility needs a canonical emission
   order **as well**, which means re-sorting the mesh or writing our own STL writer.
2. **That second half touches the artifact-producing path to change nothing about the artifact.**
   Every defect in §7c, §7e, §7h and §7i is a check or a step that measured or produced something
   other than what shipped. Rebuilding the export path so the bytes are stable, for a property no
   consumer reads, is precisely the trade this file has learned not to take.
3. **A coordinate-canonical diagonal pass needs two new thresholds** — planarity and convexity — and
   a near-planar quad flipped under a tolerance moves the surface. Small, but this file does not have
   a good record with "small and unchecked".
4. **Nothing downstream reads either property.** A slicer welds the soup by position; the sliced
   solid, the volume and the eight positional STL gates are identical whichever diagonal is cut.
5. **The actual need is already met.** The question a hash was being asked — "did this edit move the
   part?" — is answered exactly by the vertex-set digest, which is now printed every run and costs
   one `md5` over data `stl_manifold` had already parsed.

If it is ever wanted, the shape of the fix is: canonicalise the diagonal by a rule on sorted vertex
coordinates (never on mesh pointers), gate it on strict coplanarity and convexity, **and** emit
triangles in a coordinate-sorted order — then prove it with the vertex-set digest, which must not
move, not with the raw `md5`, which is the thing being changed.

## 8. Measurements still needed

1. ~~**Bar diameter**~~ — **DONE**, 3/4 in / 19.05 mm, §5. The fit-gauge comb is now
   redundant; it only needs printing if the confirmation is ever doubted.
2. **Cradle height reference** — §6.1. Sets whether it works at all. **Now the single
   remaining binding unknown**, and still the likeliest way this part fails at its job.
3. **Substrate** — §2.4. Sets the 3M product.
4. Where the shade fabric passes relative to the support, so the saddle does not pinch or chafe it. `[OPEN]`

## 9. Resolved scope

| # | Question | Answer |
|---|---|---|
| 9.1 | Replace end brackets or add mid-span support? | **Add mid-span support.** `[STATED]` |
| 9.2 | Capture or drop-in? | **Drop-in.** Ends capture, so lift-out is already prevented. `[STATED]` |
| 9.3 | Plate size? | **3 in × < 2 in.** `[STATED]` |
| 9.4 | Load? | **< 10 lb total.** `[STATED]` |
| 9.5 | How many mounts? | `[OPEN]` — one at centre, or two at third-points? Depends on span and how much sag remains. |
| 9.6 | Printer, material, finish-matching | `[OPEN]` |

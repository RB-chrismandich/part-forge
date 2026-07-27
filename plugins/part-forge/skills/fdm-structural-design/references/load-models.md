# Load models: the arithmetic in full

Every model here is closed-form. For the bracket and mount class of part that is not a
compromise: the uncertainty in the material allowable and in the print itself is larger than
the error in a section-modulus calculation, so a finite-element result would carry false
precision on top of the same assumptions.

What matters is doing the arithmetic on the *right* section, with the *right* area, against
an allowable that accounts for the part being printed rather than moulded.

## Bending

```
sigma = M * c / I           M     = load * moment_arm
                            c     = distance from the neutral axis to the extreme fibre
                            I     = second moment of area about the neutral axis
S     = I / c               section modulus, so sigma = M / S
SF    = sigma_allow / sigma
```

### Compute the section, do not assume it

`A`, the centroid, and `I` come from the actual sampled cross-section, not from a rectangle
chosen because it is easy. Sample the section by casting a fan of rays across it, build the
polygon, and integrate:

```
A   = sum over edges of the shoelace terms
cy  = (1/A) * integral of y dA          the neutral axis for pure bending
I   = integral of (y - cy)^2 dA
```

A polygon integration is twenty lines and removes the largest error term in the whole
calculation. An L-section or a T-section idealised as a rectangle can be wrong by a factor of
two in `I`, and the error is in the unsafe direction whenever the material is concentrated
away from where the rectangle puts it.

**A caveat drawn from the worked example.** Its reported section modulus is
`S = 84.88989107 mm^3`, with `area = 112.84273863 mm^2` and `section_h = 4.51370955 mm`. Those
reconcile exactly as `b*h^2/6` with `b = area / h = 25.000000 mm` -- which is the saddle width
exactly. So the harness idealised the section as a rectangle of the full part width. That is
defensible for a near-rectangular wall of constant width, and it is wrong for any section
where material is not uniformly distributed through the depth. Check which case applies
before trusting a section modulus that reduces to `b*h^2/6`.

### Walk the stations and keep the worst

The governing section is rarely at the geometric root. Step along the load path, compute `SF`
at each station, and gate on the minimum. Report *where* the minimum occurred, not only its
value -- a margin without a location cannot be re-checked after the next edit.

In the worked example the worst section sits at `y = 26.51875 mm`, which is only 5.23 mm
inboard of the load point and well out along the arm, not at the plate. That is consistent
with the creep analysis further down, which finds the trough wall carrying three quarters or
more of the compliance while the root carries very little.

### Worked example, end to end

Every number below is from the shipped `verify_report.json` for the nominal variant, and the
chain reconciles to seven significant figures.

| Quantity | Value | Source |
|---|---|---|
| design load | 5.0 lbf | ledger, section 1.5 |
| load in newtons | 5.0 * 4.4482216 = **22.2411 N** | conversion |
| load applied at | y = 31.75 mm | the mating axis depth |
| worst station found at | y = 26.51875 mm | station walk |
| moment arm at that station | 31.75 - 26.51875 = **5.23125 mm** | difference |
| bending moment | 22.2411 * 5.23125 = **116.3488 N.mm** | M = F * a |
| section area | 112.8427 mm^2 | sampled section |
| section depth | 4.5137 mm | sampled section |
| section modulus | **84.8899 mm^3** | S = I / c |
| bending stress | 116.3488 / 84.8899 = **1.37058 MPa** | sigma = M / S |
| allowable, PETG | 50 MPa | material table |
| safety factor | 50 / 1.37058 = **36.48** | SF = sigma_allow / sigma |
| required | 8.0 | SF_MIN |

Passes by a factor of four and a half over the requirement. Worth stating plainly rather than
quietly: this part is not stress-limited, so effort spent stiffening it buys nothing. The
binding constraints were elsewhere -- the mating dimensions, and the adhesive.

Note also that the whole moment is `6.25 in.lbf` at the full 1.25 in arm, and the part sees
only a fraction of that at its worst section because the section sits close to the load. A
part whose worst section is near the mount would see the full arm.

## The safety-factor budget

A safety factor for a printed part is not a fudge. It is a product of specific derating terms
that each have a reason, and writing them out separately is what stops it being cargo-culted.

| Term | Factor | Why |
|---|---|---|
| infill against solid | ~0.6 | the section is not solid plastic; walls and infill carry, voids do not |
| creep against short-term | ~0.5 | sustained load; datasheet strength is a short-pull number |
| print variation | ~0.7 | layer adhesion, temperature drift, moisture, batch |
| direction | ~0.6 | the allowable was measured on an injection-moulded coupon loaded along its strong axis; the part may be loaded across layers |

Multiply the first two and the remainder and the product lands near `1/8`, which is where
`SF_MIN = 8` comes from. Each term is a rounded estimate, and the point is not their
precision -- it is that they are all below one and they all multiply.

**Two is not a safety factor for a printed part under sustained load.** Two covers roughly
the infill term alone, leaving creep, print variation, and direction entirely uncovered. A
part designed to `SF = 2` on a datasheet allowable is, in the worst combination, running
above yield.

Take `sigma_allow` from an explicit per-material table and raise on an unknown key rather
than defaulting. Beware plausible-but-wrong entries: a table mapping both PLA and PETG to
50 MPa is a coincidence of two rounded numbers, not evidence the materials behave alike, and
a guard against a *missing* key does nothing about a wrong value.

## Adhesive: shear

```
shear = load / bonded_area
```

**Bonded area is not face area.** The worked example initially divided by the plate's tape
face, 3387 mm^2, when the adhesive actually occupied 1960 mm^2 of it -- overstating the bond
by **73%**, and understating shear stress by the same factor. Every conclusion drawn from
that divisor was wrong in the unsafe direction.

Measure the area the adhesive strips actually cover, after any trimming, and use that.

## Adhesive: peel

Peel is not a stress on the bond area; it is a *bending* problem on the bond.

```
S_bond = b * h^2 / 6           b = bond width, h = bonded height
peel   = M / S_bond            so peel scales as 1 / h^2
```

The `1/h^2` is the whole story. Bond *height* dominates, and it dominates quadratically,
which makes layout choices that look cosmetic into structural ones.

**Worked instance.** Backing the top adhesive strip off from 1.750 in of bonded height to
1.652 in costs

```
(1.750 / 1.652)^2 = 1.1222      a 12.2% peel penalty across the entire bond
```

The competing option -- notching the strip around a small void rather than backing it off --
cost `5 mm^2` of a `3387 mm^2` bond:

```
5 / 3387 = 0.15%
```

Coverage won by a factor of about eighty, and it won *on the numbers*, not on preference. A
12% penalty everywhere against 0.15% in one spot is not a close call once both are computed,
and it is entirely non-obvious before they are.

### Bond configuration comparison

Same load, same moment arm, three layouts:

| Bond | Area | Shear | Peel |
|---|---|---|---|
| one 1.00 in strip | 3.00 in^2 | 1.67 psi | 12.5 psi |
| one full plus one trimmed to 0.75 in | 5.25 in^2 | 0.95 psi | 4.1 psi |
| two full strips, taller plate | 6.00 in^2 | 0.83 psi | 3.1 psi |

Doubling the bonded area halves the shear, as expected -- and cuts peel by a factor of four,
because the height grew as well. Peel is where the design margin actually moves.

**The inversion worth remembering.** An earlier conclusion in the same project read: "at under
10 lb the adhesive is comfortable, not marginal." That was backwards. Peel at 12.5 psi against
shear at 1.67 psi was the binding constraint the whole time, and the small load number that
appeared to settle the question settled nothing, because it was being compared against the
wrong stress. Compute peel explicitly. Do not infer comfort from a small load.

## Creep: check a section's share before optimising it

Sustained load redistributes toward the most compliant region over time, so the section with
the largest instantaneous stress may contribute very little to the deflection that actually
accumulates.

Weight the compliance along the load path:

```
compliance ~ integral of (yL - y)^2 * sigma^(n-1) / I  dy
```

with `n` the Norton creep exponent, around 3 to 5 for these thermoplastics. The
`sigma^(n-1)` weighting is what makes this different from an elastic deflection integral: at
`n = 5` a region at twice the stress contributes sixteen times as much creep.

Region shares for the worked arm, comparing a small root fillet against one twice the radius:

| Region | small root fillet | large root fillet |
|---|---|---|
| root, y < 15 | 19.1% | 6.2% |
| mid | 4.4% | 4.1% |
| trough wall, y > 21 | **76.5%** | **89.7%** |

Doubling the root fillet cuts root stress several-fold. Total arm creep compliance falls:

| Norton exponent | reduction in total compliance |
|---|---|
| n = 3 | **15%** |
| n = 5 | **7%** |

The headline stress ratio at the root suggested a several-fold improvement. The delivered
improvement in what the part actually does over time is 7 to 15 percent, because the root was
never carrying much of the compliance and the fillet cannot reach the wall that is.

The generalisation: **a stress ratio is a local claim; multiply it by the region's share
before believing it is a global one.**

## Compare a deflection against what sits underneath it

An absolute deflection means nothing until it is compared with the compliance of everything
else in the load path.

The worked arm deflects about **10 micron** at the tip. The adhesive layer beneath the mount
compresses and shears by **46 to 253 micron** under the same load. Stiffening the plastic is
optimising a term that is one to two orders of magnitude smaller than the term next to it in
the same series -- the part could be made infinitely rigid and the assembly would move within
5% of what it already moves.

Before adding a stiffening feature, enumerate every compliance in series -- part, adhesive,
fastener, the substrate itself -- and check the one being improved is not the smallest.

## Long-term static rating, and the checks that cannot be done early

Adhesive datasheets lead with peak strength, which is measured by pulling until it fails in
seconds. That number does not predict what a bond does under continuous load for months, and
continuous load for months is the actual duty cycle for a mount.

Rate against the **long-term static** specification. Where the manufacturer publishes only a
peak figure, treat a substantial fraction of it as unavailable and say so in the ledger as an
open assumption rather than silently using the headline number.

Then close the loop physically, because this is the one criterion that cannot be evaluated
before the part is installed:

| When | What to check | What it catches |
|---|---|---|
| dry fit, before adhesive | fit, contact, alignment | a part that never touches what it supports |
| 24 hours | position unchanged, no visible peel at edges | a bond that was never going to hold |
| 30 days | position unchanged, no creep at the top edge | the failure mode the peel calculation is about |

Record the result back into the ledger either way. A mount that held for 30 days is a fact
worth having next time; a mount that crept is worth considerably more.

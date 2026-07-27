---
name: fdm-structural-design
description: Size and orient a printed part so it carries its load. Use when choosing wall thickness, print orientation, or safety factor for an FDM part, when a printed part broke, when sizing an adhesive or taped mount, when deciding whether a fillet is worth adding, when reasoning about overhangs as a design constraint, or when a load will sit on the part for months rather than seconds.
---

# Making a printed part carry its load

FDM parts fail in ways solid plastic does not, and the three that matter are all
orientation-dependent: layers separate before the material yields, sustained load creeps
where a brief load would not, and infill means the section is not as solid as its outline.

The reasoning below is arithmetic, not simulation. That is deliberate — for the bracket and
mount class of part, a section modulus on the back of an envelope answers the question, and
the numbers that turn out to matter are usually not the ones a stress plot makes loud.

## Start with the load path, and find its thinnest section

Trace where force enters, where it leaves, and what carries it in between. Then find the
**thinnest cross-section on that path** and check there. The convenient section is almost
never the governing one.

A concrete trap from the worked example: every verification ray was fired in the X=0 plane,
and X=0 had been deliberately placed at the centre of a ridge. The sweep measured the ridge
for the project's entire history. The groove floor beside it — thinner, and on the same load
path — was never visited until a second sampling station was added. **Ask which station is
worst, not which is easiest to reach.**

Set a floor and gate on it. Three millimetres of wall on a load path is a reasonable starting
point for PLA or PETG at typical settings; below that, layer count rather than geometry starts
deciding the strength.

## Bending

For a section of area `A` and second moment `I` about the neutral axis, with the extreme
fibre at distance `c`:

```
sigma = M * c / I           M = load * moment_arm
SF    = sigma_allow / sigma
```

Compute `A`, the centroid, and `I` from the actual sampled cross-section rather than a
rectangle you hope resembles it. Walk stations along the arm and keep the worst safety factor.

**Use a large safety factor and know what it is paying for.** Around 8 is defensible for a
printed part under sustained load: roughly a factor of 0.6 for infill against a solid section,
roughly 0.5 for creep against short-term strength, and the remainder for print variation and
the fact that `sigma_allow` from a datasheet was measured on an injection-moulded coupon in a
direction your part may not share. A safety factor of 2 on a printed part under months of load
is not a safety factor.

Take `sigma_allow` from a per-material table with an explicit lookup and raise on an unknown
key. Beware coincidence: a table mapping both PLA and PETG to 50 MPa is not evidence they
behave alike, and the guard against a *missing* key does nothing about a plausible-but-wrong
value.

## Adhesive and taped mounts

A taped mount fails in peel long before it fails in shear, and the two scale differently.

```
shear = load / bonded_area
peel  = a bending problem on the bond: S = b * h^2 / 6, so peel stress scales as 1 / h^2
```

**Bonded area is not the same as the face area.** Using the plate face as the divisor
overstated the bond by 73% in the worked example, and the resulting "average shear" figure was
wrong for that reason alone. Measure the area the adhesive actually occupies.

The `1/h^2` term is why bond *height* dominates. Losing 0.098 in of bonded height cost
`(1.750/1.652)^2 = 1.12`, a 12% peel penalty across the entire bond — which is how a
seemingly minor layout choice beat a competing concern that cost 5 mm2 of a 3387 mm2 bond, or
0.15%. Coverage won on the numbers.

Worked comparison, same load and arm, three bond layouts:

| Bond | Area | Shear | Peel |
|---|---|---|---|
| one 1.00 in strip | 3.00 in2 | 1.67 psi | 12.5 psi |
| one full plus one trimmed to 0.75 in | 5.25 in2 | 0.95 psi | 4.1 psi |
| two full strips, taller plate | 6.00 in2 | 0.83 psi | 3.1 psi |

An earlier conclusion in that project — "at under 10 lb the adhesive is comfortable, not
marginal" — was **inverted**, and the load number that appeared to settle it did not. Peel was
the binding constraint the whole time. Check peel explicitly; do not infer comfort from a small
load.

Rate against the adhesive's **long-term static** specification, not its peak strength. Creep
over months, not a single hard pull, is what takes adhesive mounts down. Then re-check the
part in place at 24 hours and again at 30 days, because this is the one criterion that cannot
be evaluated before the part is installed.

## Creep: check a section's share before optimising it

Sustained load redistributes toward the most compliant region, so the section with the loudest
stress number may contribute almost nothing to total deflection over time.

Weight the compliance integral along the load path — `integral of (yL - y)^2 * sigma^(n-1) / I dy`,
with a Norton exponent `n` around 3 to 5 for these plastics — and look at where the total
actually comes from:

| Region | small root fillet | large root fillet |
|---|---|---|
| root | 19.1% | 6.2% |
| mid | 4.4% | 4.1% |
| trough wall | **76.5%** | **89.7%** |

Doubling the root fillet cuts root stress several-fold. Total arm creep compliance falls
**15%** at `n=3` and **7%** at `n=5`, because the root was never carrying much of it and the
wall the fillet cannot reach carries three quarters or more. The headline stress ratio
overstated the benefit by more than an order of magnitude.

A related check on stiffening: compare a deflection against what sits underneath it, not
against zero. Ten microns of tip deflection is irrelevant next to 46 to 253 microns of
compliance in the tape layer below — stiffening the plastic there is optimising the wrong
component.

## Orientation is a structural decision

Layer adhesion is the weak direction. **Orient so bending is carried within layers rather
than across them.**

In the worked example the arm is loaded in bending in the Y-Z plane. Printed tape-face-down,
that bending pulls directly across layer lines at the arm root, which is exactly where FDM
parts fail. Printed on its side, the same bending is carried within layers — and it prints
without supports. One choice, two wins, and it belongs in the generator's docstring with the
reason attached rather than as a bare instruction.

Consequence worth tracking: whichever part axis becomes the build axis, any layer-aligned
feature now depends on that rotation. Grooves pitched in whole multiples of layer height only
land on layer boundaries if the axis they are pitched along is the one the printer stacks.

## Overhangs are a design constraint, not a slicer setting

Design the geometry to be printable rather than asking for supports. The 45-degree rule is a
shape rule:

- A convex profile eroded by `d` per unit of travel *is* a 45-degree taper. Match a flare's
  erosion to its travel and it costs nothing to print.
- A collar that grows faster than 1:1 along the build axis asks the printer to bridge. Shed
  radius at 1 mm per mm of build travel and it does not.

Then measure it rather than trusting the intent: cast the surface normals against the downward
build axis and report the unsupported area.

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"

# wall thickness, overhang area, and mass properties from the exported file
python3 "$S/mesh_audit.py" part.stl --build-axis z --overhang-deg 45 --json audit.json

# where is it thin, and where is it unsupported - rendered for inspection
python3 "$S/mesh_render.py" part.stl --thickness --clip-below 3.0
python3 "$S/mesh_render.py" part.stl --sections 8 --axis x
```

The section views are the ones worth looking at. An exterior render cannot show an internal
void or a wall that thins on the inside, and both are how a part that looks right breaks.

## Things that make a printed part weaker

- **Checking the convenient section.** Find the thinnest one on the load path.
- **A safety factor sized as if the part were solid isotropic plastic.** It is neither.
- **Dividing by the face area to get bond stress.** Use the bonded area.
- **Inferring adhesive comfort from a small load.** Peel scales with `1/h^2`; check it.
- **Rating adhesive on peak strength.** The failure mode is months of creep.
- **Optimising the section with the biggest stress ratio.** Check its share of the total first.
- **Orienting for bed adhesion or print time before checking where bending lands.**
- **Adding a fillet because fillets are good.** Compute what it buys; sometimes 7%.
- **Trusting a datasheet yield figure in the layer-normal direction.** It was not measured there.
- **Leaving overhangs for supports on a load-bearing surface.** Support scarring lands exactly
  where the stress is highest.

## Reference files

- `references/load-models.md` — the bending, peel, shear, and creep-compliance derivations
  with worked numbers, plus the safety-factor budget broken out term by term.
- `references/orientation-and-overhangs.md` — layer-direction reasoning, the 45-degree rule as
  geometry, layer-aligned features, and how to measure unsupported area rather than assume it.

## Related

- `parametric-part-workflow` — Stage 7.
- `mesh-verification-gate` — how to gate on minimum wall and safety factor.
- `blender-parametric-generator` — where orientation gets baked in and why it is a docstring
  claim, not a comment.
- `print-tune-bambu` — material choice, wall and infill settings, and verifying by slicing.

# Build Brief -- Gate Coupon Dish

**Hand this file to a build agent as the task. It is self-contained: it assumes no prior
conversation.**

That property is easy to lose by accident and is the whole value of the file. No phrase
below refers to anything said elsewhere.

## Your task

Generate a small shelled dish as a parametric Blender script, verify it against the
acceptance list, and export a single STL. The part already exists and is committed; this
brief is what would rebuild it from nothing.

## Context -- why this part exists

It is a **regression fixture**, not a response to a physical requirement. Nobody
measured anything. Every dimension was chosen so that a specific known defect in the
generator harness produces a failing check rather than a plausible part.

Read `FACTS.md` before changing any number. Its banner explains why the usual
measured-facts discipline reads differently here, and section 5 says what each of the
four load-bearing dimensions is protecting. Changing one of them without reading that is
how the fixture quietly stops testing anything.

## Parameters

| Name | Value | Unit | Note |
|---|---|---|---|
| `R_BASE` | 30.0 | mm | outer radius through the pedestal |
| `R_RIM` | 42.0 | mm | outer radius at the lip |
| `H_TOTAL` | 18.0 | mm | overall height |
| `Z_FLARE` | 6.0 | mm | where the wall stops being vertical |
| `WALL` | 2.0 | mm | bowl wall, PERPENDICULAR to the surface |
| `FLOOR_T` | 6.0 | mm | material under the bowl. Deliberately != `WALL` |
| `SLOT_W` | 4.0 | mm | drain slot width -- the aperture |
| `SLOT_L` | 12.0 | mm | drain slot length |
| `VOID_R` | 18.0 | mm | radius to the sealed void's centre |
| `VOID_W` | 6.0 | mm | sealed void footprint |
| `VOID_H` | 2.0 | mm | sealed void height |
| `VOID_Z` | 2.0 | mm | its floor; the void spans 2..4, inside a 6 mm pedestal |
| `SEG_RING` | 96 | -- | ring segments |
| `SEG_LOFT` | 24 | -- | loft steps |

`(R_RIM - R_BASE) / (H_TOTAL - Z_FLARE) = 12/12 = 1.0`, so the rim is at **exactly 45
degrees**. This is asserted in the acceptance list, not assumed.

## Coordinate system

    origin  centre of the base, on the bed
    +Z      up

All material sits at Z >= 0. Units: 1 Blender unit = 1 mm.

## Geometry

1. Loft the outer silhouette: vertical from z=0 to `Z_FLARE` at `R_BASE`, then a
   straight flare to `R_RIM` at `H_TOTAL`. Sample `Z_FLARE` exactly -- an even step can
   walk over a silhouette breakpoint, and the resulting dimensional error looks like a
   real defect while being a sampling artifact.
2. Shell it with `part_kit.offset_rings(rings, zs, WALL, floor=FLOOR_T,
   ceiling=H_TOTAL)`. This insets **perpendicular** to the surface. Do not inset each
   ring in its own plane; see the constraint below.
3. Carry the cavity's top ring above the lip before subtracting, so the DIFFERENCE opens
   the bowl instead of leaving a zero-thickness membrane at `z = H_TOTAL`.
4. Cut the drain slot through the floor on the axis.
5. Cut the sealed void at `VOID_R`, wholly inside the pedestal, clear of the slot.

## Constraints

- **Inset perpendicular, never in-plane.** An in-plane inset leaves `WALL * cos(alpha)`.
  At 45 degrees that is 1.4142 mm of a 2.000 mm wall. It is exact in the plane you
  measure it in, which is what makes it dangerous.
- **The floor is not the wall.** 6.0 against 2.0. Do not let `floor` default to anything.
- **Do not pass `recalc_normals=True` to `clean_mesh`.** It orients every face outward
  from its own component, which turns the sealed void inside out and silently makes the
  part solid. Nothing in the structural checks notices except the cavity count.
- **The void must stay sealed and separate from the bowl.** An aperture that reaches a
  cavity merges it into the outer shell, and `cavities` stops measuring anything.
- Prints unsupported: the rim is at the 45 degree limit, and the void spans 6 mm, which
  bridges.

## Print orientation

As modelled, base on the bed. No rotation at export.

## Deliverables

- `gate-coupon-dish_gen.py` -- the generator
- `gate_coupon_dish.stl` -- one artifact, exported only if every check passes

## Unverified assumptions -- flag these, do not hide them

None, and that is a property of this part rather than a claim about diligence: it has no
external referent, so there is nothing left to be uncertain about. Any real part would
have a list here.

## Acceptance checks -- run these and report actual numbers

| Check | Expected | Why |
|---|---|---|
| `solids` | 1 | one printed shell |
| `cavities` | 1 | the sealed void. Zero means it was flipped and the part is solid |
| `open_edges` | 0 | |
| `over_edges` | 0 | |
| `winding_flips` | 0 | |
| `degenerate_faces` | 0 | |
| `genus` | 1 | the drain slot adds one handle. **Not** the hole count: the sealed void adds none, and a bowl open at the top adds none |
| `volume` | > 0 | |
| `rim_slope_is_45deg` | 1.000 +/- 0.002 | the premise the wall check depends on |
| `rim_wall_perpendicular` | 2.000 +/- 0.06 | worst of 24 stations along the meridional normal. An in-plane inset reads 1.4142 |
| `floor_thickness` | 6.000 +/- 0.02 | |
| `aperture_was_cut` | 1 | `None` means the slot never opened through |
| `raster_hit_the_part` | 1 | every ray passing means the raster was aimed past the dish |
| `drain_aperture_w` | 4.000, within two ray pitches | measured by what passes through, biased low, never high |

Export with `expect_solids=1, expect_cavities=1`. A vessel that does not declare its
cavity is rejected as inside out, which is correct.

## Do not

- Do not measure the wall with a radial cast. On a sloped surface it reads a longer chord
  and under-reports the exact defect the check exists for.
- Do not measure the aperture by probing the material beside it. Cast a raster through it
  and measure the band that passes; that returns nothing when the feature was never cut,
  which fails a gate instead of quietly passing one.
- Do not "fix" a failing dimension by loosening its tolerance.
- Do not change a number in `FACTS.md` section 5 without reading what it protects.

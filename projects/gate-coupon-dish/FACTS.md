# Gate Coupon Dish -- Facts & Actuals

> **READ THIS FIRST. THIS LEDGER ASSERTS NOTHING ABOUT THE PHYSICAL WORLD.**
>
> Every other `FACTS.md` in this repository records measurements of something real, and
> the confidence legend exists to say how well each number is known. This part has no
> real-world counterpart. Nobody measured a shelf it must fit, a bar it must clear, or a
> coin it must pass. **Every number below is a coverage choice**, selected so that a
> specific defect in `.claude/HARNESS-LEDGER.md` fails loudly if it returns.
>
> The tags therefore mean something narrower here than the legend implies. `[STATED]`
> means "chosen deliberately, and here is what it protects". There is no `[MEASURED]`
> row and there must not be one. Reading this file as evidence about a physical
> requirement would be the exact error the measured-facts discipline exists to prevent,
> so it is said here rather than left to be inferred.
>
> Last built: 2026-07-26, Blender 5.2.0 LTS.

**Confidence legend** -- unchanged from the standard set, and see the caveat above.

- `[STATED]` -- asserted directly. Treat as true.
- `[DERIVED from N.N]` -- follows from other facts here; carries no independent authority.

## 1. The job

Be the hollow half of this repository's regression net.

`projects/shade-bar-mount/` is a solid, and a solid cannot fail the way a hollow part
can. A flipped cavity leaves `bodies`, `open_edges`, `over_edges`, `winding_flips` and
`genus` **all identical**; only the signed volume and the cavity count move. The saddle
fixture -- and therefore the entire pinned-digest regression net -- was blind to every
hollow-geometry defect in the ledger.

This part is what makes those defects visible to a gate.

The dish works as a desk catch-tray and it prints. That is a constraint rather than the
point: a fixture that could not be printed would stop modelling the thing the harness
exists to protect.

## 2. Mounting method

None. It sits on a desk. `[STATED]`

## 3. Space envelope

| Fact | Value | Confidence | Protects |
|---|---|---|---|
| overall diameter | 84.0 mm | `[DERIVED from 5]` | nothing; follows from the rim radius |
| overall height | 18.0 mm | `[STATED]` | keeps a full rebuild under a minute |
| one piece, no supports | yes | `[STATED]` | the 45 deg rim sits exactly at the unsupported limit |

The envelope constrains **the shell**, not an assembly. This part has no assembly, so
there is no section-9 mechanism row for it to contradict -- ledger #7 is the case where
those two did collide, and it is worth knowing this file cannot reproduce it.

## 4. Existing hardware -- reference only

None. There is nothing this part mates with, which is exactly why no dimension here may
ever be cited as a requirement.

## 5. The four load-bearing numbers

The reason the file exists. Each is chosen so a named defect produces a **failing
check** rather than a plausible part.

| Fact | Value | Confidence | The defect it catches |
|---|---|---|---|
| rim slope | 1.000, i.e. 45 deg | `[STATED]` | **#5.** A naive in-plane inset leaves `wall * cos(alpha)`. At 45 deg that is 1.4142 mm of a 2.000 mm wall, a 29% error. On a vertical wall `cos(0) = 1` and the correct and incorrect constructions are **identical** -- which is precisely how the defect survived until it met a dome. |
| wall thickness | 2.00 mm | `[STATED]` | **#5.** Measured perpendicular to the surface at 24 stations, along the true meridional normal. A radial cast reads a longer chord and under-reports the defect it is meant to find. |
| floor thickness | 6.00 mm | `[STATED]` | **#5, second defect.** Deliberately **not** the wall. Letting the floor default to the wall inset was an independent bug in the same function; 6.00 against 2.00 makes a regression a 4 mm error rather than a rounding one. |
| sealed void | 6 x 6 x 2 = 72.0 mm^3 | `[STATED]` | **#8 and #10.** A shell with negative signed volume. Flipping it outward moves the total by exactly +144.0 mm^3, to 24068.4142, which `inspect_model.py` detects with zero shared code. |

Material volume, `[DERIVED from 5]`: **23924.4142 mm^3**, pinned in `smoke.sh`.

## 6. Why there are two hollow features and not one

Not an aesthetic choice, and easy to get wrong.

**An aperture that reaches a cavity destroys the cavity as a separate body.** Open the
bowl to the air and its interior surface becomes part of the outer shell: one body, no
negative volume, `inverted_bodies = 0`. A vessel with only an open bowl cannot exercise
`expect_cavities` at all -- the check would pass while measuring nothing, which is the
failure class the whole ledger is about.

So the part carries both:

- an **open bowl** with a **drain slot** through the floor. Reaches the outside, adds one
  handle, gives `genus = 1`, and provides an aperture whose *opening* is the spec.
- a **sealed void** in the pedestal, opening onto nothing. Stays a separate shell with
  negative volume, and is the only feature here that can make `cavities = 1` true.

They are kept apart geometrically: the slot is on the axis, the void is at radius 18.

## 7. Defect history

**7a. First build passed 14/14 (2026-07-26).** Recorded because a clean first build is
normally a warning sign. Here it is expected -- the geometry is simple and every number
was chosen against a check that already existed. The evidence that the checks work is
not that they passed; it is section 8.

## 8. What proves these checks can fail

A gate that cannot fail is not a gate. Each defect was reintroduced and rebuilt:

| Reintroduced | Result | Failing checks |
|---|---|---|
| `clean_mesh(recalc_normals=True)` (#8) | refused, no STL | `solids`, `cavities` |
| naive in-plane inset (#5) | refused, no STL | `rim_wall_perpendicular` read **1.4142** |
| slot never cut (#4) | refused, no STL | `genus`, `aperture_was_cut`, `drain_aperture_w` |
| unmodified | exported | none |

The flipped-cavity build was then exported deliberately, bypassing the gate, to confirm
`smoke.sh` catches it from the bytes alone: `mesh_audit` reports `cavities = 0` and
volume 24068.4142, and `inspect_model` independently reports 24068.0 -- the pinned value
plus exactly twice the void.

## 9. Resolved scope

- The part is a fixture first and an object second. Where the two conflict, coverage wins.
- No `[OPEN]` items, now or ever: there is no external reality left to measure. If that
  stops being true, this file is the wrong template for whatever it has become.

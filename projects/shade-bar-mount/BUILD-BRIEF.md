# Build Brief — Shade Bar Mid-Span Saddle

**Hand this file to Claude as the task.** It is self-contained: it assumes no prior conversation.

---

## Your task

Build a 3D-printable **mid-span support saddle** for a sagging window shade bar, as a **parametric
Blender Python script**. Deliver the script, a saved `.blend`, and exported STLs.

You have a `blender-mcp` MCP server connected to a live Blender 5.2 session. Use
`execute_blender_code` to build, `get_scene_info` / `get_object_info` to verify, and
`get_viewport_screenshot` to check your work visually.

## Context — why this part exists

A wide window shade hangs from a horizontal bar. The bar is held at both ends by existing brackets
and **sags visibly in the middle**. This part is an **additional support at mid-span** that pushes
the bar back up to level. It is 3M-taped to the vertical face of a dark header band above the window.

Two consequences you must not lose:

1. **The end brackets already capture the bar.** It cannot lift out. So this part needs **no hook,
   no curl, no retention feature** — it only pushes up. Anything that wraps over the bar is wasted
   material, a longer moment arm, and a printing overhang for no benefit.
2. **It is taped, not screwed.** No holes, no fasteners. The back face is an adhesive surface and
   must be **perfectly flat and planar** — this is the single most important surface on the part.

## Parameters — put these at the top of the script as named variables

| Name | Value | Notes |
|---|---|---|
| `W_PLATE` | `76.2` | Plate width, mm (3.000 in). Fixed. |
| `H_PLATE` | `44.45` | Plate height, mm (1.75 in). **Hard cap 50.8 mm (2 in) — never exceed.** |
| `T_PLATE` | `5.5` | Plate thickness, mm |
| `R_CORNER` | `6.0` | Plate corner radius, mm. Cosmetic; not critical. |
| `D_BAR` | `19.05` | Bar diameter, mm (3/4 in). **CONFIRMED** by the owner 2026-07-25 — see FACTS §5. |
| `H_DROP` | `2.0` | Bar rest point below the plate's bottom edge, mm. **STILL UNVERIFIED** — FACTS §8. |
| `CLEAR` | `0.4` | Trough radial clearance over the bar, mm |
| `GAP` | `1.0` | Air gap between bar surface and plate front face, mm — used ONLY when `Y_BAR` is `None` |
| `Y_BAR` | `31.75` | Bar centre forward of the tape face, mm (1.250 in). **A MEASURED INPUT, not a design choice** — the existing end brackets fix where the bar is. `None` falls back to the theoretical floor `T_PLATE + D_BAR/2 + GAP`. See FACTS §6.4. |
| `W_SADDLE` | `25.0` | Saddle width along the bar, mm |
| `T_WALL` | `3.0` | Minimum wall thickness on the load path, mm |

Everything else is **derived** from these — with one honest exception, stated here rather than
discovered later. `R_ROOT`, `R_ROOT_LOW`, `ROOT_BLEND`, `FLARE` and `FLARE_TIP` are *empirical*
constants: their values were pinned by sweeping mesh robustness across the three `H_DROP` variants
at the confirmed `D_BAR`, because the boolean's failure modes are non-monotonic in those radii
(12.0, 14.25 and 14.75 fail on one variant or another while 12.5, 14.0 and 14.5 are clean). They
are **not** formulas of the ten parameters above. Changing `D_BAR` therefore requires re-sweeping
them. The acceptance gate is a **partial** backstop: it refuses to export a variant that comes back
non-manifold, multi-shell, outside its envelope or under `T_WALL`, which is how an off-plateau
radius usually presents. It does **not** gate folded faces — those are counted and reported only —
so a re-sweep is still a re-sweep, not something the gate does for you.

Committed values: `ROOT_BLEND` = 3.5, `R_ROOT` = 13.5, `R_ROOT_LOW` = 5.0, `FLARE` = 5.0,
`FLARE_TIP` = 4.0.

### Material and adhesive

- **PETG.** `SIGMA_ALLOW` = 50 MPa. Chosen over PLA for creep resistance under a sustained dead
  load and for the ~80 °C glass transition — the substrate is a dark painted band and gains solar
  heat. Every structural figure in this brief assumes it.
- **3M Scotch Extreme Mounting Strips 414H-ST**, 1 × 3 in (25.4 × 76.2 mm) each.
  The strip *length* equals the plate *width* exactly (both 3.000 in). The plate's 1.75 in height
  takes **one** strip with 0.75 in left bare; two strips need 2.00 in and overhang by 6.35 mm.
  So the bonded area with one strip is **3.00 in²**, not the 5.19 in² of the tape face — see the acceptance note
  on adhesive area, which reports the face and is not a gate.
  **Placement matters and is part of the instruction, not a detail.**

  > **Lay the full 1.00 in strip along the bottom of the plate and the 0.75 in trimmed strip along
  > the top, edges butted, the top strip's upper edge flush with the plate's top edge.** 25.4 +
  > 19.05 = 44.45 mm, so the two exactly fill the plate's height with nothing left bare.
  > **Nick the top strip's centre back to clear the witness notch** (the 4 mm wide × 2.5 mm deep V
  > at X = 0) so no tape spans the void and the notch stays open to sight through.

  That single instruction replaces two that could not both be obeyed. "Together covering the full
  1.75 in height" and "avoid ending a strip at the very top edge" are contradictory: if the bond
  reaches the top edge, then some strip's boundary **is** the top edge. **Coverage wins**, and not
  narrowly:

  - Backing the top strip off by the notch's 2.5 mm depth would sacrifice bonded height across the
    whole 76.2 mm width to protect 4 mm of it. Peel *stress* goes as `1/h²` (the bond's section
    modulus is `b·h²/6`), so `h` falling 1.750 → 1.652 in raises peel from **4.1 to 4.6 psi**:
    `(1.750/1.652)² = 1.12`, a 12% penalty everywhere.
  - Clearing the notch instead costs only the notch. Its footprint is a 4 × 2.5 mm triangle —
    **5 mm² of a 3387 mm² bond, 0.15%** — and nicking 1 mm proud of it all round (6 × 3.5 mm) is
    21 mm², 0.6%. It also disposes of the concern that motivated the original warning, whose
    mechanism runs in this order: the notch is a **full-thickness void**, so tape laid across it is
    stuck to the wall on one face and to nothing on the other; that unsupported flap is a **free
    tape edge**, and it sits at the top of the plate, which is exactly where the peel moment is
    highest; **a free edge at the peel front is where a peel begins.** Nicking the strip back clear
    of the notch removes the flap, so there is no free edge left there for a peel to start from.
  - The notch has to stay clear regardless. It exists because the tape is one-shot and the part
    cannot be slid once it touches the wall; tape laid over it blinds the only alignment feature
    the part has.

  Do not leave 0.75 in bare — the bare band is unsupported plate, and where a lone strip sits
  changes what it carries. That last point is **not** implied by the peel table (under Acceptance
  checks below, and FACTS §7f.2), though this brief used to claim it was: "the peel resultant swings
  roughly 2× depending on where it sits." Under that table's `S = b·h²/6` model the moment about the
  bond centroid is invariant to a strip's Z position, so its peel figures are a function of bonded
  *height* alone. The ~2× swing comes from a different idealisation — the plate pivoting rigidly
  about its bottom edge, where a strip's lever arm genuinely does depend on where it sits. Both
  models point the same way, so the instruction does not rest on which is right; it just must not be
  presented as a consequence of a table that does not say it.

  **The strips are rectangles and the plate's corners are `R_CORNER` = 6.0 mm arcs, so the strip
  corners hang over the arcs.** Laid as instructed the two strips span exactly 76.2 × 44.45 mm — the
  plate's bounding rectangle, the notch nick aside — and their straight edges land flush with the
  plate's straight edges, so the corners are the *only* place anything overhangs. Each overhang is
  the sliver between a 6 mm square and the quarter circle inside it: `r² − πr²/4 = (1 − π/4)·36` =
  **7.73 mm² per corner**, **30.9 mm² over the four** — the same `(4 − π)r²` = 30.90 mm² by which
  the rounded outline falls short of the full rectangle. Against the 3387 mm² face that is
  **0.91%**. It reaches 6 mm along each edge and stands at most `r(√2 − 1)` = **2.49 mm** proud at
  the diagonal. The arithmetic closes against the acceptance report: 3387.09 − 30.90 (corners)
  − 5.00 (the notch's 4 × 2.5 mm V) − 0.08 (24 segments per arc, `SEG_CORNER`) = 3351.1 mm², which
  is the `adhesive` line exactly.

  **It does not matter structurally — say so rather than dressing it up.** That 0.9% was never part
  of the bond (the reported 3351 mm² is already the rounded outline), and tape with no plate behind
  it carries no load. What it leaves is four tacky crescents of exposed adhesive at the plate's
  corners, which collect dust and show against a dark band. **Stick both strips to the plate first,
  then trim the four corners flush to the plate's outline before peeling the wall side** — the plate
  is its own template, and scissors are enough. If trimming is inconvenient, leave them; nothing
  depends on it.

  > `H_PLATE_CAP` = 50.8 mm is exactly 2.000 in — two untrimmed strips edge to edge, 6.00 in².
  > Recorded and **not recommended**: once the second strip is trimmed, raising `H_PLATE` buys only
  > a further 25% on peel, and costs a re-sweep of `R_ROOT`/`R_ROOT_LOW`/`ROOT_BLEND`/`FLARE`/
  > `FLARE_TIP` (see Parameters) plus a taller part.

## Coordinate system

- **Origin** at the centre of the plate's bottom edge, on the tape face.
- **+X** along the wall (also the bar's axis)
- **+Y** away from the wall (projection)
- **+Z** up
- The tape face is the plane **Y = 0**. All material sits at **Y ≥ 0**.

## Geometry

### Plate

- Rounded rectangle, `W_PLATE` × `H_PLATE`, corner radius `R_CORNER`.
- Extruded from `Y = 0` to `Y = T_PLATE`.
- Spans `X ∈ [−W_PLATE/2, +W_PLATE/2]`, `Z ∈ [0, H_PLATE]`.
- **The `Y = 0` face must be flat and planar. No texture, no draft, no fillet rolling onto it.**

### Saddle

- A **U-trough** whose axis is parallel to **X** (the bar lies along X).
- Trough radius: `R_TROUGH = D_BAR/2 + CLEAR`
- Rest point (lowest point of the trough): `Z = −H_DROP` — i.e. just **below** the plate's bottom edge.
- Trough axis at:
  - `Y_AXIS = Y_BAR` — the **measured** bar centre, 31.75 mm. `T_PLATE + D_BAR/2 + GAP`
    (= 16.03 mm) is only the theoretical *floor*, used when `Y_BAR` is `None`; the end brackets
    hold the bar at 1.98× that, and a saddle built to the floor never reaches it (FACTS §6.4).
  - `Z_AXIS = −H_DROP + R_TROUGH`
- Trough spans `X ∈ [−W_SADDLE/2, +W_SADDLE/2]`.
- Wrap the trough to roughly **160–180° of arc** (a cradle, not a tube). Do not close over the top.

  > **What the part actually delivers is ~187.5° at the nominal (180.2 / 194.9 on the H_DROP variants), and asymmetric: the front arm reaches 87.6° off
  > vertical, the back arm 99.9°.** These are measured and reported every run; do not trust a
  > figure quoted in prose over the one the acceptance report prints. `WRAP_DEG` clips the cradle disc at `Z_CUT`, but the convex hull
  > then drags anchor A0 — which sits well above `Z_CUT` — over the top of that clip and swallows it,
  > so the flat top the clip made never reaches the finished part. `WRAP_DEG` is a ceiling, not a
  > description. This is not a defect: the excess wrap sits *behind* the bar's rearmost tangent
  > (trough back at Y = 21.83 mm, bar back at Y = 22.23 mm), so it cannot block a vertical drop-in —
  > which is measured every run and passes with 0.400 mm of clearance. The 160–180° rule was a proxy
  > for "the bar must still go in"; that requirement is now measured directly and `mouth_rim()`
  > reports the wrap the part really has.
- Connect the trough back to the plate with a gusseted arm, minimum `T_WALL` everywhere on the load
  path, with a generous fillet at the root where arm meets plate — that root is the highest-stress
  region.

### The end closes — `FLARE_TIP`

`hull_solid`'s outermost ring is a **flat planar cut normal to X**. The branch collar
tapers its profile over the last `FLARE` mm and then the body simply stops: a square
end cap whose rim meets the arm's upper surface at 93°, measured as a single 5.46 mm
edge lying entirely in the plane X = 17.500. Anchoring the flare (below) nearly
doubled it, because the anchors are held at full depth — the cap went from 7.4 mm
tall to **13.6 mm**.

`FLARE_TIP` = 4.0 mm adds one more hull ring, eroded again by the same amount, so the
body closes down instead of being sawn off. Erosion equal to the X travel is exactly
the 45° rule, so it costs nothing to print. Cap height **13.56 → 4.43 mm** (−67%).

Eroding the anchors here costs no attachment: they sit at Y = 2.0, deep inside the
plate's ~7.3 mm face, so they are still buried when the cap closes — verified by
ray-casting the finished mesh, solid against the face through the whole run.

`FACE_PROBE_X` is **derived** from this, not chosen. It was hard-coded at 20.0 with a
comment reading "clear of the saddle (W_SADDLE/2 + FLARE = 17.5)", which stopped being
true the moment `FLARE_TIP` pushed the body to 21.5: the ray then struck the saddle
instead of the plate face and all three variants failed the swell checks. A probe in
the wrong place reported as a geometry defect — the second time in this file a
measurement has moved when the part did not.

### The flare erodes OUTWARD only

`FLARE` tapers the saddle's section over the outer 5 mm on each side, and it does it
by eroding the envelope profile. A uniform erosion shrinks the profile in *every*
direction — including backwards, away from the plate — so the collar used to pull
off the plate as well as getting smaller. Measured on the built solid, the saddle's
rear boundary stood **1.7 mm** clear of the plate face at X = 15.0, **7.2 mm** at
X = 16.0 and **15.4 mm** at the tip: a wedge of air behind the outer 3 mm of the
collar, and the 270° re-entrant corner where the tip's end cap met the plate.

The tip profile now puts the plate-side anchors back at full depth
(`hull2d(erode_convex(env, FLARE) + plate_anchors(g))`), so the collar stays
attached to the plate all the way out. Verified by ray-casting the finished mesh:
solid against the face at every station from X = 12.5 to 17.5.

This costs nothing in printability. The 45° rule only governs surfaces that *grow*
along the build direction; the plate-side edge now doesn't grow at all — it is a
vertical wall at 0°, the easiest thing an FDM printer does — while every outboard
surface still erodes at 45° exactly as before. The mid-air island it has to bridge
actually **fell from 13.2 to 7.9 mm²**.

### Structural fillets — where the cradle meets the plate

There are **two** re-entrant corners there, not one, and both are stress concentrations and places a
print peels. Both are blended with a **true tangent fillet**: for a corner at `P` whose two surfaces
leave along unit directions `u1`, `u2` separated by `θ`, the arc centre is `P + (r/sin(θ/2))·b` on the
bisector and the tangent points are at `P + (r/tan(θ/2))·u`. Nothing is assumed to be a right angle.

| | corner | measured `θ` | radius | why that radius |
|---|---|---|---|---|
| **upper** | arm's top face into the plate's **front** face | ~100.6° | `R_ROOT` = **13.5 mm** (17.72 available) | tension fibre of the arm root, and the corner the peel moment works on |
| **lower** | cradle's underside into the plate's **bottom** face | ~131.6° | `R_ROOT_LOW` = **5.0 mm** (5.21 available) | bounded by the `a1→a2` hull edge, which `ROOT_BLEND` sets |

Four things clamp each radius, all measured rather than assumed: plate face remaining above the
corner, surface remaining beyond it, the bar's rearmost surface at `Y = Y_AXIS − R_BAR` (anything in
front of that stands in the drop-in path), and the corner angle itself. The report prints what was
asked for **and** what the geometry carried, so a clamp is never silent.

**Neither radius is bounded by any of those, and neither buys any strength.** Bending SF is
**36.48 at Y = 26.52** on the nominal variant — the cradle's back wall under the bar, several
millimetres beyond the fillet's furthest reach; the run measures it per variant (41.36 / 33.04 at
`H_DROP` 0 / 4), so read it off the report rather than from here — and min wall 3.500, drop-in
0.4000, projection 45.348 and wrap-at-full-radius
(distinct from the *delivered* wrap; both are reported every run) are
bit-identical from `R_ROOT` = 8 to 16.

> Those absolute values are for `ROUND_R` = 0.5, set in iteration 6. `R_OUT` pays for the round-over
> up front, so halving the radius took 0.5 mm off the cradle wall and moved every one of them:
> at `ROUND_R` = 1.0 the same build read **SF 44.06 / 49.10 / 40.30**, min wall **4.000**, projection
> **45.849**. `T_WALL` = 3.0 is the gate and 3.500 clears it; the reserve above `T_WALL` is exactly
> `ROUND_R` by construction. What the row is claiming — invariance across `R_ROOT` — is unaffected. Total tip deflection is ~10 µm, against 46–253 µm from the
tape layer underneath. What the upper blend actually buys is **28% off the stress in the plate panel
above it** (0.769 → 0.556 MPa as its top edge moves Z = 18.0 → 24.6), ~6% off peak tape peel, and a
load path that spreads instead of stepping. It costs +3% volume.

What bounds `R_ROOT` is the **mouth ramp**, and it is monotonic. Re-swept 12.0–15.0 at 0.25 mm
across all three `H_DROP` variants after the FACTS §7i fix: **12.0 through 14.5 are clean**
(165 `[PASS]`, 0 `[FAIL]`), and 14.75 and 15.0 fail one check — `mouth ramp -Y` at 95.45° and
95.65° against its 89.1–93.7° bound, on `H_DROP` = 0. The mesh is *fine* at those radii; the
fillet has simply grown far enough into the mouth to push the ramp out of spec. 13.5 sits
mid-plateau with ~1 mm of headroom to a bound that degrades gradually and legibly rather than
cliff-edged. Still re-run all three variants if you move it.

> **This paragraph previously said the opposite and it is worth knowing why.** It read: *"What
> really bounds `R_ROOT` is mesh robustness, and it is not monotonic … 12.0, 14.25 and 14.75 fail
> while 12.5, 14.0 and 14.5 are clean … 13.5 is the centre of the only densely-verified plateau."*
> Those failures were real when measured, but two of the three — 12.0 and 14.25 — were the
> **null-debris class of FACTS §7i**, not geometry: coincident export-triangulation flaps, now
> removed at source. Once that was fixed the plateau turned out to be continuous and the true bound
> a plain geometric one. The "landmine" framing was an artifact of a bug in the exporter, and it had
> been steering the design away from radii that were never actually unsafe.

`ROOT_BLEND` was re-swept at the same time, 2.0–4.5 at 0.5 mm, and tells the same story from the
other end. It previously read *"2.5 builds non-manifold on all three, 3.0/3.5/4.0 are clean"*;
**2.5 through 4.5 are now all clean**, because 2.5's failure was that same debris class. Only 2.0
fails, and on a check that did not exist before §7i: **Euler characteristic 1** — odd, therefore
impossible for a closed orientable surface — with every edge nonetheless carrying exactly two
faces. That is a *single-vertex pinch*, two sheets meeting at a point, and it is the second
instance found (the other is `FLARE_TIP` = 3.0 on `H_DROP` = 0). Both are pre-existing and both
were **invisible to every check this file had before 2026-07-25**; neither affects a shipped value.
The lesson is the §7i lesson again: the parameter space was never as treacherous as the old map
implied, and the failures that remain are ones we previously could not detect at all.

Three things this replaced, each of which was actively harmful:

- **A right-angle blend.** The old fillet assumed a horizontal arm top meeting a vertical plate face.
  The arm's top edge actually falls ~6.5° and the swell leans the face, so the blend ran out onto the
  arm 0.46 mm above the surface at R = 4. Scaled to R = 8 that ledge would be 0.9 mm — the fillet
  would cut a new sharp corner as fast as it removed the old one.
- **A prism swept from one profile.** It filleted the middle 25 mm and left the 5 mm flare on each
  side raw, ending dead at X = ±12.5. The fillet is now **lofted**: every X station solves for its own
  corner, because the flare erodes the envelope and the crossing drops at every station.
- **A blend built on the tangent to a curved face.** Over the 6.7 mm the leg covers, the swell falls
  0.06 mm away from its own tangent, so the fillet finished *proud* of the face it dies into and the
  union left a feather ridge the full width of the part. The leg is now aimed along the **secant**, at
  the face where it ends. Nothing on the print would have shown 0.06 mm — but it is exactly the
  geometry an unclamped round-over cannot handle (see below).

The radius is full over the saddle's full-section width and then sheds **1 mm per mm of X** — the same
45° rule the flare obeys, because X is the build direction and a collar growing faster than 1:1 asks
the printer to bridge. Where the corner stops existing the last real one is held and the radius runs
out over its own length; the final ring is sunk behind the plate face so the loft caps inside solid
material rather than ending in a step. Net effect: the root footprint on the plate widened from
±12.5 mm to ±20.6 mm.

`Y_AXIS` is the **moment arm**, and it is a floor, not a target: the bar physically cannot sit closer
to the wall than `T_PLATE + D_BAR/2`. Don't try to "optimise" below it. Total part projection will
land around 46 mm, because `Y_BAR` is measured at 31.75 mm rather than derived; that's expected.

### Form

Four features that carry no load and are there for the hand and the eye. Each is measured off the
finished mesh every run, because a cosmetic feature that silently does nothing is the failure mode
this file has already been bitten by **twice**. Once when the round-over beveled at zero offset and
produced an identical part. Again, and unnoticed for four iterations, when `ROUND_MIN_EDGE_FRAC · R`
came out at 0.50 mm against 0.393 mm corner-arc links and the **plate's four corners shipped dead
sharp** while every check passed and the file's own comments called the exclusion a clean win —
FACTS §7h. Neither the spike count nor the fold count is gated, and no check anywhere asks whether a
chain the round-over was supposed to soften actually got softened.

- **Layer-aligned relief on the trough** (`LAYER_H` 0.2, `RIB_PITCH` 1.0, `RIB_WIDTH` 0.4,
  `RIB_DEPTH` 0.2). The part prints on its side, so layers stack **along the bar axis** and the
  trough's inner face is a vertical wall whose layer lines read as rings every 0.2 mm. The relief is
  24 shallow circumferential grooves pitched at **five layers**, each **two layers** wide, so every
  edge of the texture lands exactly on a layer boundary and the eye reads the grooves instead of the
  stepping. That alignment is derived, not asserted: print height is `x + W_PLATE/2`, and
  `W_PLATE/2 = 38.1 mm` is **190.5** layers at 0.2 mm, not 190 — half a layer of phase error would put
  every edge in the middle of a layer, which is the artefact the feature exists to hide. Every edge is
  snapped to a boundary and the run measures all 48 of them (0.0 µm error).
  - **Grooves, not ribs.** Cut *outward*; the land between them stays at the nominal trough radius, so
    the bar still drops onto the surface the fit was designed around and the 0.4 mm radial clearance
    is untouched. Ribs standing proud would halve that clearance and turn a drop-in into a press fit.
  - **`R_OUT` pays for `RIB_DEPTH` up front**, the same way it already pays for `ROUND_R`: the groove
    *floor*, not the land, is the thinnest section, and it is the floor that has to carry `T_WALL`.
    The wall is measured at two stations now — 3.700 mm on the land at X = 0, **3.500 mm on the groove
    floor** (4.200 / 4.000 while `ROUND_R` was 1.0; both stations move with the radius, because
    `R_OUT` = `R_TROUGH` + `T_WALL` + `ROUND_R` + `RIB_DEPTH`) — because every ray in this file is
    fired in the X = 0 plane and X = 0 is deliberately the
    centre of a land. One sweep would have measured the land forever and never looked at the groove.
  - Stops at `RIB_X_LIM` = 12.5 mm, which is not a style choice: past the full-section width the flare
    erodes the cradle and keeping `T_WALL` under a groove needs `|X| ≤ 13.5`.

- **Mouth lead-in chamfer** (`MOUTH_CHAM`, 0.8 mm at 45°, both lips). The round-over deliberately
  skips every trough-surface edge to protect the wall on the load path, which left the mouth a raw
  sawn rim. The rim is the free tip of the cradle arm, so the bending moment there is identically
  zero and relieving it costs nothing structurally. Cut geometrically, as a wedge swept along X —
  **not** as a `bmesh` bevel: the trough is a 192-facet prism and the arm's sloping top crosses it
  wherever it happens to, leaving a 0.08 mm sliver facet before the rim. A 0.8 mm bevel offset across
  that has nowhere to go; Blender swallowed the sliver, cut no chamfer at all, and left a 0.02 mm
  pucker proud of the trough that the wall rays then read as a 0.015 mm wall.
- **Swell graded in Z** (`BULGE`, `BULGE_FADE_Z`). The plate's front face is a shallow arc in X *and*
  a smoothstep fade in Z: full `BULGE` along the bottom edge where the arm leaves the plate and the
  peel moment is highest, nothing by the top edge, which carries almost none. A swell of constant
  section in Z is a cylinder about a vertical axis, not a branch collar. Built by lofting the trim
  lens ring by ring rather than extruding it — a convex hull would cut the concave half of the fade
  away as a chord.
- **Witness notch** (`NOTCH_W` × `NOTCH_D`, 4 × 2.5 mm V on the top edge at X = 0). VHB is one-shot,
  the part cannot be slid once it touches the wall, and it is symmetric with nothing else to sight
  along. The V goes through the full thickness so the pencil line on the wall can be seen through it
  while the plate is still held clear. It stays crisp on the tape side by construction: every edge it
  creates there has a vertex at Y = 0, which the round-over already excludes.

## Constraints

- **Watertight and manifold — *by position*, in the exported file.** Zero non-manifold edges, zero
  boundary edges, zero loose vertices, exactly one shell, Euler characteristic 2, zero degenerate
  faces. **Do not verify this in `bmesh` and stop there.** Blender counts faces per *topological*
  edge; STL is a triangle soup that a slicer welds *by coordinate*, so two coincident Blender edges
  read manifold there and non-manifold in the slicer. That gap shipped a file Bambu Studio refused
  while our own run reported 135 `[PASS]` and `non-manifold edges 0` — see FACTS §7i. The gate must
  parse the binary STL from disk after writing it, weld by position, and refuse *and delete* any
  variant that fails. `bmesh`'s topological answer may be printed beside it, labelled, but it is
  not the gate.
- **No degenerate geometry.** No zero-length edges, no coincident vertices.
- **The part must fit its own envelope.** `|X| ≤ W_PLATE/2`, `Z ∈ [Z_ENV_BOT, H_PLATE]`, `Y ≥ 0`.
  This is a gate because it was the one nobody wrote. The round-over has to run with
  `clamp_overlap` **off** — on, a single 0.005 mm boolean sliver clamps the whole operation to zero
  offset and silently produces an identical part — but off, an offset bevel slides each vertex along
  the intersection of its adjacent face planes, and where two of those are nearly parallel that
  direction is nearly undefined. The tangent fillets introduced exactly such faces, and two of the
  three `H_DROP` variants shipped STLs **3.9 mm and 12.3 mm** bigger than the part while all thirty
  acceptance checks passed, because not one of them looked at the bounding box. There are now three
  guards: `round_edges` asserts its own envelope cannot grow by more than the bevel radius; it
  refuses edges shorter than `ROUND_MIN_EDGE_FRAC · R`, edges whose adjoining faces are smaller than
  `ROUND_MIN_FACE · R²`, and edges folded past `ROUND_ANGLE_MAX`, none of which can carry the
  offset; and the bbox is an acceptance check in its own right.
  > Both `· R` bounds move with `ROUND_R` while the geometry they are compared against does not, so
  > **which chains they exclude is a property of the radius, not a fixed fact** — re-measure the
  > target set whenever `ROUND_R` changes. That is not a hypothetical: at `ROUND_R` = 1.0 the length
  > bound came out above the plate's whole corner-arc chain and left the four corners square
  > (FACTS §7h). The `ROUND_MIN_FACE · R²` bound now excludes nothing at all on any variant — the
  > seams it was written for are taken first by the fillet-footprint rule — so treat it as a backstop
  > rather than as the discriminator the older text described.
- Minimum wall `T_WALL` on the load path.
- Scene units: **metric, millimetres.** Set `unit_settings.length_unit = 'MILLIMETERS'`.
- Part sits at the world origin with identity rotation and scale. Apply all transforms.
  **This and the print orientation below are both true and do not conflict:** the scene object keeps
  its identity transform, and `export_stl` rotates a *throwaway copy* −90° about Y before writing.
  Do not rotate the scene object to achieve the print orientation — that moves the tape face off
  `Y = 0` and invalidates check 1's planarity, the `FACE_PROBE_X` rays and the `Y ≥ 0` envelope.
- Name the object meaningfully. No `obj_0`.
- Smooth curves — the trough should not read as faceted. Use enough segments.

## Print orientation

Export with the part oriented to print **on its side** — an X-normal face on the bed, so layer lines
run **along the bar axis (X)** and the Y–Z profile lies within the layer plane.

This matters: the saddle arm is loaded in bending in the Y–Z plane. Printed tape-face-down, that
bending would pull directly across layer lines at the arm root, which is where FDM parts fail. On
its side, the bending is carried within layers. It also prints without supports.

## Deliverables

1. `saddle_gen.py` — the generator script, parameters at the top, runnable start to finish.
2. `saddle.blend` — saved, not left in RAM.
3. STL exports of the **variant set**:
   - `saddle_h-2.stl`, `saddle_h0.stl`, `saddle_h+2.stl` — `H_DROP` at 0, 2, 4 mm

   > **State plainly what the variant set hedges, because it is narrower than it looks.** The three
   > STLs bracket `H_DROP` = 2 mm by **±2 mm**, and that is a hedge against **placement** error —
   > how precisely the plate ends up stuck on the band, and how much lift the sag actually wants.
   > It is **not** a hedge against the unit ambiguity in FACTS §6.1, where the owner's "~2m below
   > the base" is read as 2 mm but could be 2 cm. If it is 2 cm the right `H_DROP` is 20 mm — 16 mm
   > beyond the widest variant printed — so **all three STLs are scrap**, and the saddle arm has to
   > grow by ~18 mm. Settle §6.1 before printing. The variant set cannot cover for it, and printing
   > three of the wrong part is not a hedge.
   - ~~`fitgauge.stl`~~ — **no longer a deliverable.** `D_BAR` is confirmed, so the gauge has done
     its job; it is switched off by `DO_GAUGE = False` and can be switched back on if the diameter
     is ever doubted. Was: a small flat comb with semicircular notches at 19.0, 20.6, 22.2, 23.8 and
     25.4 mm, each labelled with embossed text, for identifying the real bar diameter by trying it
     against the bar.

## Unverified assumptions — flag these, don't hide them

`D_BAR` and `H_DROP` are **estimates, not measurements**:

- ~~`D_BAR = 22.0` is a photo-derived estimate.~~ **RESOLVED**: confirmed by the owner at
  **19.05 mm** (3/4 in) on 2026-07-25. The old estimate was 2.95 mm too large. FACTS §5.
- `H_DROP = 2.0` is inferred from an ambiguous note ("~2m below the base"). Could plausibly be 20 mm.

Build with the defaults, but structure the script so both are one-line changes, and **state clearly
in your final message that these two numbers are unconfirmed.** Do not present the output as
dimensionally final.

## Acceptance checks — run these and report actual numbers

Report each as a measured value, not an assertion:

> **`saddle_gen.py`'s own `acceptance()` list is the specification of record — 55 checks per
> variant, 165 across the three, every one comparing a *measured* number against an expected one.**
> (45/135 until 2026-07-25; the positional-STL gate of FACTS §7i added 8 per variant and converted
> the manifold/boundary/shell trio from topological to positional.)
> The eight below are the original hand-written list and are kept for intent only. They are not the
> gate, and several could not be one as written: this section previously said "minimum edge length
> > 0", which cannot fail in floating point, and listed the adhesive area as a criterion when it
> has no pass condition. Where the two disagree, the code wins.

1. Tape face measures **76.2 × 44.45 mm** within ±0.002 mm, and every vertex on it has `|Y| = 0`
   exactly (`tape face planarity`, measured as max |Y| over the Y=0 loop — it must be 0.0, not
   merely small, because the bevel is forbidden from touching that face at all).
2. Plate height **≤ 50.8 mm**.
3. Lowest point of the trough is at `Z = −H_DROP`, sampled at **X = 0**, which is deliberately the
   centre of a relief *land*. At a groove floor it is `−H_DROP − RIB_DEPTH`; both are correct and
   the station decides which you measure.
4. Trough axis Y equals **`Y_BAR`** (31.75 mm), *not* `T_PLATE + D_BAR/2 + GAP`. The old wording
   inverted this gate — it would have failed the corrected geometry and passed a part that misses
   the bar entirely.
5. Mesh, **measured on the exported STL after welding by position, not in `bmesh`**: 0 non-manifold
   edges, 0 boundary edges, 0 loose verts, 1 shell, Euler characteristic 2, 0 degenerate faces,
   consistent winding, volume > 0. A variant failing any of these is refused and its file deleted.
   See FACTS **§7i** for why the topological form of this check passed a file the slicer rejected.
6. Minimum edge length **> `MIN_EDGE_OK` = 2.0 × 10⁻³ mm**. Note this still does not catch faces
   folded back on themselves; those are counted and reported separately (`folds`) and are not
   currently gated — see FACTS **§7g**. (This cited §7c until 2026-07-25; §7c is the
   `clamp_overlap` / envelope-growth guard, a different defect entirely.)
7. Minimum wall on the load path ≥ `T_WALL`, swept radially from the trough surface over the
   full-thickness arc, at **two X stations**: X = 0 (a land) and the centre of a groove. One
   station would measure the land forever and never look at the groove floor, which is the
   thinner section.
8. Adhesive contact area — **report only, not a gate.** It reports the tape *face* (5.19 in²),
   which is not the bonded area: with 3M 414H-ST strips the bond is 3.00 in² (one strip). No
   allowable is asserted, because creep — not peak strength — is what fails taped mounts, and that
   is a property of the chosen product and substrate rather than of this geometry.

Load sanity, for reference — the design case is < 10 lb total, of which this part carries perhaps
5 lb. At the **confirmed** moment arm of `Y_BAR` = 31.75 mm — not the 17.5 mm the retired
`D_BAR` = 22.0 formula gave — a 5 lb design case puts **6.3 in·lbf** into the bond.

What that costs depends entirely on how much tape is actually stuck down, and peel goes as the
**square** of the bonded height because it is a bending problem (`S = b·h²/6`):

| bond | area | shear | **peel** |
|---|---|---|---|
| one 414H-ST strip (1.00 in) | 3.00 in² | 1.67 psi | **12.5 psi** |
| one full + one trimmed to 0.75 in | 5.25 in² | 0.95 psi | **4.1 psi** |
| two full strips, `H_PLATE` = 50.8 | 6.00 in² | 0.83 psi | **3.1 psi** |

**Stick two strips, trimming the second to 0.75 in.** That fills the plate's full 1.75 in height,
takes the bond to the whole tape face, and cuts peel by 3× — with **no change to the part at all**.
Where each one goes, and what to do about the witness notch, is spelled out under *Material and
adhesive* above; that placement is part of the instruction, not a refinement of it.
Raising `H_PLATE` to 50.8 buys only a further 25% on peel and costs a re-sweep of the empirical
constants plus a taller part; it is not worth it once the strip is trimmed.

Check the result against the 414H-ST **long-term static** rating before printing. Creep, not peak
strength, is what releases taped mounts over months.

> The old text here read "~1 psi shear. Comfortable. If your geometry pushes the moment arm much
> past ~20 mm, something has gone wrong." Both halves were wrong after `D_BAR` was confirmed: the
> shear divided by the tape *face* rather than the bond, and the 20 mm tripwire fires on the
> **correct** part, since the real arm is 31.75 mm. Same inversion as acceptance check 4 — caught
> in the check, missed in the prose.

## Do not

- Add a hook, curl, lip, clip, or any lift-out retention.
- Add screw holes, counterbores, or slots.
- Exceed 50.8 mm plate height.
- Round, chamfer, or texture the `Y = 0` tape face.
- Hand-edit vertices. If it isn't generated from the parameters, it doesn't belong in the script.

# Shade Bar Mount — Project Memory

**Status:** **Built and verified.** `saddle_gen.py` generates the part parametrically;
`saddle.blend` is saved; four STLs exported. Bar diameter is now **confirmed at 3/4 in**.
The one binding unknown left is cradle height (`FACTS.md` §6.1) — hence the three `H_DROP` variants.
**Last reviewed:** 2026-07-25 (via `blender-mcp` against the live Blender session)
**Owner:** chrismandich

> **Measured reality lives in [`FACTS.md`](./FACTS.md)** — that file governs. This file describes the
> model and the plan. Where they disagree, `FACTS.md` wins.

---

## 1. Purpose

A **3M-taped mid-span support that lifts a sagging shade bar back to level.**

It is an *addition*, not a replacement — the existing end brackets stay, and they capture the bar.
This part therefore only has to **push up**. Plate envelope 3 in × < 2 in; total load < 10 lb.

## 2. Current content of the scene

Live Blender session, **Blender 5.2.0 LTS**. Three objects: `Light`, `Camera`, `obj_0`.

| Property | Value |
|---|---|
| `.blend` file path | **empty — the file has never been saved** |
| Scene units | Metric, `scale_length = 1.0`, display unit **METERS** |
| Mesh objects | 1 (`obj_0`) |
| Materials | 1 on the part: `color_2829873`, base colour `(0.169, 0.180, 0.192)`, roughness 1.0, metallic 0.0 — placeholder grey |

### `obj_0` — the mount

| Metric | Value |
|---|---|
| Bounding dimensions | **76.19 × 47.69 × 44.69** (nominal units; intended mm — see §4.1) |
| Topology | 2321 verts / 6963 edges / **4642 triangles** (0 quads, 0 n-gons) |
| Watertight? | **Yes** — 0 non-manifold edges, 0 boundary edges, 0 loose verts, 1 shell |
| Volume | 39,497.6 mm³ (≈ 39.5 cm³) |
| Surface area | 10,331 mm² |
| Object transform | loc `(3.764, −25.719, −8.617)`, rot `X = +90°`, scale `1.0` |
| Modifiers | none |
| Shading | flat |

### Form (from ortho views + a 1 mm cross-section at mid-span)

- A **flat mounting plate / back wall**, ~13 mm thick, running the full 47 mm height, thickening to
  ~21–25 mm where the hook root meets it.
- A **J-hook / claw** curling off the plate, forming an open cradle.
- Cradle inscribed diameter **≈ 18 mm**.
- Hook throat (entry gap) **≈ 18 mm** — i.e. the same as the cradle, so there is **no retention lip**.
- Hook arm tapers to **≈ 2 mm** at the tip (measured at 1 mm sampling — verify).
- The part is ~71% mirror-symmetric about its length mid-plane; symmetry is approximate, not exact.

## 3. Provenance signals

`obj_0` naming, `color_2829873` material, 100% triangles, uneven edge density (median 1.55 mm,
max 48.4 mm), and a `+90° X` rotation (Y-up → Z-up conversion) all indicate an **imported or
generated mesh**, not natively CAD-modelled geometry. There is no parametric history to edit.

## 4. Findings from the review

### 4.0 Resolved by the 2026-07-25 photo set

- **Units — settled as millimetres.** The model's 76.19 mm length is exactly 3.000 in. Set the scene
  to mm and stop treating this as open.
- **Fastener holes — not needed, and the earlier "blocking" finding is withdrawn.** The mount is
  **3M-taped**, not screwed. The absence of holes is correct, not a defect. What the design needs
  instead is *adhesive area and a short moment arm* — see §4.4.

### 4.1 Blocking — resolve before any further modelling

1. **The file is unsaved.** `bpy.data.filepath` is empty. All work is currently in RAM only.
2. **Cradle size is unverified against the real bar.** 18 mm in the model; bar estimated at ≈22 mm,
   range 19–25. See `FACTS.md` §5.
3. **Cradle height is unspecified.** A drop-in mid-span support sitting too low never contacts the
   bar and does nothing. See `FACTS.md` §6 — the likeliest way this part fails at its job.
4. **The hook curl is unnecessary and should be deleted.** The end brackets capture the bar, so this
   part only pushes up. See `FACTS.md` §7.

### 4.1b Withdrawn — "wrong envelope"

The draft's tape face measures **76.19 × 44.45 mm = 3.000 × 1.750 in exactly** — precisely the
3 in × <2 in specified. The footprint was never wrong; only the projection and the hook geometry
are. Earlier concern retracted.

### 4.2 Should fix

5. ~~**No retention.**~~ Withdrawn — drop-in is correct here, the end brackets capture the bar.
6. **Thin hook tip (~2 mm).** Marginal in FDM plastic, and the load path runs across print layers.
   Disappears once the curl is deleted (§4.4).
7. **Degenerate geometry.** Minimum edge length is 0.000 and ~84 verts are coincident within 0.1 mm.
   Harmless in the viewport, a source of slicer errors on export.
8. **Faceted curves.** The hook curve is visibly polygonal at this resolution.

### 4.4 The real design problem — revised with the load number

Measured: tape face **4.86 in²**, cradle centre **32 mm (1.26 in)** forward of the wall.

| Load | Tipping moment | Peel force, top edge | Avg shear |
|---|---|---|---|
| 5 lb | 6.3 in·lbf | 3.6 lbf | 1.03 psi |
| 10 lb | 12.6 in·lbf | 7.2 lbf | 2.06 psi |

**The adhesive is comfortable, not marginal.** With < 10 lb the peel concern raised earlier is not
the binding constraint. Verify against the chosen 3M product's *long-term static* rating — creep
over months, not peak strength, is what fails adhesive mounts.

The binding constraints are instead **cradle diameter** and **cradle height** (`FACTS.md` §5, §6).

Deleting the hook curl (§4.1 item 4) pulls the moment arm from 32 mm toward ~15 mm, halving every
number above, removing the thin tip, and removing the overhang that complicates printing.

Every one of those needs a number from `FACTS.md` §8 before it can be set.

### 4.3 Housekeeping

9. Object is named `obj_0`; material is `color_2829873`.
10. Origin sits off the geometry and the part floats below the world ground plane
    (world Z −59.5 → −11.8) with a baked-in 90° rotation. Bad starting state for export or printing.

## 5. Rough print estimate

At 1 unit = 1 mm and solid PLA (1.24 g/cm³): **≈ 49 g** of material, so roughly **20–25 g** at
typical wall/infill settings. Not a constrained print; material cost is not a design driver here.

## 6. GOAL (v4 — committed)

> **Build, print, and install a 3M-taped mid-span saddle that removes the visible sag from the shade
> bar — modelled parametrically from `FACTS.md`, so any dimension that turns out wrong is a
> one-number edit and a reprint, not a remodel.**

### 6.1 Route: (b) build new, parametrically — not (a) adjust the existing mesh

The draft contributes exactly one thing worth keeping: the **3.000 × 1.750 in plate footprint**.
That is a rounded rectangle — seconds to recreate. Everything else must change: the hook curl is
deleted, the cradle moves below the plate's bottom edge, the cradle diameter is re-cut, and the
whole front face is replaced.

Against that, the draft is a 4,642-triangle traced mesh with **no parametric history**, degenerate
zero-length edges, and visibly faceted curves. Editing it means pushing triangles by hand, and every
"what if the bar is 25 mm not 22 mm" question means doing it again.

**Decision: rebuild as a Blender Python script** driven by the parameter table below. The script is
the deliverable alongside the STL. Height and diameter variants then cost one number and a re-run,
which is what makes §6.4's variant strategy affordable.

The existing `obj_0` is kept as a visual reference until the rebuild is dry-fitted, then dropped.

### 6.2 Parameter table — the model's entire input

| Param | Meaning | Value | Source |
|---|---|---|---|
| `W_plate` | Plate width | **76.2 mm** (3.000 in) | `FACTS.md` §3.1 |
| `H_plate` | Plate height | **≤ 50.8 mm** (2.000 in) hard cap; start at 44.45 mm (1.75 in) | §3.1–3.2 |
| `T_plate` | Plate thickness | ~5–6 mm, match existing bracket | §4.3 |
| `D_bar` | Bar diameter | **19.05 mm (3/4 in) — CONFIRMED** | §5 — settled 2026-07-25 |
| `Y_bar` | Bar centre depth from tape plane | **31.75 mm (1.250 in) — MEASURED INPUT** | §6.4 — not derived; the end brackets fix it |
| `H_drop` | Rest point below plate's bottom edge | **≈2 mm** | §6.1 — **unit assumed, confirm** |
| `Profile` | Saddle cross-section | **U-trough**, `R = D_bar/2 + 0.4` | see note below |
| ~~`Y_bar` derived~~ | ~~= `T_plate` + `D_bar/2` + 1 mm gap~~ | **superseded** — see the measured row above | this assumption cost a rebuild |
| `W_saddle` | Saddle width along the bar | 25 mm | design choice |

Derived: bar centre sits `D_bar/2 − H_drop` **above** the plate's bottom edge (≈9 mm at the assumed
values) and **≈17.5 mm forward** of the tape plane — versus 32 mm in the draft, so **the tipping
moment roughly halves**. Overall part projection lands ≈30 mm; the *moment arm* is the number that
matters, not the silhouette.

> **Correction (supersedes §4.4's "target ≈18 mm projection").** That figure conflated bar-centre
> depth with overall projection. The bar cannot sit closer than `T_plate + D_bar/2` to the wall, so
> ~17.5 mm is a floor, not a target, and total projection is necessarily ~30 mm.

> **Profile changed from V-notch to U-trough.** The V was recommended when the model was going to be
> hand-edited and `D_bar` might stay unknown — its virtue was tolerating any diameter. Going
> parametric removes that virtue (you measure, then regenerate) and exposes its cost: in a 90° V the
> bar centre sits `0.707·D` above the apex, so **bar height varies with diameter** — coupling the
> one dimension we're unsure of to the one that decides whether the sag is fixed. A U-trough puts
> the centre at exactly `D/2` above the rest point. Lateral self-centring, the V's other benefit, is
> worthless here because the end brackets already locate the bar.

### 6.3 Success criteria, in priority order

1. **The sag is gone.** Bar level at mid-span with the shade hung. A beautiful part that doesn't
   contact the bar is a failure.
2. **It stays up.** No adhesive creep or peel over 30 days under continuous load.
3. **It fits the envelope.** Tape face 3 in wide, **≤ 2 in tall**, projection as short as the bar allows.
4. **It fits the bar.** Saddle seats the real diameter without slop or forcing.
5. **It's printable and sound.** Watertight, no degenerate geometry, ≥ 3 mm wall on the load path,
   oriented so layer lines don't run across the saddle root.
6. **It's reproducible — as a *solid*, not as a *file*.** Script + `.blend` + STL in this repo; every
   dimension traceable to `FACTS.md`. Note the limit precisely: re-running the unedited script
   reproduces the same solid — identical unique vertex set, volume and measurements — but **not the
   same STL bytes**. Triangle emission order and the diagonal chosen on some planar quads both vary
   run to run, so `md5` of a shipped STL carries no signal. Compare the `vertex-set md5` the run
   prints. See `FACTS.md` §7j.

### 6.4 Variant strategy

Because `D_bar` and `H_drop` are both still assumptions, the first print is a **set**, not a part:
three `H_drop` variants (−2 / 0 / +2 mm) and, if the bar isn't measured first, a small **fit gauge**
— a comb with notches at 19.0 / 20.6 / 22.2 / 23.8 / 25.4 mm. Minutes of print time, and it
converts two open questions into an answer you can hold.

### 6.5 Non-goals

Retention or capture (the end brackets do that); matching the existing bracket's appearance;
supporting bar sizes other than the measured one; CAD-grade surfacing.

## 7. Next actions

**Owner, two measurements** (`FACTS.md` §5, §6):

1. Bar diameter by paper-strip: wrap, mark, measure, ÷ π.
2. Bar-centre height at an end bracket, measured down from the top edge of the header band.

**Can start now, unblocked** — the parametric rebuild does not wait on the measurements, because
the measurements are *inputs* to it:

3. Save the `.blend` into this repo — the draft is currently RAM-only.
4. Set scene units to millimetres.
5. Write the generator script against the §6.2 parameter table, with the assumed values as defaults.
6. Generate, verify watertight, confirm the tape face is 3.000 × 1.750 in and projection ≈18 mm.

**After the two numbers land:**

7. Update `D_bar` and `H_drop`, re-run, export the §6.4 variant set.
8. Dry-fit, then commit tape. Re-check level at 24 h and 30 days.
9. Record the as-built numbers back into `FACTS.md` and retire `obj_0`.

---

_All measurements in §2 and §4 were read from the live Blender session on 2026-07-25 via
`blender-mcp`. Cross-section figures (cradle, throat, arm thickness) come from a 1 mm-resolution
inside/outside sampling at the mid-span slice and carry ±1 mm uncertainty._

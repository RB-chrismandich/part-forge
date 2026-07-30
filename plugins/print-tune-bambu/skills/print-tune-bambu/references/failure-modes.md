# Failure modes → the lever that fixes them

Organized by what the user actually says, because that is what you get handed.
Each entry names the mechanism first -- if the mechanism does not match the case
in front of you, the listed setting will not help either, and you should keep
looking rather than turn the knob anyway.

Ordering within each entry is deliberate: the first fix is usually the one with
the best cost/benefit, and the later ones cost time, material, or finish.

---

## Triage first: "droopy" and "messy" name four different mechanisms

Sagging, ragged and blobby extrusion is the one symptom vocabulary that maps to
several unrelated causes, and the fix for one of them actively worsens another.
Settle which mechanism you have before reading any entry below. The evidence that
discriminates is **where on the part it happens**, not what it looks like.

| Where it happens | Mechanism | Entry |
|---|---|---|
| Underside of a sloped face | Unsupported rope sags before it freezes | "Overhangs are drooping / curling" |
| Flat ceiling spanning two anchors | Span under tension, sags in mid-flight | "The bridge sags" |
| Rim of a narrow groove, slot or raised rib | Feature narrower than two line widths; walls overlap and over-extrude | "Engraved detail prints ragged" |
| Everywhere, uniformly | Wet filament, too hot, or over-extruding | "Layers are separating", `materials.md` |

The single most useful question: **is the surface right next to the damage
clean?** Temperature, moisture and cooling are global -- they cannot wreck one
groove and leave the skin two millimetres away flawless. A local defect has a
geometric cause, and turning up the fan will not touch it.

---

## "It broke / it needs to be strong"

**Mechanism.** FDM parts are laminated. Within a layer, strength is roughly the
filament's own; across layers it is the strength of a partial weld, typically
40-70 % of that. So the load path relative to the layer plane dominates every
setting you could change.

1. **Reorient so the load runs along the layers, not across them.** Free, and
   worth more than every setting below combined. Say this first when it applies.
2. `wall_loops` 2 → 4-6. Walls are continuous extrusions carrying load in-plane;
   this is the best strength per gram and per minute available.
3. `sparse_infill_density` 15 % → 30-40 %, and only after walls. Past ~40 % you
   are paying a lot of time for a little stiffness; solid is almost never right.
4. `sparse_infill_pattern` → `gyroid` (isotropic, good under multi-axis load) or
   `cubic`. `grid` is stiff in-plane but weaker diagonally.
5. `infill_wall_overlap` 15 % → 25-30 % so the infill actually bonds to the walls
   instead of resting against them.
6. Filament side: raise `nozzle_temperature` 5-10 °C and cut cooling. Hotter and
   slower welds layers better. This is the highest-leverage change for Z strength,
   and it lives in the filament preset -- easy to overlook.
7. `layer_height` down slightly -- more layers means more interfaces but each weld
   is better and the cross-section is more uniform. Modest effect; do it last.

## "It has to hold water / be airtight"

1. `wall_loops` ≥ 4 and `bottom_shell_layers` ≥ 5 -- leaks are almost always
   through walls, not infill.
2. `sparse_infill_density` ≥ 25 % so top layers have something to bridge onto.
3. `layer_height` 0.20 → 0.12-0.16. Thinner layers squash together better.
4. Consider `spiral_mode` for a simple open vessel: one continuous wall with no
   seam at all, which is as watertight as FDM gets. Only works for single-wall,
   no-top geometry.
5. PETG holds water better than PLA -- it is less brittle and less porous at the
   seam. Worth raising as a material suggestion.

## "Overhangs are drooping / curling"

**Mechanism.** An unsupported extrusion is a rope of hot plastic. It sags until
it freezes. Cooling and time-at-temperature are the levers; supports are the
fallback when geometry leaves no choice.

1. `overhang_2_4_speed` / `overhang_3_4_speed` / `overhang_4_4_speed` down
   (stock 50/30/10 mm/s → 30/20/10). Confirm `enable_overhang_speed` is 1 and
   `detect_overhang_wall` is 1, or none of it applies.
2. Filament side: `overhang_fan_threshold` and `fan_max_speed` up. PLA tolerates
   100 % fan; ABS/ASA/PC do not, and forcing it there causes layer splitting --
   which is why the same fix helps one material and ruins another.
3. `support_threshold_angle` 30 → 20-25 only if you actually want more supports.
4. `support_type` `tree(auto)` for organic/curved overhangs -- less contact, easier
   removal, less scarring. `normal(auto)` under flat shelves where tree branches
   would have nothing to grip.
5. Reorient. A 45° rotation frequently deletes the problem outright.

## "The bridge sags"

1. `bridge_flow` 1 → 0.9-0.95. Less plastic in a span that has nothing to rest on.
2. `bridge_speed` up a little (50 → 60-80). Faster spans stretch and cool before
   they can sag -- the opposite of the overhang fix, because a bridge is anchored
   at both ends and under tension.
3. Filament side: full cooling over the bridge layer.
4. `internal_bridge_support_thickness` for internal bridges over infill.
5. `max_bridge_length` > 0 to force supports beyond a span you do not trust.
   `inspect_model.py` reports the actual longest span, so use that number.

## "Engraved detail prints ragged" -- panel lines, narrow slots, fine ribs

Reported as drooping, curling, whiskery or "messy" extrusion along engraved panel
lines and around recessed detail, on a part whose flat surfaces came out clean.
Scale-model hull panels, greebles, engraved text and inset logos are where it
shows up.

**Mechanism.** A groove has two facing walls and the slicer must fit a perimeter
on each one. At a 0.4 nozzle `outer_wall_line_width` is 0.42 mm, so a groove
narrower than about 0.85 mm has nowhere to put two walls without overlapping
them. `wall_generator` is `classic` in every stock Bambu preset -- traced to
`fdm_process_common.json`, the root of the chain -- and classic has no
variable-width path, so it lays both walls anyway. The surplus plastic has
nowhere to go but up: it climbs the rim, curls, and beads. A raised rib fails by
the mirror-image arithmetic, and with `detect_thin_wall` at its stock `0` a rib
under one line width is dropped rather than thinned.

This is a **resolution** failure, not a thermal one, and the tell is in the
triage table above: the skin a millimetre away is perfect.

1. **Measure the groove and rib widths.** Every choice below turns on this, and
   it is the number nobody has. If there is a model, `inspect_model.py` reports
   it directly under `narrow_features` -- no calipers, no photograph:

   ```bash
   S="${CLAUDE_PLUGIN_ROOT}/skills/print-tune-bambu/scripts"
   python3 "$S/inspect_model.py" --pretty part.stl --line-width 0.42
   ```

   Read `pct_of_wall_area`, not `min_mm`. A chamfer is a gap that closes, so the
   minimum tends to the floor on anything with a bevel and says nothing; the
   share of wall area sitting in the failing band is what scales with how much
   of the part comes out wrong. Under a few percent is a face tapering to an
   edge and is inherent to the shape. The comb fixture scores 23 %; the saddle
   scores 0.4 %.

   Against a 0.42 mm outer wall: under ~0.45 mm the feature cannot be resolved
   at all; 0.45-0.85 mm is the ragged band this entry describes; over ~0.9 mm it
   prints clean with no settings change. Bambu reach the same floor from the
   other side -- their PLA guidance says to thicken thin walls to ≥ 1 mm on
   complex models.

   The slicer will confirm it independently: `slice_check.py features` reports
   `Gap infill`, which is Studio's own verdict that it could not fit two walls.
   On a fixture whose slots are known to be too narrow it reaches 59 % of all
   extrusion, over exactly the z range `inspect_model` flags geometrically.
2. **Scale the model up, or decide to lose the detail.** The honest first answer
   when the feature is under the floor. Scaling a panel 1.25× moves a 0.7 mm
   groove to 0.88 mm and the problem disappears with no preset at all. Say this
   plainly rather than tuning around a feature the nozzle cannot draw.
3. `wall_generator` `classic` → `arachne`. The only setting that addresses the
   mechanism: arachne varies line width to fit the space instead of overlapping
   two fixed-width walls. Two things must be said out loud whenever you recommend
   it. It is a **whole-part** change, not a local one. And Bambu document four
   regressions against it -- seam placement, perimeters generated floating in air,
   visible slicing flaws, and uneven surfaces -- at
   `wiki_sync.py show software/bambu-studio/WallGenerator`. Its two knobs,
   `min_bead_width` and `min_feature_size`, decide what happens to a feature
   below one line width: widen it to a printable bead, or drop it. Studio's
   built-in defaults are 85 % and 25 % of line width, but **no stock preset sets
   either**, so `get` will not return them -- do not quote them as stock values.
   A/B the change with `slice_check.py compare` rather than asserting it.

   Worth knowing when the wiki and the preset appear to contradict each other
   here, because both are right. Studio's *compiled* default is still `arachne`,
   exactly as the 1.7.1 release note says. Every stock preset from every vendor --
   Bambu's own included -- then forces it back to `classic` at the root of the
   chain. The release note describes the code; `trace` describes what you are
   actually running, and only one of those slices your part.
4. `detect_thin_wall` 0 → 1 so ribs narrower than a line are printed rather than
   dropped. Helps positive detail; does nothing for grooves.
5. `reduce_crossing_wall` 0 → 1 for the fine whiskers spanning an open groove.
   Those are travel moves, not the wall defect, and they are a separate cause
   sharing one photograph.
6. A **0.2 nozzle** -- a different base preset and a different filament preset,
   not a tweak. It moves the floor to roughly 0.4 mm and is the real fix for
   model-scale detail, at a large cost in time.

**What does not work, and gets recommended anyway.** Nearly every generic answer
to a photograph of this defect reaches for supports, cooling and nozzle
temperature. None of them engage the mechanism:

- **Supports.** The groove walls are vertical; there is nothing to support. Were
  there, support inside a sub-millimetre slot could never be removed.
- **More fan, lower nozzle temperature.** Global levers against a local defect.
  They spend layer adhesion across the whole part to treat thirty microns of
  surplus extrusion in one groove.
- **Slower overhang speed.** `overhang_*_speed` only fires on walls Studio has
  classified as overhang, and it grades by *percentage of line width unsupported,
  not by angle* (see `settings-map.md`). A vertical groove wall is 0 % unsupported
  and never enters the band, so those settings are inert here at any value.
- **Reorienting.** On a panel whose entire purpose is the detailed top face, a
  rotation trades a good surface everywhere for a marginal gain in one groove.
  Orientation is the first lever for a structural overhang and the wrong one here.

## "The first layer won't stick / corners lift / it warped"

**Mechanism.** Warping is differential shrinkage: the part cools and contracts
unevenly and peels itself off the plate. Adhesion aids fight the symptom; heat
management fights the cause.

1. `brim_type` → `outer_only`, `brim_width` 5 → 8-10 for tall or small-footprint
   parts. `inspect_model.py` gives bed contact area; under ~100 mm² a brim is
   nearly always right.
2. `initial_layer_print_height` 0.2 → 0.25 and `initial_layer_line_width` 0.5 →
   0.6: more squish, more contact.
3. `initial_layer_speed` 50 → 30.
4. Filament side and more important for ABS/ASA/PA/PC: raise `chamber_temperature`
   and cut cooling on the first layers. On the H2D the active chamber heater is
   the real fix -- settings alone will not save a large ABS part in a cold chamber.
5. `elefant_foot_compensation` if the base is *splaying* rather than lifting;
   that is over-squish, the opposite problem, and more brim makes it worse.
6. Physical, not slicer: clean plate, right plate for the material, glue stick for
   PETG (which otherwise bonds to smooth PEI hard enough to chip it).

## "Layers are separating / it delaminates"

1. Filament side first: `nozzle_temperature` up 10 °C, `fan_max_speed` down.
2. **Dry the filament.** PA, PC, PETG-CF, PPS-CF absorb moisture fast, and wet
   filament produces exactly this failure plus stringing and a rough surface.
   No slicer setting substitutes for drying.
3. `chamber_temperature` up for ABS/ASA/PC/PA -- slower cooling means a better weld.
4. `layer_height` down slightly.
5. Slow `inner_wall_speed` / `outer_wall_speed`; more time at temperature.

## "The surface looks bad"

Match the fix to which surface:

- **Top surfaces pillowing or rough:** `top_shell_layers` 5 → 6-7,
  `sparse_infill_density` up so tops have support, `top_surface_pattern` →
  `monotonic`, `ironing_type` → `top` for a glassy finish (slow).
- **Vertical wall banding / ringing:** `outer_wall_speed` and
  `outer_wall_acceleration` down (200 → 120, 5000 → 2000-3000). Check the part is
  not tall and skinny -- `inspect_model.py` reports aspect ratio; above ~4:1 the
  part itself is ringing and no speed setting fully fixes it.
- **Visible seam:** `seam_position` → `back` if there is a hidden side,
  `seam_slope_type` → `external` (scarf seam) to ramp it away,
  `wall_infill_order` → outer wall last.
- **Blobs and zits:** `reduce_crossing_wall` → 1, and check retraction on the
  filament side.
- **Scarring from travel:** `reduce_crossing_wall` → 1.

## "It's too slow"

Only after establishing what may be traded away.

1. `layer_height` 0.20 → 0.24-0.28. Nearly linear time saving; the single biggest
   lever by a wide margin.
2. `sparse_infill_density` down, or `sparse_infill_pattern` → `lightning` if the
   infill is only holding up the top skin.
3. `wall_loops` down to 2 -- but not on anything structural.
4. Larger nozzle (0.6/0.8) if the detail allows. This means a different base
   preset and a different filament preset, not a tweak.
5. Speeds last. Stock H2D speeds are already near the flow limit for most
   materials, so raising them mostly produces under-extrusion rather than a
   faster print.

## "Holes are undersize / it doesn't fit"

**Mechanism.** Inner contours print small because of extrusion width geometry and
material shrinkage, and the error is roughly constant, not proportional. So
scaling the model is the wrong fix.

1. `xy_hole_compensation` -- positive to enlarge holes. 0.05-0.15 mm typical.
2. `xy_contour_compensation` for outer dimensions.
3. `wall_generator` → `arachne`, which handles thin and variable-width walls far
   better than `classic`.
4. Print a test coupon rather than iterating on the real part; the correction is
   material- and printer-specific and worth measuring once.

## "It's stringy"

Mostly the filament preset: retraction length/speed, temperature down 5-10 °C,
and drying. On the process side, `reduce_crossing_wall` → 1 and
`travel_speed` up help. For multi-material prints, check prime tower and purge
volumes before blaming retraction.

## "Small features / text won't print"

1. Smaller nozzle (0.2) -- a different base preset.
2. `layer_height` down.
3. `wall_generator` → `arachne`, which prints features narrower than one line
   width instead of dropping them.
4. `detect_thin_wall` → 1.
5. `small_perimeter_speed` down.
6. Check the mesh first: `inspect_model.py` will tell you if the feature is even
   present and watertight. Missing detail is often a modelling or export problem,
   and no slicer setting recovers geometry that is not in the file.

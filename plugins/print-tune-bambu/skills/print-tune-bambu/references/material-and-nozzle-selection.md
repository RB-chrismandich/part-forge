# Choosing the filament and the nozzle before choosing settings

Settings are the last decision, not the first. A part in the wrong material or
under the wrong nozzle cannot be rescued by a preset, and most of the time spent
tuning one is spent working around a choice that was never made deliberately.

Both choices are constraints, not preferences, and they conflict: the nozzle that
resolves fine detail is the nozzle that cannot move enough plastic to finish a
large part, and the filament that survives a hot car is the filament that warps
off the plate. Say which constraint you are honouring and which you are trading.

## Filament, by what the part has to survive

Pick from the failure the part must not have. Everything else is secondary.

| The part must | Filament | Why, and what it costs |
|---|---|---|
| Look good indoors, take no load | PLA (incl. matte) | Stiffest, easiest, best detail. Softens near 60 C -- a car interior kills it |
| Survive a car, a window sill, an attic | ASA, ABS, PC | Heat and UV. Needs a heated chamber; warps badly without one |
| Take repeated load or impact | PETG, PCTG, ABS | Tougher, less brittle than PLA. PETG strings and needs a wider support gap |
| Be stiff and dimensionally stable | PLA-CF, PETG-CF, PA-CF | Filled, so much less warp and creep. **Abrasive -- hardened nozzle required** |
| Flex, seal, or grip | TPU (95A / 85A) | Slow, no bowden retraction, dry it. 85A will not print on some paths |
| Hold water | PETG over PLA | Less porous at the seam and less brittle |
| Carry sustained load for months | Not PLA | PLA creeps under constant stress at room temperature. This surprises people |

**Matte PLA is PLA.** On an H2D its stock filament preset is identical to Basic
PLA -- same 220 C, same 25/40 mm3/s, same fan -- so it buys appearance, not
behaviour. The mineral filler that makes it matte also diffuses fine surface
detail slightly and makes it a little more brittle. If a part is failing on
detail in matte PLA, the material is not the lever.

**Filled filaments oblige a hardened nozzle.** CF, GF and most "matte" or
metal-fill blends abrade brass. This is a hardware precondition, not a setting,
and it is worth confirming out loud before recommending one.

## Nozzle, by the resolution the model actually demands

Do not guess this from the picture. `inspect_model.py` measures the model's
finest features against each nozzle and reports the share of wall area that
falls below two line widths:

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/print-tune-bambu/scripts"
python3 "$S/inspect_model.py" --pretty part.stl --line-width 0.42
```

`pct_failing_by_nozzle` re-scores the same measurement for every nozzle at or
below the one you asked about, and `smallest_resolvable_nozzle` names the
coarsest one that clears the threshold -- or `null`, which is the important
answer, because it means no nozzle resolves this model at this size.

| Nozzle | Resolves features down to | Use when |
|---|---|---|
| 0.2 | ~0.4 mm | Miniatures, scale-model panel scribing, fine text |
| 0.25 | ~0.5 mm | Detail parts that still need to finish this week |
| 0.4 | ~0.85 mm | Default. Almost everything functional |
| 0.6 | ~1.3 mm | Big functional parts, jigs, brackets; ~2x faster than 0.4 |
| 0.8 | ~1.7 mm | Bulk, vases, furniture-scale; detail is gone |

## The trade nobody prices: flow against resolution

A finer nozzle buys detail with time, and the exchange rate is brutal because it
is set by volumetric flow, not by speed. Read the real limit rather than assuming
it -- it lives on the filament side and it is nozzle-specific:

```bash
python3 "$S/bambu_profiles.py" get "Bambu PLA Matte @BBL H2D 0.2 nozzle" \
    --kind filament filament_max_volumetric_speed
```

On this install that returns **2 mm3/s**, against **25** for the same filament at
0.4 mm. A floor on print time follows directly from the part's own volume, which
`inspect_model.py` reports:

    hours >= volume_mm3 / max_volumetric_speed / 3600

A 512 cm3 model is about 5.7 hours of pure extrusion at 0.4 mm and about **71
hours** at 0.2 mm, before travel, before layer changes. That is the sentence to
put in front of someone asking for a smaller nozzle, and it is why
"use a 0.2 nozzle" is a recommendation with a bill attached.

## When no nozzle resolves the model

`smallest_resolvable_nozzle: null` means the detail is below what FDM reaches at
this size. Three honest options, in order:

1. **Scale the model up.** The only fix that recovers the detail rather than
   trading it. Every dimension scales, so check the plate: `inspect_model.py`
   reports the bounding box and flags the H2D envelope. Note that scaling 1.5x
   multiplies volume, and therefore time, by about 3.4.
2. **Accept the loss deliberately, and print it well.** Set `wall_generator` to
   `arachne` so sub-line-width features become clean single beads instead of
   overlapping walls and gap infill, and say which detail will not survive. On a
   scale-model hull this cut gap infill by 93 % at a 15 % time cost.
3. **Split the part.** Print the detailed section separately and larger, or at a
   finer nozzle, and join it. Worth raising when one region carries all the
   detail -- the z range in the narrow-feature report says whether it does.

What is not an option is tuning around it. No temperature, speed, cooling or
support setting recovers geometry the nozzle cannot draw, and time spent there
is the most common way a print gets worse instead of better.

## Related

- `failure-modes.md` -- "Engraved detail prints ragged", the mechanism behind a
  high narrow-feature score and the settings that do help once the nozzle is right.
- `materials.md` -- what each filament family constrains once it is chosen:
  temperature, chamber, drying, support strategy, failure signature.
- `slice-verification.md` -- confirming the choice by slicing, and reading
  `Gap infill` as the slicer's own verdict on whether it could fit two walls.

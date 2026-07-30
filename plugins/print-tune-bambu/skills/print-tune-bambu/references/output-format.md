# Delivering the brief and the preset JSON

Step 5 of the main skill: produce a decision brief with a delta table, **and**
an importable preset JSON. The table is what gets read and argued with; the
JSON is what gets used.

## The brief

```markdown
## <part> — <material> on <printer> <nozzle>

**Base preset:** `<exact preset name>`
**Filament preset:** `<exact filament preset name>`
**Optimizing for:** <the stated priority> · **trading away:** <the stated cost>

### What the geometry says
<3-5 bullets citing measured numbers, or the assumed premises if no file>

### Changes

| Bambu Studio location | Setting | Stock | Set to | Why |
|---|---|---|---|---|
| Quality > Layer height | Layer height | 0.20 | 0.12 | <failure mode avoided> |

### Left at stock on purpose
<the tempting knobs you did not turn, and why — this is the part that keeps
the profile honest and short>

### Watch for
<what to check on the first print, and what to change if it goes wrong>
```

## The preset JSON

Match Bambu Studio's own export format exactly -- a delta with `inherits`, not a
full config:

```json
{
  "name": "PETG-CF bracket 0.16",
  "print_settings_id": "PETG-CF bracket 0.16",
  "inherits": "0.16mm Balanced Quality @BBL H2D",
  "from": "User",
  "version": "<match the version field of an existing user preset>",
  "wall_loops": "5",
  "sparse_infill_density": "30%",
  "outer_wall_speed": ["nil", "nil", "120", "nil", "nil"]
}
```

**The H2D per-variant array is the thing that goes wrong.** On dual-nozzle
machines, every speed and acceleration key is an array with one slot per extruder
variant -- five slots on the H2D, in the order given by `print_extruder_variant`:

| Slot | Extruder | Variant |
|---|---|---|
| 0 | left (1) | Direct Drive Standard |
| 1 | left (1) | Direct Drive High Flow |
| 2 | right (2) | Direct Drive Standard |
| 3 | right (2) | Direct Drive High Flow |
| 4 | right (2) | Direct Drive TPU High Flow |

`"nil"` means "inherit this slot". Writing `"outer_wall_speed": "120"` as a bare
string, or an array of the wrong length, produces a preset that imports but does
not apply the way it reads. Set the slots for the nozzle the filament is actually
loaded in, and say in the brief which nozzle you assumed.

## Start from the user's own preset, not from stock

Run `bambu_profiles.py user-list` before writing anything. If a preset for this
part or material already exists, the delta is built **on top of it**: carry every
one of its overrides through unchanged and add yours, then diff the two and show
that nothing was dropped or altered. A preset that silently discards tuning
somebody arrived at over several prints is worse than no preset, and the loss is
invisible until the print fails the way it used to.

Inherit from the same system base the user's preset inherits from, rather than
naming their preset in `inherits` -- the chain resolves against system presets.

## Set the wall generator when the geometry demands it

`wall_generator` is `classic` in every stock preset, and it has no variable-width
path, so any feature between one and two line widths is laid as overlapping walls
and gap infill. When `inspect_model.py` reports narrow features above a few
percent of wall area, **`arachne` belongs in the delta** -- it is the only setting
that addresses that mechanism, and it is not reachable by tuning anything else.

Its companions, when the report says which one applies:

| Report says | Add | Why |
|---|---|---|
| `wall.ragged_mm2` significant | `detect_thin_wall: "1"` | stock `0` drops ribs under one line width instead of thinning them |
| whiskers across open grooves | `reduce_crossing_wall: "1"` | those are travel moves, a separate cause sharing one photograph |

All three are plain scalars, not per-variant arrays, so they need no `"nil"`
padding even on an H2D.

Say two things whenever you propose `arachne`. It is a **whole-part** change, and
Bambu document four regressions against it (seam placement, perimeters generated
floating in air, visible slicing flaws, uneven surfaces) at
`wiki_sync.py show software/bambu-studio/WallGenerator`. Then A/B it rather than
asserting it: on a 173 mm scale-model hull this cut `Gap infill` from 14.2 % of
extrusion to 0.9 %, for +15 % time and no extra filament -- and that measurement
is what makes it a recommendation instead of an opinion.

## Validate before handing it over

```bash
python3 $S/bambu_profiles.py validate /path/to/new-preset.json
```

This checks the required fields, that `inherits` names a preset that exists in
this install, that every key appears in the base chain, and that per-variant
arrays are the right length. Fix errors before presenting; surface warnings in
the brief if they are intentional.

To install it (only when the user asks -- it writes into their Studio data dir,
and Bambu Studio must be restarted to see it):

```bash
python3 $S/bambu_profiles.py install /path/to/new-preset.json --yes
```

Otherwise just write the file somewhere convenient and tell them to use
Bambu Studio's **Process preset dropdown > Import** (or drop it in the directory
that `root` printed).

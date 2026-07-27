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

Match Bambu Studio's own export format exactly — a delta with `inherits`, not a
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
variant — five slots on the H2D, in the order given by `print_extruder_variant`:

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

## Validate before handing it over

```bash
python3 $S/bambu_profiles.py validate /path/to/new-preset.json
```

This checks the required fields, that `inherits` names a preset that exists in
this install, that every key appears in the base chain, and that per-variant
arrays are the right length. Fix errors before presenting; surface warnings in
the brief if they are intentional.

To install it (only when the user asks — it writes into their Studio data dir,
and Bambu Studio must be restarted to see it):

```bash
python3 $S/bambu_profiles.py install /path/to/new-preset.json --yes
```

Otherwise just write the file somewhere convenient and tell them to use
Bambu Studio's **Process preset dropdown > Import** (or drop it in the directory
that `root` printed).

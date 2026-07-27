---
name: print-tune-bambu
description: Recommend Bambu Studio print settings for a part and emit an importable process preset. Use when slicing an STL/3MF, tuning for a material (PLA, PETG-CF, ABS, PA, TPU), fixing a failed print (warping, drooping overhangs, weak layers), or asking what a Bambu Studio setting does. Reads stock values from the local install.
---

# Bambu Studio print settings

Settings advice fails in two ways, and both are avoidable. The first is stating a
stock value that is wrong ("default wall loops is 3" — on this machine it is 2),
which quietly destroys trust in every other number in the answer. The second is
reciting a generic strong/fast/pretty profile that ignores what this particular
part actually has to survive.

So the method here is: pin down the four facts, read the real values off the
user's own Bambu Studio install, measure the actual mesh, then change only the
settings that a named failure mode justifies.

## Pin down four facts before recommending anything

Do not skip this — a settings answer with the wrong material in it is worse
than no answer, because it looks authoritative.

1. **Printer and nozzle.** Default to the **Bambu Lab H2D with a 0.4 mm nozzle**
   unless told otherwise. If the part is abrasive-filled (CF/GF), confirm a
   hardened nozzle is fitted.
2. **Filament — always confirm this, never infer it.** "PETG" and "PETG-CF" want
   different walls, different support gaps, and a different nozzle. If the user
   has not named the exact spool, ask. This is a standing instruction from the
   user of this skill, not a nicety.
3. **What the part has to survive.** Load direction, temperature, UV, water,
   fit tolerance, whether a visible face matters. This is the entire basis for
   every deviation from stock.
4. **What it is allowed to trade away.** Print time, filament, surface finish.
   Without this you cannot rank the changes, and every recommendation collapses
   into "turn everything up."

If facts 2-4 are missing, ask for them in one batched question rather than
guessing or drip-feeding. Then proceed.

## Step 1 — read the real stock values

`scripts/bambu_profiles.py` resolves Bambu Studio's own preset inheritance chain
from the local install. Use it instead of recalling defaults; presets change
between Studio releases and between printers.

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/print-tune-bambu/scripts"   # set once, reused below

python3 $S/bambu_profiles.py root                      # confirm install + user preset dir
python3 $S/bambu_profiles.py list --printer 'H2D(?!P)' --nozzle 0.4
python3 $S/bambu_profiles.py get "0.20mm Standard @BBL H2D" \
    layer_height wall_loops sparse_infill_density support_threshold_angle
python3 $S/bambu_profiles.py trace "0.20mm Standard @BBL H2D" wall_loops   # which file set it
python3 $S/bambu_profiles.py resolve "0.20mm Standard @BBL H2D"            # all ~198 keys
python3 $S/bambu_profiles.py keys 'support.*overhang'                      # find a key by name
python3 $S/bambu_profiles.py user-list                                     # user's own presets
```

`keys` marks each hit CONFIRMED (some stock preset sets it, so `get` returns a
real stock value) or candidate (the key exists in Studio's option table but no
preset overrides it — never present a candidate's value as "stock").

Also run `user-list` early: if the user already keeps a preset for this
material, inheriting from or aligning with it respects tuning they already
trust and reveals their house style.

Filament-side values (nozzle temp, bed temp, chamber, cooling, flow, shrink) live
in the filament preset: add `--kind filament`.

## Step 1b — consult the official wiki when the question is not a number

The preset files tell you what a setting *is set to*. They do not tell you what
Bambu says a setting is *for*, or how to diagnose a symptom. `wiki_sync.py` keeps
a local Markdown mirror of wiki.bambulab.com for exactly that — mechanics,
scope, and the HMS error-code lookup are in `references/wiki-mirror.md`.

```bash
python3 $S/wiki_sync.py grep 'first layer'     # search the local mirror
python3 $S/wiki_sync.py show software/bambu-studio/layer-height
python3 $S/wiki_sync.py search 'PETG warping'  # live wiki search index
python3 $S/wiki_sync.py hms 0300_9500_0001_0005 --show   # printer error code
```

**Staleness is handled for you.** A `PreToolUse` hook on the `Skill` tool runs
`wiki_sync.py autorefresh` whenever this skill is invoked, throttled to one
check per 24 h. Read the injected note rather than running `status` reflexively:
if it says a background refresh just started, the new text is *not* in this
turn's mirror yet — re-read the page after it lands, or flag the answer as
possibly stale. Run `sync` yourself only when you need the fresh text right now.

When wiki guidance and a stock preset value disagree, the preset wins for "what
is it set to" and the wiki wins for "what does it mean" — and it is worth saying
which one you used.

## Step 2 — measure the model, do not eyeball it

If a file was provided, run it. Claims like "steep overhangs" or "tall and tippy"
should come from numbers, so the recommendation can cite them.

```bash
python3 $S/inspect_model.py --pretty part.stl     # .stl / .3mf / .obj, add nothing else
```

It reports bounding box, volume, bed-contact area, downward-face area split by
slope band (Bambu's threshold-angle convention: 0° = flat down, 90° = vertical),
bridge spans, tipping aspect ratio, and watertightness.

Read the flags first. A **non-watertight mesh is a stop sign** — no amount of
setting tuning fixes missing walls or phantom infill, so say so and point at the
repair before continuing. And note that bed contact and true bridges are excluded
from `support_needed_area_mm2` on purpose: a flat bottom face is not an overhang,
and a bridge anchored at both ends usually wants bridge tuning, not supports.

STEP and other CAD formats are not mesh formats and cannot be measured here — ask
for an exported STL/3MF, or work from the description.

If no file was provided, work from the description and say plainly which
geometric premises you assumed.

## Step 2b — verify by slicing, when the printer allows it

A recommendation nobody measured is an assertion. `slice_check.py` drives Bambu
Studio's headless CLI and reads back what the slicer *actually* did: the applied
layer height, wall count and infill, predicted time broken down by feature,
filament mass, and the slicer's own geometry warnings.

```bash
python3 $S/slice_check.py check part.stl \
    --machine "Bambu Lab X1 Carbon 0.4 nozzle" \
    --process "0.20mm Standard @BBL X1C" --filament "Bambu PLA Basic @BBL X1C"

python3 $S/slice_check.py compare part.stl \
    --machine "Bambu Lab X1 Carbon 0.4 nozzle" --filament "Bambu PLA Basic @BBL X1C" \
    --base "0.20mm Standard @BBL X1C" --candidate "0.20mm Strength @BBL X1C"
```

`compare` is the one that earns its keep — it turns "more walls costs some time"
into "+32% time, +96% mass, inner wall +827 s, sparse infill −306 s". That is the
trade the user was asked to accept, stated in the units they care about.

**The H2D cannot be sliced this way.** The CLI has no flag to map filaments to
nozzles, so any multi-extruder machine fails with `return_code -66`; single-
extruder machines (X1C, P1S, A1) work completely. On an H2D, pass a **3MF
exported from Bambu Studio** (it carries the mapping the GUI assigned) or slice
a single-extruder proxy and report the delta as *relative* — say so if you do,
since a proxy number presented as an H2D number is exactly the confident-wrong
claim this skill exists to avoid.

## Step 3 — choose the base preset, then change as little as possible

Pick the stock preset whose layer height already matches the job, and inherit
from it. A short delta is reviewable, survives Studio updates, and makes the
reasoning legible. A 60-key profile that reimplements the stock preset is not.

Rough starting points on the H2D 0.4 nozzle — confirm against `list`:

| Job | Base |
|---|---|
| Everyday / prototype | `0.20mm Standard @BBL H2D` |
| Load-bearing, layer adhesion matters | `0.20mm Balanced Strength @BBL H2D` |
| Visible surface, fine detail | `0.12mm Fine @BBL H2D` or `0.16mm Balanced Quality @BBL H2D` |
| Miniature / tiny features | `0.08mm Extra Fine @BBL H2D` |
| Bulk, speed over looks | `0.24mm Standard @BBL H2D` |

## Step 4 — derive each change from a failure mode

For every setting you touch, you should be able to finish the sentence "without
this, the part will ___". If you cannot, drop the change.

`references/failure-modes.md` maps symptoms and requirements to the specific
levers, with the reasoning for each. Read it when you need more than layer
height and walls. `references/settings-map.md` maps the Bambu Studio UI label to
the JSON key, which you need to write the preset and to tell the user where to
click. `references/materials.md` covers what each family constrains.

Two habits that separate good advice from generic advice:

- **Reach for geometry and orientation before settings.** Rotating a part 90° can
  delete the supports, fix the layer-line direction on a load path, and halve the
  time. If that is the real answer, lead with it, then give settings for the
  chosen orientation.
- **Strength is anisotropic.** Walls carry load along the layer; layers are the
  weak plane. For a loaded part, more `wall_loops` beats more
  `sparse_infill_density` per gram almost every time, and orientation beats both.

## Step 5 — deliver both artifacts, then validate

Produce a decision brief with a delta table, **and** an importable preset JSON
that matches Bambu Studio's own export format — a delta with `inherits`, not a
full config. On the H2D, every speed/acceleration key is a 5-slot per-extruder-
variant array; a bare string or wrong-length array imports but silently does
not apply the way it reads.

`references/output-format.md` has the brief template, the JSON example, the
full per-variant slot table, and the `validate`/`install` commands to run
before handing the preset over.

## Things that make the advice worse

- Turning knobs without a named failure mode. Every extra line in the delta is a
  future debugging surface.
- Quoting a stock value from memory when `get` would have taken two seconds.
- Recommending supports for a flat face that is sitting on the build plate.
- Ignoring the filament preset. Warping, stringing, and layer adhesion are more
  often temperature, cooling, and drying than they are process settings — and
  those live on the filament side.
- Maxing speed on the H2D because it can do 1000 mm/s travel. The limit for a
  given print is volumetric flow, cooling, and part rigidity, not the motion
  system.
- Silently assuming which nozzle the material is in on a dual-nozzle machine.

## Reference files

- `references/output-format.md` — the decision-brief template, the preset JSON
  example, the full H2D per-variant slot table, and the validate/install commands.
- `references/failure-modes.md` — symptom or requirement → the lever that fixes
  it, and why. Read this for anything beyond layer height and walls.
- `references/settings-map.md` — Bambu Studio UI label ↔ JSON key, grouped by
  the page it lives on. Read this when writing a preset or telling someone where
  to click.
- `references/materials.md` — what each filament family constrains: temperature,
  chamber, drying, abrasion, support strategy, failure signature.
- `references/h2d.md` — H2D hardware envelope, dual-nozzle and prime-tower
  behavior, and the per-variant array convention in full.
- `references/wiki-mirror.md` — how the wiki mirror works, what the GraphQL
  endpoint does and does not expose, HMS lookup, image mirroring costs, the
  weekly refresh agent, and how to point a RAG index at it.
- `references/slice-verification.md` — what the headless slicer reports, how to
  read a comparison, and the multi-extruder limitation in detail.
- `references/generator-handoff.md` — reading a part-forge `verify_report.json`,
  and why `inspect_model.py` and `mesh_audit.py` deliberately overlap.

## When the model came from a generator

A `part-forge` generator leaves a `verify_report.json` beside the STL that has
already measured most of what Step 2 asks for, on the exported bytes — read it
before running `inspect_model.py` and quote its numbers. It does not remove the
need for a real slice, and its overhang figure does not transfer if the part is
placed differently than the generator's build axis. `references/generator-handoff.md`
has the full handoff, including why `inspect_model.py` and part-forge's
`mesh_audit.py` deliberately overlap.

## Related

- `parametric-part-workflow` — the design process upstream of this one. Stage 9
  hands off here.
- `fdm-structural-design` — orientation and wall thickness as structural decisions
  rather than slicer settings, decided before the model reaches this skill.
- `mesh-verification-gate` — why a mesh that passes every check can still be
  refused by a slicer, and what to check instead.

# print-tune-bambu

Settings advice fails in two ways, and both look authoritative on the way out. The first is
quoting a stock value that is wrong — "default wall loops is 3", when on this machine it is 2.
One wrong number costs you the reader's trust in every other number in the answer. The second
is reciting a generic strong/fast/pretty profile that never asked what this particular part
has to survive.

`print-tune-bambu` closes both by refusing to work from memory. Stock values come out of the
user's own Bambu Studio install by resolving its preset inheritance chain. Explanations come
out of a local mirror of Bambu's own wiki. Geometry claims come from measuring the mesh. The
predicted cost of a change comes from actually slicing it. What ships is a decision brief where
every deviation from stock is traced to a named failure mode, plus a preset you can import.

## Why it is built this way

A preset value recalled from training data is indistinguishable, in the answer, from one read
off disk two seconds ago. The reader cannot tell which they got. So the skill does not offer
the choice: `bambu_profiles.py get` is two seconds, and the instruction is to run it.

The same reasoning drives the rest. `keys` marks every hit **CONFIRMED** (some stock preset
actually sets it) or **candidate** (the key exists in Studio's option table but nothing
overrides it) — because presenting a candidate's value as "stock" is the same failure wearing
a different hat. And `slice_check.py compare` exists so that "more walls costs some time"
becomes "+32% time, +96% mass, inner wall +827 s, sparse infill −306 s", which is the trade
the user was actually asked to accept.

## What it installs

### Skill

| Skill | Purpose |
|---|---|
| `print-tune-bambu` | The method: pin down four facts, read real stock values, measure the mesh, slice to verify, then change only what a named failure mode justifies. |

Eight reference files sit behind it and are read on demand: `failure-modes.md` (symptom → lever,
and why), `settings-map.md` (Studio UI label ↔ JSON key), `materials.md` (what each filament
family constrains), `h2d.md` (dual-nozzle envelope and the per-variant array convention),
`output-format.md` (brief template, preset JSON, validate/install), `slice-verification.md`,
`wiki-mirror.md`, and `generator-handoff.md`.

### Scripts

| Script | Purpose |
|---|---|
| `bambu_profiles.py` | Resolves Studio's preset inheritance from the local install. `root`, `list`, `get`, `trace`, `resolve`, `keys`, `user-list`, `validate`, `install`. |
| `inspect_model.py` | Measures an STL/3MF/OBJ: bounding box, volume, bed contact, downward-face area by slope band, bridge spans, tipping ratio, watertightness. |
| `slice_check.py` | Drives Studio's headless CLI and reads back what the slicer *did*. `check` for one preset, `compare` for a base-versus-candidate delta. |
| `wiki_sync.py` | Maintains the local wiki mirror. `status`, `sync`, `search`, `grep`, `show`, `hms`, `autorefresh`, `agent`. |

### Hook

A `PreToolUse` hook on the `Skill` tool runs `wiki_sync.py autorefresh` when — and only when —
this skill is invoked, throttled to one check per 24 hours. Any real sync is spawned detached,
and the command ends in `|| true` behind a 20-second timeout, so a refresh that is slow, failing,
or offline can never fail the tool call it rode in on.

It needs `jq` to decide whether the invoked skill is this one. **Without `jq` the hook fails
silently** and the mirror stops refreshing; nothing warns you.

## Installing

Try it locally without installing:

```bash
claude --plugin-dir /path/to/part-forge/plugins/print-tune-bambu
```

Install from this repository's marketplace:

```
/plugin marketplace add /path/to/part-forge
/plugin install print-tune-bambu@part-forge
```

## Prerequisites

**Bambu Studio**, for anything that reads real values. `bambu_profiles.py` looks for the bundled
profiles at `/Applications/BambuStudio.app/Contents/Resources/profiles`; `slice_check.py` looks
for the binary inside the same bundle. Both accept overrides — `BAMBU_PROFILES_ROOT`,
`BAMBU_USER_ROOT`, `BAMBU_BINARY` — so a non-standard install or another platform is a matter of
pointing them at it.

**python3.** No virtual environment. `inspect_model.py` handles STL, 3MF and OBJ.

**jq**, for the wiki-refresh hook only. Everything else works without it.

**Network**, for `wiki_sync.py sync` and `search`. Once the mirror exists at `~/.cache/bambu-wiki`
(override with `BAMBU_WIKI_DIR`), `grep`, `show` and `hms` are entirely local.

## Quick start

```bash
S=<plugin>/skills/print-tune-bambu/scripts

python3 $S/bambu_profiles.py list --printer 'H2D(?!P)' --nozzle 0.4
python3 $S/bambu_profiles.py get "0.20mm Standard @BBL H2D" wall_loops sparse_infill_density
python3 $S/inspect_model.py --pretty part.stl
python3 $S/slice_check.py compare part.stl \
    --machine "Bambu Lab X1 Carbon 0.4 nozzle" --filament "Bambu PLA Basic @BBL X1C" \
    --base "0.20mm Standard @BBL X1C" --candidate "0.20mm Strength @BBL X1C"
```

In a Claude Code session you invoke the skill instead and it runs these itself — but the scripts
stand alone, which is what makes the numbers in a brief checkable by hand.

## Known limits

**The H2D cannot be sliced headlessly.** Studio's CLI has no flag mapping filaments to nozzles,
so every multi-extruder machine fails with `return_code -66`. Single-extruder machines (X1C,
P1S, A1) work completely. On an H2D you pass a 3MF exported from Studio, which carries the
mapping the GUI already assigned, or you slice a single-extruder proxy and report the delta as
*relative* — clearly labelled, because a proxy number presented as an H2D number is precisely
the confident-wrong claim this plugin exists to prevent.

**The wiki mirror is a hybrid, not a GraphQL client.** wiki.bambulab.com runs Wiki.js, and
anonymous access reaches `pages.list` and `pages.search` but not `pages.single` or
`singleByPath` (`PageViewForbidden 6013`). GraphQL therefore answers *what exists and when it
changed* but never *what it says*; content is fetched from the public HTML. That split is why
staleness checking is nearly free and content sync is the expensive part.

**STEP and other CAD formats are not mesh formats** and cannot be measured. Export an STL or 3MF.

## The handoff from part-forge

`part-forge` is the sibling plugin in this marketplace, and it stops at an accepted solid — it
does not slice. When a model came from one of its generators there is a `verify_report.json`
beside the STL that has already measured most of what Step 2 asks for, on the exported bytes;
the skill reads it and quotes its numbers rather than re-deriving them.

The two plugins' mesh inspectors overlap on purpose. `inspect_model.py` here and
`mesh_audit.py` there share no code, and two implementations agreeing from different evidence
is the premise the whole marketplace is built on. When they disagree, the disagreement is the
finding. `references/generator-handoff.md` has the full contract.

```
/plugin install part-forge@part-forge
/plugin install print-tune-bambu@part-forge
```

## What this deliberately does not do

**It does not guess the filament.** "PETG" and "PETG-CF" want different walls, different support
gaps, and a different nozzle. If the exact spool has not been named, the skill asks. This is a
standing instruction, not a nicety.

**It does not turn knobs without a reason.** Every setting it touches has to complete the
sentence "without this, the part will ___". Every extra line in a delta is a future debugging
surface, so a short delta that inherits from a stock preset beats a 60-key profile that
reimplements one.

**It does not reach for settings first.** Rotating a part 90° can delete the supports, fix the
layer-line direction on a load path, and halve the print time. Where that is the real answer,
it leads with that.

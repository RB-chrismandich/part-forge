# part-forge

A Claude Code plugin marketplace for designing, verifying, and printing functional 3D-printed
parts: a measured-facts ledger that governs the model, parametric Blender generators, an
acceptance gate that reads the exported bytes back off disk, and slicer tuning grounded in a
real local install.

## Why it is built this way

A generator once reported `non-manifold edges: 0` across 135 passing checks. Bambu Studio
opened the same file and reported 2 non-manifold edges. Both were right: Blender counts faces
per *topological* edge, a slicer reconstructs topology *by position*. So verification here
always runs on the artifact that ships, by position, in an implementation sharing no code with
the thing that produced it — see [docs/ARCHITECTURE_DIAGRAMS.md](docs/ARCHITECTURE_DIAGRAMS.md)
for how that plays out end to end, including why `mesh_audit.py` and `saddle_gen.py`'s
verification half are never allowed to merge.

## Quick start

Try a plugin locally without installing:

```bash
claude --plugin-dir /path/to/part-forge/plugins/part-forge
```

Or install from this repository as a marketplace:

```
/plugin marketplace add /path/to/part-forge
/plugin install part-forge@part-forge
/plugin install print-tune-bambu@part-forge
```

Then, inside a Claude Code session, either invoke a skill directly (e.g.
`/part-forge:new-part my-bracket`) or just describe the physical part you need — the skill
descriptions are written to trigger on the problem, not just the command name.

## What ships

| Plugin | Version | Purpose |
|---|---|---|
| [`part-forge`](plugins/part-forge) | 0.2.0 | Design a part as a parametric generator: facts ledger, Blender generator, gated mesh verification, structural sizing. |
| [`print-tune-bambu`](plugins/print-tune-bambu) | 0.1.0 | Recommend Bambu Studio print settings grounded in the local install's real stock values, and emit an importable process preset. |

`part-forge` carries 8 skills, 2 agents (`facts-auditor`, `part-design-reviewer`), and 5
verification/generation scripts (`mesh_audit.py`, `mesh_render.py`, `mesh_repair.py`,
`new_part.py`, `part_kit.py`). Full inventory, install prerequisites, and the verification-tier
table: [plugins/part-forge/README.md](plugins/part-forge/README.md).

`print-tune-bambu` carries 1 skill backed by `inspect_model.py`, `slice_check.py`,
`bambu_profiles.py`, and `wiki_sync.py` (kept fresh by a `PreToolUse` hook, throttled to once a
day). It needs `jq` on `PATH` — the hook fails silently without it.

## Worked examples / regression fixtures

| Project | What it is | Why it exists |
|---|---|---|
| [`projects/shade-bar-mount`](projects/shade-bar-mount) | A solid saddle bracket generator (`saddle_gen.py`). | The baseline: a solid part cannot fail the way a shelled vessel can. |
| [`projects/gate-coupon-dish`](projects/gate-coupon-dish) | A hollow, shelled vessel generator. | Exercises wall-thickness and overhang checks a solid never exercises. |

Each carries its own `FACTS.md`, `PROJECT.md`, `BUILD-BRIEF.md`, generator script, exported
STL(s), and `verify_report.json`. `smoke.sh` pins a digest of the welded, rounded vertex set
`mesh_audit` parses out of the committed STL — not the raw bytes — so it survives the
generator's own byte-level nondeterminism.

## Before you commit

```bash
python3 .claude/scripts/repo_check.py     # structure, frontmatter, links, flag drift, README inventory
.claude/scripts/smoke.sh                  # only if you touched a script
.claude/scripts/kit_smoke.sh              # only if you touched part_kit's Blender half
```

All three must be clean. `repo_check.py` also shells out to `claude plugin validate`, the
authority on what the runtime accepts. `smoke.sh` never invokes Blender by design, so
`kit_smoke.sh` is the opt-in half that covers `boolean`, `clean_mesh`, `triangulate_and_purge`,
`gated_export`, and `Probe`.

There is no unit-test suite otherwise: `smoke.sh`, `kit_smoke.sh`, and the fixture STLs above
are the entire regression net.

## Toolchain

- **python3** and **trimesh** for verification (trimesh is optional — Tier 0 of `mesh_audit.py`
  is standard-library-only so the gate can run inside Blender's bundled Python).
- **Blender 4.2+** to author a part. On macOS, use
  `/Applications/Blender.app/Contents/MacOS/Blender` — the `.app` path alone will not run a
  script.
- **pyvista** and **pymeshlab**, fetched on demand via `uvx`, never required.
- **jq**, required by print-tune-bambu's `PreToolUse` hook.

## Repository layout

```
.claude-plugin/marketplace.json   both plugins, advertised
plugins/part-forge/               facts ledger, parametric generators, mesh gate
plugins/print-tune-bambu/         Bambu Studio settings, grounded in the local install
projects/shade-bar-mount/         worked example: a solid part, and the regression fixture
projects/gate-coupon-dish/        worked example: the hollow fixture
.claude/                          tooling for maintaining this repo (not shipped)
```

Component map, verification-flow, and end-to-end sequence diagrams:
[docs/ARCHITECTURE_DIAGRAMS.md](docs/ARCHITECTURE_DIAGRAMS.md).

## Traps specific to this repository

- Unquoted frontmatter values starting with `[` parse as a YAML flow sequence and silently
  empty the skill's metadata. Quote every `argument-hint`.
- Script paths in a runnable fence must go through `${CLAUDE_PLUGIN_ROOT}` — an installed
  plugin is never the working directory.
- `plugin.json`'s version silently beats `marketplace.json`'s. Bump both.

Full trap list and cross-plugin contracts:
[.claude/skills/plugin-authoring/references/repo-map.md](.claude/skills/plugin-authoring/references/repo-map.md)
(not shipped — repo maintainer reference only).

## Contributing

See [CLAUDE.md](CLAUDE.md) for the conventions this repository is built around, and the
`plugin-authoring`, `repo-consistency`, `script-smoke`, and `release-plugins` skills for the
workflows that enforce them.

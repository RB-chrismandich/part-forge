# part-forge

A Claude Code plugin marketplace for designing, verifying and printing functional parts.
Two plugins ship from here, plus one worked example that doubles as the only test fixture.

```
.claude-plugin/marketplace.json   both plugins, advertised
plugins/part-forge/               facts ledger, parametric generators, mesh gate
plugins/print-tune-bambu/         Bambu Studio settings, grounded in the local install
projects/shade-bar-mount/         the worked example, and the regression fixture
.claude/                          tooling for maintaining this repo (not shipped)
```

## The idea the repository is built around

A generator once reported `non-manifold edges: 0` across 135 passing checks. Bambu Studio
opened the same file and reported 2 non-manifold edges. Both were right: Blender counts
faces per *topological* edge, a slicer reconstructs topology *by position*.

So verification here runs on the artifact that ships, by position, in an implementation
sharing no code with the thing that produced it. `inspect_model.py` and `mesh_audit.py`
overlap **on purpose**. If either ever imports the other, the evidence is gone.

Precedence is strict: `FACTS.md` beats `PROJECT.md` beats the generator beats the mesh.
Where prose and an executable check disagree, the code is the specification of record.

## Before you commit

```bash
python3 .claude/scripts/repo_check.py     # structure, frontmatter, links, flag drift
.claude/scripts/smoke.sh                  # only if you touched a script
```

Both must be clean. `repo_check.py` also shells out to `claude plugin validate`, which is
the authority on what the runtime accepts.

## Traps specific to this repository

- **Unquoted frontmatter values starting with `[`** parse as a YAML flow sequence and take
  the whole block with them. The skill then loads with *empty metadata* and nothing warns.
  This shipped once already. Quote every `argument-hint`.
- **Script paths in a runnable fence must go through `${CLAUDE_PLUGIN_ROOT}`.** An installed
  plugin is never the working directory.
- **`plugin.json`'s version silently beats `marketplace.json`'s.** Bump both.
- **There is no test suite.** `smoke.sh` and the fixture STLs are the entire regression net,
  and the pinned vertex digest is what makes it meaningful.
- **Tier 0 of `mesh_audit.py` must stay standard-library-only** so the gate can run inside
  Blender's bundled Python without acquiring an install step.

## Skills for working here

Invoke these rather than reconstructing the conventions:

| Skill | For |
|---|---|
| `plugin-authoring` | writing or editing anything under `plugins/` |
| `repo-consistency` | running the structural gate and fixing what it reports |
| `script-smoke` | proving a script change broke nothing |
| `release-plugins` | versioning and publishing a plugin |
| `plugin-drift-auditor` | agent — documented claims versus the artifacts behind them |

`.claude/skills/plugin-authoring/references/repo-map.md` carries the cross-plugin contracts
and the current known-stale list.

## Toolchain

`python3` and `trimesh` for verification; Blender 4.2+ (`/Applications/Blender.app/Contents/MacOS/Blender`
on macOS — the `.app` path alone will not run a script) to author a part; `pyvista` and
`pymeshlab` fetched on demand via `uvx`, never required. `jq` is needed by
print-tune-bambu's hook, which fails silently without it.

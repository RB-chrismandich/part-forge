# part-forge

A Claude Code plugin marketplace for designing, verifying and printing functional parts.
Two plugins ship from here, plus two worked examples that double as the test fixtures:
a solid part and a vessel.

```
.claude-plugin/marketplace.json   both plugins, advertised
plugins/part-forge/               facts ledger, parametric generators, mesh gate
plugins/print-tune-bambu/         Bambu Studio settings, grounded in the local install
projects/shade-bar-mount/         the worked example: a solid, and the regression fixture
projects/gate-coupon-dish/        the hollow fixture -- a solid part cannot fail as a vessel does
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
.claude/scripts/kit_smoke.sh              # only if you touched part_kit's Blender half
```

All must be clean. `repo_check.py` also shells out to `claude plugin validate`, which is
the authority on what the runtime accepts.

`smoke.sh` deliberately never invokes Blender, so it cannot see `boolean`, `clean_mesh`,
`triangulate_and_purge`, `gated_export` or `Probe` — which is every function here that has
ever produced a wrong artifact. `kit_smoke.sh` is that half, and it is slow and opt-in.

## Traps specific to this repository

- **Unquoted frontmatter values starting with `[`** parse as a YAML flow sequence and take
  the whole block with them. The skill then loads with *empty metadata* and nothing warns.
  This shipped once already. Quote every `argument-hint`.
- **Script paths in a runnable fence must go through `${CLAUDE_PLUGIN_ROOT}`.** An installed
  plugin is never the working directory.
- **`plugin.json`'s version silently beats `marketplace.json`'s.** Bump both.
- **Editing a plugin's files is what obliges a bump, not deciding to release.** An install
  resolves on the version string alone, so content shipped under an unchanged version is
  content no installer can ever receive — and `plugin update` answers "already at the
  latest version" forever. Both plugins have already shipped this way. `version-agreement`
  cannot see it, because both manifests agree while the files move underneath them;
  `version-freshness` is the check that reads the directory instead, and it errors on
  anything changed since the commit that set the declared version. If you touched
  `plugins/`, the change is unfinished until the version moves too.
- **There is no test suite.** `smoke.sh`, `kit_smoke.sh` and the fixture STLs are the entire
  regression net. The pinned digest hashes the **welded, rounded, sorted unique vertex set
  `mesh_audit` parses out of the committed file** — deliberately *not* the bytes. That is why
  it survives the generator's byte-level nondeterminism (nine runs, nine raw file hashes, one
  stable digest), and it means a moved digest is always real geometry moving, never re-export
  noise. Never accept a moved digest as "expected after regenerating".
- **`saddle_gen.py` is a partial fork of `part_kit`, and only partly on purpose.** Its
  *construction* half now routes `boolean` through the kit, so the pinned digest can notice a
  kit regression. Its *verification* half — `stl_triangles`, `stl_manifold`, `stl_acceptance` —
  must never be deduplicated: it is a third independent opinion on the exported bytes, and
  collapsing it into `mesh_audit` destroys the evidence, exactly as the paragraph above says.
  The remaining construction forks (`prism`, `loft_solid`, `clean_mesh`, `circumscribed_circle`,
  `rounded_rect`, `corner_fillet`) are deliberately divergent, not drifted. `circumscribed_circle`
  is rotated 90 degrees so a flat facet lands at the trough's rest point rather than a
  tessellation valley; swapping any of them moves the pinned digest for no gain.
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

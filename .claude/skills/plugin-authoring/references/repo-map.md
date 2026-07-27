# What lives where, and what depends on it

A map of this repository written for someone about to change something in it. Paths are
from the repository root.

## Layout

```
.claude-plugin/marketplace.json     the two plugins, advertised
plugins/part-forge/                 design and verification
  .claude-plugin/plugin.json
  README.md                         the only doc an installed user reads
  agents/                           facts-auditor, part-design-reviewer
  scripts/                          shared by several skills AND by the agents
  skills/                           5 depth skills, 3 command skills
plugins/print-tune-bambu/           slicer settings
  .claude-plugin/plugin.json
  hooks/hooks.json                  PreToolUse on the Skill tool
  skills/print-tune-bambu/          one skill; its scripts are nested inside it
projects/shade-bar-mount/           the worked example: a solid, and a test fixture
projects/gate-coupon-dish/          the hollow fixture: shelled vessel, sealed cavity
.claude/                            this tooling -- project-scoped, not shipped
  scripts/repo_check.py             structural gate
  scripts/smoke.sh                  regression harness
  skills/, agents/                  maintenance skills for the repo itself
```

Nothing under `.claude/` is installed by either plugin. It exists to maintain them.

## Contracts that cross a plugin boundary

These have no schema file and no test. They are prose on both sides, which is why they are
listed here.

| Contract | Producer | Consumer |
|---|---|---|
| `verify_report.json` shape and location beside the STL | part-forge generator | print-tune-bambu references/generator-handoff.md |
| the string `print-tune-bambu` and the install id `print-tune-bambu@part-forge` | -- | 5 files inside part-forge |
| `mesh_audit.py --json` top-level keys | part-forge | its own skills, and quoted by print-tune-bambu |
| `inspect_model.py` and `mesh_audit.py` reading the same file **independently** | -- | the premise of the repository |
| the `.gitignore` rules seeded into every scaffolded project | `new_part.py` GITIGNORE constant | a second copy of the repo-root `.gitignore` |

The third and fourth are in tension on purpose. The two mesh readers overlap so that
agreement from different evidence means something; if either ever imports the other, the
overlap stops being evidence and becomes a single point of failure.

## Exit codes the skills branch on

| Code | Meaning | Scripts |
|---|---|---|
| 0 | ran, accepted | all |
| 1 | ran, refused -- a gate or expectation failed; or the target exists and `--force` was withheld | mesh_audit, mesh_repair, new_part |
| 2 | could not read the input | mesh_audit, mesh_render, mesh_repair, new_part |
| 3 | a required optional dependency is missing; prints a runnable `uvx` line | mesh_render, mesh_repair |

Exit 3 is not a failure. It is the tiering working: the gate is dependency-free by design
so that it can run inside Blender's bundled Python, and the richer libraries are
cross-checks fetched on demand.

## Dependency tiers

| Tier | Needs | Gives |
|---|---|---|
| 0 | standard library | STL parse, positional weld, manifold and winding checks, Euler, signed volume, vertex digest |
| 1 | trimesh | mass properties, centre of mass, inertia, solidity, ray-cast thickness, overhang area, non-STL formats |
| 2 | pymeshlab | repair, cleaning, decimation, Hausdorff distance |
| 3 | pyvista | section plots, orthographic renders, heatmaps |

Tier 0 must stay importable with nothing installed. A new dependency in `mesh_audit.py`
breaks the one property that makes the gate trustworthy.

`part_kit.py` guards its `bpy` import and sets `HAVE_BPY`. Everything above its geometry
kernel is pure Python and testable; everything past `_need_bpy` raises without Blender.
`positional_topology()` imports `mesh_audit` by relative path, so the two files must stay
in the same directory.

## Known stale, as of 2026-07-26

Verified, unfixed, and not caught by any automated check. Each is a documentation claim
that no longer matches the artifact.

- **`README.md`** is one line reading `# 3d-blender-projects` -- the repository's former
  name.
- **No `LICENSE` file**, though both plugin manifests declare `"license": "MIT"`.
- **No CI.** Nothing runs `repo_check.py` or `smoke.sh` except a person.
- **`projects/shade-bar-mount/PROJECT.md`** §2 describes a live Blender session whose
  `.blend` "has never been saved", and reports the pre-parametric object `obj_0` with 4642
  triangles. `saddle.blend` is committed, and the shipped part is `ShadeBarSaddle` at 26688
  triangles. The section documents a state one generation out of date.
- **`projects/shade-bar-mount/FACTS.md:11`** says "Last updated: 2026-07-25" while §7h.3
  inside it is dated 2026-07-26.
- **`verify_report.json`** records absolute paths under a worktree named
  `3d-blender-projects/emdash/setup-mcp-dkmao`, which predates the rename and no longer
  exists.
- **`wiki_sync.py` `cmd_status`** calls `fetch_manifest` with no try/except, while
  `cmd_autorefresh` wraps the identical call specifically to degrade offline. `status` will
  traceback on a machine with no network.
- **`hooks/hooks.json`** allows the hook 20 seconds; the `wiki_sync` request path allows 90
  seconds per attempt with up to 4 attempts. A black-holed connection is killed externally
  before the graceful handler runs, which contradicts the file's own claim that it can never
  fail the tool call.
- **`.gitignore`** has no rule for `*.png`. `mesh_render.py` writes its renders next to the
  mesh, so running it against the fixture drops untracked images into the project directory.
- **`verify-part/SKILL.md:50`** uses an ASCII `--` where the top-level house style is an
  em-dash.
- **23 bare script paths** in print-tune-bambu's `references/*.md` bash fences, and that
  plugin has no README.

The tail of this list is what `plugin-drift-auditor` exists to regenerate. A claim in a
document is not checked by anything until someone reads both it and the artifact.

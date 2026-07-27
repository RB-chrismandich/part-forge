---
name: script-smoke
description: Exercise the plugin Python against the repository's fixture project after changing it — mesh_audit, mesh_render, mesh_repair, new_part, part_kit, or the print-tune-bambu scripts. Use after editing any script under plugins/, when a refactor needs proving it changed nothing, when an exit code or JSON key may have moved, or when the vertex digest of the fixture STLs must be confirmed unchanged. There is no unit-test suite; this is the whole regression net.
argument-hint: "[-v]"
allowed-tools: Bash, Read, Glob, Grep, Skill
---

# Prove the scripts still do what callers depend on

There are roughly five thousand lines of Python under `plugins/` and no tests. What breaks
them is not a crash — it is a refactor that still runs, and returns a slightly different
number to a caller that never checks.

`projects/shade-bar-mount/` is the only fixture in the repository: three exported STLs, a
facts ledger, and a `verify_report.json` recording what the generator measured. Everything
below runs against those bytes.

## Step 1 - run it

```bash
.claude/scripts/smoke.sh        # 27 assertions, ~10 seconds
.claude/scripts/smoke.sh -v     # echo each command as it runs
```

Exit 0 and `SMOKE CLEAN` means every assertion held. Nothing it does writes inside the
repository, reaches the network, or needs Blender.

## Step 2 - know what each group is protecting

| Group | The contract |
|---|---|
| help paths | `--help` succeeds with **no optional dependency installed** — otherwise it fails exactly the person working out what to install. |
| acceptance gate | The three fixture STLs are accepted, and two deliberately wrong expectations are still refused. A gate that cannot fail is not a gate. |
| error paths | Unreadable input exits **2**, distinct from a gate failure at **1**. Skills branch on this. |
| determinism | The vertex digest reproduces run to run, and equals the pinned value. |
| json contract | `mesh_audit --json` still carries the keys documents and the sibling plugin quote. |
| variant comparison | Two different solids report different digests — the mode used to review a design change. |
| scaffolding | `new_part.py` finds its templates through the plugin, not the caller's cwd, and refuses to overwrite. |
| part_kit without blender | The pure-Python geometry kernel imports with `HAVE_BPY False`, and bpy-dependent calls raise rather than silently misbehave. |
| optional dependencies | Missing pyvista or pymeshlab exits **3** with a runnable `uvx` line. A traceback is not the contract. |
| cross-plugin agreement | print-tune-bambu's `inspect_model.py` still reads the same file. Its independence from `mesh_audit.py` is the premise of the whole repository. |

## Step 3 - when the digest moves

`smoke.sh` pins `a916d985268c8921fff6f15315bc8e74` and volume `32953.0289` for
`saddle_h0.stl`. The digest is computed from coordinates already fixed in the file on disk,
sorted before hashing, so it is invariant to triangle order, platform and Python version.

It moves for exactly two reasons:

1. **The fixture STL changed.** Legitimate if the commit regenerated it — update the pinned
   constants in the same commit, and say in the message why the geometry moved.
2. **`mesh_audit.py`'s weld, rounding or digest changed.** This is a breaking change to the
   only reproducibility signal the repository has. It needs to be deliberate and stated.

There is no third reason. A digest that moves without one of these is the bug.

Note that `verify_report.json` records a *different* digest (`d62fe6e8…`) from the one
`mesh_audit.py` reports. That is not drift — the generator hashes its own representative
and the auditor hashes the exported bytes, deliberately sharing no code. Comparing the two
numbers is meaningless; comparing each to its own history is the point.

## Step 4 - what smoke does not cover

Blender is needed to *author* a part and is deliberately not needed to verify one, so
nothing here runs `saddle_gen.py`. If you changed `part_kit.py` below the geometry kernel —
anything past `_need_bpy` — the smoke run cannot see it. Regenerate the part:

```bash
blender --background --python-exit-code 1 --python projects/shade-bar-mount/saddle_gen.py
```

`--python-exit-code 1` is not optional; without it Blender exits 0 when the script raises.

Equally uncovered: `mesh_render.py`'s actual rendering (only its degrade path is asserted),
`wiki_sync.py`'s network paths, and `slice_check.py`, which needs the Bambu Studio binary.

## Step 5 - extend it when you extend a contract

A new flag, exit code or JSON key that a skill or the sibling plugin will read is a new
contract, and belongs asserted here in the same commit. Follow the existing shape: assert
the exit code with `expect_exit`, or run the command and follow it with `check <label>`.

Add the negative case too. Most of what these assertions are worth comes from the two that
prove the gate still refuses.

## Notes

`smoke.sh` is shellcheck-clean and should stay that way — `shellcheck .claude/scripts/smoke.sh`.

Assertions that need a dependency this machine lacks report `skip`, not `ok`. A skip is not
a pass; it means that contract went unverified on this run.

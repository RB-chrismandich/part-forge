---
name: repo-consistency
description: Run the structural gate over this marketplace repository and fix what it reports — frontmatter that does not parse, skills named differently from their directory, dead links, documented flags that no script declares, orphaned reference files, README inventories that have drifted, and version disagreement between plugin.json and marketplace.json.
argument-hint: "[--strict] [--json] [--skip-cli]"
allowed-tools: Bash, Read, Edit, Glob, Grep, Skill
---

# Check that the repository still says what it means

Two scripts answer this, and they answer different questions. `repo_check.py` knows what
this repository has decided; `claude plugin validate` knows what the runtime will accept.
Run both. Where they disagree the runtime wins and the checker gains a case.

## Step 1 - run the gate

```bash
python3 .claude/scripts/repo_check.py
```

Exit 0 means no errors. Exit 1 means at least one, and the run prints every finding as
`check`, location, and what is wrong. Add `--json` when you want to filter, `--strict` to
make warnings fail too, `--skip-cli` to skip the shell-out when `claude` is unavailable.

## Step 2 - read the errors as a class, not a list

Each check exists because the failure it catches is silent. Knowing which silence you are
looking at tells you how to fix it.

| Check | What actually broke |
|---|---|
| `skill-frontmatter` | The file loads with **empty metadata** — no description, no tools. Almost always an unquoted value opening with `[`. |
| `skill-name-matches-dir` | Plugin skills invoke by frontmatter `name`, project skills by directory. A mismatch means the two readings disagree. |
| `dead-link`, `dead-plugin-path` | A document sends a reader somewhere that does not exist. |
| `flag-drift` | A fence documents a flag no script declares. The script still works; the documentation is now false. |
| `reference-orphan` | A supporting file exists that no SKILL.md names. Nothing will ever load it. |
| `readme-inventory` | A skill, agent or script exists that the plugin README does not list. |
| `version-agreement` | `plugin.json` silently wins over `marketplace.json` at runtime. A stale manifest masks the version you set. |
| `marketplace-coverage` | A plugin directory nobody advertises. It ships to no one. |
| `claude-validate` | The runtime itself refuses the manifest. This one is never advisory. |
| `python-syntax` | A script does not compile. There is no test suite behind these. |

## Step 3 - fix the cause, not the finding

A dead link is fixed by pointing at the real file *or* by creating the file the document
promised — decide which the document meant. A `flag-drift` error is fixed by correcting
the prose *or* by restoring the flag, and only reading the script tells you which.

Never suppress a check to make a run green. If a check is wrong, it is wrong for every
repository state and belongs edited or deleted in `.claude/scripts/repo_check.py`, with
the reason in the docstring next to it.

## Step 4 - confirm with the runtime

```bash
claude plugin validate .
claude plugin validate ./plugins/part-forge
claude plugin validate ./plugins/print-tune-bambu
```

`repo_check.py` already shells out to these unless `--skip-cli` was passed. Run them by
hand when a finding is confusing — the validator's own message is often more specific.

## Step 5 - re-run, then smoke if you touched code

```bash
python3 .claude/scripts/repo_check.py && .claude/scripts/smoke.sh
```

The structural gate says the repository is coherent. It says nothing about whether the
scripts still work; `script-smoke` covers that.

## Notes

The standing warnings as of the last audit are 23 bare script paths in
print-tune-bambu's `references/*.md` and one missing plugin README. They are real and
unfixed, which is why they are warnings rather than errors — a run that reports exactly
those is clean. A run reporting anything else is not.

Warnings are not decoration. `--strict` is the right setting in CI and the wrong setting
mid-edit.

---
name: new-part
description: Scaffold a new parametric part project - creates the directory with FACTS.md, PROJECT.md, BUILD-BRIEF.md, a generator skeleton, and a .gitignore, then interviews the user for the facts that must be measured before anything can be built.
argument-hint: <part-name> [--dir projects] [--date YYYY-MM-DD]
allowed-tools: Bash, Read, Write, Edit, Glob, Skill
---

# Scaffold a part project

Create the project skeleton, then get the facts ledger to a state where the next step is
unambiguous. An empty template that nobody fills in is worse than no template, so the
interview is part of the job, not an optional extra.

## Step 1 - resolve the name and location

Parse `$ARGUMENTS` for the part name and optional `--dir` / `--date`. If no name was given,
ask for one before doing anything else.

Derive a kebab-case slug from the name. Default the parent directory to `projects/` under the
repository root, creating it if absent. If a directory of that name already exists, stop and
report it — do not pass `--force` on the user's behalf.

## Step 2 - run the scaffolder

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/new_part.py" shade-bar-mount --dir projects
```

It writes `FACTS.md`, `PROJECT.md`, `BUILD-BRIEF.md`, `<slug>_gen.py`, and `.gitignore`, and
substitutes the part name, slug, constant prefix, and date into the placeholder tokens. Report
the tree it prints.

## Step 3 - interview for the ledger

Load the `measured-facts-discipline` skill and work through the questions below with the user.
Write each answer straight into `FACTS.md` with a confidence tag; do not batch them up in
conversation and write at the end.

Ask, in this order:

1. **What does the part have to do?** Push, pull, capture, locate, space, cover. Push back on
   verbs that bundle several jobs — a part asked to do less gets smaller and stronger.
2. **What already exists that this must fit?** Every dimension fixed by existing hardware is a
   `[MEASURED]` or `[OPEN]` input, never `[DERIVED]`. Record which object fixes it.
3. **What is the envelope?** The space the part may occupy, and which faces are hard limits.
4. **What is the load, and for how long?** A number in lbf or N, and whether it is momentary
   or continuous. Continuous means creep, which changes the safety factor.
5. **How does it mount?** Screws, adhesive, clamp, friction. Adhesive means peel is likely the
   binding constraint.
6. **Which numbers are actually measured, and with what?** Tag each one. An instrument that
   cannot resolve the tolerance being claimed is not evidence.
7. **What is still unknown?** These become the section 8 blocker list.

For anything the user does not know, tag it `[OPEN]` and put it in the blocker list rather than
accepting an estimate as a value. If a dimension cannot be measured with tools on hand, propose
a printed go/no-go gauge and say what it would cost in print time.

## Step 4 - state what blocks what

Finish by writing, into `PROJECT.md`, two short lists: what cannot start until the owner
measures something, and what can start now. Parametric work belongs in the second list — the
measurements are *inputs* to the generator, so writing it does not wait on them.

## Step 5 - report

Tell the user: the path created, how many facts are tagged and how many are `[OPEN]`, the
specific measurements needed and the procedure for each, and that `/part-forge:gen-part` is the
next command once the parameter table has values.

## Notes

- Do not invent dimensions to fill the template. An `[OPEN]` row is the correct output when the
  number is not known.
- Do not write a goal statement the user has not committed to. Leave the GOAL section marked as
  a draft until they confirm it.
- If the repository already has a part project, read its `FACTS.md` section structure first and
  match the numbering, so the two are comparable.

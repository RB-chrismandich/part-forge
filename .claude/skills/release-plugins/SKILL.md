---
name: release-plugins
description: Cut a version of part-forge or print-tune-bambu — bump the version in both places it is recorded, refresh the README inventories, run the gate and the smoke harness, and verify the marketplace still installs. Use when publishing a change to either plugin, when a version needs bumping, when the marketplace entry and plugin manifest have diverged, or when deciding whether a change is breaking for someone who already installed it.
argument-hint: "<plugin-name> <major|minor|patch>"
allowed-tools: Bash, Read, Edit, Glob, Grep, Skill
---

# Publish a version someone else will install

A plugin in this repository is consumed by `/plugin install <name>@part-forge` from a
machine that has none of this context. The release is the only moment anything is checked
on that person's behalf.

The two plugins version **independently**. They ship separately, install separately, and a
change to the slicer settings map has no bearing on the mesh gate. Lockstep versioning
would only communicate a coupling that does not exist.

## Step 1 - decide what kind of change this is

The question is not how much code moved. It is what breaks for someone already running the
previous version.

| Bump | When |
|---|---|
| `major` | A skill or command was renamed or removed; a script's flag, exit code or JSON key changed meaning; a documented contract now behaves differently. |
| `minor` | A skill, agent, script, flag or reference file was added. Existing behaviour is intact. |
| `patch` | Prose, a fixed link, a corrected number, a bug fix that restores documented behaviour. |

Renaming a skill is always `major`, and in this repository it is worse than it looks: the
name `print-tune-bambu` appears verbatim in five files inside part-forge, and part-forge's
skills are named from print-tune-bambu's. Grep before renaming anything:

```bash
grep -rn "<old-name>" plugins/ projects/ .claude-plugin/ README.md
```

## Step 2 - bump both records, together

The version lives in two files, and they disagree silently: at runtime `plugin.json`
**always wins**, with no warning, so a stale manifest quietly masks whatever
`marketplace.json` says.

```bash
plugins/<name>/.claude-plugin/plugin.json      # "version"
.claude-plugin/marketplace.json                # the matching entry's "version"
```

`repo_check.py` reports disagreement as an error. That is the only thing standing between
a bump and a version nobody receives.

Two manifests agreeing is necessary and not sufficient. They can agree exactly while the
files they describe have moved underneath them, which is how print-tune-bambu shipped a
restructured skill and two new reference files under an unchanged `0.1.0`. The
`version-freshness` check is the one that reads the plugin directory rather than the
manifests: it finds the commit that introduced the declared version and errors on
anything changed since. Run it *before* choosing the bump size — what it lists is the
change set you are versioning, and it is routinely larger than what you remember editing.

While you are there, confirm the two `description` fields still match. They are separately
authored copies of one sentence and drift is a warning, not an error, because the
marketplace entry is allowed to read differently — but usually it should not.

## Step 3 - refresh the inventories

`plugins/part-forge/README.md` carries three tables — skills, agents, scripts — and they
are the only documentation an installed user sees. A new component with no row is
invisible.

```bash
python3 .claude/scripts/repo_check.py --json | python3 -c "
import json,sys
for f in json.load(sys.stdin)['findings']:
    if f['check'].startswith('readme'): print(f['where'], f['message'])"
```

print-tune-bambu has no README at all. That is a standing warning; if this release is the
one that fixes it, mirror part-forge's structure — what it installs, prerequisites, the
dependency tiering, and what it deliberately does not do.

## Step 4 - run everything

```bash
python3 .claude/scripts/repo_check.py --strict     # warnings fail too, at release
.claude/scripts/smoke.sh
claude plugin validate .
claude plugin validate ./plugins/<name>
```

`--strict` belongs here and nowhere else. Mid-edit it is noise; at a release the standing
warnings are exactly the debt you are deciding to ship again.

## Step 5 - install it the way a stranger would

Validation reads the manifests. It does not prove the plugin loads.

```bash
claude --plugin-dir "$PWD/plugins/<name>"
```

Then confirm the skills appear and a command skill actually runs. A skill whose frontmatter
failed to parse still *appears* — it loads with empty metadata — so check that its
description is present, not merely that its name is.

## Step 6 - commit the bump as its own change

Version bump, README rows and any pinned constants belong in one commit, separate from the
work being released. The message should say what a previous installer will experience, not
what was edited.

## Notes

`homepage` and `repository` in both manifests point at
`https://github.com/RB-chrismandich/part-forge`. The repository was renamed from
`3d-blender-projects`; anything still carrying the old name is stale, including the
top-level `README.md`.

The marketplace `name` is `part-forge` and so is one of the plugins. That is legal and
intentional — `part-forge@part-forge` is the install id — but it makes grep results
ambiguous, so scope searches to a path when renaming.

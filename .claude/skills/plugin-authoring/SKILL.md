---
name: plugin-authoring
description: Write or edit anything under plugins/ in this repository — a SKILL.md, an agent, a reference file, a template, or a script. Use when adding a skill or agent to part-forge or print-tune-bambu, when changing a skill's frontmatter or description, when deciding where a new script belongs, when a reference file is being split out of a SKILL.md, or when a documented flag or path may have drifted from the code behind it. Carries this repository's house conventions and the frontmatter traps that fail silently.
---

# Authoring inside this marketplace

This repository ships two plugins to strangers. Everything under `plugins/` is read by
someone who never saw the conversation that produced it, on a machine where the repo is
not the working directory, through a runtime that fails quietly when a file is malformed.

Those three facts generate every convention below. None of them are aesthetic.

## The failure that has already happened here

`gen-part/SKILL.md` shipped with this line:

```yaml
argument-hint: [path/to/part_gen.py] [--out DIR] [--no-export]
```

YAML reads a plain scalar opening with `[` as a flow sequence, then finds text after the
closing bracket and gives up — on the **entire block**. The skill loaded with no
description, no `allowed-tools`, no name. Nothing warned. The file looks correct, reads
correctly, and is correct prose; it was simply not the document the runtime saw.

**Any frontmatter value starting with `[`, `{`, `*`, `&`, `>` or `|`, or containing `: `,
must be quoted.** Argument hints in this repo use `<required>` and `[--flag VALUE]`
notation, so in practice every `argument-hint:` needs quotes.

Run `python3 .claude/scripts/repo_check.py` after touching any frontmatter. It parses with
a real YAML parser precisely because a permissive hand-rolled one would bless files the
runtime drops.

## Two classes of skill, and the frontmatter tells you which

| | Depth skill | Command skill |
|---|---|---|
| Frontmatter | `name`, `description` | plus `argument-hint`, `allowed-tools` |
| Invoked by | the model, on its own judgment | a person typing `/plugin:name` |
| Description | third-person opener, then `Use when X, when Y, or when Z` | declarative — what it does, not when |
| Body | prose sections, ending `## Reference files` then `## Related` | `## Step 1 - …` through `## Notes` |
| Examples | `mesh-verification-gate`, `fdm-structural-design` | `new-part`, `gen-part`, `verify-part` |

`argument-hint` and `allowed-tools` travel together. One without the other is an oversight
every time: the hint tells a person what to pass, the tool list keeps the command from
being handed the whole toolbox.

A depth skill's description is the entire basis on which it gets selected, and it competes
with every other skill installed on that machine. Enumerate the *situations* — "when a mesh
passes every check but the slicer rejects it" — not the capabilities. Never summarise the
workflow in the description; an agent that can read the procedure in the description will
follow that summary instead of opening the file.

## Where a script belongs

Both plugins are right, and they differ:

- **`plugins/<plugin>/scripts/`** when more than one skill, or any agent, uses the script.
  part-forge's `mesh_audit.py` is named by three skills and both agents; an agent cannot
  reach into a skill's private directory, so the script lives at plugin root.
- **`plugins/<plugin>/skills/<skill>/scripts/`** when exactly one skill owns it.
  print-tune-bambu is a single skill and its four scripts are its own, which keeps the
  skill directory self-contained and liftable into another plugin unmodified.

The rule is ownership, not habit. A script that gains a second caller moves up.

## Paths, in the only environment that matters

An installed plugin is never the working directory. Inside any fence a reader will
copy-paste, a script path goes through the variable:

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"        # set once at the top, reused below
python3 "$S/mesh_audit.py" part.stl --gate
```

A bare `scripts/part_kit.py` is acceptable **only** as a prose citation naming where a
function lives — never inside a runnable block. The distinction is whether someone could
paste the line and expect it to work.

`repo_check.py` reports a bare invocation as a `hardcoded-script-path` warning. The corpus
is clean; there is no standing exception to point at any more, so a new warning here is a
new mistake rather than company. print-tune-bambu's references carried 23 of these for a
while — long enough that the count had been written down as a fact of the repo, which is
how a warning becomes furniture.

Set the path once at the top of the fence and reuse it, so the block survives being
pasted whole:

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/print-tune-bambu/scripts"
python3 "$S/wiki_sync.py" status
```

## Prose conventions

Lines wrap at 90 columns. Tables and fences run long and are exempt.

The H1 is a sentence-case fragment naming the activity — "The gate that decides whether a
solid ships" — never a title-cased noun phrase.

Dashes split by depth: **em-dash `—` in `SKILL.md` and `agents/*.md`; ASCII `--` (and
`-`, never `–`) everywhere under `references/`, `templates/`, `examples/`.** The ASCII
half is enforced by `repo_check.py`'s `dash-convention`, which exempts code fences —
those carry literal program output, and rewriting a dash there would make the sample
disagree with the tool that printed it.

This rule described itself as enforced for a while before it was. part-forge's twelve
reference files honoured it; print-tune-bambu's eight had drifted to 130 typographic
dashes, and nothing said so. A convention documented as enforced but unchecked is worse
than one documented as a preference, because the prose promises a guarantee the repo
does not keep.

Tables carry legends, checklists, tolerance regimes and parameter lists. Prose carries
reasoning. A table of prose is neither.

Every depth skill closes with a section listing what makes the outcome worse — the failure
catalogue — before `## Reference files` and `## Related`.

## Reference files earn their split

Move material out of a SKILL.md when it exceeds roughly 100 lines and is consulted rather
than read — API surfaces, check inventories, worked examples, measurement procedures.

Every file under `references/`, `templates/` or `examples/` **must be named in its own
SKILL.md**. A reference nobody links is a file no agent will ever open, and the checker
treats an orphan as an error. The corpus currently has a perfect bijection; keep it.

## Agents

Frontmatter is `name`, `description`, `model`, `color`, `tools`. The description is a block
scalar carrying three `<example>` blocks, each with Context / user / assistant /
`<commentary>`. That shape is convention rather than schema, and it is what makes the
delegating model trigger reliably.

Plugin-shipped agents silently ignore `hooks`, `mcpServers` and `permissionMode`. Do not
add them; they will not run and nothing will say so.

`name` must equal the filename stem.

## Before you call it done

```bash
python3 .claude/scripts/repo_check.py     # structure, frontmatter, links, flag drift
claude plugin validate ./plugins/<name>   # what the runtime will actually accept
.claude/scripts/smoke.sh                  # only if you touched a script
```

The first two disagree occasionally. When they do, the runtime is right and `repo_check.py`
needs a new check.

## Before you stop: did the version move?

If you changed anything under `plugins/<name>/`, the change is not finished until the
version moves with it. Editing content is what obliges the bump — not deciding to
publish. There is no separate release moment when someone notices; a plugin installed
from this marketplace resolves on the version string alone, so content that ships under
an unchanged version is content the installer can never receive, and `plugin update`
will keep answering "already at the latest version" indefinitely.

`repo_check.py`'s `version-freshness` check is what enforces this. It finds the commit
that introduced the currently declared version and errors on anything under the plugin
that has moved since — committed or not. If it fires, invoke `release-plugins` and bump;
do not silence it.

The trap this closes is specific: `version-agreement` compares one manifest to the other,
and both can agree perfectly while describing files that changed underneath them.

## Things that make a plugin worse

- **A description that summarises the procedure.** The agent follows the summary and never
  opens the file, so the body becomes documentation nobody reads.
- **A flag documented in prose and renamed in the script.** The script keeps working; only
  the documentation becomes a lie. `repo_check.py` diffs fences against `argparse`.
- **A reference file split out and never linked.** Invisible, and it rots undisturbed.
- **A relative script path in a fence.** Works for the author, fails for every installer.
- **A new skill whose row nobody added to the plugin README.** The README is the only
  documentation an installed user has.
- **Editing a template without editing the project it was derived from**, or the reverse.
  `projects/shade-bar-mount/` and `measured-facts-discipline/templates/` are two copies of
  one structure with nothing linking them.

## Reference files

- `references/repo-map.md` — what lives where, which contracts cross plugin boundaries,
  and the known-stale list as of the last audit.

## Related

- `repo-consistency` — run the structural gate and act on what it reports.
- `script-smoke` — the regression harness for the Python under `plugins/`.
- `release-plugins` — version, sync and publish.
- `plugin-drift-auditor` — the judgment-level audit this checker cannot do.

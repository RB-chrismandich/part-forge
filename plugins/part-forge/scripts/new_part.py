#!/usr/bin/env python3
"""Scaffold a part project: the three documents, a generator, and a .gitignore.

Why this exists
---------------
The documents are the process. A part that starts as a lone script accumulates
its constraints as comments, and by the time a dimension turns out wrong there is
no record of whether it was measured, guessed, or inherited from something that
already exists. Starting from the full document set costs a minute and makes the
question answerable for the life of the part.

What it creates
---------------
    <slug>/
      FACTS.md        measured reality, one confidence tag per number -- governs
      PROJECT.md      status, plan, and the decision log
      BUILD-BRIEF.md  self-contained task packet handed to a fresh agent
      <slug>_gen.py   parametric generator with its acceptance gate
      .gitignore

Templates come from the plugin's own skills when they are present, so the
scaffold and the documentation cannot drift apart. When they are absent a minimal
inline fallback is written instead, and the report says which was used.

Usage
-----
    new_part.py "Shade Bar Mount"
    new_part.py bracket --dir projects --date 2026-07-26
    new_part.py bracket --from-template     # fail rather than fall back

Exit codes
----------
    0  created
    1  the target directory exists and --force was not given
    2  a template or output file could not be read or written
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATES = {
    "FACTS.md": os.path.join(PLUGIN_ROOT, "skills", "measured-facts-discipline",
                             "templates", "FACTS.md"),
    "PROJECT.md": os.path.join(PLUGIN_ROOT, "skills", "measured-facts-discipline",
                               "templates", "PROJECT.md"),
    "BUILD-BRIEF.md": os.path.join(PLUGIN_ROOT, "skills", "measured-facts-discipline",
                                   "templates", "BUILD-BRIEF.md"),
    "_gen.py": os.path.join(PLUGIN_ROOT, "skills", "blender-parametric-generator",
                            "examples", "generator_template.py"),
}

GITIGNORE = """*.blend1
__pycache__/
*.pyc

# Bambu Studio CLI drops this next to the working dir on every slice
result.json
"""

# ===========================================================================
#  NAME FORMS
# ===========================================================================

def name_forms(raw):
    """One argument, four spellings. Every template placeholder wants a different
    one, and deriving them here keeps a part from being called three things."""
    slug = re.sub(r"[^a-z0-9]+", "-", raw.strip().lower()).strip("-")
    if not slug:
        raise ValueError(f"{raw!r} contains no usable characters")
    words = slug.split("-")
    return {
        "PART_NAME": raw.strip() if raw.strip() != slug else " ".join(w.capitalize() for w in words),
        "PART_SLUG": slug,
        "PART_CONST": "_".join(w.upper() for w in words),
        "PART_CLASS": "".join(w.capitalize() for w in words),
        # Where part_kit.py lived when this project was scaffolded. Baked in as a
        # *fallback* candidate, never as the only one: a scaffolded project sits
        # outside the plugin, so the template's relative search cannot reach the
        # plugin's scripts directory and the generator would fail to import on the
        # first run. PART_FORGE_SCRIPTS still overrides it, which is what keeps
        # this from breaking when the plugin is moved or reinstalled elsewhere.
        "PART_FORGE_SCRIPTS": os.path.dirname(os.path.abspath(__file__)),
    }


def substitute(text, tokens):
    for key, val in tokens.items():
        text = text.replace("{{%s}}" % key, val)
    return text


# ===========================================================================
#  INLINE FALLBACKS
# ===========================================================================

def fallback_facts():
    """Minimal but not empty: the confidence legend and the blocker list are the
    two things whose absence lets an assumption pass as a measurement."""
    return """# {{PART_NAME}} -- Facts & Actuals

Single source of truth for **real-world constraints**. Nothing here is inferred from the
model; the model conforms to this file, never the reverse. Where this file and any other
document disagree, **this file wins**.

- `[STATED]` -- asserted directly by the owner. Treat as true.
- `[MEASURED +/-t]` -- measured directly, with the tolerance of the method.
- `[PHOTO +/-t]` -- read off a photo against a ruler. **Carries real error. Confirm before printing.**
- `[DERIVED from N.N]` -- follows from other rows. Only as good as they are.
- `[OPEN]` -- not yet known. Blocking until it is.

**Last updated:** {{DATE}}
**Sources:**

Nothing here is deleted. When a row turns out wrong, strike it through, write the
correction underneath, and keep both -- how this file was wrong is the point of the file.

---

## 1. The job

| # | Fact | Confidence |
|---|---|---|
| 1.1 | | `[OPEN]` |

## 2. Mounting method

| # | Fact | Confidence |
|---|---|---|
| 2.1 | | `[OPEN]` |

## 3. Space envelope

| # | Fact | Confidence |
|---|---|---|
| 3.1 | | `[OPEN]` |

## 4. What already exists that this must conform to

Dimensions fixed by existing hardware are **inputs, not derivations**. A theoretical
minimum is only the answer if the world happens to sit at the minimum.

| # | Fact | Confidence |
|---|---|---|
| 4.1 | | `[OPEN]` |

## 5. Load case

| # | Fact | Confidence |
|---|---|---|
| 5.1 | | `[OPEN]` |

## 6. Measurements still needed

These block the build. Each one names the procedure that would close it.

1. `[OPEN]` --

## 7. Defect history

One numbered sub-section per defect found, kept permanently. Record what was measured,
what the check missed, and why.

## 8. Resolved scope

Decisions that are settled and should not be reopened without new evidence.
"""


def fallback_project():
    return """# {{PART_NAME}} -- Project Memory

**Status:** scaffolded {{DATE}}, nothing built yet.
**Owner:**

> **Measured reality lives in [`FACTS.md`](./FACTS.md)** -- that file governs. This file
> describes the model and the plan. Where they disagree, `FACTS.md` wins.

---

## 1. Purpose

What the part does, in one sentence, phrased as the narrowest job that solves the problem.

## 2. Route: parametric rebuild or edit in place

Record the decision and the reason. Rebuild parametrically whenever a dimension is still
open, because then a wrong guess costs one number and a re-run instead of a remodel.

## 3. Parameter table -- the model's entire input

| Param | Meaning | Value | Source |
|---|---|---|---|
| `{{PART_CONST}}_W` | | | `FACTS.md` 3.1 |

Derived values belong in the generator's `derive()`, computed once, not restated here.

## 4. Success criteria, in priority order

1. It does its job.
2. It stays put.
3. It fits the envelope.
4. It fits the thing it mates with.
5. It is printable and sound -- watertight, no degenerate geometry, wall thickness held on
   the load path, oriented so layer lines do not run across the load.
6. It is reproducible **as a solid, not as a file**: compare the vertex-set digest, never
   the STL bytes.

## 5. Variant strategy

If a binding unknown survives, print a set that brackets it rather than a single guess --
and state what the set does *not* cover.

## 6. Non-goals

## 7. Next actions

1. Fill in the `FACTS.md` rows and tag every number.
2. List the `[OPEN]` blockers and the procedure that closes each.
3. Run the generator and read the acceptance report.

## 8. Decision log

Newest first. Each entry: what was considered, what was chosen, and which fact decided it.
"""


def fallback_brief():
    return """# Build Brief -- {{PART_NAME}}

**Hand this file to Claude as the task.** It is self-contained: it assumes no prior
conversation.

---

## Your task

Generate `{{PART_SLUG}}_gen.py`, a parametric Blender generator for this part, and export
the accepted mesh. The script is a deliverable alongside the mesh.

## Context -- why this part exists

## Parameters

Place these at the top of the script as named constants, each annotated with the
`FACTS.md` section it comes from. Nothing downstream recomputes a derived value; derive
once, in `derive()`.

| Name | Meaning | Value | Units | Source |
|---|---|---|---|---|
| `{{PART_CONST}}_W` | | | mm | `FACTS.md` 3.1 |

## Coordinate system

State the origin, the axis directions, and that one Blender unit is one millimetre.

## Geometry

Ordered construction phases. State the intent of each, not just the operations.

## Constraints

Each of these is a gate, not a preference. Every one is measured off the finished mesh and
compared against its expected value.

- watertight, single body, Euler characteristic 2
- no degenerate faces, no edge shorter than the stated floor
- minimum wall on the load path at or above the stated thickness
- the envelope is respected in every axis
- bending safety factor at or above the stated minimum

## Print orientation

State the build direction and *why* -- the load must be carried within layers, not across
them.

## Deliverables

- `{{PART_SLUG}}_gen.py`
- `{{PART_SLUG}}.blend`
- `{{PART_SLUG}}.stl` (plus variants, if any)
- `verify_report.json`

## Unverified assumptions -- flag these, don't hide them

## Acceptance checks -- run these and report actual numbers

The script's own `acceptance()` list is the specification of record. Where this prose and
the code disagree, **the code wins**. The gate must parse the exported file back from disk
and weld by position; verifying in `bmesh` and stopping there is not the same claim.
A variant that fails is refused and deleted, never exported with a warning.

## Do not

- Derive a dimension that something already existing fixes. Measure it.
- Delete a fact that turned out wrong. Strike it through and correct it underneath.
- Gate on a property of the authoring tool's in-memory mesh instead of the shipped file.
"""


def fallback_generator():
    return '''#!/usr/bin/env python3
"""Parametric generator for {{PART_NAME}}.

Run headless:
    blender --background --python-exit-code 1 --python {{PART_SLUG}}_gen.py

`--python-exit-code 1` is not optional. Without it Blender exits 0 even when this
script raises, and a failed build looks like a success to whatever called it.

Run inside a live session:
    exec(open("{{PART_SLUG}}_gen.py").read())

Coordinate system: state the origin and axes here. One Blender unit is one
millimetre.

Scaffolded {{DATE}}.
"""

import json
import os
import sys

# bpy is imported lazily so the pure-geometry helpers below stay importable --
# and therefore testable -- outside Blender.
try:
    import bpy
    import bmesh
    HAVE_BPY = True
except ImportError:
    bpy = bmesh = None
    HAVE_BPY = False

MM_PER_IN = 25.4

# ===========================================================================
#  PARAMETERS -- the model's entire input
# ===========================================================================
# Every value cites the FACTS.md section it comes from. A value with no citation
# is an assumption, and must say so.

{{PART_CONST}}_W = 0.0        # mm   FACTS.md 3.1  TODO

# ===========================================================================
#  DERIVE -- computed once; nothing downstream computes its own
# ===========================================================================

def derive():
    """Return every derived dimension in one dict, and assert the invariants.

    Failing here, before any geometry exists, is much cheaper than failing in
    acceptance -- and the message can name the parameter combination at fault.
    """
    g = {"W": {{PART_CONST}}_W}
    assert g["W"] > 0.0, "W must be positive; got %r" % g["W"]
    return g


# ===========================================================================
#  BUILD
# ===========================================================================

def build():
    if not HAVE_BPY:
        raise RuntimeError("build() needs Blender; run this under blender --python")
    g = derive()
    raise NotImplementedError("construct the solid here")


# ===========================================================================
#  VERIFY -- measured off the finished mesh, never assumed from a parameter
# ===========================================================================

def verify(obj, g):
    """Measure. Return a plain dict; do not raise and do not judge."""
    return {}


def acceptance(v, g, tol=2.0e-3):
    """The specification of record: (name, measured, expected, ok) per check.

    Two tolerance regimes, deliberately: `tol` for dimension-bearing geometry,
    a looser one for form features that come out of booleans and lofts.
    """
    return []


# ===========================================================================
#  MAIN
# ===========================================================================

def out_dir():
    """Where artifacts land. `__file__` is undefined when this is exec()'d into a
    live Blender session, which is a supported way to run it."""
    env = os.environ.get("{{PART_CONST}}_OUT_DIR")
    if env:
        return env
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def main():
    g = derive()
    obj = build()
    v = verify(obj, g)
    checks = acceptance(v, g)
    ok = all(c[3] for c in checks)
    for name, got, want, good in checks:
        print("[%s] %-40s got %s want %s" % ("PASS" if good else "FAIL", name, got, want))

    out = out_dir()
    with open(os.path.join(out, "verify_report.json"), "w") as fh:
        json.dump({"{{PART_SLUG}}": v, "_accepted": ok}, fh, indent=2)

    # Export only behind the gate, then re-verify the written bytes and delete
    # the file if it fails. See the mesh-verification-gate skill.
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
'''


FALLBACKS = {
    "FACTS.md": fallback_facts,
    "PROJECT.md": fallback_project,
    "BUILD-BRIEF.md": fallback_brief,
    "_gen.py": fallback_generator,
}


# ===========================================================================
#  SCAFFOLD
# ===========================================================================

def read_source(key, require_template):
    """Return (text, origin). origin is the template path or "inline fallback"."""
    path = TEMPLATES[key]
    if os.path.isfile(path):
        with open(path) as fh:
            return fh.read(), os.path.relpath(path, PLUGIN_ROOT)
    if require_template:
        raise FileNotFoundError(f"--from-template given but {path} does not exist")
    return FALLBACKS[key](), "inline fallback"


def scaffold(target, tokens, require_template, date):
    """Write every file. Returns a list of (relative path, bytes, origin).

    Every source is resolved and substituted *before* the directory is created,
    so a missing template fails without leaving a half-made project behind. An
    empty directory left by a failed run would block the retry that fixes it.
    """
    subs = dict(tokens)
    subs["DATE"] = date

    planned = []
    for key in ("FACTS.md", "PROJECT.md", "BUILD-BRIEF.md", "_gen.py"):
        text, origin = read_source(key, require_template)
        name = f"{tokens['PART_SLUG']}_gen.py" if key == "_gen.py" else key
        planned.append((name, substitute(text, subs), origin, key == "_gen.py"))
    planned.append((".gitignore", GITIGNORE, "inline", False))

    os.makedirs(target, exist_ok=True)
    written = []
    for name, body, origin, executable in planned:
        path = os.path.join(target, name)
        with open(path, "w") as fh:
            fh.write(body)
        if executable:
            os.chmod(path, 0o755)
        written.append((name, len(body), origin))
    return written


# ===========================================================================
#  CLI
# ===========================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Scaffold a part project: FACTS.md, PROJECT.md, BUILD-BRIEF.md, "
                    "a parametric generator, and a .gitignore.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Templates are taken from the plugin's own skills when present, so the\n"
               "scaffold and the documentation cannot drift. Otherwise a minimal inline\n"
               "fallback is written and the report says so.\n"
               "\n"
               "The name may be given in any spelling: \"Shade Bar Mount\", shade-bar-mount,\n"
               "or shade_bar_mount all produce the same slug.",
    )
    ap.add_argument("name", help="part name, in any spelling")
    ap.add_argument("--dir", default=".", metavar="PATH",
                    help="parent directory for the new part (default: current directory)")
    ap.add_argument("--date", metavar="YYYY-MM-DD",
                    help="date stamped into the documents (default: today)")
    ap.add_argument("--from-template", action="store_true",
                    help="fail if a template is missing instead of using the inline fallback")
    ap.add_argument("--force", action="store_true",
                    help="write into an existing directory, overwriting files")
    args = ap.parse_args(argv)

    try:
        tokens = name_forms(args.name)
    except ValueError as exc:
        print(f"new_part: {exc}", file=sys.stderr)
        return 2

    if args.date:
        try:
            date = datetime.date.fromisoformat(args.date).isoformat()
        except ValueError as exc:
            print(f"new_part: --date: {exc}", file=sys.stderr)
            return 2
    else:
        date = datetime.date.today().isoformat()

    target = os.path.abspath(os.path.join(args.dir, tokens["PART_SLUG"]))
    if os.path.exists(target) and not args.force:
        print(f"new_part: {target} already exists; pass --force to write into it",
              file=sys.stderr)
        return 1

    try:
        written = scaffold(target, tokens, args.from_template, date)
    except (OSError, FileNotFoundError) as exc:
        print(f"new_part: {exc}", file=sys.stderr)
        return 2

    print(f"  created  {target}")
    print()
    for i, (name, size, origin) in enumerate(written):
        branch = "`--" if i == len(written) - 1 else "|--"
        print(f"    {branch} {name:<28} {size:>6} bytes   ({origin})")
    print()
    print(f"  part name   {tokens['PART_NAME']}")
    print(f"  slug        {tokens['PART_SLUG']}")
    print(f"  constants   {tokens['PART_CONST']}_*")
    print(f"  dated       {date}")
    print()
    print("  NEXT, in this order")
    print("    1. Fill in the FACTS.md rows and put a confidence tag on every number.")
    print("       An untagged number is an assumption that will be read as a measurement.")
    print("    2. List the [OPEN] blockers in FACTS.md section 6, each with the procedure")
    print("       that would close it. Nothing downstream may treat an [OPEN] as known.")
    print(f"    3. Write the parameter table into {tokens['PART_SLUG']}_gen.py, then run:")
    print(f"         blender --background --python-exit-code 1 --python "
          f"{tokens['PART_SLUG']}_gen.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

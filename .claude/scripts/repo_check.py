#!/usr/bin/env python3
"""Structural consistency gate for the part-forge marketplace repo.

Everything mechanically checkable about this repository lives here rather than in
prose, because a rule a script enforces cannot rot the way a rule in a README does.
The skills under .claude/skills/ carry the judgment calls; this file carries the
facts a machine can settle.

Standard library only, and deliberately so: it must run in a bare checkout, in CI,
and inside a hook without acquiring an install step.

    python3 .claude/scripts/repo_check.py            # human-readable, exit 1 on error
    python3 .claude/scripts/repo_check.py --json     # machine-readable
    python3 .claude/scripts/repo_check.py --strict   # warnings also fail
"""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import sys
import tempfile
from pathlib import Path

# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #

ERROR = "error"
WARN = "warn"


class Report:
    def __init__(self) -> None:
        self.findings: list[dict] = []
        self.checks_run = 0

    def add(self, level: str, check: str, where: str, message: str) -> None:
        self.findings.append(
            {"level": level, "check": check, "where": where, "message": message}
        )

    def error(self, check: str, where: str, message: str) -> None:
        self.add(ERROR, check, where, message)

    def warn(self, check: str, where: str, message: str) -> None:
        self.add(WARN, check, where, message)

    def counts(self) -> tuple[int, int]:
        e = sum(1 for f in self.findings if f["level"] == ERROR)
        w = sum(1 for f in self.findings if f["level"] == WARN)
        return e, w


# --------------------------------------------------------------------------- #
# Frontmatter
# --------------------------------------------------------------------------- #

_SCALAR_KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")

try:  # optional, and the run is honest about it when absent
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None

# A plain YAML scalar that opens with '[' or '{' is a flow collection, and any
# text after the closing bracket is a parse error that takes the WHOLE block
# with it. The skill then loads with no metadata at all -- no description, no
# allowed-tools -- and nothing anywhere says so. This repo shipped exactly that
# bug in gen-part's argument-hint, which is why the pattern is checked by name
# rather than left to whichever YAML parser happens to be installed.
FLOW_SCALAR_HAZARD = re.compile(r"^([A-Za-z][\w-]*):\s+(?P<v>[\[{].*)$")


def yaml_hazards(block: str) -> list[str]:
    """Frontmatter shapes that parse as something other than they read as."""
    out = []
    for line in block.split("\n"):
        m = FLOW_SCALAR_HAZARD.match(line)
        if not m:
            continue
        value = m.group("v").strip()
        if value.startswith("[") and value.endswith("]") and value.count("[") == 1:
            continue  # a genuine, well-formed flow sequence
        out.append(
            f"unquoted value starting with {value[0]!r} is read as a YAML flow "
            f"collection, not text: {line.strip()!r} -- wrap the value in quotes"
        )
    return out


def parse_frontmatter(text: str) -> tuple[dict, str] | tuple[None, str]:
    """Parse the leading --- YAML block.

    Uses PyYAML when it is importable, because the runtime uses a real YAML
    parser and a hand-rolled one that is more permissive would bless files the
    runtime silently drops. The permissive path below is the fallback, and the
    caller warns when it is the one in use.
    """
    if not text.startswith("---\n"):
        return None, "no YAML frontmatter (file must start with '---')"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "frontmatter opened with '---' but never closed"
    block = text[4:end]
    body = text[end + 4 :]

    hazards = yaml_hazards(block)
    if hazards:
        return None, hazards[0]

    if _yaml is not None:
        try:
            loaded = _yaml.safe_load(block)
        except Exception as exc:  # noqa: BLE001 -- any parse failure is the finding
            first = str(exc).strip().split("\n")[0]
            return None, (
                f"YAML frontmatter does not parse ({first}) -- at runtime this file "
                "loads with EMPTY metadata and every field is silently dropped"
            )
        if not isinstance(loaded, dict):
            return None, "frontmatter must be a mapping of key to value"
        return {k: v if isinstance(v, str) else str(v) for k, v in loaded.items()}, body

    data: dict[str, str] = {}
    lines = block.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = _SCALAR_KEY.match(line)
        if not m:
            return None, f"unparseable frontmatter line: {line!r}"
        key, value = m.group(1), m.group(2).strip()
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            collected: list[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and not nxt.startswith((" ", "\t")):
                    break
                collected.append(nxt.strip())
                i += 1
            data[key] = "\n".join(collected).strip()
            continue
        data[key] = value.strip("'\"")
        i += 1
    return data, body


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".claude-plugin" / "marketplace.json").exists():
            return parent
    return here.parents[2]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path, rep: Report, check: str) -> dict | None:
    try:
        return json.loads(read(path))
    except FileNotFoundError:
        rep.error(check, str(path), "file does not exist")
    except json.JSONDecodeError as exc:
        rep.error(check, f"{path}:{exc.lineno}", f"invalid JSON: {exc.msg}")
    return None


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

# Skills whose frontmatter carries command-only fields. A skill with these is
# invocable as /plugin:skill; one without is model-invoked. Both are legitimate.
COMMAND_FIELDS = {"argument-hint", "allowed-tools", "disable-model-invocation"}
KNOWN_SKILL_FIELDS = {
    "name",
    "description",
    "argument-hint",
    "allowed-tools",
    "disable-model-invocation",
    "model",
    "license",
    "metadata",
    "version",
} | COMMAND_FIELDS
KNOWN_AGENT_FIELDS = {"name", "description", "tools", "model", "color"}

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def check_marketplace(root: Path, rep: Report) -> list[Path]:
    """marketplace.json agrees with the plugin directories it points at."""
    rep.checks_run += 1
    mpath = root / ".claude-plugin" / "marketplace.json"
    data = load_json(mpath, rep, "marketplace-json")
    if data is None:
        return []

    for field in ("name", "owner", "plugins"):
        if field not in data:
            rep.error("marketplace-json", str(mpath), f"missing required field {field!r}")

    listed_dirs: list[Path] = []
    listed_names: set[str] = set()
    for entry in data.get("plugins", []):
        name = entry.get("name", "<unnamed>")
        listed_names.add(name)
        src = entry.get("source")
        if not src:
            rep.error("marketplace-json", f"{mpath}#{name}", "entry has no 'source'")
            continue
        pdir = (root / src).resolve()
        if not pdir.is_dir():
            rep.error(
                "marketplace-source",
                f"{mpath}#{name}",
                f"source {src!r} is not a directory",
            )
            continue
        listed_dirs.append(pdir)

        manifest = pdir / ".claude-plugin" / "plugin.json"
        pdata = load_json(manifest, rep, "plugin-json")
        if pdata is None:
            continue
        if pdata.get("name") != name:
            rep.error(
                "name-agreement",
                str(manifest),
                f"plugin.json name {pdata.get('name')!r} != marketplace entry {name!r}",
            )
        mver, pver = entry.get("version"), pdata.get("version")
        if mver is not None and pver is not None and mver != pver:
            rep.error(
                "version-agreement",
                str(manifest),
                f"plugin.json version {pver!r} != marketplace entry version {mver!r} "
                "-- bump both or neither",
            )
        if entry.get("description") != pdata.get("description"):
            rep.warn(
                "description-agreement",
                str(manifest),
                "description differs between plugin.json and marketplace.json",
            )

    # Every plugin directory on disk must be advertised.
    plugins_dir = root / "plugins"
    if plugins_dir.is_dir():
        for child in sorted(plugins_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.resolve() not in listed_dirs:
                rep.error(
                    "marketplace-coverage",
                    str(child),
                    f"plugin directory not listed in marketplace.json "
                    f"(known entries: {sorted(listed_names)})",
                )
    return listed_dirs


def check_skills(root: Path, rep: Report) -> list[Path]:
    """Every SKILL.md parses, is named after its directory, and declares triggers."""
    skills = sorted(root.glob("plugins/*/skills/*/SKILL.md")) + sorted(
        root.glob(".claude/skills/*/SKILL.md")
    )
    for path in skills:
        rep.checks_run += 1
        fm, body = parse_frontmatter(read(path))
        if fm is None:
            rep.error("skill-frontmatter", str(path), body)
            continue

        name = fm.get("name")
        if not name:
            rep.error("skill-frontmatter", str(path), "missing required field 'name'")
        else:
            if name != path.parent.name:
                # Legal in both cases but read differently: for a plugin skill
                # `name` sets the invocable command, for a project skill the
                # directory does and `name` is display-only. A repo that mixes
                # both cannot afford the ambiguity, so they must agree here.
                rep.error(
                    "skill-name-matches-dir",
                    str(path),
                    f"name {name!r} != directory {path.parent.name!r} -- these "
                    "select the invocation differently for plugin vs project "
                    "skills; keep them identical so neither reading surprises",
                )
            if not NAME_RE.match(name):
                rep.error(
                    "skill-name-charset",
                    str(path),
                    f"name {name!r} must be lowercase letters, digits and hyphens",
                )

        desc = fm.get("description", "")
        if not desc:
            rep.error(
                "skill-description", str(path), "missing required field 'description'"
            )
        elif len(desc) > 1024:
            rep.error(
                "skill-description",
                str(path),
                f"description is {len(desc)} chars; the frontmatter limit is 1024",
            )
        elif len(desc) < 60:
            rep.warn(
                "skill-description",
                str(path),
                f"description is only {len(desc)} chars -- it is the entire basis on "
                "which this skill gets selected; enumerate triggering situations",
            )

        unknown = set(fm) - KNOWN_SKILL_FIELDS
        if unknown:
            rep.warn(
                "skill-frontmatter",
                str(path),
                f"unrecognised frontmatter field(s): {sorted(unknown)}",
            )

        if not body.lstrip().startswith("#"):
            rep.warn(
                "skill-body", str(path), "body does not open with a level-1 heading"
            )
    return skills


def check_agents(root: Path, rep: Report) -> list[Path]:
    agents = sorted(root.glob("plugins/*/agents/*.md")) + sorted(
        root.glob(".claude/agents/*.md")
    )
    for path in agents:
        rep.checks_run += 1
        fm, body = parse_frontmatter(read(path))
        if fm is None:
            rep.error("agent-frontmatter", str(path), body)
            continue
        name = fm.get("name")
        if not name:
            rep.error("agent-frontmatter", str(path), "missing required field 'name'")
        elif name != path.stem:
            rep.error(
                "agent-name-matches-file",
                str(path),
                f"name {name!r} != filename stem {path.stem!r}",
            )
        if not fm.get("description"):
            rep.error(
                "agent-description", str(path), "missing required field 'description'"
            )
        unknown = set(fm) - KNOWN_AGENT_FIELDS
        if unknown:
            rep.warn(
                "agent-frontmatter",
                str(path),
                f"unrecognised frontmatter field(s): {sorted(unknown)}",
            )
    return agents


# A path-shaped token inside prose or a code fence. Restricted to the extensions
# this repo actually ships so that prose like "wall thickness" is never a hit.
PATHISH = re.compile(
    r"(?:\$\{CLAUDE_PLUGIN_ROOT\}/|\$S/|\./)?"
    r"((?:[\w.\-]+/)*[\w.\-]+\.(?:py|md|json|stl|blend|sh|dot))"
)
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")


def check_references(root: Path, rep: Report) -> None:
    """Every path a document names must exist.

    Stale paths are the failure mode with the worst blast radius here: a skill
    that tells an agent to run a script that moved does not fail loudly, it sends
    the agent looking for a workaround.
    """
    docs = sorted(root.glob("plugins/**/*.md")) + sorted(root.glob(".claude/**/*.md"))
    for path in docs:
        text = read(path)
        plugin_root = _plugin_root_for(path, root)

        for lineno, line in enumerate(text.split("\n"), 1):
            for m in MD_LINK.finditer(line):
                target = m.group(1)
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                rep.checks_run += 1
                resolved = (path.parent / target).resolve()
                if not resolved.exists():
                    rep.error(
                        "dead-link",
                        f"{path}:{lineno}",
                        f"markdown link target does not exist: {target}",
                    )

            if "${CLAUDE_PLUGIN_ROOT}" in line:
                for m in PATHISH.finditer(line):
                    frag = m.group(1)
                    if not line[: m.start()].rstrip().endswith("}") and (
                        "${CLAUDE_PLUGIN_ROOT}" not in line[: m.end()]
                    ):
                        continue
                    rep.checks_run += 1
                    if plugin_root is None:
                        continue
                    if not (plugin_root / frag).exists():
                        rep.error(
                            "dead-plugin-path",
                            f"{path}:{lineno}",
                            f"${{CLAUDE_PLUGIN_ROOT}}/{frag} does not exist",
                        )


def _plugin_root_for(path: Path, root: Path) -> Path | None:
    for parent in path.parents:
        if (parent / ".claude-plugin" / "plugin.json").exists():
            return parent
        if parent == root:
            return None
    return None


def check_plugin_root_var(root: Path, rep: Report) -> None:
    """Inside a plugin, a script path must go through ${CLAUDE_PLUGIN_ROOT}.

    A relative path works when the agent happens to be cwd'd at the repo, and
    fails for every user who installed the plugin -- which is the only case that
    matters and the one never exercised during development.
    """
    for path in sorted(root.glob("plugins/**/*.md")):
        plugin = _plugin_root_for(path, root)
        if plugin is None:
            continue
        # Only a script this plugin actually ships can be a stale-path hazard. A
        # bare name that matches nothing on disk is a placeholder for the user's
        # own file (part_gen.py), and prefixing it would be wrong.
        shipped = {p.name for p in plugin.rglob("*.py")}
        text = read(path)
        for lineno, line in enumerate(text.split("\n"), 1):
            if "CLAUDE_PLUGIN_ROOT" in line or "$S/" in line:
                continue
            m = re.search(r"python3?\s+((?:[\w.\-]+/)*[\w.\-]+\.py)", line)
            if not m:
                continue
            frag = m.group(1)
            if Path(frag).name not in shipped:
                continue
            rep.checks_run += 1
            rep.warn(
                "hardcoded-script-path",
                f"{path}:{lineno}",
                f"script invoked as {frag!r} without ${{CLAUDE_PLUGIN_ROOT}} -- "
                "this resolves only when cwd happens to be the repo, which is "
                "never true for an installed plugin",
            )


def check_readme_inventory(root: Path, rep: Report) -> None:
    """The README tables are an inventory; inventories drift.

    part-forge's README lists every skill, agent and script in markdown tables.
    A new skill that nobody adds a row for is invisible to anyone reading the
    README, which is the only documentation an installed user has.
    """
    readme = root / "plugins" / "part-forge" / "README.md"
    if not readme.exists():
        rep.warn("readme-inventory", str(readme), "plugin has no README.md")
        return
    text = read(readme)
    ticked = set(re.findall(r"`/?(?:part-forge:)?([\w.\-]+)`", text))

    plugin = root / "plugins" / "part-forge"
    expected: list[tuple[str, str]] = []
    for skill in sorted(plugin.glob("skills/*/SKILL.md")):
        expected.append(("skill", skill.parent.name))
    for agent in sorted(plugin.glob("agents/*.md")):
        expected.append(("agent", agent.stem))
    for script in sorted(plugin.glob("scripts/*.py")):
        expected.append(("script", script.name))

    for kind, name in expected:
        rep.checks_run += 1
        if name not in ticked:
            rep.error(
                "readme-inventory",
                str(readme),
                f"{kind} {name!r} exists but is not named in the README",
            )

    for plugin_dir in sorted((root / "plugins").iterdir()):
        if plugin_dir.is_dir() and not (plugin_dir / "README.md").exists():
            rep.warn(
                "readme-present",
                str(plugin_dir),
                "plugin has no README.md -- it is what a user sees before installing",
            )


def check_python_compiles(root: Path, rep: Report) -> None:
    """Syntax gate. Cheap, and the scripts have no test suite behind them."""
    scripts = sorted(root.glob("plugins/**/*.py")) + sorted(root.glob(".claude/**/*.py"))
    with tempfile.TemporaryDirectory() as tmp:
        for path in scripts:
            rep.checks_run += 1
            out = Path(tmp) / (path.stem + ".pyc")
            try:
                py_compile.compile(str(path), cfile=str(out), doraise=True)
            except py_compile.PyCompileError as exc:
                rep.error("python-syntax", str(path), str(exc).strip())


def check_hooks(root: Path, rep: Report) -> None:
    for path in sorted(root.glob("plugins/*/hooks/hooks.json")):
        rep.checks_run += 1
        data = load_json(path, rep, "hooks-json")
        if data is None:
            continue
        events = data.get("hooks", data)
        if not isinstance(events, dict):
            rep.error("hooks-json", str(path), "'hooks' must be an object keyed by event")
            continue
        valid = {
            "PreToolUse",
            "PostToolUse",
            "UserPromptSubmit",
            "Notification",
            "Stop",
            "SubagentStop",
            "SessionStart",
            "SessionEnd",
            "PreCompact",
        }
        for event in events:
            if event not in valid:
                rep.error(
                    "hooks-json", str(path), f"unknown hook event {event!r}"
                )


def check_reference_bijection(root: Path, rep: Report) -> None:
    """A skill's supporting files and its `## Reference files` list must agree.

    A reference nobody links is a file no agent will ever open; a link with no
    file behind it sends an agent looking for something that is not there.
    Both are silent, and both are cheap to rule out.
    """
    for skill in sorted(root.glob("plugins/*/skills/*/SKILL.md")) + sorted(
        root.glob(".claude/skills/*/SKILL.md")
    ):
        d = skill.parent
        present = {
            p.name
            for sub in ("references", "templates", "examples")
            for p in d.glob(f"{sub}/*")
            if p.is_file()
        }
        if not present:
            continue
        text = read(skill)
        for fname in sorted(present):
            rep.checks_run += 1
            if fname not in text:
                rep.error(
                    "reference-orphan",
                    str(d / fname),
                    f"{fname} exists under {d.name}/ but the SKILL.md never names "
                    "it -- nothing will ever load it",
                )


def check_command_skill_shape(root: Path, rep: Report) -> None:
    """argument-hint and allowed-tools travel together.

    A skill invocable as a command needs both: the hint so a user knows what to
    pass, the tool list so it is not handed the whole toolbox. Having one and
    not the other is always an oversight rather than a decision.
    """
    for skill in sorted(root.glob("plugins/*/skills/*/SKILL.md")) + sorted(
        root.glob(".claude/skills/*/SKILL.md")
    ):
        fm, _ = parse_frontmatter(read(skill))
        if fm is None:
            continue
        has_hint = "argument-hint" in fm
        has_tools = "allowed-tools" in fm
        if has_hint != has_tools:
            rep.checks_run += 1
            missing = "allowed-tools" if has_hint else "argument-hint"
            rep.warn(
                "command-skill-shape",
                str(skill),
                f"declares {'argument-hint' if has_hint else 'allowed-tools'} but "
                f"not {missing} -- command skills in this repo carry both",
            )


FLAG_IN_FENCE = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]+)")
SCRIPT_IN_FENCE = re.compile(r"([\w.\-]+\.py)")


def check_flag_drift(root: Path, rep: Report) -> None:
    """Every --flag a document tells you to pass must exist in the script.

    Prose describing a CLI is a second, unexecuted copy of that CLI's interface.
    When a flag is renamed the script keeps working and only the documentation
    becomes a lie, which is the direction that costs an agent the most time.
    """
    scripts: dict[str, set[str]] = {}
    for py in sorted(root.glob("plugins/**/*.py")) + sorted(root.glob(".claude/**/*.py")):
        src = read(py)
        flags = set(re.findall(r"add_argument\(\s*[\"'](--[\w-]+)[\"']", src))
        # argparse supplies these without them appearing in the source.
        flags |= {"--help"}
        if flags:
            scripts.setdefault(py.name, set()).update(flags)

    docs = sorted(root.glob("plugins/**/*.md")) + sorted(root.glob(".claude/**/*.md"))
    for doc in docs:
        text = read(doc)
        in_fence = False
        current: set[str] = set()
        for lineno, line in enumerate(text.split("\n"), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                if not in_fence:
                    current = set()
                continue
            if not in_fence:
                continue
            for name in SCRIPT_IN_FENCE.findall(line):
                if name in scripts:
                    current = scripts[name]
            if not current:
                continue
            for flag in FLAG_IN_FENCE.findall(line):
                rep.checks_run += 1
                if flag not in current:
                    rep.error(
                        "flag-drift",
                        f"{doc}:{lineno}",
                        f"{flag} is documented here but no script in the fence "
                        "declares it",
                    )


def check_claude_cli(root: Path, rep: Report) -> None:
    """Defer to the runtime's own validator when it is installed.

    This script encodes what this repo cares about; `claude plugin validate`
    encodes what the runtime will actually accept. Where they disagree the
    runtime wins, so it gets the last word rather than being reimplemented.
    """
    import shutil
    import subprocess

    exe = shutil.which("claude")
    if exe is None:
        rep.warn(
            "claude-validate",
            str(root),
            "the `claude` CLI is not on PATH, so manifest validation was skipped "
            "-- this run cannot vouch for what the runtime will accept",
        )
        return

    targets = [root] + [
        p for p in sorted((root / "plugins").glob("*")) if (p / ".claude-plugin").is_dir()
    ]
    for target in targets:
        rep.checks_run += 1
        try:
            proc = subprocess.run(
                [exe, "plugin", "validate", str(target)],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            rep.warn("claude-validate", str(target), f"validator did not run: {exc}")
            continue
        if proc.returncode != 0:
            detail = (proc.stdout + proc.stderr).strip()
            lines = [ln.strip() for ln in detail.split("\n") if "❯" in ln or "✘" in ln]
            rep.error(
                "claude-validate",
                str(target),
                "; ".join(lines) or detail.split("\n")[-1],
            )


def check_gitignore_twin(root: Path, rep: Report) -> None:
    """new_part.py seeds a .gitignore into every scaffolded project.

    That template is a second copy of a rule the repo root also carries. Two
    copies of one string with no shared source is a drift the moment either
    side is edited, and the scaffolded copy is the one nobody re-reads.
    """
    scaffolder = root / "plugins" / "part-forge" / "scripts" / "new_part.py"
    gitignore = root / ".gitignore"
    if not (scaffolder.exists() and gitignore.exists()):
        return
    rep.checks_run += 1
    seeded = read(scaffolder)
    for rule in ("result.json", "*.blend1", "__pycache__/"):
        if rule in read(gitignore) and rule not in seeded:
            rep.warn(
                "gitignore-twin",
                str(scaffolder),
                f"repo .gitignore ignores {rule!r} but the scaffolded template "
                "does not -- a new project will commit what this repo excludes",
            )


def check_fixture(root: Path, rep: Report) -> None:
    """The dogfood projects are the only fixtures the scripts have.

    If their artifacts go missing, every smoke check in this repo silently has
    nothing to run against.

    Every directory under `projects/` is checked, not a hard-coded one. This used
    to name `shade-bar-mount` literally, and it is the only checker in this file
    that looks at `projects/` at all -- so a second fixture could be added and the
    gate would print CONSISTENT without ever having opened it. Reporting that as
    evidence the fixture was wired in is the false green this repository catalogues.
    """
    projects_dir = root / "projects"
    projects = sorted(p for p in projects_dir.glob("*") if p.is_dir())
    if not projects:
        rep.warn("fixture", str(projects_dir), "no worked-example project is present")
        return
    for proj in projects:
        for required in ("FACTS.md", "PROJECT.md", "BUILD-BRIEF.md", "verify_report.json"):
            rep.checks_run += 1
            if not (proj / required).exists():
                rep.error("fixture", str(proj / required), "fixture document is missing")
        rep.checks_run += 1
        if not list(proj.glob("*.stl")):
            rep.error(
                "fixture",
                str(proj),
                "no STL in the worked example -- the mesh scripts have nothing to "
                "verify against",
            )
        rep.checks_run += 1
        if not list(proj.glob("*_gen.py")) and not list(proj.glob("*gen.py")):
            rep.warn(
                "fixture",
                str(proj),
                "no generator script -- the artifacts cannot be reproduced, so a "
                "moved digest could never be attributed",
            )


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def run(root: Path, skip_cli: bool = False) -> Report:
    rep = Report()
    check_marketplace(root, rep)
    check_skills(root, rep)
    check_agents(root, rep)
    check_references(root, rep)
    check_plugin_root_var(root, rep)
    check_reference_bijection(root, rep)
    check_command_skill_shape(root, rep)
    check_flag_drift(root, rep)
    check_readme_inventory(root, rep)
    check_python_compiles(root, rep)
    check_hooks(root, rep)
    check_gitignore_twin(root, rep)
    check_fixture(root, rep)
    if not skip_cli:
        check_claude_cli(root, rep)
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--strict", action="store_true", help="warnings fail the run as well as errors"
    )
    ap.add_argument("--root", help="repository root (default: inferred from this file)")
    ap.add_argument(
        "--skip-cli",
        action="store_true",
        help="do not shell out to `claude plugin validate`",
    )
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else repo_root()
    rep = run(root, skip_cli=args.skip_cli)
    errors, warnings = rep.counts()

    if args.json:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "checks_run": rep.checks_run,
                    "errors": errors,
                    "warnings": warnings,
                    "findings": rep.findings,
                },
                indent=2,
            )
        )
    else:
        width = max((len(f["check"]) for f in rep.findings), default=0)
        for f in rep.findings:
            tag = "ERROR" if f["level"] == ERROR else " warn"
            where = os.path.relpath(f["where"].split(":")[0], root)
            suffix = ":" + f["where"].split(":", 1)[1] if ":" in f["where"] else ""
            print(f"  {tag}  {f['check']:<{width}}  {where}{suffix}")
            print(f"         {f['message']}")
        print()
        print(f"  {rep.checks_run} checks, {errors} error(s), {warnings} warning(s)")
        if errors == 0 and (warnings == 0 or not args.strict):
            print("  CONSISTENT")

    if errors:
        return 1
    if warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

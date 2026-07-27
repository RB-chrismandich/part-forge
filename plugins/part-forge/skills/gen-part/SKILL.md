---
name: gen-part
description: Run a parametric part generator in Blender, report every acceptance check, and export only the variants that pass. Reports measured-versus-expected numbers rather than a pass count, and independently re-audits the exported files outside Blender.
argument-hint: "[path/to/part_gen.py] [--out DIR] [--no-export]"
allowed-tools: Bash, Read, Glob, Grep, Skill
---

# Run a generator behind its gate

The generator prints a verdict. That verdict is only worth as much as the checks behind it, so
this command surfaces the numbers and then verifies the output a second time by a different
route.

## Step 1 - locate the generator

Take the path from `$ARGUMENTS`. If none was given, glob for `*_gen.py` under `projects/` and
under the current directory. On exactly one match, use it. On several, list them and ask. On
none, say so and suggest `/part-forge:new-part`.

Read the generator's module docstring and its parameter block before running anything. Report
the parameter values that will be used, and flag any constant whose comment marks it unverified,
assumed, or open — those are the ones that decide whether the run is worth doing.

## Step 2 - find Blender

```bash
BL=$(command -v blender \
  || ls /Applications/Blender.app/Contents/MacOS/Blender 2>/dev/null \
  || ls /Applications/Blender*.app/Contents/MacOS/Blender 2>/dev/null | head -1)
"$BL" --version | head -1
```

If Blender is absent, stop and say so. Do not attempt to generate geometry another way — the
generator is Blender Python and there is no substitute path.

## Step 3 - run headless, with the exit code wired up

```bash
SADDLE_OUT_DIR=./out "$BL" --background --python-exit-code 1 --python projects/part/part_gen.py
```

`--python-exit-code 1` is not optional. Without it Blender returns 0 even when the script
raises, and a failed build reports success. If the generator reads a different output-directory
variable, use that name — check its `out_dir()` equivalent rather than assuming.

Capture the full output. Blender prints a great deal of unrelated startup noise; the report
section is what matters.

## Step 4 - report the numbers, not the count

From the run output and `verify_report.json`, report:

- Every **failing** check with its measured value, its expected value, and the tolerance.
- Any variant that was **refused**, and which gate refused it — the mesh tier or the file tier.
- The quantities the generator marks **reported, not gated**. State them separately and say so
  explicitly. A passing count is not coverage, and a reader who sees only the count will assume
  these were enforced.
- The **vertex digest** per variant, so the run can be compared against a later one.
- Anything that passed but sits close to its limit: minimum wall within 10% of the required
  floor, safety factor within 20% of the minimum, a dimension at the edge of its envelope.

Do not report "165 of 165 passed" as the headline. Report what was measured and what it came to.
If a check group reports how many stations it tested versus skipped, say so — a check that
skipped every station passed without looking.

## Step 5 - audit the exports independently

For each exported file, run the headless auditor. It shares no code with the generator, which is
the point: two implementations agreeing from different evidence is a much stronger claim than
either alone.

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"
for f in out/*.stl; do
  python3 "$S/mesh_audit.py" "$f" --gate --json "${f%.stl}_audit.json" || echo "GATE FAILED: $f"
done
```

Reconcile the two reports. If the generator's volume and the auditor's volume disagree beyond
float noise, or the body counts differ, that discrepancy is the finding — investigate it before
reporting success. A disagreement here is exactly the class of defect this whole arrangement
exists to catch.

## Step 6 - verdict

State plainly: which variants exported, which were refused and why, which numbers are close to
their limits, and what the next step is. If everything passed, say so without hedging. If
anything failed, quote the measured and expected values rather than describing the failure.

Recommend `/part-forge:verify-part` with a render pass when a wall or overhang number is
marginal — a section view shows what a scalar cannot.

## Notes

- Never edit the generator to make a check pass. If a check is wrong, say which check and why;
  changing the expectation to match the measurement is how a gate stops being a gate.
- `--no-export` in `$ARGUMENTS` means run the verification only. Honour it by setting the
  generator's export flag if it exposes one; if it does not, say so rather than editing the file.
- If the run raises, report the traceback's own message. The generator's asserts are written to
  name the physical consequence, so the message is usually the diagnosis.

# Invocation and export

Everything between "the geometry is right" and "the file on disk is right". Most of what
goes wrong here is silent, which is why each section names the symptom.

## Two invocation modes

### Headless

```bash
blender --background --python-exit-code 1 --python part_gen.py
```

This is how a build should run: no GUI, no saved state, reproducible from nothing.

### Live session

```python
exec(open("part_gen.py").read())
```

This is how a Blender MCP connection runs a generator -- the script text is pushed into an
already-running interpreter attached to an open session. It matters for two reasons. The
first is that `__file__` does not exist, so any path resolution based on it raises
`NameError`. The second is that the session is dirty: objects, materials and meshes from
previous runs are present, so the script must purge by name before building rather than
assuming an empty scene.

A generator that supports only the first mode cannot be driven interactively. A generator
that supports only the second cannot be automated. Support both and say so in the docstring.

## `--python-exit-code 1` is not optional

**Symptom when missing:** every failed build reports success.

Blender's default behaviour is to print a Python traceback and exit 0. The script raised, the
part was never built, and the exit code says everything is fine. Any caller that trusts exit
codes -- a shell loop, a Makefile, CI, an agent running the build -- will proceed to the next
step on a build that did not happen.

`--python-exit-code 1` makes an unhandled exception exit 1. Put it in the docstring next to
the invocation line, and put a comment on the `sys.exit` at the bottom explaining why the
flag matters, because the flag lives in the caller and the reason lives in the script.

```python
if __name__ == "__main__":
    sys.exit(0 if main() else 1)
```

Note the two distinct failure channels: a raise gives exit 1 via the flag, and a clean run
whose acceptance list failed gives exit 1 via the return value. Both must be non-zero, and
they are different situations -- the first is a broken script, the second is a broken part.

## Resolving the output directory

Three cases have to work: headless from the script's own directory, headless with the output
redirected somewhere else, and `exec()` where `__file__` is undefined.

```python
def out_dir():
    env = os.environ.get("PARTNAME_OUT_DIR")
    if env:
        os.makedirs(env, exist_ok=True)
        return env
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:          # exec()'d into a live session
        return os.getcwd()
```

Environment variable first, so a caller can redirect without editing the script. The
`NameError` fallback is not defensive padding; it is the live-session path, and omitting it
means the generator cannot be driven over MCP at all.

The same three-case problem applies to locating a shared library like `part_kit.py`. The
template resolves it through an environment variable, then a path relative to `__file__`,
then a value baked in at scaffold time -- because a generator copied into a part project sits
outside the plugin and cannot walk up to it.

## Units: set the scene, then tell the exporter to leave it alone

```python
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 0.001      # 1 Blender unit == 1 mm
scene.unit_settings.length_unit = "MILLIMETERS"
```

and at export:

```python
bpy.ops.wm.stl_export(..., global_scale=1.0, use_scene_unit=False)
```

**Symptom when wrong:** the part arrives in the slicer at 1000x or 1/1000 of its intended
size, or -- more insidiously -- at exactly the right size on one machine and not another,
because the scene setting was saved into the `.blend` on one and defaulted on the other.

The reasoning: mesh coordinates are already millimetres, because that is the convention the
script declares. `scale_length = 0.001` tells Blender's *UI* how to display those numbers.
`use_scene_unit=True` would tell the exporter to apply that factor as well, scaling
millimetres by 0.001 into metres and writing a part 1000 times too small. Setting it False
with `global_scale=1.0` writes the raw coordinates, which are already correct.

Assert the exported bounding box against the parameter table. It is one line and it catches
every variant of this.

## Bake the coordinate system, keep the object transform at identity

**Symptom when wrong:** a part that looks right in the viewport and exports rotated,
offset, or scaled; or a mesh nobody can reason about six months later.

The part's coordinate system belongs in vertex data. The object's location, rotation and
scale should all read identity at the end of the build:

```python
obj.location = (0.0, 0.0, 0.0)
obj.rotation_euler = (0.0, 0.0, 0.0)
obj.scale = (1.0, 1.0, 1.0)
```

An object-level transform is a transform the exporter may or may not apply depending on
flags, and a transform that every downstream measurement has to remember to compose. A
baked-in **+90 deg X rotation** in particular is the classic signature of an imported mesh --
it is what a Y-up-to-Z-up conversion leaves behind -- and finding one is a reliable sign that
the geometry has no construction history behind it.

Measure in the part's own frame, where the numbers match the parameter table. Only the export
copy moves.

## The disposable export copy

Print orientation and bed placement are properties of the *file*, not of the part. Doing them
to the canonical object means every subsequent measurement is in printer coordinates and
every assertion needs a mental rotation.

```
copy the object and its mesh data
rotate the copy's vertex data into print orientation
drop its minimum along the build axis to zero
centre it in the other two axes
export
delete the copy
```

Order matters: rotate before dropping, or the minimum computed is the wrong one.

`part_kit.export_stl` implements this and returns the exported dimensions, which are worth
recording -- they are the numbers the slicer will show, and they differ from the part's own
bounding box whenever a rotation was applied.

The exporter call in full:

```python
bpy.ops.wm.stl_export(
    filepath=filepath, export_selected_objects=True,
    global_scale=1.0, use_scene_unit=False,
    apply_modifiers=True, ascii_format=False,
    forward_axis="Y", up_axis="Z",
)
```

Binary, not ASCII: an ASCII STL of a 27,000-triangle part is roughly ten times the size and
carries no more information.

## Variants: keyword overrides, and names derived from offsets

Build variants by passing overrides into `derive()` and the build function:

```python
obj, g = build(name=name, d_shelf=D_SHELF + offset)
```

Not by mutating module constants. A mutated constant leaks into the next iteration, and the
second variant is then built from the first variant's state -- a bug that presents as "the
last two exports are identical".

**Derive the file name from the offset, and assert the round trip.**

```python
def variant_name(base, offset):
    if abs(offset) < 1e-9:
        return f"{base}_d0"
    return f"{base}_d{offset:+g}".replace("+", "p").replace("-", "m")

assert abs(_offset_from_name(base, name) - offset) < 1e-9
```

The failure this prevents is specific and was live in the reference: variant names were
written by hand as `part_h-2 / part_h0 / part_h+2` against absolute values `0 / 2 / 4`, with
nothing tying the two together. The names encode an offset from the nominal default, so the
moment that default moves every exported file is mislabelled -- and mislabelled in a way no
geometric check can detect, because each file is individually correct. Somebody prints the
wrong one.

## Gate, write, re-verify, delete on failure

The export sequence, in order, with the reason for each step:

1. **Run the mesh acceptance list.** If it fails, do not export -- and delete any file already
   sitting at that path from a previous run. Otherwise a failing build leaves last week's
   passing STL in place, with a fresh timestamp on the directory and nothing to indicate the
   file is stale. Somebody prints it.
2. **Export.**
3. **Re-parse the file just written** and run the positional checks on those bytes. Not the
   mesh in memory -- the file. This is the step that catches what the in-memory check
   structurally cannot.
4. **On failure, delete the file** and record the variant as refused.

### The window, honestly

Between steps 2 and 4 an unverified file exists on disk. If the process is killed in that
window, a file that has not passed the file-level gate survives.

The alternative is to write to a temporary name and rename on success, which closes the
window -- rename is atomic within a filesystem. It was not chosen, and the tradeoff is worth
stating rather than glossing: temp-then-rename adds a second path to reason about, leaves
temp files behind on a crash in a different way, and complicates the case where the
destination already exists. The window is milliseconds wide and only matters if the process
dies inside it, whereas the stale-file problem in step 1 is a real thing that happens.

Either choice is defensible. An undocumented choice is not, because the next person cannot
tell whether the window was considered or missed.

## What to record

`verify_report.json` should carry, per variant, the full measurement dict, and at the top
level:

- `_exports` -- what was written, with dimensions, triangle count and vertex digest
- `_refused` -- what failed, which gate refused it, and which checks failed
- `_stl` -- the file-level topology per variant

`_refused` being an empty list is a meaningful, positive statement. A report with no such key
cannot distinguish "nothing was refused" from "refusals were not tracked".

## Reproducibility: what the digest is for

Two runs of an unedited generator produce **different files** and **the same solid**.
Verified on the template: two consecutive runs gave file digests `c210a5b7...` and
`a4699451...`, with an identical vertex digest and a volume delta of exactly zero.

The causes are ordinary. Triangle emission order varies because boolean and mesh operators
iterate structures keyed on pointer identity, and the diagonal chosen when triangulating an
ambiguous planar quad can flip between runs. Neither moves a vertex.

So hashing the exported file to answer "did my edit change the part" returns yes every time
and carries no signal. Hash the sorted unique welded vertex set instead, print it per
variant, and diff that. Report it, never gate it -- a legitimate parameter change is supposed
to move it, and a gate on the digest would fail every real edit.

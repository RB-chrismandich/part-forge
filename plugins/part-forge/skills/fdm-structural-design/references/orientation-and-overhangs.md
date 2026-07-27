# Orientation and overhangs

Orientation is chosen once, early, and silently decides both how strong the part is and
whether it can be printed at all. It deserves a paragraph of reasoning in the generator's
docstring, not a line in the slicer profile.

## Layer adhesion is the weak direction

An FDM part is not isotropic. Within a layer the material is continuous extruded polymer.
Between layers it is a thermal weld formed as a cooling bead meets a cooler surface, and that
weld is weaker -- commonly 40 to 70 percent of the in-layer strength, worse with poor cooling
control, worse again with materials that crystallise or absorb moisture.

The consequence for a bending load:

- **Bending carried within layers** loads continuous extrusions in tension and compression.
  The part behaves roughly like the datasheet says.
- **Bending carried across layers** puts the tensile face of the beam directly onto the
  inter-layer welds. The part fails at the weld, well below the material allowable, and it
  fails suddenly -- a delamination crack runs along the layer boundary rather than yielding.

This is why the derating table in `load-models.md` carries a direction term of roughly 0.6,
and why that term is the one that can be *removed* by choosing the orientation rather than
paid for in wall thickness.

## The worked orientation decision

The saddle arm is loaded in bending in the Y-Z plane -- the shade bar pushes down on the
cradle, the mount plate holds the other end, and the arm between them bends.

**Printed tape-face-down** (the intuitive choice, since it gives the largest flat surface on
the bed) the layers stack along the arm's bending axis. The tensile face at the arm root is a
stack of layer boundaries, and the arm root is exactly where the moment is largest. The part
would fail by delamination at its most stressed section.

**Printed on its side** the same bending is carried within layers. The extrusions run along
the arm, in the direction of the tensile stress.

That single choice also removed the supports: on its side the cradle opens sideways rather
than upward, and the overhanging surfaces fall within the printable band. One decision, two
wins -- which is common, because the orientation that puts material along the load usually
also puts the large flat surfaces where the printer wants them.

Record it as a claim with a reason:

```
Print on the side face, not tape-face-down. The arm is loaded in bending in the Y-Z
plane; tape-face-down that bending pulls directly across layer lines at the arm root,
which is where FDM parts fail. On its side the bending is carried within layers, and
it prints without supports.
```

## The coupling nobody expects

Whichever part axis becomes the build axis, **every layer-pitched feature now depends on that
rotation.**

The saddle carries relief grooves pitched at 1.0 mm with a 0.4 mm width, both whole multiples
of the 0.2 mm layer height. That pitch is only meaningful if the grooves are stacked along
the build direction. The export bakes a -90 deg rotation about Y, turning the part's X axis
into the printer's Z -- so the grooves are pitched along X in the model precisely because X
becomes the build axis at export.

Two failure modes follow, and both are silent:

**A pitch that is not a whole number of layers.** The groove drifts relative to the layer
boundaries, so consecutive grooves land at different phases within a layer. Some become
crisp, some become a smear across two layers, and the surface reads as a printing defect
rather than a feature. Assert the integer relationship in `derive()`, before any geometry
exists:

```python
assert abs(RIB_PITCH / LAYER_H - round(RIB_PITCH / LAYER_H)) < 1e-9, \
    "rib pitch must be a whole number of layers or the grooves will not land on layer lines"
```

**A half-layer phase error.** Even with an integer pitch, the whole comb can sit offset by
half a layer from the boundaries, so every groove is equally wrong. The pitch check passes;
the feature still does not work. Gate the measured distance from each detected edge to its
nearest layer boundary -- the worked example gates this at 1 micron and measures 6.7e-07 mm,
because the feature is either exact or pointless.

And state the coupling at both sites. A comment on the pitch constant that does not mention
the export rotation, and an export function that does not mention the pitch, is two correct
pieces of code with the dependency between them written down nowhere.

## The 45-degree rule is geometry, not a slicer setting

Treating overhangs as something the slicer solves with supports gives up control over the
surface finish exactly where the part is most stressed. Design them out instead.

**Convex erosion by `d` per unit of travel is a 45-degree taper.** Not approximately -- if a
convex profile is inset by `d` on every edge while the sweep advances by `d`, the resulting
surface makes 45 deg with the build direction by construction. Match the erosion to the travel
step and the flare costs nothing to print. `erode_convex()` in `scripts/part_kit.py` is this
operation; its docstring records that the shape constraint and the printability constraint are
satisfied by the same call.

**A collar growing faster than 1:1 along the build axis asks the printer to bridge.** A blend
that gains radius faster than the build advances presents an underside shallower than 45 deg.
Shed radius at no more than 1 mm per mm of build travel and the underside stays printable --
the same rule, applied to a fillet instead of a flare.

**Design the overhang out before designing a support in.** A support that is generated is a
support that must be removed, and removing it leaves scarring.

## Measuring unsupported area rather than assuming it

Intent is not evidence. Measure the delivered geometry.

`mesh_audit.py` uses this definition, stated explicitly because conventions differ:

```
tilt_deg = angle between the face normal and the NEGATIVE build axis

  tilt_deg = 0     flat downward-facing ceiling  -- fully unsupported
  tilt_deg = 45    a 45 deg overhang             -- the usual threshold
  tilt_deg = 90    vertical wall                 -- fully supported

  overhang when tilt_deg < threshold_deg
```

**Slicer interfaces phrase the same threshold as a "support angle", and the numbers agree
while the wording does not.** Setting a slicer's support threshold to 45 and passing
`--overhang-deg 45` here flag the same faces. Do not attempt to convert between them; check
against a known face before trusting a comparison.

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"

python3 "$S/mesh_audit.py" part.stl --build-axis z --overhang-deg 45 --json audit.json
python3 "$S/mesh_render.py" part.stl --overhang --build-axis z
```

**The build axis must match how the part will actually be placed.** An overhang figure
computed against the wrong axis is not conservative or optimistic, it is unrelated. In the
worked example the exported STL is already rotated into print orientation, so `z` is correct
for the file -- but the model's own Z is the part's up, and auditing the unexported mesh with
`--build-axis z` would measure a placement that will never be printed.

Treat the result as reported, not gated. The acceptable unsupported area depends on
orientation, material, cooling, and how visible the surface is -- so gate on nothing and read
the number, with the location it occurs at. The worked example reports 1.17, 9.82 and
4.92 mm^2 across its three variants, all at around x = 17 mm, which is small enough to ignore
and specific enough to find if it ever grows.

## Support scarring lands where the stress is highest

Support removal leaves a rough, partially delaminated surface. On a load-bearing part that
surface is frequently the underside of the most stressed section, because the same geometry
that concentrates stress -- a root, an undercut, a sharp transition -- is what needed support.

So the cost of supports is not only finish and time. Surface roughness is a stress raiser,
and a rough surface at the tensile face of the worst section removes margin exactly where the
calculation said there was least. If a load-bearing surface needs supports, prefer changing
the orientation or the geometry over accepting them.

## Choosing an orientation: a procedure

1. **Identify the load direction.** Where force enters, where it leaves, and its magnitude.
2. **Identify the plane the bending acts in.** For most brackets there is one dominant plane;
   if there are two, the larger moment governs.
3. **Enumerate candidate orientations.** Usually three or four, given a flat face has to meet
   the bed.
4. **Rank by whether the dominant bending is carried within layers or across them.** This
   dominates everything below it. An orientation that puts the tensile face on layer
   boundaries at the worst section is disqualified, not merely worse.
5. **Break ties on support requirement**, weighting supports on load-bearing surfaces much more
   heavily than supports on cosmetic ones.
6. **Break remaining ties on bed footprint and height** -- a wider footprint resists tipping
   during the print, and a shorter part is less exposed to warping and to a knock.
7. **Write the choice and the reason into the generator docstring**, and bake the rotation into
   the export copy's vertex data so the exported file needs no further handling.

Step 4 before step 5 is the ordering that matters. Choosing orientation to avoid supports, and
discovering afterwards that the part delaminates, is the common way round and the expensive
one.

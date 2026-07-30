# When the model came from a generator

If the part was produced by a `part-forge` generator, a `verify_report.json` sits
beside the STL and it has already measured most of what Step 2 asks for -- wall
thickness at the worst station, overhang area, volume, bounding box, and the load
path's safety factor -- against expected values, on the exported bytes. Read it
before running `inspect_model.py` and quote its numbers; it knows which station
is the thin one, a fresh measurement does not.

It does not remove the need for a real slice -- time, mass, and the slicer's own
warnings still require one -- and its overhang figure is computed for the build
axis the generator baked in, so it does not transfer if the part is placed
differently on the bed.

`inspect_model.py` and part-forge's `mesh_audit.py` overlap deliberately. They are
independent implementations reading the same file, and two tools agreeing from
different evidence is a much stronger claim than either alone -- the whole reason
part-forge audits outside Blender is that a single implementation once passed 135
checks on a file Bambu Studio refused to slice. When the two disagree, that
disagreement is the finding. Do not average them; establish which one is measuring
what the slicer will read.

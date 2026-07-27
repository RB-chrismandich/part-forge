#!/usr/bin/env python3
"""Clean, compare, and decimate meshes with PyMeshLab -- and report the cost.

Why this exists
---------------
A repair that silently changes the solid is not a repair. Automatic mesh cleaning
is genuinely useful on imported or scanned geometry, and it is also the easiest
way to ship a part that is subtly not the part you designed: hole-closing invents
material, non-manifold repair deletes faces, decimation moves every vertex a
little. All three leave a mesh that passes a manifold check.

So every operation here reports what it changed and, for `clean`, refuses to
write the output when the volume moved more than a stated fraction. That rule is
borrowed from the reference generator, whose own purge step treats a
volume-altering cleanup as an error rather than a success.

Where this sits in the toolchain
--------------------------------
    mesh_audit.py    diagnoses -- no dependencies, never mutates
    mesh_repair.py   this file  -- mutates, needs pymeshlab
    mesh_render.py   shows      -- needs pyvista

Reach for repair only on geometry you did not generate. If a generator produced a
broken mesh, fix the generator: a cleaned output cannot be regenerated, so the
defect comes back on the next run and the clean step becomes load-bearing.

Usage
-----
    mesh_repair.py clean IN.stl OUT.stl
    mesh_repair.py clean IN.stl OUT.stl --max-hole-size 60 --json clean.json
    mesh_repair.py compare A.stl B.stl
    mesh_repair.py decimate IN.stl OUT.stl --target-faces 20000

Exit codes
----------
    0  done
    1  refused to write -- the operation changed the solid more than allowed
    2  could not read or write a file
    3  pymeshlab is missing (the uvx line is printed)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

# ===========================================================================
#  DEPENDENCIES
# ===========================================================================

def require_pymeshlab():
    """Import pymeshlab or exit 3 with a runnable command.

    pymeshlab is a large binary wheel and not worth installing for a one-off
    cleanup, so the uvx form is offered first.
    """
    try:
        import pymeshlab
        return pymeshlab
    except ImportError:
        pass
    argv = " ".join(sys.argv[1:])
    print("mesh_repair: pymeshlab is not installed", file=sys.stderr)
    print("", file=sys.stderr)
    print("Run it without installing anything:", file=sys.stderr)
    print(f"  uvx --with pymeshlab python {os.path.abspath(__file__)} {argv}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Or install once:", file=sys.stderr)
    print("  python3 -m pip install pymeshlab", file=sys.stderr)
    sys.exit(3)


def try_trimesh():
    """trimesh is optional here: it supplies true per-body volumes, which
    pymeshlab's component filters cannot express."""
    try:
        import trimesh
        return trimesh
    except ImportError:
        return None


# ===========================================================================
#  FILTER NAME COMPATIBILITY
# ===========================================================================

# PyMeshLab renamed most filters in 2022.2. Rather than pin a version, each step
# names the candidates it accepts, newest first, and reports which one ran -- so
# a future rename shows up as a named failure instead of a wrong result.
FILTERS = {
    "duplicate_verts": ("meshing_remove_duplicate_vertices", "remove_duplicate_vertices"),
    "duplicate_faces": ("meshing_remove_duplicate_faces", "remove_duplicate_faces"),
    "null_faces": ("meshing_remove_null_faces", "remove_zero_area_faces"),
    "unreferenced": ("meshing_remove_unreferenced_vertices", "remove_unreferenced_vertices"),
    "small_components": ("meshing_remove_connected_component_by_face_number",
                         "remove_isolated_pieces_wrt_face_num"),
    "nm_edges": ("meshing_repair_non_manifold_edges",
                 "repair_non_manifold_edges_by_removing_faces"),
    "nm_verts": ("meshing_repair_non_manifold_vertices",
                 "repair_non_manifold_vertices_by_splitting"),
    "close_holes": ("meshing_close_holes", "close_holes"),
    "decimate": ("meshing_decimation_quadric_edge_collapse",
                 "simplification_quadric_edge_collapse_decimation"),
    "hausdorff": ("get_hausdorff_distance", "hausdorff_distance"),
}


def apply_filter(ms, key, **params):
    """Run the first filter name that exists. Returns (name, result_or_None).

    A missing filter raises with the full candidate list, because "which
    pymeshlab is this" is the only useful question at that point.
    """
    tried = []
    for name in FILTERS[key]:
        try:
            return name, ms.apply_filter(name, **params)
        except pymeshlab_errors() as exc:
            tried.append(f"{name}: {type(exc).__name__}: {exc}")
    raise RuntimeError(f"no working filter for {key!r}; tried -- " + " | ".join(tried))


def pymeshlab_errors():
    """The exception types pymeshlab raises for an unknown filter or bad params."""
    import pymeshlab
    types = [RuntimeError, ValueError, TypeError]
    for attr in ("PyMeshLabException",):
        exc = getattr(pymeshlab, attr, None)
        if isinstance(exc, type) and issubclass(exc, BaseException):
            types.append(exc)
    return tuple(types)


# ===========================================================================
#  MEASUREMENT
# ===========================================================================

def measure(ms):
    """Every metric worth diffing across an operation.

    Volume is the one that decides whether a clean is accepted, so its absence
    (pymeshlab omits it on a non-watertight mesh) is recorded rather than
    defaulted to zero -- a missing volume must not read as "no change".
    """
    m = ms.current_mesh()
    out = {"vertices": int(m.vertex_number()), "faces": int(m.face_number())}

    try:
        geo = ms.get_geometric_measures()
    except pymeshlab_errors() as exc:
        out["geometric_error"] = repr(exc)
        geo = {}
    out["volume_mm3"] = _num(geo.get("mesh_volume"))
    out["area_mm2"] = _num(geo.get("surface_area"))
    bbox = geo.get("bbox")
    if bbox is not None:
        try:
            out["bbox_min"] = [float(v) for v in bbox.min()]
            out["bbox_max"] = [float(v) for v in bbox.max()]
            out["bbox_diag"] = float(bbox.diagonal())
            out["dims_mm"] = [out["bbox_max"][i] - out["bbox_min"][i] for i in range(3)]
        except (AttributeError, TypeError) as exc:
            out["bbox_error"] = repr(exc)

    try:
        topo = ms.get_topological_measures()
    except pymeshlab_errors() as exc:
        out["topological_error"] = repr(exc)
        topo = {}
    for src, dst in (("non_two_manifold_edges", "non_manifold_edges"),
                     ("non_two_manifold_vertices", "non_manifold_verts"),
                     ("boundary_edges", "boundary_edges"),
                     ("connected_components_number", "components"),
                     ("number_holes", "holes"),
                     ("genus", "genus"),
                     ("unreferenced_vertices", "unreferenced_verts")):
        if src in topo:
            out[dst] = _num(topo[src])
    return out


def _num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def diff_table(before, after):
    """Only the metrics that moved. An unchanged row is noise."""
    rows = []
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        if isinstance(b, list) or isinstance(a, list) or key.endswith("_error"):
            continue
        if b is None and a is None:
            continue
        if b is None or a is None or abs(float(a) - float(b)) > 1e-9:
            rows.append({"metric": key, "before": b, "after": a,
                         "delta": (None if b is None or a is None else float(a) - float(b))})
    return rows


# ===========================================================================
#  COMMAND: clean
# ===========================================================================

def cmd_clean(args):
    pymeshlab = require_pymeshlab()
    if not os.path.isfile(args.infile):
        print(f"mesh_repair: {args.infile}: not found", file=sys.stderr)
        return 2

    report = {"command": "clean", "input": os.path.abspath(args.infile),
              "output": os.path.abspath(args.outfile), "steps": []}

    # Stage 1: drop debris bodies by true volume, which needs trimesh.
    staged, body_info = drop_small_bodies(args.infile, args.min_volume_frac)
    report["body_purge"] = body_info

    ms = pymeshlab.MeshSet()
    try:
        ms.load_new_mesh(staged or args.infile)
    except pymeshlab_errors() as exc:
        print(f"mesh_repair: cannot load {args.infile}: {exc}", file=sys.stderr)
        return 2

    original = measure(ms)
    report["before"] = original
    if body_info.get("dropped"):
        # the purge already happened; record the pre-purge volume for the gate
        report["before"]["volume_mm3_pre_purge"] = body_info.get("volume_before")

    # Stage 2: the pymeshlab chain, in an order that matters -- welding and
    # degenerate removal first, because manifold repair on duplicated geometry
    # deletes real faces to resolve a fault that welding would have removed.
    chain = [
        ("remove duplicate vertices", "duplicate_verts", {}),
        ("remove duplicate faces", "duplicate_faces", {}),
        ("remove zero-area faces", "null_faces", {}),
        ("remove unreferenced vertices", "unreferenced", {}),
        ("repair non-manifold edges", "nm_edges", {}),
        ("repair non-manifold vertices", "nm_verts", {}),
    ]
    if args.max_hole_size > 0:
        chain.append(("close holes", "close_holes", {"maxholesize": args.max_hole_size}))

    for label, key, params in chain:
        pre = measure(ms)
        try:
            name, _ = apply_filter(ms, key, **params)
            status = "ok"
        except (RuntimeError,) + pymeshlab_errors() as exc:
            name, status = FILTERS[key][0], f"skipped: {exc}"
        post = measure(ms)
        report["steps"].append({"step": label, "filter": name, "status": status,
                                "changed": diff_table(pre, post)})

    after = measure(ms)
    report["after"] = after

    # Stage 3: the gate. Compare against the volume the file arrived with.
    base_vol = body_info.get("volume_before") or original.get("volume_mm3")
    delta_pct = None
    if base_vol and after.get("volume_mm3") is not None and base_vol != 0:
        delta_pct = 100.0 * (after["volume_mm3"] - base_vol) / abs(base_vol)
    report["volume_delta_pct"] = delta_pct
    report["max_volume_delta_pct"] = args.max_volume_delta_pct

    refused = None
    if delta_pct is None:
        refused = ("volume could not be measured on one side of the operation, so "
                   "the change cannot be bounded")
    elif abs(delta_pct) > args.max_volume_delta_pct:
        refused = (f"volume moved {delta_pct:+.4f}%, over the {args.max_volume_delta_pct}% "
                   f"limit -- this cleaned a different solid")

    if refused and not args.force:
        report["written"] = False
        report["refused"] = refused
        _emit(report, args, cleanup=staged)
        print(f"\n  REFUSED to write {args.outfile}\n    {refused}"
              f"\n    pass --force to write it anyway", file=sys.stderr)
        return 1

    try:
        ms.save_current_mesh(args.outfile, binary=True)
    except pymeshlab_errors() as exc:
        print(f"mesh_repair: cannot write {args.outfile}: {exc}", file=sys.stderr)
        _cleanup(staged)
        return 2

    report["written"] = True
    report["forced"] = bool(refused and args.force)
    if refused:
        report["refused_but_forced"] = refused
    _emit(report, args, cleanup=staged)
    return 0


def drop_small_bodies(path, min_frac):
    """Remove connected components whose volume is below `min_frac` of the largest.

    pymeshlab can only filter components by face count or diameter, neither of
    which is what "debris" means: a dense speck has many faces and no volume.
    trimesh gives real per-body volumes, so the purge happens here and the result
    is staged to a temp file for the rest of the chain.
    """
    trimesh = try_trimesh()
    if trimesh is None:
        return None, {"available": False,
                      "reason": "trimesh not installed; small-body purge skipped. "
                                "Install trimesh or use pymeshlab's face-count filter."}
    try:
        mesh = trimesh.load(path, force="mesh", process=False)
        bodies = mesh.split(only_watertight=False)
    except (OSError, ValueError, IndexError) as exc:
        return None, {"available": False, "reason": repr(exc)}

    vols = [abs(float(b.volume)) for b in bodies]
    total = float(abs(mesh.volume))
    if len(bodies) <= 1:
        return None, {"available": True, "bodies": len(bodies), "dropped": 0,
                      "volume_before": total,
                      "note": "single body, nothing to purge"}

    biggest = max(vols) if vols else 0.0
    keep = [b for b, v in zip(bodies, vols) if biggest and v >= min_frac * biggest]
    dropped = [v for v in vols if not (biggest and v >= min_frac * biggest)]
    if not dropped:
        return None, {"available": True, "bodies": len(bodies), "dropped": 0,
                      "volume_before": total, "body_volumes_mm3": vols,
                      "note": "all bodies above the threshold; nothing purged"}

    merged = trimesh.util.concatenate(keep) if keep else None
    if merged is None:
        return None, {"available": True, "bodies": len(bodies), "dropped": 0,
                      "volume_before": total,
                      "note": "every body was below the threshold; purge skipped "
                              "rather than emptying the file"}

    fd, staged = tempfile.mkstemp(suffix=".stl", prefix="mesh_repair_")
    os.close(fd)
    merged.export(staged)
    return staged, {
        "available": True,
        "bodies": len(bodies),
        "kept": len(keep),
        "dropped": len(dropped),
        "min_volume_frac": min_frac,
        "body_volumes_mm3": vols,
        "dropped_volumes_mm3": dropped,
        "volume_before": total,
        "volume_dropped_mm3": sum(dropped),
        "staged_file": staged,
    }


# ===========================================================================
#  COMMAND: compare
# ===========================================================================

def cmd_compare(args):
    pymeshlab = require_pymeshlab()
    for p in (args.a, args.b):
        if not os.path.isfile(p):
            print(f"mesh_repair: {p}: not found", file=sys.stderr)
            return 2

    ms = pymeshlab.MeshSet()
    try:
        ms.load_new_mesh(args.a)
        a = measure(ms)
        ms.load_new_mesh(args.b)
        b = measure(ms)
    except pymeshlab_errors() as exc:
        print(f"mesh_repair: cannot load: {exc}", file=sys.stderr)
        return 2

    report = {"command": "compare",
              "a": {"file": os.path.abspath(args.a), **a},
              "b": {"file": os.path.abspath(args.b), **b},
              "delta": diff_table(a, b)}

    # Hausdorff is asymmetric: sampling A against B misses material present only
    # in B. Both directions, and the larger max, is the honest number.
    report["hausdorff"] = {}
    for label, sampled, target in (("a_to_b", 0, 1), ("b_to_a", 1, 0)):
        try:
            name, res = apply_filter(ms, "hausdorff", sampledmesh=sampled,
                                     targetmesh=target, samplenum=args.samples)
            report["hausdorff"][label] = {
                "filter": name,
                "max": _num(res.get("max")) if isinstance(res, dict) else None,
                "mean": _num(res.get("mean")) if isinstance(res, dict) else None,
                "rms": _num(res.get("RMS")) if isinstance(res, dict) else None,
                "min": _num(res.get("min")) if isinstance(res, dict) else None,
            }
        except (RuntimeError,) + pymeshlab_errors() as exc:
            report["hausdorff"][label] = {"available": False, "reason": repr(exc)}

    maxes = [h.get("max") for h in report["hausdorff"].values() if h.get("max") is not None]
    report["max_deviation_mm"] = max(maxes) if maxes else None
    report["verdict"] = _compare_verdict(report, args.same_tol)
    _emit(report, args)
    return 0


def _compare_verdict(report, tol):
    dev = report.get("max_deviation_mm")
    if dev is None:
        return "cannot tell -- Hausdorff unavailable; use mesh_audit.py --compare instead"
    if dev <= tol:
        return (f"geometrically the same solid within {tol} mm "
                f"(max deviation {dev:.6f} mm)")
    return (f"different solids -- max deviation {dev:.4f} mm exceeds {tol} mm. "
            f"Expected if a parameter changed; a defect if nothing did")


# ===========================================================================
#  COMMAND: decimate
# ===========================================================================

def cmd_decimate(args):
    pymeshlab = require_pymeshlab()
    if not os.path.isfile(args.infile):
        print(f"mesh_repair: {args.infile}: not found", file=sys.stderr)
        return 2

    ms = pymeshlab.MeshSet()
    try:
        ms.load_new_mesh(args.infile)
    except pymeshlab_errors() as exc:
        print(f"mesh_repair: cannot load {args.infile}: {exc}", file=sys.stderr)
        return 2

    before = measure(ms)
    try:
        name, _ = apply_filter(ms, "decimate", targetfacenum=args.target_faces,
                               preserveboundary=True, preservenormal=True,
                               planarquadric=True)
    except (RuntimeError,) + pymeshlab_errors() as exc:
        print(f"mesh_repair: decimation failed: {exc}", file=sys.stderr)
        return 2
    after = measure(ms)

    report = {"command": "decimate", "input": os.path.abspath(args.infile),
              "output": os.path.abspath(args.outfile), "filter": name,
              "target_faces": args.target_faces,
              "before": before, "after": after, "changed": diff_table(before, after)}

    if before.get("volume_mm3") and after.get("volume_mm3") is not None:
        report["volume_delta_pct"] = 100.0 * (
            after["volume_mm3"] - before["volume_mm3"]) / abs(before["volume_mm3"])

    try:
        ms.save_current_mesh(args.outfile, binary=True)
    except pymeshlab_errors() as exc:
        print(f"mesh_repair: cannot write {args.outfile}: {exc}", file=sys.stderr)
        return 2

    # What the reduction cost, measured against the original rather than assumed.
    ms2 = pymeshlab.MeshSet()
    try:
        ms2.load_new_mesh(args.infile)
        ms2.load_new_mesh(args.outfile)
        name, res = apply_filter(ms2, "hausdorff", sampledmesh=1, targetmesh=0,
                                 samplenum=args.samples)
        report["hausdorff_cost"] = {
            "filter": name,
            "max_mm": _num(res.get("max")) if isinstance(res, dict) else None,
            "mean_mm": _num(res.get("mean")) if isinstance(res, dict) else None,
            "rms_mm": _num(res.get("RMS")) if isinstance(res, dict) else None,
        }
    except (RuntimeError, OSError) + pymeshlab_errors() as exc:
        report["hausdorff_cost"] = {"available": False, "reason": repr(exc)}

    report["written"] = True
    _emit(report, args)
    return 0


# ===========================================================================
#  REPORTING
# ===========================================================================

def _emit(report, args, cleanup=None):
    if not args.quiet:
        print(render_text(report))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=2)
        if not args.quiet:
            print(f"\n  report -> {args.json}")
    _cleanup(cleanup)


def _cleanup(path):
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def render_text(report):
    L = [f"  command     {report['command']}"]
    for key in ("input", "output", "a", "b"):
        val = report.get(key)
        if isinstance(val, str):
            L.append(f"  {key:<11} {val}")
        elif isinstance(val, dict) and "file" in val:
            L.append(f"  {key:<11} {val['file']}")

    purge = report.get("body_purge")
    if purge:
        if purge.get("available"):
            L.append(f"  bodies      {purge.get('bodies')} found, "
                     f"{purge.get('dropped', 0)} dropped"
                     + (f", {purge['volume_dropped_mm3']:.6f} mm3 removed"
                        if purge.get("volume_dropped_mm3") else ""))
        else:
            L.append(f"  bodies      purge skipped -- {purge.get('reason')}")

    for step in report.get("steps", []):
        marker = " " if step["status"] == "ok" else "!"
        L.append(f"  {marker} {step['step']:<28} {step['filter']}")
        if step["status"] != "ok":
            L.append(f"      {step['status']}")
        for row in step["changed"]:
            L.append(f"      {row['metric']}: {_fmt(row['before'])} -> {_fmt(row['after'])}")

    changed = report.get("changed") or report.get("delta")
    if changed:
        L.append("")
        L.append("  CHANGED")
        for row in changed:
            d = f"  ({row['delta']:+g})" if row.get("delta") is not None else ""
            L.append(f"    {row['metric']:<22} {_fmt(row['before'])} -> {_fmt(row['after'])}{d}")

    haus = report.get("hausdorff")
    if haus:
        L.append("")
        L.append("  HAUSDORFF (mm)")
        for label, h in haus.items():
            if h.get("available") is False:
                L.append(f"    {label:<8} unavailable -- {h.get('reason')}")
            else:
                L.append(f"    {label:<8} max {_fmt(h.get('max'))}  mean {_fmt(h.get('mean'))}"
                         f"  rms {_fmt(h.get('rms'))}")

    cost = report.get("hausdorff_cost")
    if cost:
        if cost.get("available") is False:
            L.append(f"  cost        unavailable -- {cost.get('reason')}")
        else:
            L.append(f"  cost        max {_fmt(cost.get('max_mm'))} mm deviation from the original")

    if report.get("volume_delta_pct") is not None:
        L.append(f"  volume      {report['volume_delta_pct']:+.4f}%"
                 + (f" (limit {report['max_volume_delta_pct']}%)"
                    if "max_volume_delta_pct" in report else ""))

    if report.get("verdict"):
        L.append("")
        L.append(f"  VERDICT     {report['verdict']}")
    if report.get("refused"):
        L.append("")
        L.append(f"  NOT WRITTEN {report['refused']}")
    elif report.get("refused_but_forced"):
        L.append("")
        L.append(f"  FORCED      written despite: {report['refused_but_forced']}")
    elif report.get("written"):
        L.append("")
        L.append("  WRITTEN     output saved")
    return "\n".join(L)


def _fmt(v):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


# ===========================================================================
#  CLI
# ===========================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Clean, compare, and decimate meshes with PyMeshLab, reporting "
                    "what each operation cost.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Needs pymeshlab. If it is not installed the exact uvx command that\n"
               "would work is printed and the exit code is 3.\n"
               "\n"
               "Prefer fixing a generator over cleaning its output: a cleaned mesh\n"
               "cannot be regenerated, so the defect returns on the next run.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--json", metavar="OUT", help="write the full report as JSON")
        p.add_argument("--quiet", action="store_true", help="suppress the text report")

    c = sub.add_parser("clean", help="ordered, reported repair chain",
                       description="Weld, drop degenerate faces, purge debris bodies, "
                                   "repair non-manifold geometry, then close holes. "
                                   "Refuses to write if the solid changed materially.")
    c.add_argument("infile")
    c.add_argument("outfile")
    c.add_argument("--max-hole-size", type=int, default=30, metavar="EDGES",
                   help="largest hole to close, in boundary edges; 0 disables (default 30)")
    c.add_argument("--min-volume-frac", type=float, default=0.001, metavar="FRAC",
                   help="drop bodies below this fraction of the largest body's volume "
                        "(default 0.001)")
    c.add_argument("--max-volume-delta-pct", type=float, default=0.5, metavar="PCT",
                   help="refuse to write if the volume moves more than this (default 0.5)")
    c.add_argument("--force", action="store_true",
                   help="write the output even if the volume gate refused it")
    common(c)
    c.set_defaults(func=cmd_clean)

    m = sub.add_parser("compare", help="is this the same solid?",
                       description="Hausdorff distance both directions plus volume, area "
                                   "and bbox deltas. For checking whether an unedited "
                                   "generator reproduced its own output, mesh_audit.py's "
                                   "vertex digest is cheaper and stricter -- use this for "
                                   "meshes that are meant to differ, where the question is "
                                   "how much.")
    m.add_argument("a")
    m.add_argument("b")
    m.add_argument("--samples", type=int, default=100000, metavar="N",
                   help="Hausdorff sample count (default 100000)")
    m.add_argument("--same-tol", type=float, default=1.0e-4, metavar="MM",
                   help="deviation below which the solids are called the same (default 1e-4)")
    common(m)
    m.set_defaults(func=cmd_compare)

    d = sub.add_parser("decimate", help="reduce face count and report the cost",
                       description="Quadric edge-collapse decimation, followed by a "
                                   "Hausdorff measurement of what the reduction cost.")
    d.add_argument("infile")
    d.add_argument("outfile")
    d.add_argument("--target-faces", type=int, required=True, metavar="N")
    d.add_argument("--samples", type=int, default=100000, metavar="N",
                   help="Hausdorff sample count (default 100000)")
    common(d)
    d.set_defaults(func=cmd_decimate)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

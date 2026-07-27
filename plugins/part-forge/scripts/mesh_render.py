#!/usr/bin/env python3
"""Render a part for review, not for looks. Offscreen, via PyVista.

Why this exists
---------------
A numeric audit tells you a wall is 3.5 mm somewhere; it does not tell you the
saddle mouth is on the wrong side, or that the fillet swallowed the notch. Those
are errors of *form*, and the cheapest detector for them is a picture that a
reviewer — human or multimodal model — can look at once.

So every image here is built to be read rather than admired: parallel projection
so lengths compare directly, plain light background, no dramatic lighting, and
every measurement that the picture implies is also written out as text in a
sidecar JSON. An annotated number nobody can copy is a number nobody can check.

The section view earns its own note. Exterior renders cannot show an internal
void, a pinched root, or the true thickness at the thinnest station. A filled
cross-section can, which makes `--sections` the mode most likely to catch a
defect the audit missed.

Modes
-----
    --views          six orthographic views plus isometric, as a contact sheet
    --sections N     N filled cross-sections along an axis, area annotated
    --thickness      surface coloured by local wall thickness, thin walls flagged
    --overhang       surface coloured by tilt from the build direction

Usage
-----
    mesh_render.py PART.stl --views
    mesh_render.py PART.stl --sections 6 --axis z
    mesh_render.py PART.stl --thickness --clip-below 3.0
    mesh_render.py PART.stl --overhang --build-axis z --overhang-deg 45

Exit codes
----------
    0  rendered
    2  could not read the input
    3  a required optional dependency is missing (the uvx line is printed)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

AXES = {"x": 0, "y": 1, "z": 2}

# Which axis points "up" in the image for a camera looking down each axis.
UP_FOR = {"x": (0.0, 0.0, 1.0), "y": (0.0, 0.0, 1.0), "z": (0.0, 1.0, 0.0)}

# name -> (camera direction from the focal point, up vector)
ORTHO_VIEWS = (
    ("front",  (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    ("back",   (0.0, 1.0, 0.0),  (0.0, 0.0, 1.0)),
    ("left",   (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ("right",  (1.0, 0.0, 0.0),  (0.0, 0.0, 1.0)),
    ("top",    (0.0, 0.0, 1.0),  (0.0, 1.0, 0.0)),
    ("bottom", (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    ("iso",    (1.0, -1.0, 0.8), (0.0, 0.0, 1.0)),
)

BACKGROUND = "white"
SURFACE = "#c8ccd0"
OUTLINE = "#202428"

# ===========================================================================
#  DEPENDENCIES
# ===========================================================================

def require(*modules):
    """Import optional modules or exit 3 with a runnable uvx invocation.

    Exiting with a copy-pasteable command is the difference between a dead end
    and a one-line fix. A traceback here would only say "no module named
    pyvista", which the reader already knows.
    """
    missing, mods = [], {}
    for name in modules:
        try:
            mods[name] = __import__(name)
        except ImportError:
            missing.append(name)
    if not missing:
        return mods

    withs = " ".join(f"--with {m}" for m in ("pyvista", "trimesh", "numpy"))
    argv = " ".join(sys.argv[1:])
    print(f"mesh_render: missing {', '.join(missing)}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Run it without installing anything:", file=sys.stderr)
    print(f"  uvx {withs} python {os.path.abspath(__file__)} {argv}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Or install once:", file=sys.stderr)
    print(f"  python3 -m pip install {' '.join(missing)}", file=sys.stderr)
    sys.exit(3)


def load(path, mods):
    """Return (pyvista PolyData, trimesh Trimesh). Both, because each is better
    at something: PyVista renders, trimesh measures.

    PolyData is built explicitly from vertices and faces rather than through
    pv.read or pv.wrap, so the two objects are guaranteed to describe the same
    triangles and cell order — which is what makes per-face scalars line up.
    """
    np, trimesh = mods["numpy"], mods["trimesh"]
    pv = mods["pyvista"]

    tri = trimesh.load(path, force="mesh", process=False)
    if not hasattr(tri, "faces"):
        raise ValueError(f"{path}: not a triangle mesh")

    faces = tri.faces
    cells = np.hstack([np.full((len(faces), 1), 3, dtype=np.int64), faces]).ravel()
    poly = pv.PolyData(np.asarray(tri.vertices, dtype=float), cells)
    return poly, tri


# ===========================================================================
#  CAMERA
# ===========================================================================

def frame(plotter, poly, direction, up, pad=1.08):
    """Point a parallel-projection camera at the whole part along `direction`.

    Parallel projection is not a style choice: with perspective, two features at
    different depths render at different scales and the picture stops being
    measurable.
    """
    b = poly.bounds
    centre = ((b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0)
    diag = math.dist((b[0], b[2], b[4]), (b[1], b[3], b[5])) or 1.0

    n = _unit(direction)
    pos = tuple(centre[i] + n[i] * diag * 2.0 for i in range(3))
    plotter.camera_position = [pos, centre, tuple(up)]
    plotter.enable_parallel_projection()
    plotter.camera.parallel_scale = (diag / 2.0) * pad
    return centre, diag


def _unit(v):
    m = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / m for c in v)


def silhouette_extent(poly, direction):
    """The in-plane mm extents a viewer of this direction is actually seeing."""
    b = poly.bounds
    dims = {"x": b[1] - b[0], "y": b[3] - b[2], "z": b[5] - b[4]}
    n = _unit(direction)
    dominant = max(AXES, key=lambda a: abs(n[AXES[a]]))
    others = [a for a in ("x", "y", "z") if a != dominant]
    return dominant, {a: dims[a] for a in others}


# ===========================================================================
#  MODE: ORTHOGRAPHIC VIEWS
# ===========================================================================

def render_views(mods, poly, out_base, size, separate):
    pv = mods["pyvista"]
    entries = []

    if separate:
        for name, direction, up in ORTHO_VIEWS:
            path = f"{out_base}_{name}.png"
            p = pv.Plotter(off_screen=True, window_size=list(size))
            p.background_color = BACKGROUND
            p.add_mesh(poly, color=SURFACE, smooth_shading=False, show_edges=False)
            entries.append(_one_view(p, poly, name, direction, up, path))
            p.screenshot(path)
            p.close()
        return entries

    cols = 4
    rows = math.ceil(len(ORTHO_VIEWS) / cols)
    path = f"{out_base}_views.png"
    p = pv.Plotter(off_screen=True, shape=(rows, cols),
                   window_size=[size[0] * cols // 2, size[1] * rows // 2])
    p.background_color = BACKGROUND
    for i, (name, direction, up) in enumerate(ORTHO_VIEWS):
        p.subplot(i // cols, i % cols)
        p.background_color = BACKGROUND
        p.add_mesh(poly, color=SURFACE, smooth_shading=False, show_edges=False)
        entries.append(_one_view(p, poly, name, direction, up, path))
    # leave any trailing cell blank rather than repeating a view
    p.screenshot(path)
    p.close()
    return entries


def _one_view(plotter, poly, name, direction, up, path):
    frame(plotter, poly, direction, up)
    axis, extent = silhouette_extent(poly, direction)
    label = " x ".join(f"{k} {v:.2f}" for k, v in extent.items())
    plotter.add_text(f"{name}  ({label} mm)", position="upper_left",
                     font_size=9, color=OUTLINE)
    return {
        "view": name,
        "file": os.path.basename(path),
        "camera_direction": list(direction),
        "up": list(up),
        "projection": "parallel",
        "view_axis": axis,
        "in_plane_extent_mm": extent,
    }


# ===========================================================================
#  MODE: FILLED CROSS-SECTIONS
# ===========================================================================

def render_sections(mods, poly, tri, out_base, size, count, axis):
    """Cut the solid `count` times and photograph each cut face.

    Stations are placed at (i + 0.5) / count of the span, never at the ends: a
    section coplanar with a face is a coin toss between empty and full, and
    either answer is misleading.
    """
    pv, np = mods["pyvista"], mods["numpy"]
    ai = AXES[axis]
    b = poly.bounds
    lo, hi = b[2 * ai], b[2 * ai + 1]
    span = hi - lo
    centre = [(b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0]
    normal = [0.0, 0.0, 0.0]
    normal[ai] = 1.0

    entries = []
    for i in range(count):
        t = lo + span * (i + 0.5) / count
        origin = list(centre)
        origin[ai] = t
        path = f"{out_base}_section_{axis}{i:02d}.png"

        area, area_note = _section_area(mods, tri, origin, normal)
        cap, cap_note = _capped_half(poly, origin, normal)
        outline = _slice_lines(poly, origin, normal)

        p = pv.Plotter(off_screen=True, window_size=list(size))
        p.background_color = BACKGROUND
        if cap is not None:
            p.add_mesh(cap, color=SURFACE, smooth_shading=False)
        if outline is not None and outline.n_points:
            p.add_mesh(outline, color=OUTLINE, line_width=3)
        frame(p, poly, normal, UP_FOR[axis])

        head = f"section {i + 1}/{count}   {axis} = {t:.3f} mm"
        body = f"area {area:.2f} mm2" if area is not None else f"area unavailable ({area_note})"
        p.add_text(f"{head}\n{body}", position="upper_left", font_size=9, color=OUTLINE)
        _add_scale_bar(p, poly, ai, np)

        p.screenshot(path)
        p.close()

        entries.append({
            "index": i,
            "file": os.path.basename(path),
            "axis": axis,
            "station_mm": t,
            "area_mm2": area,
            "area_note": area_note,
            "cap_note": cap_note,
            "origin": origin,
            "normal": normal,
        })
    return entries


def _section_area(mods, tri, origin, normal):
    """True cross-section area, from trimesh rather than from the render.

    Measuring the picture would measure the renderer. This measures the solid.
    """
    try:
        sec = tri.section(plane_origin=origin, plane_normal=normal)
    except (ValueError, IndexError) as exc:
        return None, repr(exc)
    if sec is None:
        return None, "plane misses the solid"
    try:
        planar, _ = sec.to_planar()
        return float(planar.area), "trimesh Path2D"
    except (ValueError, IndexError, AttributeError) as exc:
        return None, repr(exc)


def _capped_half(poly, origin, normal):
    """Half the solid, with the cut sealed, so the section reads as filled.

    Voids show up as holes in the cap, which is exactly the failure this mode is
    for. If capping is unsupported or fails, the outline alone still communicates
    the shape, so a failure here is degraded output rather than no output.
    """
    if not hasattr(poly, "clip_closed_surface"):
        return None, "pyvista too old for clip_closed_surface; outline only"
    try:
        return poly.clip_closed_surface(normal=normal, origin=origin), "clip_closed_surface"
    except (RuntimeError, ValueError, TypeError) as exc:
        return None, f"cap failed, outline only: {exc!r}"


def _slice_lines(poly, origin, normal):
    try:
        return poly.slice(normal=normal, origin=origin)
    except (RuntimeError, ValueError, TypeError):
        return None


def _add_scale_bar(plotter, poly, axis_index, np):
    """A 10 mm ruler laid along the bottom of the frame.

    Without it the image has no absolute scale, and a reviewer comparing two
    sections rendered at different zooms will reach a wrong conclusion.
    """
    if not hasattr(plotter, "add_ruler"):
        return
    b = poly.bounds
    in_plane = [i for i in range(3) if i != axis_index]
    a = [0.0, 0.0, 0.0]
    a[axis_index] = b[2 * axis_index]
    a[in_plane[0]] = b[2 * in_plane[0]]
    a[in_plane[1]] = b[2 * in_plane[1]]
    z = list(a)
    z[in_plane[0]] = min(b[2 * in_plane[0]] + 10.0, b[2 * in_plane[0] + 1])
    try:
        plotter.add_ruler(pointa=a, pointb=z, title="10 mm", number_labels=2,
                          font_size_factor=0.5)
    except (TypeError, RuntimeError):
        pass


# ===========================================================================
#  MODE: WALL THICKNESS
# ===========================================================================

def render_thickness(mods, poly, tri, out_base, size, clip_below, samples):
    """Colour every face by the material thickness beneath it.

    Same inward-ray measurement as mesh_audit.py, applied to every face rather
    than a sample, because a picture with gaps is a picture that hides the thin
    spot. Its blind spots carry over too: a ray down the axis of a fillet reads
    the chord, and a knife edge reads long. This flags candidates; callipers
    settle them.
    """
    pv, np = mods["pyvista"], mods["numpy"]
    thick, note = _face_thickness(mods, tri, samples)
    if thick is None:
        return [], {"available": False, "reason": note}

    finite = thick[np.isfinite(thick)]
    if finite.size == 0:
        return [], {"available": False, "reason": "no ray hits"}

    poly = poly.copy()
    poly.cell_data["wall_mm"] = thick

    lo = float(clip_below) if clip_below else float(np.nanmin(finite))
    hi = float(np.nanpercentile(finite, 98))
    if hi <= lo:
        hi = lo + 1.0

    entries = []
    for name, direction, up in ORTHO_VIEWS:
        if name in ("back", "bottom"):
            continue  # four views plus iso is enough to see a thin band
        path = f"{out_base}_wall_{name}.png"
        p = pv.Plotter(off_screen=True, window_size=list(size))
        p.background_color = BACKGROUND
        kw = {"scalars": "wall_mm", "cmap": "viridis", "clim": [lo, hi],
              "scalar_bar_args": {"title": "wall mm", "color": OUTLINE}}
        if clip_below:
            kw["below_color"] = "magenta"
        p.add_mesh(poly, smooth_shading=False, **kw)
        frame(p, poly, direction, up)
        head = f"wall thickness  {name}"
        if clip_below:
            head += f"\nmagenta = thinner than {clip_below:.2f} mm"
        p.add_text(head, position="upper_left", font_size=9, color=OUTLINE)
        p.screenshot(path)
        p.close()
        entries.append({"view": name, "file": os.path.basename(path)})

    below = int((finite < clip_below).sum()) if clip_below else 0
    return entries, {
        "available": True,
        "method": "inward ray cast from face centroid, first hit",
        "note": note,
        "min_mm": float(np.nanmin(finite)),
        "p01_mm": float(np.nanpercentile(finite, 1)),
        "p05_mm": float(np.nanpercentile(finite, 5)),
        "median_mm": float(np.nanmedian(finite)),
        "colour_range_mm": [lo, hi],
        "clip_below_mm": clip_below,
        "faces_below_clip": below,
        "faces_measured": int(finite.size),
        "faces_total": int(thick.size),
    }


def _face_thickness(mods, tri, samples):
    """Per-face thickness array, NaN where no ray hit."""
    np = mods["numpy"]
    n = len(tri.faces)
    if n == 0:
        return None, "no faces"

    step = 1 if samples in (0, None) or samples >= n else max(1, n // samples)
    idx = np.arange(0, n, step)
    normals = tri.face_normals[idx]
    origins = tri.triangles_center[idx] - normals * 1e-4

    try:
        locs, ray_ids, _ = tri.ray.intersects_location(
            ray_origins=origins, ray_directions=-normals, multiple_hits=False)
    except (ValueError, RuntimeError, MemoryError) as exc:
        return None, repr(exc)

    out = np.full(n, np.nan)
    if len(ray_ids):
        d = np.linalg.norm(locs - origins[ray_ids], axis=1)
        good = d > 1e-6
        out[idx[ray_ids[good]]] = d[good]

    note = "every face" if step == 1 else f"every {step}th face; unsampled faces render as gaps"
    return out, note


# ===========================================================================
#  MODE: OVERHANG
# ===========================================================================

def render_overhang(mods, poly, tri, out_base, size, build_axis, threshold):
    """Colour by tilt from the downward build axis and flag the unsupported band.

    tilt_deg is the angle between a face normal and -build_axis: 0 is a flat
    ceiling, 90 a vertical wall. Flagged when tilt_deg < threshold. Same
    definition as mesh_audit.py, so the picture and the number agree.
    """
    pv, np = mods["pyvista"], mods["numpy"]
    ai = AXES[build_axis]
    down = np.zeros(3)
    down[ai] = -1.0

    tilt = np.degrees(np.arccos(np.clip(tri.face_normals @ down, -1.0, 1.0)))
    mask = tilt < threshold
    areas = tri.area_faces

    poly = poly.copy()
    poly.cell_data["tilt_deg"] = tilt

    flagged = None
    if mask.any():
        try:
            flagged = poly.extract_cells(np.flatnonzero(mask))
        except (RuntimeError, ValueError):
            flagged = None

    entries = []
    for name, direction, up in ORTHO_VIEWS:
        if name in ("top", "back"):
            continue  # overhangs are seen from below and from the sides
        path = f"{out_base}_overhang_{name}.png"
        p = pv.Plotter(off_screen=True, window_size=list(size))
        p.background_color = BACKGROUND
        p.add_mesh(poly, scalars="tilt_deg", cmap="coolwarm_r", clim=[0.0, 90.0],
                   smooth_shading=False,
                   scalar_bar_args={"title": "tilt deg", "color": OUTLINE})
        if flagged is not None:
            p.add_mesh(flagged, color="red", opacity=0.55, smooth_shading=False)
        frame(p, poly, direction, up)
        p.add_text(f"overhang  {name}\nred = tilt below {threshold:.0f} deg, "
                   f"build axis {build_axis.upper()}",
                   position="upper_left", font_size=9, color=OUTLINE)
        p.screenshot(path)
        p.close()
        entries.append({"view": name, "file": os.path.basename(path)})

    return entries, {
        "available": True,
        "build_axis": build_axis,
        "threshold_deg": threshold,
        "definition": "tilt_deg = angle(face normal, -build_axis); overhang when tilt_deg < threshold_deg",
        "area_mm2": float(areas[mask].sum()),
        "faces": int(mask.sum()),
        "total_area_mm2": float(areas.sum()),
        "min_tilt_deg": float(tilt[mask].min()) if mask.any() else None,
    }


# ===========================================================================
#  CLI
# ===========================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Render a printable part for review: orthographic views, filled "
                    "cross-sections, wall thickness, and overhang.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Needs pyvista, trimesh and numpy. If they are not installed the exact\n"
               "uvx command that would work is printed and the exit code is 3.\n"
               "\n"
               "Every run also writes a sidecar JSON beside the images: whatever a\n"
               "picture claims, the same number is available as text.\n"
               "\n"
               "On a headless Linux box add --xvfb. macOS renders offscreen natively.",
    )
    ap.add_argument("mesh", help="path to STL (or any trimesh-readable mesh)")
    ap.add_argument("--out", metavar="BASE",
                    help="output path prefix (default: alongside the mesh)")
    ap.add_argument("--views", action="store_true", help="six orthographic views plus isometric")
    ap.add_argument("--separate", action="store_true", help="one file per view instead of a contact sheet")
    ap.add_argument("--sections", type=int, default=0, metavar="N",
                    help="render N filled cross-sections")
    ap.add_argument("--axis", choices=("x", "y", "z"), default="z", help="section axis (default z)")
    ap.add_argument("--thickness", action="store_true", help="colour the surface by wall thickness")
    ap.add_argument("--clip-below", type=float, default=None, metavar="MM",
                    help="render material thinner than MM in magenta")
    ap.add_argument("--thickness-samples", type=int, default=0, metavar="N",
                    help="rays to cast; 0 (default) means every face")
    ap.add_argument("--overhang", action="store_true", help="colour the surface by build-direction tilt")
    ap.add_argument("--build-axis", choices=("x", "y", "z"), default="z", help="build direction (default z)")
    ap.add_argument("--overhang-deg", type=float, default=45.0, metavar="DEG",
                    help="overhang tilt threshold (default 45)")
    ap.add_argument("--size", type=int, nargs=2, default=(900, 900), metavar=("W", "H"),
                    help="pixel size per view (default 900 900)")
    ap.add_argument("--xvfb", action="store_true", help="start a virtual framebuffer first (headless Linux)")
    ap.add_argument("--quiet", action="store_true", help="suppress the text report")
    args = ap.parse_args(argv)

    if not (args.views or args.sections or args.thickness or args.overhang):
        args.views = True  # a bare invocation should still produce something useful

    mods = require("pyvista", "trimesh", "numpy")
    pv = mods["pyvista"]
    pv.OFF_SCREEN = True
    if args.xvfb:
        try:
            pv.start_xvfb()
        except (OSError, RuntimeError) as exc:
            print(f"mesh_render: --xvfb failed: {exc}", file=sys.stderr)
            return 3

    try:
        poly, tri = load(args.mesh, mods)
    except (OSError, ValueError) as exc:
        print(f"mesh_render: {exc}", file=sys.stderr)
        return 2

    base = args.out or os.path.splitext(os.path.abspath(args.mesh))[0]
    os.makedirs(os.path.dirname(base) or ".", exist_ok=True)

    b = poly.bounds
    sidecar = {
        "mesh": os.path.abspath(args.mesh),
        "triangles": int(poly.n_cells),
        "vertices": int(poly.n_points),
        "bounds": {"min": [b[0], b[2], b[4]], "max": [b[1], b[3], b[5]]},
        "dims_mm": [b[1] - b[0], b[3] - b[2], b[5] - b[4]],
        "volume_mm3": float(tri.volume),
        "background": BACKGROUND,
        "projection": "parallel",
        "images": {},
    }

    if args.views:
        sidecar["images"]["views"] = render_views(mods, poly, base, args.size, args.separate)
    if args.sections:
        sidecar["images"]["sections"] = render_sections(
            mods, poly, tri, base, args.size, args.sections, args.axis)
    if args.thickness:
        imgs, meta = render_thickness(mods, poly, tri, base, args.size,
                                      args.clip_below, args.thickness_samples)
        sidecar["images"]["thickness"] = imgs
        sidecar["wall_thickness"] = meta
    if args.overhang:
        imgs, meta = render_overhang(mods, poly, tri, base, args.size,
                                     args.build_axis, args.overhang_deg)
        sidecar["images"]["overhang"] = imgs
        sidecar["overhang"] = meta

    side_path = f"{base}_render.json"
    with open(side_path, "w") as fh:
        json.dump(sidecar, fh, indent=2)

    if not args.quiet:
        print(render_text(sidecar, side_path))
    return 0


def render_text(sidecar, side_path):
    L = [f"  mesh        {sidecar['mesh']}",
         f"  triangles   {sidecar['triangles']}",
         "  dims        " + " x ".join(f"{d:.3f}" for d in sidecar["dims_mm"]) + " mm"]
    for group, items in sidecar["images"].items():
        L.append(f"  {group:<11} {len(items)} image(s)")
        for it in items:
            name = it.get("view") or f"{it.get('axis')}={it.get('station_mm', 0):.3f}"
            extra = ""
            if it.get("area_mm2") is not None:
                extra = f"   area {it['area_mm2']:.2f} mm2"
            L.append(f"                {it['file']}  ({name}){extra}")
    wall = sidecar.get("wall_thickness", {})
    if wall.get("available"):
        L.append(f"  min wall    {wall['min_mm']:.3f} mm  (p05 {wall['p05_mm']:.3f})")
        if wall.get("clip_below_mm"):
            L.append(f"  under {wall['clip_below_mm']:.2f} mm   {wall['faces_below_clip']} faces, shown magenta")
    elif wall:
        L.append(f"  min wall    unavailable -- {wall.get('reason')}")
    oh = sidecar.get("overhang", {})
    if oh.get("available"):
        L.append(f"  overhang    {oh['area_mm2']:.2f} mm2 below {oh['threshold_deg']:.0f} deg tilt")
    L.append(f"\n  sidecar     {side_path}")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())

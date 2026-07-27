#!/usr/bin/env python3
"""
saddle_gen.py -- parametric generator for a 3M-taped mid-span shade-bar support saddle.

Run inside Blender (>= 4.2; developed against 5.2 LTS):

    blender --background --python-exit-code 1 --python saddle_gen.py
    # --python-exit-code is not optional: without it Blender returns 0 even when
    # this script raises, so a failed build looks like a success to the caller.
    # or, in a live session:
    exec(open("saddle_gen.py").read())

Coordinate system (see BUILD-BRIEF.md):
    origin  centre of the plate's bottom edge, ON the tape face
    +X      along the wall, and along the bar axis
    +Y      away from the wall (projection).  Tape face is the plane Y = 0.
    +Z      up
All material sits at Y >= 0.  Units: 1 Blender unit = 1 mm.

The part only pushes UP.  The existing end brackets already capture the bar, so
there is deliberately no hook, curl, lip or retention feature.  It is taped, so
there are no holes and the Y = 0 face is left dead flat.
"""

# ---------------------------------------------------------------------------
# PARAMETERS -- everything below is derived from these.
# Changing D_BAR (or H_DROP) and re-running produces a correct part with no
# other edits.  That is the whole point of this file.
# ---------------------------------------------------------------------------

W_PLATE   = 76.2    # plate width, mm (3.000 in).  Fixed.
H_PLATE   = 44.45   # plate height, mm (1.750 in).  HARD CAP 50.8 mm.
T_PLATE   = 5.5     # plate thickness, mm
R_CORNER  = 6.0     # plate corner radius, mm (cosmetic)

D_BAR     = 19.05   # bar diameter, mm = 3/4 in.  CONFIRMED by owner 2026-07-25
                    # (was 22.0, a photo-derived estimate; see FACTS.md 5)
H_DROP    = 2.0     # bar rest point below the plate's bottom edge, mm
                    #                             <-- STILL UNVERIFIED
CLEAR     = 0.4     # trough radial clearance over the bar, mm
GAP       = 1.0     # air gap between bar and plate face, mm -- used ONLY when
                    # Y_BAR is None, to sit the bar as close to the wall as
                    # physically possible

Y_BAR     = 1.25 * 25.4   # bar centre distance from the tape face, mm (1.250 in)
                    # THIS IS A MEASURED INPUT, NOT A DESIGN CHOICE.  The existing
                    # end brackets fix where the bar actually is; this part must
                    # reach it.  Set None to fall back to the theoretical minimum
                    # T_PLATE + D_BAR/2 + GAP (= 16.025 mm), which is only correct
                    # if the end brackets happen to hold the bar that close.
W_SADDLE  = 25.0    # saddle width along the bar, mm
T_WALL    = 3.0     # minimum wall thickness on the load path, mm

# --- shape / tessellation controls (secondary; not dimension-bearing) -------
WRAP_DEG    = 170.0  # trough wrap angle, degrees (brief asks for 160-180)
ROOT_BLEND  = 3.5    # gusset blend size at the arm/plate root, mm.  It places the
                     # three hull anchors, and through a2 it sets how much of the
                     # cradle's lower edge survives past the Z = 0 crossing -- which
                     # is the ONLY thing standing between R_ROOT_LOW and the radius
                     # it asks for.  At the old 1.5 that edge left 1.0035 mm and the
                     # lower blend was clamped to 2.235 mm; at 3.5 it leaves 2.34 mm
                     # and the full 5.0 mm is delivered.  Do not set it to 2.5: that
                     # value builds non-manifold on all three H_DROP variants.
# --- form -------------------------------------------------------------------
BULGE       = 2.5    # convex swell of the plate's FRONT face at X=0, Z=0, mm.
                     # The face becomes a shallow arc, thickest on the centreline
                     # where the arm leaves it and fairing to exactly T_PLATE at
                     # the side edges.  The Y=0 tape face is NOT touched.
BULGE_FADE_Z = H_PLATE  # height at which the swell has faded back to nothing, mm.
                     # The swell is a branch collar, so it must be graded in Z as
                     # well as X: thickest along the bottom edge, where the arm
                     # actually leaves the plate and the peel moment is highest,
                     # and gone by the top edge, which carries almost nothing.  A
                     # swell of constant section in Z is a cylinder, not a collar.
                     # Set <= H_PLATE; a smaller value leaves a flat band on top.
SEG_BULGE_Z = 32     # rings the graded swell is lofted from.  32 puts the loft
                     # within 0.002 mm of the true surface at BULGE = 2.5.

ROUND_R     = 0.5    # router-style round-over radius on sharp edges, mm.
                     # Was 1.0 until iteration 6.  At 1.0 the MIN EDGE rule
                     # below (ROUND_MIN_EDGE_FRAC * ROUND_R = 0.50 mm) sat ABOVE
                     # the plate's 0.393 mm corner-arc links, so every one of
                     # them was excluded and THE PLATE'S FOUR CORNERS SHIPPED
                     # DEAD SHARP, with the perimeter round-over stopping at
                     # eight tangent points.  At 0.5 the same rule computes a
                     # 0.25 mm bound, the arcs clear it on their own, and the
                     # round-over runs round the corners.  FACTS 7h.
ROUND_SEG   = 3      # segments in the round-over
ROUND_ANGLE = 25.0   # only edges sharper than this get rounded, so the
                     # 192-facet trough is left alone
ROUND_ANGLE_MAX = 130.0  # ...and only edges blunter than this.  An offset bevel
                     # across a tighter fold has to slide radius/tan(phi/2) along
                     # both faces -- 4.5 mm at 155 degrees -- and nothing here has
                     # that much face to give, so with clamp_overlap necessarily
                     # off the vertex ends up wherever the arithmetic lands.
ROUND_MIN_FACE_FRAC = 0.03  # ...and only where there is face enough to slide along.
                     # _FRAC because this is a FRACTION, not an absolute mm^2 floor:
                     # of ROUND_R^2, where ROUND_MIN_EDGE_FRAC below is a fraction of
                     # ROUND_R.  An area bound scaling as R^2 and a length bound as
                     # R^1 is dimensionally right for the BEVEL -- both track what the
                     # cut needs -- but it does NOT hold the target population still
                     # when ROUND_R moves, and this comment claimed it did until
                     # iteration 6 disproved it directly.  The geometry the two bounds
                     # are compared against does not scale with R at all: the plate's
                     # corner-arc links are 0.393 mm at any radius, and their adjoining
                     # faces are 0.0657 mm^2 at any radius.  Halving ROUND_R therefore
                     # halved the length cut straight past those links, from 0.50 mm
                     # (above them, all excluded, corners shipped sharp) to 0.25 mm
                     # (below them, all included).  Read both bounds as bounds on the
                     # CUT, and re-measure the target set whenever ROUND_R moves.
                     #
                     # A bevel travels of order the radius across each adjoining face;
                     # one a few thousandths of a square millimetre across cannot
                     # absorb that, and what comes back is a spurious face the size of
                     # the offset.  When this rule was written the two populations did
                     # not overlap at ROUND_R 1.0: real edges carried adjoining faces
                     # of 0.27 mm^2 and up and the fillets' tangency seams carried
                     # 0.003 to 0.08, against a 0.03 mm^2 cut.  Re-measured at
                     # ROUND_R 0.5 (cut 0.0075 mm^2): the smallest adjoining face
                     # anywhere in the target set is 0.0657 mm^2 -- the corner arcs,
                     # which are real edges and now sit INSIDE the old 0.003-0.08
                     # seam band -- so the clean two-population separation the 0.27
                     # figure described is gone.  The rule is still safe and still
                     # drops none of the plate's perimeter chain, but it is a backstop
                     # rather than a discriminator: measured on all three variants at
                     # both radii, with every other rule applied, FACE AREA now
                     # excludes nothing at all.  The seams it was written for are
                     # taken first by FILLET FOOTPRINT.
                     #
                     # THIS population had to be caught by face AREA, not by edge
                     # length: at ROUND_R 1.0, 32 of the edges an at-the-radius
                     # (1.0 mm) length rule drops were on the plate's perimeter chain
                     # while none of the small-face ones were, so set at the radius it
                     # tore the corner arcs -- a chain beveled in some segments and not
                     # others reads as a chewed edge rather than a soft one.  There is
                     # an edge-length rule as well now (ROUND_MIN_EDGE_FRAC, below).
                     # It is set at half the radius and it does NOT drop only whole
                     # chains: at ROUND_R 0.5 it leaves 40 sub-0.25 mm fragments of the
                     # corner-arc chain unrounded between rounded links.  See
                     # ROUND_MIN_EDGE_FRAC for why that is tolerable and what it costs.

ROUND_MIN_EDGE_FRAC = 0.5  # ...and only on edges long enough to carry the cut, as a
                     # fraction of ROUND_R.  A bevel opens a corner patch at each end
                     # of the edge it cuts and those patches walk of order the radius
                     # along the chain, so on a chain whose links are much shorter
                     # than the radius each link's bevel overruns both its
                     # neighbours; with clamp_overlap necessarily off (see
                     # round_edges) they interpenetrate, and what comes back is a row
                     # of spikes rather than a soft edge.
                     #
                     # That chain is the plate's corner arcs.  R_CORNER 6.0 over
                     # SEG_CORNER 24 is a 6*(pi/2)/24 = 0.393 mm segment, and
                     # measured they fold at 82.7 to 90.0 degrees, so the slide the
                     # bevel has to make along each adjoining face, R*tan(phi/2), is
                     #   R = 1.0   0.880 to 0.999 mm   a 2.2x to 2.5x overrun
                     #   R = 0.5   0.440 to 0.500 mm   a 1.1x to 1.3x overrun
                     # on a 0.393 mm link.  At ROUND_R 1.0 that was the spike cluster
                     # on the plate's four corners, 236 of the 418 spike vertices on
                     # the nominal build, and it is why this bound is on the EDGE and
                     # not on the fold: at 83 to 90 degrees those edges are ordinary
                     # corners, nowhere near ROUND_ANGLE_MAX.
                     #
                     # WHAT THAT COST, AND WHY ROUND_R MOVED (iteration 6).  A bound
                     # of 0.5*ROUND_R is 0.50 mm at ROUND_R 1.0, which is ABOVE every
                     # 0.393 mm link, so the rule took the ENTIRE corner-arc chain out
                     # of the target set and THE PLATE'S FOUR CORNERS SHIPPED DEAD
                     # SHARP -- the perimeter round-over ran the straight edges and
                     # stopped at eight tangent points.  Measured on the finished mesh
                     # at ROUND_R 1.0, in the four corner-arc regions: 456 edges, of
                     # which 120 fold at 80-100 degrees (the square corner itself) and
                     # nothing else above 40 except four at ~145.  Identical on all
                     # three variants.  Nothing in this file said so; it read as a
                     # clean win.  At ROUND_R 0.5 the same rule computes 0.25 mm, the
                     # arcs clear it on their own, and those regions come back with
                     # 1416 edges, near-90 count 120 -> 38, and the population moved
                     # into the shallow buckets a 3-segment round-over makes (247 at
                     # 10-20 deg, 129 at 20-30, 84 at 30-40).  See FACTS 7h for the
                     # before/after counts and what the change cost elsewhere.
                     #
                     # It is worth being plain that at 0.5 the arcs are beveled even
                     # though their own slide (0.440-0.500) still overruns the link
                     # (0.393).  The overrun is 1.1x-1.3x instead of 2.2x-2.5x, so the
                     # interpenetration is mild instead of gross: 36 plate-perimeter
                     # spikes remain, against 46 before and 0 if the arcs are excluded
                     # again.  Rounded-with-mild-overrun is the owner's call over
                     # square-and-clean; the residual is recorded, not hidden.
                     #
                     # Two earlier values are why this is a fraction, and why it is
                     # this fraction.  BOTH are ROUND_R 1.0 measurements -- at that
                     # radius the fractions meant 0.2 mm and 1.0 mm:
                     #   0.2 mm  did nothing, and was removed as ineffective -- 0.393
                     #           > 0.2, so every corner-arc segment stayed in the
                     #           target set and stayed overlapping.  The rule was
                     #           sound; the value never reached the population that
                     #           was doing the damage.
                     #   1.0 mm  the radius itself, the honest physical bound, is too
                     #           aggressive.  It cut INTO chains that must stay:
                     #           4 of the 48 plate side edges, 4 of 50 on top, 4 of 22
                     #           on the bottom, 2 of the 6 on the notch -- the chewed
                     #           edge recorded above -- and it failed `shells` on
                     #           H_DROP=2.
                     #
                     # WHERE THE THRESHOLD ACTUALLY LANDS, re-measured at ROUND_R 0.5.
                     # It is still in a gap, but a thin and incidental one rather than
                     # the separation between two populations, and the old sentence
                     # ("a gap ... so no chain is left half cut") was true of 1.0 and
                     # is NOT true here.  Cut 0.25 mm; longest edge below it 0.2491,
                     # shortest above it 0.2613 -- the same two bounds on all three
                     # H_DROP variants -- so the gap is 0.0122 mm wide and the cut
                     # clears the edge below it by 0.0009 mm.  The two bounds are not
                     # even the same feature: 0.2491 is a mouth-rim link at X = +-12.5
                     # and 0.2613 is the long half of a corner-arc segment a boolean
                     # seam split in two.  The spectrum around it is dense -- 44 edges
                     # below the cut and 330 above, on the nominal.
                     #
                     # For contrast, the ROUND_R 1.0 spectrum this file used to quote,
                     # kept because it is the as-built record of everything printed so
                     # far: corner arcs topping out at 0.3951, the collar's loft seams
                     # a 96-edge spike at 0.4623, stragglers on the flare-tip end-cap
                     # rims at 0.4486 / 0.4641 / 0.4644, and the shortest visibly
                     # round-over-carrying link at 0.5062 (the plate's top edge).  The
                     # 0.50 cut landed in the 0.4644..0.5062 gap, 0.042 mm wide.
                     #
                     # SO THE CHAIN IS NOW PART-CUT, and that has to be said.  44 edges
                     # sit below 0.25 on the nominal (48 / 44 on H_DROP 0 / 4): 40 of
                     # them are sub-0.25 fragments OF the corner-arc chain, left where
                     # boolean seams inserted extra vertices into it, 2 are on a
                     # flare-tip cap and 2 are the 0.2491 mouth-rim pair.  A 0.5 mm
                     # bevel slides ~0.5 mm along the chain from each neighbour, which
                     # is longer than every one of those fragments (0.014 to 0.24 mm),
                     # so they are overrun rather than left standing -- which is why
                     # the corners read rounded and the perimeter spike count fell
                     # rather than rose.  It is still a chain cut in parts, not whole.
                     #
                     # THE 0.6 / 0.7 REJECTION WAS A ROUND_R 1.0 ARGUMENT AND DOES NOT
                     # TRANSFER.  There those fractions meant 0.60 and 0.70 mm and they
                     # dropped four edges 0.5 kept, all at the witness notch -- the two
                     # 0.5062 stubs of the top edge at the shoulders and the two 0.5833
                     # flanks of the V -- leaving a 0.5 mm square ear at each shoulder
                     # on the one feature the part is aligned by.  At ROUND_R 0.5 the
                     # same fractions mean 0.30 and 0.35 mm; the notch chain is at
                     # 0.5062 / 0.5833 and is nowhere near them.  Re-swept at ROUND_R
                     # 0.5 across all three variants, 0.3 / 0.48 / 0.5 / 0.6 / 0.7 ALL
                     # pass -- the ROUND_R 1.0 failure modes (non-manifold at 0.3 and
                     # 0.45, 2 shells at 0.4, 3 shells at 1.0) do not reproduce -- and
                     # the counts are:
                     #   0.3    perimeter spikes 53   folds 116 / 143 / 110
                     #   0.48   perimeter spikes 36   folds 102 / 129 /  97
                     #   0.5    perimeter spikes 36   folds 107 / 133 / 104  (shipped)
                     #   0.6    perimeter spikes 28   folds 111 / 138 / 106
                     #   0.7    perimeter spikes 26   folds 113 / 140 / 103
                     # What 0.6 and 0.7 drop here is 12 and 16 more of the arc's
                     # split-link halves, i.e. whole arc segments going back to square
                     # in exchange for less interpenetration.  0.5 is HELD, not
                     # re-derived: iteration 6 moved ROUND_R only.  It is no longer
                     # demonstrably the best fraction at this radius and that is
                     # recorded as open in FACTS 7h rather than quietly settled here.
                     #
                     # The tip-cap asymmetry the old text cited under 0.6/0.7 is real
                     # and is measured out in FACTS 7h: at ROUND_R 1.0 the -X cap
                     # carries two different rim links off the same vertex at
                     # Z = 4.1672 -- a 0.4644 running down to Z = 3.7029, whose +X
                     # mirror is the 0.4641, and (on H_DROP = 0 only) a 0.5168 running
                     # up to Z = 4.6839, whose +X counterpart runs to Z = 4.9324 and
                     # measures 0.7654.  Two links, not one; both sentences were about
                     # real edges.
                     #
                     # It bounds the EDGE, not the faces beside it.  The stricter
                     # "the adjoining faces must be longer than the slide" rule is a
                     # different test and still answers no to nearly everything; that
                     # experiment is recorded in round_edges.

MOUTH_CHAM  = 0.8    # 45-degree lead-in chamfer on the trough mouth rim, mm.
                     # The round-over deliberately skips every trough-surface
                     # edge (see round_edges), which protects the wall but leaves
                     # the mouth a raw, sharp cut.  The rim sits at the free tips
                     # of the cradle arms, where the bending moment is zero, so
                     # taking material off it costs nothing structurally -- and
                     # it widens the mouth from 19.8 to 21.4 mm at the top, which
                     # is what lets the bar be felt into place one-handed.
                     # It DOES shorten the full-thickness wrap by 2*CHAM/R_TROUGH
                     # radians; derive() gates that at 160 degrees.

# --- form: the witness notch -----------------------------------------------
NOTCH_W     = 4.0    # width of the centreline witness notch on the plate's top
NOTCH_D     = 2.5    # depth of same, mm.  VHB is one-shot -- the part cannot be
                     # slid after it touches the wall -- and the part is
                     # symmetric with no other feature to sight along.  A V cut
                     # through the full thickness at X=0 lets the pencil line on
                     # the wall be seen through the notch while the plate is
                     # still held clear of it.

# --- form: the branch collar ----------------------------------------------
FLARE       = 5.0    # 45-degree flare on each X end of the saddle body, mm.
                     # Widens the arm 25 -> 25+2*FLARE where it meets the plate,
                     # which is the "branch collar" look, spreads the moment into
                     # the plate over a wider footprint, and -- because layers
                     # stack along X -- turns a 343 mm^2 mid-air island into
                     # 8.1 mm^2.  Must stay under the envelope's inradius or the
                     # end profile vanishes; 5 mm is the knee, past which the
                     # island does not shrink further.

FLARE_TIP   = 4.0    # extra 45-degree taper beyond FLARE that CLOSES the end, mm.
                     # Without it hull_solid's outermost ring is a flat planar cut
                     # normal to X: the branch collar tapers its profile over the
                     # last 5 mm and then the body simply stops, leaving a square
                     # end cap 13.6 mm tall whose rim meets the arm's upper surface
                     # at 93 degrees.  Anchoring the flare to the plate (see
                     # build_saddle) nearly doubled that cap, because the anchors
                     # are held at full depth.  This ring erodes the tip profile
                     # again -- anchors included -- so the body closes down instead
                     # of being sawn off.  The anchors sit at Y = 2.0, deep inside
                     # the plate's 7.5 mm face, so eroding them here costs no
                     # attachment: they are still buried when the cap closes.
ARM_ROOT_FRAC = 0.45 # arm depth at the plate, as a fraction of its reach.  A
                     # cantilever must be DEEPEST where the moment is highest;
                     # without this the gusset anchors pinch the root to ~2 mm
                     # and the arm is thinnest exactly where it is worst loaded.

# --- structural check (reported and gated on every run) --------------------
LOAD_LBF    = 5.0    # design load carried by this one support, lbf (FACTS 1.5)
MATERIAL    = "PETG" # the material the allowable is for (FACTS 7f).  It lives here,
                     # touching the allowable, because the two must move together
                     # and once did not: the material was changed to PETG and
                     # report() went on printing "on solid PLA" for every run
                     # afterwards, because the label was hard-coded at the far end
                     # of the file.  Anything that names the material reads this.
SIGMA_ALLOW_BY_MATERIAL = {   # MPa, tensile yield, per material.  This is a table
    "PLA":  50.0,             # and not a loose constant because the pairing used to
    "PETG": 50.0,             # be enforced by a comment only: PLA and PETG happen to
}                             # share 50, so when the material changed the number did
                     # not have to, and nothing anywhere flagged that the printed label
                     # had gone stale.  A wrong allowable feeds the safety-factor gate
                     # directly, so an unknown MATERIAL now stops the run instead of
                     # silently borrowing whichever number was left in the file.
if MATERIAL not in SIGMA_ALLOW_BY_MATERIAL:
    raise ValueError(
        f"MATERIAL is {MATERIAL!r}, which has no entry in SIGMA_ALLOW_BY_MATERIAL "
        f"(known: {sorted(SIGMA_ALLOW_BY_MATERIAL)}).  Add its tensile yield in MPa "
        f"there rather than letting the safety-factor gate run on some other "
        f"material's allowable.")
SIGMA_ALLOW = SIGMA_ALLOW_BY_MATERIAL[MATERIAL]   # MPa, derived -- do not set by hand
SF_MIN      = 8.0    # required safety factor on SOLID material, so that the
                     # print survives infill (~0.6x) and creep (~0.5x)

R_ROOT      = 13.5   # fillet radius where the arm's TOP face dies into the plate's
                     # front face, mm.  That corner is the arm's tension fibre and
                     # the corner the peel moment works on, so it gets the largest
                     # blend the geometry will carry.  Nothing here is trusted: the
                     # radius is clamped at run time by how much plate face there is
                     # above the corner, how much arm face there is beyond it, and
                     # how close the bar's drop-in path comes -- see fillet_stations.
                     #
                     # NONE of those clamps is what bounds this number in practice.
                     # corner_room never binds below 16.89 mm, and every functional
                     # measurement is bit-identical from R = 8 to R = 16.  The values
                     # themselves move with ROUND_R, because R_OUT pays for the
                     # round-over up front (see derive), so read them off the run:
                     #   ROUND_R 1.0  SF 44.06 @ Y=26.52, min wall 4.000,
                     #                drop-in 0.4000, projection 45.849, wrap 178.3
                     #   ROUND_R 0.5  SF 36.48 @ Y=26.52, min wall 3.500,
                     #                drop-in 0.4000, projection 45.348, wrap 177.9
                     # What survives the radius change is the INVARIANCE across
                     # R_ROOT, which is the claim this paragraph is making.
                     # This blend buys no
                     # strength and no stiffness; what it buys is 28% off the stress
                     # in the plate panel above it and a smoother load path.
                     #
                     # What DOES bound it is mesh robustness: at large radii the
                     # fillet's forward leg grazes the 192-facet trough cylinder and
                     # the boolean leaves slivers the round-over cannot survive.  The
                     # failures are NON-MONOTONIC -- 12.0, 14.25 and 14.75 break on
                     # one variant or another while 12.5, 14.0 and 14.5 are clean --
                     # so this is not a value to nudge without re-running all three
                     # H_DROP variants.  13.0 to 14.0 was swept at 0.1 mm and is
                     # clean throughout; 13.5 is the centre of that plateau and
                     # 0.75 mm clear of the nearest landmine.
R_ROOT_LOW  = 5.0    # fillet radius where the cradle's underside dies into the
                     # plate's BOTTOM face, mm.  Same construction.  It used to be
                     # clamped to 2.235 mm because the a1->a2 hull edge left only
                     # 1.0035 mm past the Z = 0 crossing; ROOT_BLEND now lengthens
                     # that edge to 2.34 mm and the full radius is delivered.  The
                     # corner is on the compression side of the design load, but it
                     # is still re-entrant -- 131.6 degrees of void, 228.4 of
                     # material, measured off the envelope every run -- and it is
                     # the first place a peel crack starts.  The report prints both
                     # the asked-for and the carried radius, so if a change to
                     # ROOT_BLEND ever takes the room away again it will say so
                     # rather than quietly shrinking the blend.
FILLET_SEG   = 16    # segments in each fillet arc
FILLET_BURY  = 1.2   # how far a fillet's corner is pushed INTO the solid, mm, so the
                     # union has volume to bite on instead of a tangency.  Its own
                     # constant, deliberately: it used to borrow ROOT_BLEND, which is
                     # the hull gusset size and unrelated, so raising ROOT_BLEND to
                     # 3.5 silently shoved the lower fillet out through the plate.
                     # Clamped per station by burial_room() against the local face.
FILLET_TERM_SCALE = 0.15  # the loft's last ring, as a fraction of the one before it,
                     # shrunk onto a seed inside the solid so the end cap is buried
FILLET_R_MIN = 0.05  # smallest radius lofted before the collar is sunk behind the
                     # plate face and capped inside solid material
FILLET_STEPS = 12    # X stations across the taper, per side

# --- form: the layer-aligned relief on the trough --------------------------
LAYER_H     = 0.2    # the layer height this part is DRAWN for, mm.  export_stl lays
                     # the part's X along the printer's Z, so anything that repeats
                     # along X repeats along the build direction: pitch it in whole
                     # layers and every edge of the texture lands exactly on a layer
                     # boundary instead of being rounded to one by the slicer.
RIB_PITCH   = 1.0    # centre-to-centre spacing of the relief grooves, mm (5 layers)
RIB_WIDTH   = 0.4    # width of each groove along the bar axis, mm (2 layers)
RIB_DEPTH   = 0.2    # how far each groove is cut OUT of the trough surface, mm.
                     # Cut outward, never inward: the land between grooves stays at
                     # the nominal trough radius, so the bar still drops onto the
                     # surface the fit was designed around and the 0.4 mm radial
                     # clearance is untouched.  Ribs standing PROUD of the trough
                     # would halve that clearance and turn a drop-in into a press
                     # fit.  R_OUT is grown by RIB_DEPTH in derive() so the groove
                     # floor -- not the land -- is what carries T_WALL: the same
                     # rule ROUND_R already obeys, that a cosmetic feature is not
                     # allowed to eat a structural one.
RIB_X_LIM   = 12.5   # grooves stay inside the saddle's full-section half-width, mm.
                     # Not a style choice: past W_SADDLE/2 the flare erodes the
                     # cradle, so the wall at erosion e is (R_OUT - e) - R_TROUGH,
                     # and keeping T_WALL under a groove needs e <= ROUND_R, i.e.
                     # |X| <= W_SADDLE/2 + ROUND_R = 13.0 at the defaults (it was
                     # 13.5 while ROUND_R was 1.0; the bound moves with the radius,
                     # this limit does not).  Stopping at the full-section
                     # width is the same bound with a millimetre in hand, and it
                     # puts the edge of the texture where the arm's section changes
                     # rather than somewhere arbitrary along the taper.

SEG_CIRCLE  = 192    # segments per full circle (trough + cradle envelope)
SEG_CORNER  = 24     # segments per plate corner arc

H_PLATE_CAP = 50.8   # hard ceiling on plate height, mm (2.000 in)

# --- fit gauge -------------------------------------------------------------
GAUGE_DIAS  = [19.0, 20.6, 22.2, 23.8, 25.4]  # candidate bar diameters, mm
GAUGE_T     = 3.0    # gauge plate thickness, mm
GAUGE_WALL  = 5.0    # material between adjacent notches, mm
GAUGE_LABEL = 5.0    # label text height, mm
GAUGE_EMB   = 0.6    # label emboss height, mm
GAUGE_MARG  = 4.0    # margin above/below the label band, mm
GAUGE_Y_OFF = -90.0  # where the gauge parks in the .blend, mm (out of the way)

# --- outputs ---------------------------------------------------------------
PART_NAME   = "ShadeBarSaddle"
GAUGE_NAME  = "ShadeBarFitGauge"
VARIANTS    = [("saddle_h-2", 0.0), ("saddle_h0", 2.0), ("saddle_h+2", 4.0)]
DO_EXPORT   = True   # write STLs
DO_SAVE     = True   # save the .blend
DO_GAUGE    = False  # build and export the bar-diameter fit gauge.  Off: D_BAR is
                     # CONFIRMED at 19.05 mm by the owner (FACTS.md 5), so the gauge
                     # has done its job and no longer belongs in the scene or the
                     # export set.  The builder and its checks are kept because
                     # H_DROP is still unverified -- if the bar turns out to sit
                     # somewhere else, this is the tool that settles the diameter
                     # again, and it costs one flag rather than a rewrite.

# ---------------------------------------------------------------------------

import collections
import hashlib
import json
import math
import os
import struct
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector


def _load_part_kit():
    """Import the shipped kit, so this fixture exercises the code the plugin ships.

    Only the CONSTRUCTION half of this file delegates to `part_kit`, and currently
    only `boolean`.  The verification half below -- `stl_triangles`, `stl_manifold`,
    `stl_acceptance` -- must stay an independent implementation; see the note above
    `stl_manifold`.

    Resolved from this file's own location rather than the working directory,
    because a generator is run from wherever the caller happens to be.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.environ.get("PART_FORGE_SCRIPTS") or os.path.normpath(
        os.path.join(here, "..", "..", "plugins", "part-forge", "scripts"))
    if cand not in sys.path:
        sys.path.insert(0, cand)
    import part_kit
    return part_kit


_kit = _load_part_kit()

MM_PER_IN = 25.4
MM2_PER_IN2 = MM_PER_IN ** 2

_UNSET = object()   # lets y_bar=None mean "derive the floor", distinct from "not given"


# ===========================================================================
# derived dimensions
# ===========================================================================

def derive(d_bar=None, h_drop=None, y_bar=_UNSET):
    """All secondary dimensions, as a dict.  Nothing downstream computes its own."""
    d_bar = D_BAR if d_bar is None else d_bar
    h_drop = H_DROP if h_drop is None else h_drop
    y_bar = Y_BAR if y_bar is _UNSET else y_bar

    r_bar = d_bar / 2.0
    r_trough = r_bar + CLEAR              # trough radius (bar + clearance)
    # Cradle outer radius.  The round-over eats into the outer surface near the
    # arm tips, so the wall is grown by ROUND_R up front and the measured wall
    # still comes out at T_WALL afterwards.  The cosmetic feature pays for
    # itself in material rather than being subtracted from the structure.
    # The layer-aligned relief obeys the same rule from the other side: it is cut
    # OUT of the trough, so its floor -- not the land between grooves -- is the
    # thinnest section, and RIB_DEPTH is paid for here rather than out of T_WALL.
    r_out = r_trough + T_WALL + max(ROUND_R, 0.0) + max(RIB_DEPTH, 0.0)
    # Trough axis depth == the moment arm.  Measured if we have it, otherwise the
    # theoretical closest the bar could possibly sit.
    # Front face on the centreline at Z=0, where the graded swell is at its most
    # proud.  Every clearance below is the worst case over the plate's height, so
    # this is the value they all want -- not the face beside the trough.
    face = plate_face_y(0.0, 0.0)
    y_axis = (face + r_bar + GAP) if y_bar is None else y_bar
    gap_eff = y_axis - face - r_bar       # actual air gap, bar surface to plate
    z_axis = -h_drop + r_trough           # trough axis height
    half_wrap = math.radians(WRAP_DEG / 2.0)
    z_cut = z_axis - r_trough * math.cos(half_wrap)   # ceiling on the cradle arms

    d = dict(
        D_BAR=d_bar, H_DROP=h_drop, Y_BAR_INPUT=y_bar, GAP_EFF=gap_eff,
        R_BAR=r_bar, R_TROUGH=r_trough, R_OUT=r_out,
        Y_AXIS=y_axis, Z_AXIS=z_axis, Z_CUT=z_cut,
        Z_REST=-h_drop,                        # lowest point of the trough
        Y_TROUGH_BACK=y_axis - r_trough,       # == T_PLATE + gap_eff - CLEAR
        Y_ENV_BACK=y_axis - r_out,             # == T_PLATE + gap_eff - CLEAR - T_WALL
        Z_ENV_BOT=z_axis - r_out,
        Y_PROJ=y_axis + r_out,
        CHAM_DEG=math.degrees(MOUTH_CHAM / r_trough),  # arc the chamfer eats, per side
        BACK_CLEAR=y_axis - r_bar,             # wall to nearest bar surface
        REACH=y_axis - T_PLATE,                # plate face to the load point
        Z_ARM_TOP=max(ARM_ROOT_FRAC * (y_axis - T_PLATE), 2.0 * T_WALL),
    )

    # --- invariants that keep the part valid across the parameter range -----
    assert H_PLATE <= H_PLATE_CAP, f"H_PLATE {H_PLATE} exceeds the {H_PLATE_CAP} mm cap"
    assert gap_eff > CLEAR, (
        f"bar centre at Y={y_axis:.3f} leaves only {gap_eff:.3f} mm to the plate face; "
        f"needs more than CLEAR={CLEAR} or the trough bites into the plate")
    assert d["Y_TROUGH_BACK"] > face, "trough would intersect the plate's front face"
    assert d["Y_ENV_BACK"] > 0.0, "cradle would break the Y=0 tape plane"
    assert 0.0 < z_cut < H_PLATE, "cradle arms must terminate within the plate height"
    assert 160.0 <= WRAP_DEG <= 180.0, "wrap must stay a cradle, not a tube"
    assert r_out < W_PLATE / 2.0, "cradle wider than the plate"
    assert 0.0 <= BULGE_FADE_Z <= H_PLATE, "the swell must fade out within the plate"
    assert NOTCH_D < H_PLATE / 4.0 and NOTCH_W < W_PLATE / 4.0, (
        "the witness notch is a sighting mark, not a feature")
    assert R_ROOT > 0.0 and R_ROOT_LOW >= 0.0, "fillet radii are sizes, not switches"
    assert FILLET_R_MIN > 0.0, (
        "a fillet loft cannot end on a zero radius: every point of the arc would "
        "collapse onto the tangent point and the end ring would be degenerate")
    if RIB_DEPTH > 0.0:
        assert LAYER_H > 0.0, "the relief is pitched in layers; give it a layer height"
        for name, val in (("RIB_PITCH", RIB_PITCH), ("RIB_WIDTH", RIB_WIDTH)):
            n_layers = val / LAYER_H
            assert abs(n_layers - round(n_layers)) < 1.0e-9, (
                f"{name}={val} is {n_layers:.4f} layers at LAYER_H={LAYER_H}.  The "
                f"whole point of this feature is that its edges land ON layer "
                f"boundaries, so it must be a whole number of them")
        assert 0.0 < RIB_WIDTH < RIB_PITCH, "a groove has to be narrower than its pitch"
        assert RIB_DEPTH <= T_WALL / 4.0, (
            f"RIB_DEPTH={RIB_DEPTH} is {RIB_DEPTH/T_WALL:.0%} of the wall; this is a "
            f"texture, not a channel")
        assert 0.0 < RIB_X_LIM <= W_SADDLE / 2.0 + FLARE, (
            "the relief cannot run past the end of the cradle it is cut into")
    return d


# ===========================================================================
# 2-D geometry helpers
# ===========================================================================

def circumscribed_circle(cu, cv, r, n):
    """Polygon that CONTAINS the circle of radius r, with a flat facet at the bottom.

    Circumscribing both the trough cutter and the cradle envelope with the same
    phase makes the radial gap between them exactly T_WALL at every angle, and
    puts the trough's lowest surface exactly at v = cv - r (no tessellation
    sag under the rest point).
    """
    rr = r / math.cos(math.pi / n)
    out = []
    for k in range(n):
        a = (k + 0.5) * (2.0 * math.pi / n)   # 0 == straight down
        out.append((cu + rr * math.sin(a), cv - rr * math.cos(a)))
    return out


def clip_halfplane(poly, a, b, c):
    """Sutherland-Hodgman clip of a convex polygon to a*u + b*v <= c."""
    out = []
    n = len(poly)
    for i in range(n):
        cur, nxt = poly[i], poly[(i + 1) % n]
        dc = a * cur[0] + b * cur[1] - c
        dn = a * nxt[0] + b * nxt[1] - c
        if dc <= 0.0:
            out.append(cur)
        if (dc <= 0.0) != (dn <= 0.0):
            t = dc / (dc - dn)
            out.append((cur[0] + t * (nxt[0] - cur[0]),
                        cur[1] + t * (nxt[1] - cur[1])))
    return out


def clip_below(poly, v_max):
    return clip_halfplane(poly, 0.0, 1.0, v_max)


def erode_convex(poly, d):
    """Shrink a CONVEX polygon by d, by pushing every edge inward along its normal.

    Erosion by d, swept over d of travel in X, is exactly a 45-degree flare --
    the silhouette grows one unit outward per unit along the build direction,
    which is the shallowest slope FDM prints without support.
    """
    res = poly[:]
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        length = math.hypot(ex, ey)
        if length < 1.0e-12:
            continue
        nx, ny = ey / length, -ex / length          # outward normal, CCW winding
        res = clip_halfplane(res, nx, ny, nx * x0 + ny * y0 - d)
        if len(res) < 3:
            return []
    return res


def span_at_v(poly, v):
    """(u_min, u_max) of a CONVEX polygon at height v, or None if it misses."""
    us = []
    n = len(poly)
    for i in range(n):
        (u0, v0), (u1, v1) = poly[i], poly[(i + 1) % n]
        if (v0 > v) == (v1 > v):
            continue
        us.append(u0 + (v - v0) * (u1 - u0) / (v1 - v0))
    return (min(us), max(us)) if len(us) >= 2 else None


def area_beyond_face(poly, x_face, steps=400):
    """Area of a convex Y-Z profile lying in front of the plate's front face.

    The face leans: the graded swell makes it a curve in Z, so this integrates
    the profile in Z strips rather than clipping it to a vertical half-plane.
    """
    if len(poly) < 3:
        return 0.0
    z_lo = min(p[1] for p in poly)
    z_hi = max(p[1] for p in poly)
    if z_hi - z_lo <= 0.0:
        return 0.0
    dz = (z_hi - z_lo) / steps
    total = 0.0
    for i in range(steps):
        z = z_lo + (i + 0.5) * dz
        span = span_at_v(poly, z)
        if span is None:
            continue
        y0, y1 = span
        total += max(y1 - max(y0, plate_face_y(x_face, z)), 0.0) * dz
    return total


def hull2d(pts):
    """Andrew's monotone chain.  Returns the convex hull, CCW, without duplicates."""
    pts = sorted(set((round(p[0], 9), round(p[1], 9)) for p in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def point_in_poly(pt, poly):
    """Even-odd test.  Used only by the self-check, never by the builder."""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xc = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xc:
                inside = not inside
    return inside


def bulge_shape(x):
    """Normalised X profile of the swell: 1 on the centreline, 0 at the side edges.

    A shallow arc through (+/-W_PLATE/2, 0) and (0, 1), so the plate's outline
    and its Y=0 tape face are untouched -- only the front face moves, and only
    forwards.  Sampled outside +/-W_PLATE/2 it goes slightly negative, which is
    harmless: that part of the lens lies outside the plate's own outline.
    """
    if BULGE <= 0.0:
        return 0.0
    half = W_PLATE / 2.0
    r = (half * half) / (2.0 * BULGE) + BULGE / 2.0
    return ((BULGE - r) + math.sqrt(max(r * r - x * x, 0.0))) / BULGE


def bulge_at(z):
    """Amplitude of the swell at height z: full at the bottom edge, nil on top.

    Smoothstep, so the graded face leaves the bottom edge and meets the flat top
    band with zero slope in both places -- no crease at either end of the fade.
    """
    if BULGE <= 0.0 or BULGE_FADE_Z <= 0.0:
        return 0.0
    if z <= 0.0:
        return BULGE
    if z >= BULGE_FADE_Z:
        return 0.0
    t = z / BULGE_FADE_Z
    return BULGE * (1.0 + t * t * (2.0 * t - 3.0))


def plate_face_y(x=0.0, z=0.0):
    """Y of the plate's front face at a given X and height Z.

    Separable: the X arc sets the shape, the Z fade sets its amplitude.  The
    default z=0 is the bottom edge, where the face is at its most proud -- the
    right value for anything that needs the worst case rather than a local one.
    """
    return T_PLATE + bulge_at(z) * bulge_shape(x)


def lens_profile(z, seg=64):
    """The swell as a closed 2-D profile in (X, Y) at height z.

    Lofting these up Z is what curves the front face; the back of the profile
    runs behind Y = 0 so the plate's own flat tape cap survives the intersection
    untouched.
    """
    half = W_PLATE / 2.0
    over = 2.0
    pts = [(-half - over, -1.0), (half + over, -1.0)]
    for i in range(seg + 1):
        x = (half + over) - 2.0 * (half + over) * i / seg
        pts.append((x, plate_face_y(x, z)))
    return pts


def lens_rings():
    """Z stations for the lens loft: one below the plate, the fade, one above."""
    zs = [-10.0]
    zs += [BULGE_FADE_Z * i / SEG_BULGE_Z for i in range(SEG_BULGE_Z + 1)]
    zs += [H_PLATE + 10.0]
    return [(z, lens_profile(z)) for z in sorted(set(zs))]


def notch_profile():
    """The witness notch as a V in (X, Z), to be swept along Y through the plate.

    NOTCH_W is the width AT the top edge, which is the only place it can be
    seen or measured.  The flanks are then carried past Z = H_PLATE on that same
    slope -- so the cut is a notch in the edge rather than a slot in the face --
    which means the profile's own top is wider than NOTCH_W and must be worked
    out, not simply set to NOTCH_W/2.
    """
    over = 2.0
    half = NOTCH_W / 2.0
    return [(-half * (NOTCH_D + over) / NOTCH_D, H_PLATE + over),
            (0.0, H_PLATE - NOTCH_D),
            (half * (NOTCH_D + over) / NOTCH_D, H_PLATE + over)]


def rounded_rect(w, h, r, seg):
    """Rounded rectangle in (u, v), spanning u in [-w/2, w/2] and v in [0, h].  CCW."""
    assert r < min(w, h) / 2.0, "corner radius too large for the plate"
    u0, u1 = -w / 2.0, w / 2.0
    v0, v1 = 0.0, h
    corners = [(u1 - r, v0 + r, -90.0, 0.0),
               (u1 - r, v1 - r, 0.0, 90.0),
               (u0 + r, v1 - r, 90.0, 180.0),
               (u0 + r, v0 + r, 180.0, 270.0)]
    pts = []
    for cu, cv, a0, a1 in corners:
        for i in range(seg + 1):
            a = math.radians(a0 + (a1 - a0) * i / seg)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


# ===========================================================================
# 2-D geometry: the structural fillets
# ===========================================================================

def _unit(v):
    length = math.hypot(v[0], v[1])
    return (v[0] / length, v[1] / length) if length > 1.0e-12 else (0.0, 0.0)


def face_dir(x, z, h=1.0e-3):
    """Unit direction straight UP the plate's front face at (x, z).

    Not (0, 1): the graded swell leans the face forward by up to BULGE, so the
    surface a fillet has to be tangent to is a curve, and a fillet built against
    a vertical plane would sit a fraction of a millimetre proud of it.
    """
    dy = (plate_face_y(x, z + h) - plate_face_y(x, z - h)) / (2.0 * h)
    return _unit((dy, 1.0))


def dist_to_poly(pt, poly):
    """Shortest distance from a point to a closed polygon's boundary."""
    best = float("inf")
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 <= 0.0 else max(0.0, min(1.0, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / L2))
        best = min(best, math.hypot(pt[0] - ax - t * dx, pt[1] - ay - t * dy))
    return best


def near_fillet(co, plan, margin):
    """Is this point inside a lofted fillet's profile, or within `margin` of it?

    Tested against the ACTUAL profile polygon at the bracketing X stations, not a
    disc around the corner.  A disc is the obvious shortcut and it is far too
    greedy: the upper fillet's legs are 11.2 mm long, so a disc that covers them
    also swallows the plate's bottom edge for the whole 52 mm the collar spans, and
    that edge loses its round-over for no reason.
    """
    if not plan:
        return False
    ax = abs(co.x)
    if ax > plan[-1][0] + margin:
        return False
    idx = min(range(len(plan)), key=lambda i: abs(plan[i][0] - ax))
    for j in (idx - 1, idx, idx + 1):
        if not 0 <= j < len(plan):
            continue
        pts = plan[j][1]
        if point_in_poly((co.y, co.z), pts) or dist_to_poly((co.y, co.z), pts) <= margin:
            return True
    return False


def burial_room(x, pt, direction, limit, margin=0.25):
    """How far a point may travel along `direction` and still lie behind the plate face.

    Burying a fillet's corner is only safe while there is plate to bury it in, and
    how much there is depends on the station: the flare pushes the lower corner
    outward until it is within a millimetre of the face it is supposed to hide
    inside.  Travel that is not checked against the local face is travel straight
    out through the front of the part.
    """
    def inside(t):
        return pt[0] + t * direction[0] <= plate_face_y(x, pt[1] + t * direction[1]) - margin

    if inside(limit):
        return limit
    lo, hi = 0.0, limit
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if inside(mid):
            lo = mid
        else:
            hi = mid
    return lo


def aim_along_face(x, corner, r_hint):
    """Re-aim a fillet's plate-face leg at the face where the leg ENDS, not starts.

    The face is a curve, and over the ~6.7 mm the leg covers at R_ROOT = 8 the
    swell falls away by 0.06 mm.  Built against the TANGENT at the corner, the
    fillet's leg therefore finishes 0.06 mm in front of the face it is supposed to
    die into, and the union leaves a feather ridge the whole width of the part:
    3.1 mm edges folded to 11 degrees.  Nothing on the finished print would show it
    -- 0.06 mm is under a third of a layer -- but it is precisely the geometry an
    unclamped round-over cannot handle, and it was 162 such edges the round-over
    had to be taught to refuse.

    Aiming the leg along the SECANT instead lands both of its ends exactly on the
    face and leaves the middle a few microns behind it, which is the right side to
    err on: buried geometry disappears into the union, proud geometry does not.
    The leg length depends on the corner angle, which depends on the leg, so this
    is a fixed point -- it converges in two passes and is given four.
    """
    p, u1, u2, len1, len2 = corner
    for _ in range(4):
        cosv = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        theta = math.acos(cosv)
        if not 1.0e-4 < theta < math.pi - 1.0e-4:
            return corner
        z_end = p[1] + (r_hint / math.tan(theta / 2.0)) * u1[1]
        if not p[1] + 1.0e-6 < z_end < H_PLATE:
            return corner
        u1 = _unit((plate_face_y(x, z_end) - p[0], z_end - p[1]))
    return p, u1, u2, len1, len2


def corner_fillet(p, u1, u2, r, seg=None, bury=None):
    """A fillet of radius r tangent to BOTH surfaces leaving the corner at p.

    u1 and u2 are unit directions along those two surfaces, pointing away from the
    corner into the open air between them.  With theta the angle between them, the
    arc centre sits at p + (r / sin(theta/2)) * bisector and the two tangent points
    at p + (r / tan(theta/2)) * u.  That is the entire construction, and it is what
    makes the blend meet each surface with a matching slope instead of a step.

    The version this replaces assumed the corner was exactly 90 degrees -- a
    horizontal arm top meeting a vertical plate face.  It is neither.  The arm's
    upper edge falls about 6.5 degrees on its way out to the cradle and the plate's
    face leans with the swell, so a right-angle blend ran out onto the arm 0.46 mm
    above the surface at R = 4.  Scaled to R = 8 that ledge would have been 0.9 mm:
    the fillet would have been cutting a new sharp corner as fast as it removed the
    old one, which is the opposite of the point.

    Returned as a dict: `pts` is the closed Y-Z polygon corner -> T1 -> arc -> T2,
    with the corner pushed `bury` back INTO the solid so the union has real volume
    to bite on rather than a tangency; `c`, `t1`, `t2`, `b` and `r` come back too,
    because the acceptance checks measure this arc off the finished mesh and need
    to know where to aim.  Vertex count is always seg + 2, which is what lets a
    row of these be lofted along X.
    """
    seg = FILLET_SEG if seg is None else seg
    bury = FILLET_BURY if bury is None else bury
    u1, u2 = _unit(u1), _unit(u2)
    cosv = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
    theta = math.acos(cosv)
    if r <= 0.0 or theta <= 1.0e-4 or theta >= math.pi - 1.0e-4:
        return None
    off = r / math.tan(theta / 2.0)
    b = _unit((u1[0] + u2[0], u1[1] + u2[1]))
    reach = r / math.sin(theta / 2.0)
    c = (p[0] + b[0] * reach, p[1] + b[1] * reach)
    t1 = (p[0] + u1[0] * off, p[1] + u1[1] * off)
    t2 = (p[0] + u2[0] * off, p[1] + u2[1] * off)
    a1 = math.atan2(t1[1] - c[1], t1[0] - c[0])
    a2 = math.atan2(t2[1] - c[1], t2[0] - c[0])
    d = a2 - a1                                  # the arc spans exactly pi - theta,
    while d > math.pi:                           # so the short way round is right
        d -= 2.0 * math.pi
    while d < -math.pi:
        d += 2.0 * math.pi
    root = (p[0] - b[0] * bury, p[1] - b[1] * bury)
    pts = [root, t1]
    for i in range(1, seg):
        a = a1 + d * i / seg
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    pts.append(t2)
    return dict(pts=pts, r=r, c=c, t1=t1, t2=t2, b=b, root=root, off=off, p=p,
                u1=u1, u2=u2,
                theta=math.degrees(theta), a1=a1, a2=a2, sweep=d)


def upper_corner(profile, x):
    """The re-entrant corner where the cradle's top face dies into the plate's FRONT face.

    Returns (corner, u1, u2, len1, len2): the point, the two surface directions
    leaving it, and how far each of those surfaces actually runs -- which is what
    bounds the fillet radius, and is why it is measured here rather than assumed.

    None when this station's profile never crosses the face at all, which is what
    the outer end of the flare looks like: eroded clear of the plate, standing in
    front of it, touching nothing.
    """
    best = None
    n = len(profile)
    for i in range(n):
        p0, p1 = profile[i], profile[(i + 1) % n]
        d0 = p0[0] - plate_face_y(x, p0[1])
        d1 = p1[0] - plate_face_y(x, p1[1])
        if d0 * d1 >= 0.0:
            continue
        lo, hi = 0.0, 1.0
        for _ in range(48):                      # the face is a curve: bisect, do
            mid = 0.5 * (lo + hi)                # not interpolate on Y alone
            y = p0[0] + (p1[0] - p0[0]) * mid
            z = p0[1] + (p1[1] - p0[1]) * mid
            if (y - plate_face_y(x, z)) * d0 > 0.0:
                lo = mid
            else:
                hi = mid
        t = 0.5 * (lo + hi)
        pt = (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
        far = p1 if p1[0] > p0[0] else p0        # the end of the edge AWAY from the plate
        if best is None or pt[1] > best[0][1]:   # the highest crossing is the corner
            best = (pt, far)
    if best is None:
        return None
    pt, far = best
    u2 = _unit((far[0] - pt[0], far[1] - pt[1]))
    len2 = math.hypot(far[0] - pt[0], far[1] - pt[1])
    return pt, face_dir(x, pt[1]), u2, max(H_PLATE - pt[1], 0.0), len2


def lower_corner(profile, x):
    """The re-entrant corner where the cradle's underside dies into the plate's BOTTOM face.

    The plate stops at Z = 0, so this corner is where the cradle's rear edge crosses
    that plane -- and only when it does so INSIDE the plate's own thickness.  Where
    the flare has eroded the profile clear of the plate there is no such corner and
    this returns None, which the caller reads as "freeze and run out".
    """
    best = None
    n = len(profile)
    for i in range(n):
        p0, p1 = profile[i], profile[(i + 1) % n]
        if (p0[1] > 0.0) == (p1[1] > 0.0):
            continue
        t = -p0[1] / (p1[1] - p0[1])
        y = p0[0] + (p1[0] - p0[0]) * t
        down = p1 if p1[1] < p0[1] else p0
        if best is None or y < best[0]:          # the REAR crossing, not the front one
            best = (y, down)
    if best is None:
        return None
    y, down = best
    if not (0.0 < y < plate_face_y(x, 0.0)):
        return None                              # the cradle has left the plate here
    pt = (y, 0.0)
    u2 = _unit((down[0] - pt[0], down[1] - pt[1]))
    len2 = math.hypot(down[0] - pt[0], down[1] - pt[1])
    return pt, (-1.0, 0.0), u2, y, len2


CORNER_DEG = (25.0, 155.0)   # what still counts as a corner worth blending


def corner_room(corner, y_lim):
    """(corner, u1, u2, largest honest radius) for a blendable corner, or None.

    Three of the four bounds are the surfaces themselves: a fillet cannot run off
    the top of the plate, cannot reach past the next hull vertex (beyond which it
    would be tangent to nothing), and cannot cross Y = y_lim, the bar's rearmost
    surface, without standing in its vertical drop-in path.

    The fourth bound is the corner angle, and it is the one that matters most.  The
    tangent offset is r / tan(theta/2), so as two surfaces approach parallel the
    fillet's tangent points run away to infinity.  The flare produces exactly that:
    at the station where the eroded envelope's back face lies within a hair of the
    plate's own face, the "corner" between them closes to a couple of degrees, and
    what comes back is not a blend but a sliver several millimetres long.  Refusing
    to call that a corner is cheaper than trying to build one.
    """
    p, u1, u2, len1, len2 = corner
    cosv = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
    theta = math.degrees(math.acos(cosv))
    if not CORNER_DEG[0] <= theta <= CORNER_DEG[1]:
        return None
    tan_half = math.tan(math.radians(theta) / 2.0)
    reach_y = max(u1[0], u2[0], 1.0e-6)          # how fast the legs head for the bar
    r_cap = min(len1 * tan_half, len2 * tan_half,
                max(y_lim - p[0], 0.0) / reach_y * tan_half)
    return (p, u1, u2, r_cap) if r_cap >= FILLET_R_MIN else None


def rib_bands(x_lim=None):
    """[(x0, x1)] of the layer-aligned relief grooves, in part coordinates.

    Two things are load-bearing here and neither is cosmetic:

    * Every edge is SNAPPED to a layer boundary.  export_stl drops the part onto
      the bed after rotating X into the printer's Z, so print height is
      x + W_PLATE/2 -- and W_PLATE/2 = 38.1 mm is 190.5 layers at 0.2 mm, not 190.
      Half a layer of phase error would put every groove edge in the middle of a
      layer, which is precisely the stair-step this feature exists to hide.
    * X = 0 is always the centre of a LAND, never a groove.  Every verification ray
      in this file is fired in the X = 0 plane -- the wall sweep, the trough circle
      fit, the rest point, the drop-in clearance, the mouth chamfer.  A groove there
      would move all of them at once and the harness would be measuring the texture
      instead of the part.  The grooves are offset half a pitch to guarantee it.
    """
    if RIB_DEPTH <= 0.0 or RIB_PITCH <= 0.0 or RIB_WIDTH <= 0.0:
        return []
    x_lim = RIB_X_LIM if x_lim is None else x_lim

    def snap(x):                                 # nearest layer boundary, from the bed
        return round((x + W_PLATE / 2.0) / LAYER_H) * LAYER_H - W_PLATE / 2.0

    bands, k = [], 0
    while True:
        x0 = snap((k + 0.5) * RIB_PITCH - RIB_WIDTH / 2.0)
        x1 = x0 + RIB_WIDTH
        if x1 > x_lim:
            break
        bands.append((x0, x1))
        bands.append((-x1, -x0))
        k += 1
    return sorted(bands)


# ===========================================================================
# Blender object helpers
# ===========================================================================

def purge_startup_junk():
    """Delete Blender's default Cube, Camera and Light -- and nothing else.

    A background Blender starts on the startup file, so the scene this script
    builds into already contains a 2 x 2 x 2 unit Cube at the world origin.  At
    scale_length = 0.001 that is a 2 mm cube sitting exactly on the centre of the
    plate's bottom edge, and it was saved into every .blend this file has ever
    written.  It never reached an STL -- export_stl exports the selected object
    only -- but it is the first thing you see on opening the scene, and it looks
    like a defect in the part.

    The identification is deliberately narrow, because the module docstring
    invites running this file inside a LIVE session with other work open: name,
    type, an exactly-8-vertex mesh, 2 mm on every side, and sitting on the origin.
    A mesh that fails any of those is somebody's, and is left alone.  Returns the
    names removed so the caller can say what it did rather than delete in silence.
    """
    gone = []
    for obj in list(bpy.data.objects):
        if obj.name == "Cube" and obj.type == 'MESH':
            if (len(obj.data.vertices) == 8
                    and all(abs(d - 2.0) < 1.0e-6 for d in obj.dimensions)
                    and obj.location.length < 1.0e-6):
                gone.append(obj.name)
                purge(obj.name)
        elif obj.name in ("Camera", "Light") and obj.type in ('CAMERA', 'LIGHT'):
            gone.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return gone


def scene_setup():
    scn = bpy.context.scene
    scn.unit_settings.system = 'METRIC'
    scn.unit_settings.scale_length = 0.001      # 1 Blender unit == 1 mm
    scn.unit_settings.length_unit = 'MILLIMETERS'
    junk = purge_startup_junk()
    if junk:
        print(f"  [scene] removed Blender's startup objects: {', '.join(junk)}")


def purge(*names):
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        mesh = obj.data if obj.type == 'MESH' else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def prism(name, pts2d, to3d, extrude):
    """Closed manifold prism: a planar n-gon swept along `extrude`.

    `to3d(u, v)` maps a profile point into 3-space; `extrude` is the sweep vector.
    """
    extrude = Vector(extrude)
    bm = bmesh.new()
    verts = [bm.verts.new(to3d(u, v)) for (u, v) in pts2d]
    face = bm.faces.new(verts)
    bm.normal_update()
    if face.normal.dot(extrude) > 0.0:
        face.normal_flip()          # cap must face away from the sweep
    ret = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=moved, vec=extrude)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def banded_prism(name, pts2d, bands):
    """One cutter object carrying the same profile as many disjoint closed shells.

    Two dozen grooves could be two dozen booleans.  They are one: every band is a
    separate watertight shell in a single mesh, which is still manifold (every edge
    has exactly two faces) and which both solvers accept.  Doing it in one pass also
    means the vertex-count guard in boolean() is checked once against the whole
    texture rather than being satisfied by whichever groove happened to bite first.
    """
    bm = bmesh.new()
    for x0, x1 in bands:
        verts = [bm.verts.new((x0, u, v)) for (u, v) in pts2d]
        face = bm.faces.new(verts)
        bm.normal_update()
        if face.normal.x > 0.0:
            face.normal_flip()
        ret = bmesh.ops.extrude_face_region(bm, geom=[face])
        moved = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=moved, vec=(x1 - x0, 0.0, 0.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def loft_solid(name, rings, to3d):
    """Closed manifold solid stitched ring to ring, with a cap at each end.

    rings is [(w, [(u, v), ...]), ...] and every ring must carry the SAME vertex
    count, in the same order, so ring i vertex k pairs with ring i+1 vertex k.
    Unlike hull_solid this reproduces a NON-convex sweep faithfully -- which the
    graded swell needs, since a smoothstep fade is concave over its lower half
    and a convex hull would cut that away as a chord.
    """
    n = len(rings[0][1])
    assert all(len(pts) == n for _, pts in rings), "loft rings differ in vertex count"
    assert len(rings) >= 2, "a loft needs at least two rings"

    bm = bmesh.new()
    layers = [[bm.verts.new(to3d(u, v, w)) for (u, v) in pts] for w, pts in rings]
    for lo, hi in zip(layers, layers[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(layers[0])
    bm.faces.new(layers[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _apply_boolean(target, cutter, operation, solver):
    mod = target.modifiers.new(name="bool", type='BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    try:
        mod.solver = solver
    except TypeError:
        mod.solver = 'EXACT'
    dg = bpy.context.evaluated_depsgraph_get()
    new_mesh = bpy.data.meshes.new_from_object(
        target.evaluated_get(dg), preserve_all_data_layers=False, depsgraph=dg)
    target.modifiers.remove(mod)
    old = target.data
    target.data = new_mesh
    new_mesh.name = old.name
    bpy.data.meshes.remove(old)


def hull_solid(name, rings):
    """Closed convex solid through a set of 2-D profiles placed at given X.

    rings is [(x, [(y, z), ...]), ...].  Every ring is convex and the outer ones
    are eroded subsets of the inner ones, so the 3-D convex hull IS the loft:
    planar 45-degree side facets between them, and guaranteed watertight and
    manifold with no boolean involved.
    """
    bm = bmesh.new()
    for x, profile in rings:
        for (u, v) in profile:
            bm.verts.new((x, u, v))
    bm.verts.ensure_lookup_table()
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    interior = [g for g in (res.get("geom_interior") or []) if g.is_valid]
    if interior:
        bmesh.ops.delete(bm, geom=interior, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def boolean(target, cutter, operation, solver='MANIFOLD'):
    """Apply a boolean, delegating the guard to part_kit.

    This used to guard on VERTEX COUNT: retry on EXACT if the count did not move,
    and raise if it still did not.  That catches the silent no-op -- the failure
    that once cost the fit gauge its labels -- but not the worse one beside it.
    When the MANIFOLD solver DECLINES, the failed modifier still bakes and merges
    the cutter in as a second closed shell.  The vertex count moves, so a
    "did anything change" guard accepts it on the first attempt and never reaches
    the EXACT retry that would have worked.  part_kit.boolean tests the SIGN of the
    signed-volume change against the operation instead, which is the same guard this
    file's `_signed_volume` docstring reasons about, and it raises with the cutter's
    own volume so the `target + cutter` merge signature is visible on first read.

    Delegated rather than reimplemented because the kit's version is strictly
    stronger and this file is the repository's regression fixture: routing the
    fixture's booleans through the shipped code is what makes the pinned digest
    capable of noticing a kit regression at all.  Verified digest-neutral before
    landing -- all three variants reproduce byte-identical geometry.
    """
    return _kit.boolean(target, cutter, operation, solver=solver)


def round_edges(obj, g=None, radius=None, segments=None, angle_deg=None, tol=1.0e-6):
    """Router-style round-over on sharp edges -- but never on the tape face.

    The work is done by the target filter, not by the bevel.  Its rules are NAMED
    and not numbered: they have been counted twice in this file's history and the
    count went stale both times while the rules themselves stayed correct, so a
    header said "four" over a filter that tested six.  Adding a rule means adding
    an entry here, never renumbering one.  Every test the filter applies is below,
    in the order it runs them; the first is a guard, the rest are exclusions.

      MANIFOLD GUARD -- an edge without exactly two faces is not a fold and has no
        round-over to give.  It leads because every rule after it reads the two
        adjoining faces.
      MIN EDGE (ROUND_MIN_EDGE_FRAC * radius) -- a bevel cannot fit an edge much
        shorter than its own radius: the corner patches it opens at the two ends
        overrun each other and, with clamp_overlap off, interpenetrate.  Note that
        the bound moves WITH the radius while the geometry it is compared against
        does not, so which chains it catches is a property of ROUND_R and not a
        fixed fact.  At ROUND_R 1.0 the bound was 0.50 mm and it took the plate's
        entire corner-arc chain -- 0.393 mm links -- out of the target set, which
        is why the four plate corners shipped dead sharp for four iterations.  At
        the current ROUND_R 0.5 the bound is 0.25 mm, the arcs are IN, and what it
        still excludes is 44 short fragments (40 of them sub-links of that same
        arc chain).  See ROUND_MIN_EDGE_FRAC for the measured spectrum.
      TAPE FACE -- any edge with a vertex at Y = 0.  Beveling one would drag a
        tape-face vertex and change the 76.2 x 44.45 adhesive rectangle, which is
        the one surface on this part that must not move.
      TROUGH SURFACE -- any edge with a vertex ON the trough surface.  Left in, the
        round-over nibbles the cradle rim and the measured wall on the load path
        falls from 3.000 mm to 0.015 mm -- a cosmetic feature is not allowed to
        eat a structural one.
      FOLD, BOTH BOUNDS (ROUND_ANGLE .. ROUND_ANGLE_MAX) -- one test carrying two
        exclusions, which is exactly how the header lost count before.  Below
        ROUND_ANGLE there is no crease worth softening, so the 192-facet trough is
        left alone instead of being nibbled at every facet junction.  Above
        ROUND_ANGLE_MAX the slide an offset bevel must make along each adjoining
        face is more than anything here has to give, and with clamp_overlap off
        the vertex ends up wherever the arithmetic lands.
      FACE AREA (ROUND_MIN_FACE_FRAC * radius^2) -- there must be face enough
        beside the edge to slide along.  The structural fillets' tangency seams
        come back from the boolean as micron-scale faces, and a bevel across one
        returns a spurious face the size of its own offset rather than a
        round-over.
      FILLET FOOTPRINT (near_fillet) -- any edge inside a lofted structural
        fillet's profile, or within a radius of it.  Those are tangent blends:
        there is no sharp edge in one for a round-over to soften, and every edge
        found inside one is an artefact of how the loft tessellated.  It runs last
        on purpose -- Python short-circuits, so the polygon test only sees the few
        hundred edges that survived the cheap rules, not the thirty thousand in
        the mesh.

    Uses bmesh.ops.bevel on an explicit edge list rather than the Bevel modifier.
    The modifier route needs a bevel_weight_edge attribute, and writing that from
    bmesh yields bevel TOPOLOGY at zero offset -- 3764 verts and an unchanged
    32462.8 mm^3 -- which the following weld then quietly collapses again.

    Returns the number of edges rounded.
    """
    radius = ROUND_R if radius is None else radius
    segments = ROUND_SEG if segments is None else segments
    thresh = math.radians(ROUND_ANGLE if angle_deg is None else angle_deg)
    if radius <= 0.0:
        return 0

    def on_trough(v):
        if g is None:
            return False
        dy, dz = v.co.y - g["Y_AXIS"], v.co.z - g["Z_AXIS"]
        return abs(math.hypot(dy, dz) - g["R_TROUGH"]) < 0.05

    hard_fold = math.radians(ROUND_ANGLE_MAX)
    min_face = ROUND_MIN_FACE_FRAC * radius * radius   # mm^2; _FRAC is of radius^2
    min_edge = ROUND_MIN_EDGE_FRAC * radius
    # MIN EDGE is the newest of the rules and the only one aimed at a chain rather
    # than at a sliver; it goes at the front of the filter below, straight after the
    # manifold guard, because calc_length is the cheapest test here.  How much it
    # drops depends entirely on ROUND_R: at ROUND_R 1.0 it took 62% of the edges the
    # other rules would have passed (375 targets to 140 on the nominal build); at the
    # current ROUND_R 0.5 it takes 12% (374 to 330).  Why 0.5 and not 0.2 or 1.0 --
    # and why the earlier sweep's verdicts belong to the 1.0 radius -- is at
    # ROUND_MIN_EDGE_FRAC.
    #
    # FOLD and FACE AREA each catch a failure the other does not.  Both arrived with
    # the structural fillets, whose tangent seams the boolean leaves as micron-scale
    # faces folded almost flat -- the one shape an unclamped offset bevel cannot do
    # anything sane with.  Measured across all three H_DROP variants, at ROUND_R 1.0
    # and before MIN EDGE existed -- these four rows are the experiment that put the
    # two bounds in the filter, not a description of the current build (the current
    # one rounds 330 edges on the nominal and reads SF 36.48):
    #
    #   neither bound   H_DROP=0 grew its bounding box by 8.3 mm
    #   fold only       envelope fine, but a spurious bevel face cut clean through
    #                   the arm at Y = 8.5 and the bending check read SF 0.49
    #   face only       (untested alone; the fold bound is cheap and provably needed)
    #   both            envelope exact, SF 46.6 at the right section, 525 edges
    #                   rounded, and the plate's perimeter chain untouched
    #
    # A rule that is deliberately NOT in the filter -- "the adjoining faces must be
    # longer than the slide" -- is the honest question and answers no to nearly
    # everything, because boolean seams subdivide the plate's front face into strips
    # shorter than the radius: 907 rounded edges fell to 42 and the part came back
    # with sharp outer edges.  FACE AREA is the bound that was kept in its place, and
    # it is on the AREA rather than on the length for that reason.
    #
    # FILLET FOOTPRINT excludes the structural fillets themselves.
    #
    # They are TANGENT blends.  They arrive at the surfaces they join with matching
    # slope, by construction -- there is no sharp edge there for a round-over to
    # soften, and every edge it finds inside one is an artefact of how the loft was
    # tessellated rather than a feature of the part.  Beveling them is all cost.
    #
    # Measured, on the lower collar's runout: before the round-over that region has
    # 122 creases sharper than 30 degrees and NOT ONE folded face; after it, 287
    # creases and 78 folds at better than 170 degrees -- zero-thickness fins.  The
    # round-over creates every one of them.  That is the ragged patch you can see
    # under the plate's bottom edge either side of the arm.
    #
    # This exclusion goes LAST in the chain on purpose: Python short-circuits, so
    # the polygon test only runs for the few hundred edges that survived the cheap
    # rules, not the thirty thousand in the mesh.
    plans = [p for p in (g.get("FILLET_PLAN_upper"), g.get("FILLET_PLAN_lower")) if p] if g else []
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    targets = [e for e in bm.edges
               if len(e.link_faces) == 2
               and e.calc_length() >= min_edge
               and all(abs(v.co.y) > tol for v in e.verts)
               and not any(on_trough(v) for v in e.verts)
               and thresh <= e.calc_face_angle(0.0) <= hard_fold
               and min(f.calc_area() for f in e.link_faces) >= min_face
               and not any(near_fillet(v.co, plan, radius)
                           for v in e.verts for plan in plans)]
    def bounds():
        return [(min(v.co[i] for v in bm.verts), max(v.co[i] for v in bm.verts))
                for i in range(3)]

    if targets:
        before = bounds()
        # clamp_overlap must stay OFF.  Blender clamps the whole operation to the
        # worst edge in the set, and one 0.0051 mm boolean sliver survives here,
        # which silently drives the offset to zero everywhere: 3764 verts of
        # bevel topology and not one cubic millimetre removed.  With it off the
        # round-over is real; the acceptance checks below police the result.
        bmesh.ops.bevel(bm, geom=targets, offset=radius, offset_type='OFFSET',
                        segments=segments, profile=0.5, affect='EDGES',
                        clamp_overlap=False, loop_slide=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        # ...and this is the price of leaving it off.  An unclamped bevel offsets
        # each vertex along the intersection of its adjacent face planes, and where
        # two of those planes are nearly parallel that direction is nearly
        # undefined: the vertex is thrown as far as the arithmetic likes.  A
        # round-over of radius R cannot legitimately move any surface further than
        # R, so the envelope is checked rather than trusted.  Left unchecked, two
        # of the three H_DROP variants silently shipped STLs 3.9 mm and 12.3 mm
        # bigger than the part, and every other acceptance check passed, because
        # not one of them looked at the bounding box.
        after = bounds()
        grew = max(max(before[i][0] - after[i][0], after[i][1] - before[i][1])
                   for i in range(3))
        assert grew <= radius + tol, (
            f"the round-over grew {obj.name}'s envelope by {grew:.3f} mm with a "
            f"{radius} mm radius.  With clamp_overlap off that means it found an "
            f"edge whose faces are nearly parallel -- a sliver or a degenerate "
            f"blend -- and slid a vertex along it")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(targets)


WELD_PRE_ROUND = 5.0e-3  # mm; how hard to weld immediately BEFORE the round-over.
                       # Left at the general weld distance, and that is a MEASURED
                       # result, not a default.  The obvious theory is that the
                       # unclamped bevel trips on the micron-scale faces a tangent
                       # blend leaves along its tangent lines (5 to 11 um), so
                       # welding harder first should cure it.  It does not: swept
                       # at 0.005 / 0.02 / 0.03 / 0.05 / 0.08 mm, all three H_DROP
                       # variants failed identically at every value.  Whatever the
                       # round-over is tripping on when the fillet loft is re-sampled
                       # is not a weldable sliver.  The hook stays so the next
                       # person does not have to re-run the experiment.
MIN_EDGE_OK = 2.0e-3   # mm; anything shorter counts as a coincident vertex pair
MERGE_DIST  = 5.0e-3   # mm; welds boolean slivers, still 2x below the finest
                       # real feature in the part (font glyph detail ~0.010 mm)


def clean_mesh(obj, merge_dist=MERGE_DIST):
    """Weld coincident vertices, drop degenerate faces, re-orient normals.

    Exact booleans leave micron-scale slivers where a fillet grazes the trough
    almost tangentially -- one H_DROP variant produced a 0.000995 mm edge. Those
    are coincident vertices in all but name, so weld at a distance chosen to be
    above the sliver scale and below any genuine feature.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=merge_dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


NULL_VOLUME = 1.0e-6   # mm^3; below this a connected component encloses nothing.
                       # Not a tuned threshold and nothing sits near it: the
                       # debris this catches is a pair of identical triangles in
                       # opposite winding and measures ~1e-15, while the part is
                       # 33531.  A 1e-6 mm^3 body would be a 0.01 mm cube.  The
                       # test is "encloses nothing", NOT "is small", because
                       # small-but-real means the part came apart and that must be
                       # shouted about rather than swept up.


def _face_groups(bm):
    """Faces grouped into bodies the way a SLICER groups them: adjacency only
    across edges that have exactly two faces.

    An edge with four faces is not a join, it is a fault, so anything hanging off
    the solid through one of those is correctly seen as a separate body rather
    than as part of it.  That is the whole reason this convention is used here
    instead of "share any edge": it is what makes null debris fall out as its own
    component instead of hiding inside the shell.
    """
    parent = list(range(len(bm.faces)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for e in bm.edges:
        if len(e.link_faces) == 2:
            ra, rb = find(e.link_faces[0].index), find(e.link_faces[1].index)
            if ra != rb:
                parent[rb] = ra
    groups = {}
    for f in bm.faces:
        groups.setdefault(find(f.index), []).append(f)
    return list(groups.values())


def _signed_volume(faces):
    """Enclosed volume by the divergence theorem.  Near zero for anything that
    does not enclose, which is exactly the discriminator wanted here.

    Two details that are not fussiness.  The sum is taken about the component's
    OWN centroid, and in float64.  Done the obvious way -- mathutils vectors
    about the world origin -- a back-to-back pair of triangles 23 mm from the
    origin came back at 9.5e-06 mm^3 instead of zero, because mathutils is
    SINGLE precision and the two tetrahedra are ~60 mm^3 each cancelling to
    nothing; 9.5e-06 is just float32 epsilon at that magnitude.  It was enough to
    make null debris read as a solid body and abort the build.  Recentring
    removes the cancellation (and, for a closed surface, changes nothing: the
    integral is translation-invariant), and float64 removes the rest.  The same
    pair now measures ~1e-15.
    """
    verts = {id(v): v for f in faces for v in f.verts}.values()
    n = len(verts)
    ox = sum(float(v.co.x) for v in verts) / n
    oy = sum(float(v.co.y) for v in verts) / n
    oz = sum(float(v.co.z) for v in verts) / n
    total = 0.0
    for f in faces:
        vs = f.verts
        ax = float(vs[0].co.x) - ox
        ay = float(vs[0].co.y) - oy
        az = float(vs[0].co.z) - oz
        for i in range(1, len(vs) - 1):
            bx = float(vs[i].co.x) - ox
            by = float(vs[i].co.y) - oy
            bz = float(vs[i].co.z) - oz
            cx = float(vs[i + 1].co.x) - ox
            cy = float(vs[i + 1].co.y) - oy
            cz = float(vs[i + 1].co.z) - oz
            total += (ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx)
                      + az * (bx * cy - by * cx)) / 6.0
    return total


def triangulate_and_purge(obj):
    """Make the mesh BE the file, then delete the null geometry that exposes.

    THIS REMOVES NULL GEOMETRY.  IT IS NOT A SHAPE REPAIR.  Nothing here moves a
    vertex or changes the solid; it deletes faces that enclose no volume and
    asserts the volume is unchanged.  If the shape were wrong, this would not fix
    it and must not be asked to.

    Two steps, and the first is what the second needs.

    TRIANGULATE.  Blender's exact boolean merges its output triangles into
    n-gons, some of them slightly non-planar.  A non-planar n-gon has no surface
    of its own -- it only means something once something chooses a triangulation
    -- and the STL exporter chooses one at write time, in a place nothing in this
    script can see or check.  Doing it here instead means the mesh that is
    measured, saved in the .blend and written to the file are one mesh.  It also
    makes verify()'s topological counts equal the file's positional ones, which
    they have not been all session: measured over 324 build/parameter
    combinations, Blender's non-manifold count and the exported file's agreed in
    every single one after this call and disagreed regularly before it.

    PURGE.  The triangulation is what makes the defect visible.  Where two
    n-gons meet along a run of nearly-collinear vertices -- the flare-tip cap
    grazing the trough cutter is the case that shipped -- both of them clip the
    same ear off that run, so the same three vertices get emitted twice with
    opposite winding.  That pair is a back-to-back flap: it encloses nothing,
    contributes nothing, and its area here is 3.1e-5 and 5.0e-5 mm^2.  It is also
    invisible to every check this file had, because the flap's own three edges
    each have two faces and read manifold, while the edge it SHARES with the
    solid ends up with four -- two from the body, two from the flap.  That is the
    "2 non-manifold edges" Bambu Studio refused to slice, against the zero this
    script reported.

    Measured on the file that shipped: 25200 triangles in three positional
    components -- one body of 25196 triangles carrying 33531.5060 mm^3 and euler
    2, and two flaps of two triangles each carrying 0.0000.

    So: drop every component that encloses nothing, and insist that exactly one
    is left and that it still holds all of the volume.  A second component with
    REAL volume is a genuine geometry failure -- the part came apart -- and this
    refuses to quietly keep the bigger half.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY',
                          ngon_method='BEAUTY')
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    groups = _face_groups(bm)
    vols = [_signed_volume(g) for g in groups]
    total = sum(vols)
    solid = [i for i, v in enumerate(vols) if abs(v) >= NULL_VOLUME]
    if len(solid) != 1:
        bm.free()
        raise RuntimeError(
            f"{obj.name}: {len(solid)} components enclose real volume "
            f"({[round(vols[i], 4) for i in solid]} mm^3) -- the part is in "
            f"pieces, which is a geometry failure and not debris.  Refusing to "
            f"keep the largest and call it the part.")
    main = solid[0]
    dropped = [f for i, g in enumerate(groups) if i != main for f in g]
    stat = dict(triangles=len(bm.faces), components=len(groups),
                dropped_components=len(groups) - 1, dropped_faces=len(dropped),
                volume=vols[main], volume_dropped=total - vols[main])
    if dropped:
        bmesh.ops.delete(bm, geom=dropped, context='FACES_ONLY')
        loose_e = [e for e in bm.edges if not e.link_faces]
        if loose_e:
            bmesh.ops.delete(bm, geom=loose_e, context='EDGES')
        loose_v = [v for v in bm.verts if not v.link_faces]
        if loose_v:
            bmesh.ops.delete(bm, geom=loose_v, context='VERTS')

    after = _signed_volume(bm.faces)
    if abs(after - vols[main]) > max(NULL_VOLUME, 1.0e-9 * abs(vols[main])):
        bm.free()
        raise RuntimeError(
            f"{obj.name}: purging debris changed the enclosed volume "
            f"{vols[main]:.6f} -> {after:.6f} mm^3.  It is only allowed to "
            f"delete geometry that encloses nothing.")
    stat.update(triangles_kept=len(bm.faces),
                euler=len(bm.verts) - len(bm.edges) + len(bm.faces),
                non_manifold=sum(1 for e in bm.edges if len(e.link_faces) != 2))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return stat


def grey_material(obj, name=MATERIAL + "_grey"):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.30, 0.31, 0.33, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.75
    obj.data.materials.clear()
    obj.data.materials.append(mat)


# ===========================================================================
# the part
# ===========================================================================

def plate_anchors(g):
    """The three points that drag the cradle hull back into the plate.

    A0  high on the plate face -- sets the arm's DEPTH at the root, where the
        bending moment peaks.  Without it the hull necks down to the A1-A2 spacing
        and the arm is thinnest exactly where it is worst loaded.
    A1  buried inside the plate, just above its bottom edge
    A2  just outside the plate's bottom-front corner
    A1 and A2 close the small notch under the plate; A0 carries the load.
    """
    return [(T_PLATE - ROOT_BLEND, g["Z_ARM_TOP"]),
            (T_PLATE - ROOT_BLEND, ROOT_BLEND),
            (T_PLATE + ROOT_BLEND / 3.0, -ROOT_BLEND / 2.0)]


def saddle_profiles(g):
    """The two Y-Z profiles the saddle is made of: cradle envelope, trough cutter.

    The truncated disc is the cradle proper.  Three anchor points drag the convex
    hull back into the plate, and that is what forms the arm, the gusset and the
    root blend:
        A0  high on the plate face -- sets the arm's DEPTH at the root, which is
            where the bending moment peaks.  Without it the hull necks down to
            the A1-A2 spacing and the arm is at its thinnest exactly where it is
            worst loaded.
        A1  buried inside the plate, just above its bottom edge
        A2  just outside the plate's bottom-front corner
    A1 and A2 close the small notch under the plate; A0 carries the load.  If a
    given D_BAR/H_DROP already puts the disc behind them, the hull ignores them
    and the cradle merges into the plate on its own.
    """
    disc = circumscribed_circle(g["Y_AXIS"], g["Z_AXIS"], g["R_OUT"], SEG_CIRCLE)
    env = hull2d(clip_below(disc, g["Z_CUT"]) + plate_anchors(g))
    trough = circumscribed_circle(g["Y_AXIS"], g["Z_AXIS"], g["R_TROUGH"], SEG_CIRCLE)
    return env, trough


def mouth_rim(g, env_profile, step_deg=0.05, limit_deg=179.0):
    """Where the trough surface leaves the solid, per side, in degrees off vertical.

    WRAP_DEG does NOT answer this.  It clips the cradle disc at Z_CUT, but the
    hull then drags anchor A0 -- which sits well above Z_CUT -- over the top of
    that clip and swallows it whole, so the flat top the clip made never reaches
    the finished part.  What actually terminates the trough is wherever the arm's
    sloping upper face crosses the trough circle, and that is asymmetric: the
    back arm reaches further round the bar than the front one.

    So the wrap is measured, both from the trough surface (`rim_*`, where the
    cradle ends) and from a radius T_WALL behind it (`wall_*`, where the wall
    stops being full thickness).  Every consumer takes these instead of assuming
    WRAP_DEG describes the part -- it does not.
    """
    out = {}
    for sgn, side in ((1.0, "plus"), (-1.0, "minus")):
        for radius, tag in ((g["R_TROUGH"] + 0.01, "rim"),
                            (g["R_TROUGH"] + T_WALL, "wall")):
            last, phi = 0.0, 0.0
            while phi <= limit_deg:
                a = math.radians(phi)
                pt = (g["Y_AXIS"] + sgn * radius * math.sin(a),
                      g["Z_AXIS"] - radius * math.cos(a))
                if point_in_poly(pt, env_profile):
                    last = phi
                elif last > 0.0:
                    break               # first gap past the run: that is the edge
                phi += step_deg
            out[tag + "_" + side] = last
    return out


def plate_face_join(env_profile, fallback):
    """Highest Z at which the cradle envelope crosses the plate's front face.

    Above this the envelope has left the plate and anything between them is open
    air; below it, the two are side by side and a pinched slot is possible. That
    makes it both the root-fillet location and the ceiling for the void check.
    """
    # The face is a curve in Z now, not a plane, so each crossing is bisected
    # rather than solved -- a straight interpolation on Y would land wherever the
    # fade happened to put the face at the WRONG height.
    crossings = []
    n = len(env_profile)
    for i in range(n):
        y0, z0 = env_profile[i]
        y1, z1 = env_profile[(i + 1) % n]
        d0 = y0 - plate_face_y(0.0, z0)
        d1 = y1 - plate_face_y(0.0, z1)
        if d0 * d1 >= 0.0:
            continue
        lo, hi = 0.0, 1.0
        for _ in range(48):
            mid = 0.5 * (lo + hi)
            y = y0 + (y1 - y0) * mid
            z = z0 + (z1 - z0) * mid
            if (y - plate_face_y(0.0, z)) * d0 > 0.0:
                lo = mid
            else:
                hi = mid
        crossings.append(z0 + (z1 - z0) * 0.5 * (lo + hi))
    return max(crossings) if crossings else fallback


def fillet_stations(g, env_profile, kind, r_nom):
    """X stations and Y-Z profiles for one lofted structural fillet.

    The corner this blends is not one corner.  It moves: the flare erodes the
    envelope as it approaches the plate, so the arm's top edge crosses the face
    lower at every station, and the graded swell moves the face itself in X.  A
    prism swept from a single profile -- which is what this replaces -- therefore
    filleted the middle 25 mm and left the 5 mm flare on each side raw, with a step
    at X = +/-12.5 where it stopped dead.  Every station is solved for its own
    corner instead.

    The radius is full over the saddle's full-section width and then sheds one
    millimetre per millimetre of X.  That is the same 45-degree rule the flare
    itself obeys, and it is not decoration: X is the build direction, so a collar
    that grew faster than 1:1 would be asking the printer to bridge into mid-air.
    Where the taper finally runs out the profile is pushed BEHIND the plate's front
    face and the loft is capped inside solid material, so the fillet dies invisibly
    instead of ending in a fresh sharp edge.

    Every radius is also clamped, per station, by three things measured from the
    geometry rather than assumed:
      * how much plate face there is above the corner (a fillet cannot run off the
        top edge of the plate)
      * how much of the other surface there is beyond the corner (past the next
        hull vertex the blend would be tangent to nothing)
      * the bar's rearmost surface at Y = Y_AXIS - R_BAR: anything in front of that
        stands in the bar's vertical drop-in path, which is the constraint the old
        R <= GAP_EFF clamp was expressing.
    """
    half = W_SADDLE / 2.0
    y_lim = g["Y_AXIS"] - g["R_BAR"]
    span = max(r_nom - FILLET_R_MIN, 0.0)
    xs = [half * i / 4.0 for i in range(5)]
    xs += [half + span * (i + 1) / FILLET_STEPS for i in range(FILLET_STEPS)]

    frozen, out = None, []
    for x in xs:
        e = max(x - half, 0.0)
        # Same profile the saddle BODY is built from, anchors and all.  The body's
        # flare erodes outward only (see build_saddle); if the fillet stations kept
        # eroding uniformly they would be solving for a cradle that is not there --
        # the lower corner would appear to run out at X = 14.8 and the collar would
        # taper away to nothing in the middle of a flank that is in fact still
        # fully attached to the plate.  That mismatch is the seam you can see where
        # the collar meets the flare.
        prof = env_profile if e <= 0.0 else hull2d(
            erode_convex(env_profile, min(e, FLARE)) + plate_anchors(g))
        if e > FLARE:                            # past the flare: the closing cap
            prof = erode_convex(prof, min(e - FLARE, FLARE_TIP)) or prof
        found = None
        if len(prof) >= 3:
            found = upper_corner(prof, x) if kind == "upper" else lower_corner(prof, x)
        room = corner_room(found, y_lim) if found is not None else None
        if room is not None and kind == "upper":
            found = aim_along_face(x, found, min(r_nom - e, room[3]))
            room = corner_room(found, y_lim) or room
        if room is not None:
            p, u1, u2, r_cap = room
            r = min(r_nom - e, r_cap)
            frozen = (p, u1, u2, r_cap, x, r)
        elif frozen is not None:
            p, u1, u2, r_cap, x0, r0 = frozen
            r = min(r_nom - e, r0 - (x - x0))
        else:
            continue                             # the fillet has not started yet
        if r < FILLET_R_MIN - 1.0e-9:
            break                                # past here it is not a fillet
        # How deep the corner may be pushed into the solid is a per-station
        # question, not a constant.  It used to be ROOT_BLEND, which is the hull
        # gusset size and has nothing to do with it; when ROOT_BLEND went 1.5 -> 3.5
        # the lower fillet's corner was shoved 3.5 mm along the inward bisector,
        # which at the outer stations is straight out through the plate's front
        # face.  What came back was a flange standing 3 mm proud of the plate that
        # the round-over then chewed into a sawtooth.
        bis = _unit((u1[0] + u2[0], u1[1] + u2[1]))
        bury = burial_room(x, p, (-bis[0], -bis[1]), FILLET_BURY)
        fil = corner_fillet(p, u1, u2, r, bury=bury)
        if fil is None:
            break
        fil["cap"] = r_cap
        out.append((x, fil))

    # Land the runout ON the floor rather than wherever the last station fell.
    # The stations are spaced span/FILLET_STEPS apart, so the loop can break with
    # up to a full step of radius still standing -- 0.628 mm on the nominal variant,
    # which is a visible ledge where the collar should be dying into the surface.
    # Worse, it is quantisation, not a floor: lowering FILLET_R_MIN moved the
    # stations and made the H_DROP=+2 variant WORSE (0.407 -> 0.454 mm).  One extra
    # station, placed at exactly the X where the 1:1 taper reaches the floor, ends
    # the collar at the floor on every variant.
    if out:
        x_last, last = out[-1]
        drop = last["r"] - FILLET_R_MIN
        if drop > 1.0e-6:
            tail = corner_fillet(last["p"], last["u1"], last["u2"], FILLET_R_MIN,
                                 bury=burial_room(x_last + drop, last["p"],
                                                  (-last["b"][0], -last["b"][1]),
                                                  FILLET_BURY))
            if tail is not None:
                tail["cap"] = last["cap"]
                out.append((x_last + drop, tail))

    if not out:
        return []
    # Terminator: the last profile, shoved along the inward bisector until it is
    # wholly behind the plate's front face, so loft_solid's end cap is buried in
    # solid material.  Tapering the radius to zero instead would collapse every
    # point of the arc onto the tangent point and hand the boolean a degenerate ring.
    x_last, last = out[-1]
    x_term = x_last + 0.5
    # Shrink the last ring onto a seed point known to be inside the solid, rather
    # than translating the whole profile along the bisector and hoping.  The
    # translation was the bug: it moved every vertex by r + ROOT_BLEND + 0.5, which
    # for the LOWER fillet points +Y and +Z -- out through the plate's front face,
    # not into it.  A ring scaled to a fraction of its size about a seed that was
    # itself distance-checked against the face cannot leave the material no matter
    # which way the bisector happens to face.
    bis, p = last["b"], last["p"]
    room = burial_room(x_term, p, (-bis[0], -bis[1]), FILLET_BURY)
    seed = (p[0] - bis[0] * room, p[1] - bis[1] * room)
    term = dict(last)
    term["pts"] = [(seed[0] + (y - seed[0]) * FILLET_TERM_SCALE,
                    seed[1] + (z - seed[1]) * FILLET_TERM_SCALE)
                   for (y, z) in last["pts"]]
    for (y, z) in term["pts"]:
        assert y < plate_face_y(x_term, z), (
            f"the {kind} fillet's terminating ring reaches Y={y:.3f} Z={z:.3f} at "
            f"X={x_term:.3f}, in front of the plate face at "
            f"{plate_face_y(x_term, z):.3f} -- the loft would cap in open air and "
            f"leave a flange for the round-over to chew on")
    out.append((x_term, term))
    return out


def fillet_collar(name, g, env_profile, kind, r_nom):
    """The lofted fillet as a closed solid, mirrored about X = 0."""
    stations = fillet_stations(g, env_profile, kind, r_nom)
    if not stations:
        return None, None, None
    rings = [(-x, f["pts"]) for x, f in reversed(stations)]
    rings += [(x, f["pts"]) for x, f in stations if x > 0.0]
    obj = loft_solid(name, rings, lambda u, v, w: Vector((w, u, v)))
    # The station profiles come back too: the round-over needs them to know where
    # this collar is, so it can leave it alone.
    plan = [(x, f["pts"]) for x, f in stations]
    return obj, stations[0][1], plan


def mouth_chamfer_profile(g, side, env_profile):
    """One lip of the trough mouth relieved at 45 degrees, as a Y-Z triangle.

    This is cut geometrically rather than beveled on the mesh, and the reason is
    worth recording.  A bmesh bevel on the rim edge cannot work here: the trough
    is a 192-facet prism and the arm's sloping top crosses it wherever it
    happens to, so the last facet before the rim is a sliver -- 0.08 mm at the
    defaults.  A 0.8 mm offset across a 0.08 mm face has nowhere to go; Blender
    swallowed the sliver, produced no chamfer at all, and left a 0.02 mm pucker
    standing proud of the trough that the wall rays then read as a 0.015 mm wall.

    The cut is a wedge with its apex ON the trough surface, MOUTH_CHAM of arc
    below the rim, bounded by:
      * the ramp itself, at 45 degrees to the trough surface, opening out and up
      * the perpendicular to that ramp through the same apex, which is what
        keeps the half-plane from running away down the back of the part and
        slicing the bottom of the cradle off
      * a short leg length, so the wedge stays a local feature
    Swept along X it relieves the mouth over the full width of the saddle.  In
    the flared ends the arm is already below this line, so nothing more is taken.
    """
    sgn = 1.0 if side == "plus" else -1.0
    phi = math.radians(g["rim_" + side] - g["CHAM_DEG"])
    s, c = math.sin(phi), math.cos(phi)
    apex = (g["Y_AXIS"] + sgn * g["R_TROUGH"] * s, g["Z_AXIS"] - g["R_TROUGH"] * c)
    radial = (sgn * s, -c)                    # straight out of the trough at the apex
    tangent = (sgn * c, s)                    # along the trough, towards the rim
    inv = math.sqrt(0.5)
    ramp = (inv * (tangent[0] + radial[0]), inv * (tangent[1] + radial[1]))
    perp = (-sgn * ramp[1], sgn * ramp[0])    # across the ramp, towards the rim
    leg = max(4.0, 8.0 * MOUTH_CHAM)
    far = [(apex[0] + d[0] * leg, apex[1] + d[1] * leg) for d in (ramp, perp)]
    for p in far:
        assert not point_in_poly(p, env_profile), (
            f"the {side} mouth chamfer wedge reaches back into the cradle at "
            f"Y={p[0]:.3f} Z={p[1]:.3f}; MOUTH_CHAM is too large for this arm")
    return [apex] + far


def overhang_area(g):
    """Cross-section area that appears unsupported when printed X-normal-down.

    Layers stack along X, so the saddle's first cross-section appears all at once
    with nothing beneath it.  Whatever part of that section sits beyond the
    plate's front face (Y > T_PLATE) is a genuine mid-air island.  With FLARE the
    first section is the ERODED profile, which is what makes the flare pay for
    itself: at defaults this falls from 334 mm^2 to about 11 mm^2.
    """
    env, trough = saddle_profiles(g)
    void = clip_below(trough, g["Z_CUT"])
    # Support comes from the plate, whose face at the flared end is where the
    # swell has faired to in X -- and, now that the swell is graded, where the
    # fade has left it at each height.  That is a curve, not a plane, so
    # area_beyond_face integrates it instead of clipping to a half-plane.
    x_end = W_SADDLE / 2.0 + FLARE + FLARE_TIP

    def island(erosion):
        e = erode_convex(env, erosion) if erosion > 0.0 else env
        if len(e) < 3:
            return 0.0
        return max(area_beyond_face(e, x_end) - area_beyond_face(void, x_end), 0.0)

    reach = FLARE + FLARE_TIP
    if reach <= 0.0:
        return island(0.0), x_end
    # March inward a layer at a time and report the FIRST section that actually
    # has material.  Reporting the fully-eroded end alone gives a false zero:
    # when it is empty, nothing has printed yet and the real island appears a
    # few layers later, in mid-air.  The X it was found at comes back with it:
    # the report used to name the flare tip regardless, and the value is usually
    # from half a millimetre inboard of that.
    #
    # This measures the SADDLE BODY only.  The fillet collars reach further out in
    # X than the body does, so the genuinely first-laid section is theirs -- but at
    # FILLET_R_MIN it is 0.02 mm^2, three orders below this, and it grows at the
    # same 45 degrees the flare does, so it is supported from the layer it appears.
    steps = max(int(reach / LAYER_H), 1)
    for i in range(steps + 1):
        erosion = reach - reach * i / steps
        a = island(erosion)
        if a > 1.0e-9:
            return a, W_SADDLE / 2.0 + erosion
    return 0.0, x_end


def build_saddle(name=PART_NAME, d_bar=None, h_drop=None, y_bar=_UNSET):
    """Build the saddle and return (object, derived-dimension dict)."""
    g = derive(d_bar, h_drop, y_bar)
    purge(name, "_tmp_env", "_tmp_trough", "_tmp_fil_upper", "_tmp_fil_lower",
          "_tmp_lens", "_tmp_notch", "_tmp_ribs")

    # --- plate: rounded rectangle in X-Z at Y = 0, extruded to Y = T_PLATE ---
    plate_profile = rounded_rect(W_PLATE, H_PLATE, R_CORNER, SEG_CORNER)
    obj = prism(name, plate_profile,
                lambda u, v: Vector((u, 0.0, v)),
                (0.0, T_PLATE + max(BULGE, 0.0), 0.0))
    if BULGE > 0.0:
        # Carve the front face into a graded swell.  The plate is extruded proud
        # by BULGE and then trimmed back by the lens, so the outline and the flat
        # Y=0 cap come through the intersection unchanged.  The lens is LOFTED,
        # not extruded: its section shrinks as it climbs, which is what turns a
        # cylindrical swell into a collar that dies out at the top edge.
        lens = loft_solid("_tmp_lens", lens_rings(),
                          lambda u, v, w: Vector((u, v, w)))
        boolean(obj, lens, 'INTERSECT')
        purge("_tmp_lens")

    # --- witness notch: a V through the plate's top edge on the centreline ----
    if NOTCH_D > 0.0 and NOTCH_W > 0.0:
        notch = prism("_tmp_notch", notch_profile(),
                      lambda u, v: Vector((u, -1.0, v)),
                      (0.0, T_PLATE + max(BULGE, 0.0) + 2.0, 0.0))
        boolean(obj, notch, 'DIFFERENCE')
        purge("_tmp_notch")

    # --- cradle envelope: convex profile in Y-Z, swept along X --------------
    env_profile, trough_profile = saddle_profiles(g)
    assert min(p[0] for p in env_profile) > 0.0, "cradle envelope breaks the tape plane"
    z_join = plate_face_join(env_profile, g["Z_CUT"])
    g["ROOT_VOID_SCAN"] = _assert_root_is_solid(env_profile, g, z_join)

    # The wrap the part actually delivers, and what the mouth chamfer costs it.
    g.update(mouth_rim(g, env_profile))
    g["WRAP_MEAS_DEG"] = g["rim_plus"] + g["rim_minus"]
    g["WRAP_FULL_DEG"] = g["WRAP_MEAS_DEG"] - 2.0 * g["CHAM_DEG"]
    # The wall sweep stops a further half a degree inside the chamfer's start.
    # A ray fired at exactly the start grazes along the ramp's first micron and
    # comes back 0.02 mm light -- an artefact of where the ray is aimed, not a
    # thin wall.  The margin is arc, not material: 0.087 mm of it.
    g["PHI_WALL_PLUS"] = g["rim_plus"] - g["CHAM_DEG"] - 0.5
    g["PHI_WALL_MINUS"] = g["rim_minus"] - g["CHAM_DEG"] - 0.5
    assert g["WRAP_FULL_DEG"] >= 160.0, (
        f"MOUTH_CHAM={MOUTH_CHAM} leaves only {g['WRAP_FULL_DEG']:.1f} deg of "
        f"cradle at full trough radius; the brief asks for at least 160")
    assert g["PHI_WALL_PLUS"] <= g["wall_plus"] and g["PHI_WALL_MINUS"] <= g["wall_minus"], (
        "the chamfer does not reach back as far as the wall thins out, so the "
        "wall check would sweep into a taper and report it as a failure")

    # Flared to a branch collar: full section over the central W_SADDLE, then a
    # 45-degree taper out to X = +/-(W_SADDLE/2 + FLARE).
    half = W_SADDLE / 2.0
    rings = [(-half, env_profile), (half, env_profile)]
    if FLARE > 0.0:
        # Erode OUTWARD only: put the plate-side anchors back at full depth so the
        # collar stays attached to the plate all the way to the flare tip.
        #
        # A uniform erosion shrinks the profile in every direction, including
        # backwards, so the tip pulled AWAY from the plate as well as getting
        # smaller: measured, the saddle's rear boundary stood 1.7 mm clear of the
        # plate face at X=15.0, 7.2 mm at X=16.0 and 15.4 mm at the tip, leaving a
        # wedge of air behind the outer 3 mm of the collar.  That is the dark
        # undercut you can see beneath the arm, and it is also the 270-degree
        # re-entrant corner where the tip's end cap met the plate.
        #
        # Holding the anchors costs nothing in printability.  The 45-degree rule
        # only governs surfaces that GROW along the build direction; the plate-side
        # edge now does not grow at all, it is a vertical wall at 0 degrees, which
        # is the easiest thing an FDM printer does.  The outboard surfaces still
        # erode at 45 degrees exactly as before.
        tip = hull2d(erode_convex(env_profile, FLARE) + plate_anchors(g))
        assert len(tip) >= 3, (
            f"FLARE={FLARE} exceeds the envelope's inradius; the flared end "
            f"profile collapses to nothing")
        rings += [(-half - FLARE, tip), (half + FLARE, tip)]
        if FLARE_TIP > 0.0:
            cap = erode_convex(tip, FLARE_TIP)
            assert len(cap) >= 3, (
                f"FLARE_TIP={FLARE_TIP} closes the end profile completely; the hull "
                f"would have nothing to terminate on")
            rings += [(-half - FLARE - FLARE_TIP, cap), (half + FLARE + FLARE_TIP, cap)]
    env = hull_solid("_tmp_env", rings)

    # --- trough cutter: cylinder on the bar axis, overrunning both X ends ----
    over = max(10.0, T_WALL * 2.0) + FLARE + FLARE_TIP   # clear the flared ends too
    cutter = prism("_tmp_trough", trough_profile,
                   lambda u, v: Vector((-W_SADDLE / 2.0 - over, u, v)),
                   (W_SADDLE + 2.0 * over, 0.0, 0.0))

    # --- structural fillets: added BEFORE the trough cut, so the cutter trims any
    #     of them that strays into the bar's space and the blend ends tangent to
    #     the trough surface instead of in a sharp corner.
    #
    #     Two of them, because there are two re-entrant corners where the cradle
    #     meets the plate and only one of them was ever blended:
    #       upper  the arm's top face into the plate's FRONT face, 100.6 degrees of
    #              void on the nominal (98.1 / 100.6 / 103.1 for H_DROP 0/2/4, FACTS
    #              7b).  Tension fibre of the arm root, and the corner the peel
    #              moment works on.  Gets the big radius.
    #       lower  the cradle's underside into the plate's BOTTOM face, 131.6 degrees
    #              of void and so 228.4 of material (FACTS 7b).  Compression side
    #              under the design load, but still re-entrant, and it is where a
    #              peel crack would start.
    boolean(obj, env, 'UNION')
    fillets = {}
    for kind, r_nom in (("upper", R_ROOT), ("lower", R_ROOT_LOW)):
        if r_nom <= 0.0:
            continue
        fil, at_centre, plan = fillet_collar(f"_tmp_fil_{kind}", g, env_profile, kind, r_nom)
        g["FILLET_PLAN_" + kind] = plan
        if fil is None:
            raise RuntimeError(
                f"the {kind} fillet found no corner to blend at any X station -- the "
                f"cradle no longer meets the plate the way this expects")
        boolean(obj, fil, 'UNION')
        purge(f"_tmp_fil_{kind}")
        # Weld between the stages, not just at the end.  A tangent blend meets the
        # surface it lands on at zero angle, so each of these unions leaves a seam
        # of micron-scale faces; carried into the next boolean they compound, and
        # the result is that the build is not a smooth function of the radius at
        # all.  Before this, R_ROOT = 9.0, 11.0, 12.0, 14.25 and 14.75 came back
        # non-manifold while 8, 10, 13, 14 and 14.5 were clean -- a landmine field
        # rather than a parameter.  The welds are what make the radius tunable.
        clean_mesh(obj)
        fillets[kind] = at_centre
        g["FILLET_" + kind] = at_centre
    boolean(obj, cutter, 'DIFFERENCE')
    purge("_tmp_env", "_tmp_trough")
    g["R_ROOT_USED"] = fillets["upper"]["r"] if "upper" in fillets else 0.0

    # Weld first, THEN round.  With use_clamp_overlap on, a single 0.005 mm
    # sliver edge left over from the booleans clamps the round-over to nothing
    # across the entire part -- it silently produces an identical mesh.
    clean_mesh(obj, merge_dist=WELD_PRE_ROUND)
    g["ROUNDED_EDGES"] = round_edges(obj, g)
    clean_mesh(obj)

    # Mouth chamfer LAST, after the round-over.  Cut earlier, the round-over
    # would find the ramp's own top edge, see a 45-degree crease and soften the
    # very lead-in this just cut -- at ROUND_R 1.0 against a 0.8 mm ramp it would
    # have consumed it outright, and at the current 0.5 it would still take most
    # of it.  A lead-in wants to stay a crisp ramp, so the ordering stands
    # whatever the radius is.
    if MOUTH_CHAM > 0.0:
        over = max(10.0, T_WALL * 2.0) + FLARE + FLARE_TIP
        for side in ("plus", "minus"):
            wedge = prism("_tmp_cham", mouth_chamfer_profile(g, side, env_profile),
                          lambda u, v: Vector((-W_SADDLE / 2.0 - over, u, v)),
                          (W_SADDLE + 2.0 * over, 0.0, 0.0))
            boolean(obj, wedge, 'DIFFERENCE')
            purge("_tmp_cham")
        clean_mesh(obj)

    # --- layer-aligned relief on the trough, LAST of all ---------------------
    # After the round-over, and for the same reason the mouth chamfer is: the
    # round-over skips edges that sit ON the trough surface, but a groove floor is
    # RIB_DEPTH outside it and would not be skipped.  A round-over turned loose on
    # a 0.2 mm groove does not soften it, it eats it -- at ROUND_R 1.0 five times
    # over, at the current 0.5 still two and a half times over, so the ordering is
    # not something the radius change relaxes.
    bands = rib_bands()
    g["RIB_BANDS"] = bands
    if bands:
        # Stop the grooves short of where the mouth chamfer begins.  Running them
        # to the rim would have a 192-facet annulus meeting a 45-degree ramp at a
        # glancing angle, which is exactly the sliver factory the chamfer was cut
        # geometrically to avoid in the first place.
        phi_stop = min(g["PHI_WALL_PLUS"], g["PHI_WALL_MINUS"]) - 0.5
        g["Z_RIB_TOP"] = g["Z_AXIS"] - g["R_TROUGH"] * math.cos(math.radians(phi_stop))
        # Same facet count and same phase as the trough cutter, so the radial gap
        # between the two is exactly RIB_DEPTH at every angle rather than wandering
        # between the inscribed and circumscribed radii.
        relief = clip_below(
            circumscribed_circle(g["Y_AXIS"], g["Z_AXIS"], g["R_TROUGH"] + RIB_DEPTH,
                                 SEG_CIRCLE),
            g["Z_RIB_TOP"])
        relief_cutter = banded_prism("_tmp_ribs", relief, bands)
        boolean(obj, relief_cutter, 'DIFFERENCE')
        purge("_tmp_ribs")
        clean_mesh(obj)

    # LAST of all, after every boolean, the round-over and the relief: freeze the
    # triangulation into the mesh and delete the null geometry that exposes.
    # This is the step that makes the EXPORTED FILE sliceable -- the mesh reads
    # manifold in Blender either way, which is the entire problem.  It removes no
    # material and moves no vertex; see triangulate_and_purge.
    g["PURGE"] = triangulate_and_purge(obj)

    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    grey_material(obj)
    return obj, g


def _assert_root_is_solid(env_profile, g, z_join):
    """No pinched void between the plate's front face and the cradle at the root.

    Only the band from Z = 0 up to where the envelope leaves the plate face can
    trap air: below it, plate and cradle run alongside each other and a slot can
    form between them.  Above z_join the envelope has departed the plate and the
    space between them is simply open, which is what a long arm looks like.

    KNOWN GAP, recorded rather than hidden: on the current geometry this asserts
    nothing.  All 61 stations take the `y_back - face > T_WALL` early-out, on all
    three H_DROP variants -- the arm stands well clear of the plate over the whole
    band, so there is no near-touching pair to pinch anything.  That is the right
    answer for this shape, but it means the check is currently vacuous and would
    stay green if a future change did introduce a slot somewhere it does not
    sample.  The branch counts go into `g` and into the report so that "it passed"
    can be told apart from "it never looked".
    """
    y_c, z_c, r = g["Y_AXIS"], g["Z_AXIS"], g["R_OUT"]
    steps = 60
    seen = dict(stations=steps + 1, off_circle=0, inside=0, open_span=0, tested=0)
    for i in range(steps + 1):
        z = max(z_join, 0.0) * i / steps    # only Z >= 0 can be a trapped void
        dy2 = r * r - (z - z_c) ** 2
        if dy2 <= 0.0:
            seen["off_circle"] += 1
            continue
        y_back = y_c - math.sqrt(dy2)       # cradle's rearmost point at this height
        face = plate_face_y(0.0, z)
        if y_back <= face:
            seen["inside"] += 1
            continue                        # cradle is inside the plate here: solid
        if y_back - face > T_WALL:
            seen["open_span"] += 1
            continue                        # a deliberate standoff spanned by the
                                            # arm, not a slot pinched between two
                                            # nearly-touching surfaces
        seen["tested"] += 1
        for j in range(1, 20):
            y = face + (y_back - face) * j / 20.0
            assert point_in_poly((y, z), env_profile), (
                f"root void at Y={y:.3f} Z={z:.3f}: increase ROOT_BLEND")
    return seen


# ===========================================================================
# fit gauge
# ===========================================================================

def build_gauge(name=GAUGE_NAME):
    purge(name, "_tmp_labels")
    dias = sorted(GAUGE_DIAS)
    r_max = max(dias) / 2.0
    width = sum(dias) + (len(dias) + 1) * GAUGE_WALL
    height = r_max + GAUGE_LABEL + 2.0 * GAUGE_MARG
    x0 = -width / 2.0

    # notch centres, left to right, walls between and at both ends
    centres, cursor = [], x0 + GAUGE_WALL
    for d in dias:
        centres.append((cursor + d / 2.0, d / 2.0))
        cursor += d + GAUGE_WALL

    # outline CCW in (X, Y): bottom, right edge, top edge (dipping into each
    # notch, right to left), left edge.
    pts = [(x0, 0.0), (-x0, 0.0), (-x0, height)]
    for cx, r in reversed(centres):
        pts.append((cx + r, height))
        seg = max(24, int(SEG_CIRCLE / 4))
        for i in range(1, seg):
            a = math.pi * i / seg
            pts.append((cx + r * math.cos(a), height - r * math.sin(a)))
        pts.append((cx - r, height))
    pts.append((x0, height))

    obj = prism(name, pts,
                lambda u, v: Vector((u, v + GAUGE_Y_OFF, 0.0)),
                (0.0, 0.0, GAUGE_T))

    # Embossed labels, half-buried in the top face so the union is volumetric.
    # Blender's own text `extrude` produces an OPEN shell (front and back caps
    # are not stitched to the side walls), which the MANIFOLD boolean solver
    # rejects silently.  Fill the glyphs flat and give them depth with SOLIDIFY
    # instead -- that yields a genuinely closed solid.
    labels = []
    for (cx, r), d in zip(centres, dias):
        cur = bpy.data.curves.new(f"_lbl_{d}", type='FONT')
        cur.body = f"{d:.1f}"
        cur.size = GAUGE_LABEL
        cur.extrude = 0.0
        cur.align_x, cur.align_y = 'CENTER', 'CENTER'
        cur.resolution_u = 6
        txt = bpy.data.objects.new(f"_lbl_{d}", cur)
        txt.location = (cx, GAUGE_MARG + GAUGE_LABEL / 2.0 + GAUGE_Y_OFF, GAUGE_T)
        sol = txt.modifiers.new("solidify", type='SOLIDIFY')
        sol.thickness = GAUGE_EMB
        sol.offset = 0.0                     # straddle the top face
        bpy.context.scene.collection.objects.link(txt)
        labels.append(txt)

    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for txt in labels:
        me = bpy.data.meshes.new_from_object(txt.evaluated_get(dg), depsgraph=dg)
        assert len(me.vertices) > 0, f"label {txt.name} produced no geometry"
        me.transform(txt.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        curve = txt.data
        bpy.data.objects.remove(txt, do_unlink=True)
        bpy.data.curves.remove(curve)     # else the font curve orphans every run
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    assert open_edges == 0, f"label solid is not closed ({open_edges} non-manifold edges)"
    lbl_mesh = bpy.data.meshes.new("_tmp_labels")
    bm.to_mesh(lbl_mesh)
    bm.free()
    lbl_obj = bpy.data.objects.new("_tmp_labels", lbl_mesh)
    bpy.context.scene.collection.objects.link(lbl_obj)

    boolean(obj, lbl_obj, 'UNION')
    purge("_tmp_labels")
    clean_mesh(obj)
    grey_material(obj)
    return obj


# ===========================================================================
# verification -- measured, not asserted
# ===========================================================================

def _shell_count(bm):
    """Topological shell count: faces joined by ANY shared bmesh edge.

    Kept, but no longer what anything is gated on.  It reported 1 on the mesh
    that shipped while the exported file positionally contained 3 -- the body
    and two null flaps -- because it walks across bmesh edges, and the flaps hang
    off the body through an edge Blender considers two separate edges.  Same bug
    class as the non-manifold count: a true answer to a question about the wrong
    object.  positional_mesh() is the one the acceptance checks use.
    """
    seen, shells = set(), 0
    for f in bm.faces:
        if f.index in seen:
            continue
        shells += 1
        stack = [f]
        seen.add(f.index)
        while stack:
            cur = stack.pop()
            for e in cur.edges:
                for nb in e.link_faces:
                    if nb.index not in seen:
                        seen.add(nb.index)
                        stack.append(nb)
    return shells


def positional_mesh(bm, weld=None):
    """The mesh as a SLICER sees it: vertices identified by position, not by
    identity.  Same reconstruction stl_manifold() performs on the written file,
    run here on the bmesh so the acceptance checks and the export gate are
    asking one question in two places rather than two questions.
    """
    weld = STL_WELD if weld is None else weld
    bm.verts.index_update()
    ids, nverts = _weld_ids([tuple(v.co) for v in bm.verts], weld)
    faces, degenerate = [], 0
    for f in bm.faces:
        loop, prev = [], None
        for v in f.verts:                      # drop points welded onto their
            i = ids[v.index]                   # own neighbour inside a face
            if i != prev:
                loop.append(i)
            prev = i
        if len(loop) > 1 and loop[0] == loop[-1]:
            loop.pop()
        if len(loop) < 3 or len(set(loop)) != len(loop):
            degenerate += 1
            continue
        faces.append(loop)
    edges = collections.Counter()
    for loop in faces:
        for a, b in zip(loop, loop[1:] + loop[:1]):
            edges[(a, b) if a < b else (b, a)] += 1

    parent = list(range(len(faces)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    owners = collections.defaultdict(list)
    for i, loop in enumerate(faces):
        for a, b in zip(loop, loop[1:] + loop[:1]):
            owners[(a, b) if a < b else (b, a)].append(i)
    for e, fs in owners.items():
        if len(fs) == 2:
            ra, rb = find(fs[0]), find(fs[1])
            if ra != rb:
                parent[rb] = ra
    shells = len({find(i) for i in range(len(faces))})
    return dict(
        verts=nverts, edges=len(edges), faces=len(faces), degenerate=degenerate,
        non_manifold_edges=sum(1 for k in edges.values() if k != 2),
        boundary_edges=sum(1 for k in edges.values() if k < 2),
        over_edges=sum(1 for k in edges.values() if k > 2),
        shells=shells, euler=nverts - len(edges) + len(faces),
    )


def _fit_circle(pts):
    """Least-squares circle through (u, v) samples: y^2+z^2 + A u + B v + C = 0."""
    n = len(pts)
    su = sv = suu = svv = suv = sr = sru = srv = 0.0
    for u, v in pts:
        r2 = u * u + v * v
        su += u; sv += v; suu += u * u; svv += v * v; suv += u * v
        sr += r2; sru += r2 * u; srv += r2 * v
    a = [[suu, suv, su, -sru], [suv, svv, sv, -srv], [su, sv, float(n), -sr]]
    for col in range(3):                       # Gaussian elimination, 3x3
        piv = max(range(col, 3), key=lambda r: abs(a[r][col]))
        a[col], a[piv] = a[piv], a[col]
        for row in range(3):
            if row == col:
                continue
            f = a[row][col] / a[col][col]
            for k in range(col, 4):
                a[row][k] -= f * a[col][k]
    A, B, C = (a[i][3] / a[i][i] for i in range(3))
    cu, cv = -A / 2.0, -B / 2.0
    return cu, cv, math.sqrt(max(cu * cu + cv * cv - C, 0.0))


LBF_TO_N = 4.448222


def bending_check(obj, g, steps=40):
    """Peak bending stress along the arm, from the real cross-sections.

    The arm is a prism W_SADDLE wide in X, so at each Y the section is that width
    by whatever spans of material exist in Z.  March raycasts up each column to
    find those spans, take the true second moment about the section centroid, and
    compare M(y)/S(y) against yield.  Reports the WORST section, which is the
    only one that matters and is not necessarily at the root.
    """
    b = W_SADDLE
    y_load = g["Y_AXIS"]
    force = LOAD_LBF * LBF_TO_N
    # Start just clear of the plate's front face -- which BULGE moves forward.
    # Sampling behind it measures plate, not arm, and the plate is not what is
    # working in bending here.  Z=0 is where the graded swell stands proudest,
    # so this clears the face at EVERY height the arm spans, not just at its own.
    y_root = plate_face_y(0.0, 0.0) + 0.5
    worst = None
    for i in range(steps + 1):
        y = y_root + (y_load - y_root) * i / steps
        spans, z = [], g["Z_ENV_BOT"] - 20.0
        eps = 1.0e-3            # big enough not to re-hit the face just crossed
        for _ in range(24):
            ok, p, _, _ = obj.ray_cast(Vector((0.0, y, z)), Vector((0, 0, 1)))
            if not ok:
                break
            ok2, p2, _, _ = obj.ray_cast(Vector((0.0, y, p.z + eps)), Vector((0, 0, 1)))
            if not ok2:
                break
            spans.append((p.z, p2.z))
            z = p2.z + eps
        if not spans:
            continue
        area = b * sum(hi - lo for lo, hi in spans)
        if area <= 0.0:
            continue
        zc = b * sum((hi * hi - lo * lo) / 2.0 for lo, hi in spans) / area
        inertia = b * sum((hi ** 3 - lo ** 3) / 3.0 for lo, hi in spans) - area * zc * zc
        c = max(max(abs(lo - zc), abs(hi - zc)) for lo, hi in spans)
        if inertia <= 0.0 or c <= 0.0:
            continue
        sigma = force * (y_load - y) / (inertia / c)
        sf = SIGMA_ALLOW / sigma if sigma > 0.0 else float("inf")
        if worst is None or sf < worst["sf"]:
            worst = dict(sf=sf, y=y, sigma=sigma, section_h=max(h for _, h in spans)
                         - min(l for l, _ in spans), area=area, S=inertia / c)
    worst = worst or dict(sf=float("nan"), y=float("nan"), sigma=float("nan"),
                          section_h=float("nan"), area=float("nan"), S=float("nan"))
    worst["load_lbf"] = LOAD_LBF
    worst["sf_required"] = SF_MIN
    return worst


# --- where the verification rays are fired from ----------------------------
NOTCH_PROBE_X = 0.2   # mm either side of the notch apex.  A ray straight down
                      # the apex lands on an edge, which the BVH can miss.
NOTCH_PROBE_Y = 1.0   # inside the plate's thickness, so the top face is the flat
                      # part of it: the tape-side top edge is never rounded and
                      # the front-side round-over does not reach this far back.
FACE_PROBE_X  = W_SADDLE / 2.0 + FLARE + FLARE_TIP + 2.0   # clear of the saddle, so
                      # a ray through the plate meets the front face and nothing
                      # else.  DERIVED, not chosen: it was hard-coded at 20.0 with
                      # a comment reading "clear of the saddle (W_SADDLE/2 + FLARE
                      # = 17.5)", which stopped being true the moment FLARE_TIP
                      # pushed the body out to 20.5.  The ray then struck the
                      # saddle instead of the plate and all three variants failed
                      # the swell checks -- a probe in the wrong place reported as
                      # a geometry defect, which is the second time in this file a
                      # measurement has moved when the part did not.
FACE_PROBE_Z  = (3.0, H_PLATE - 3.0)   # low and high, either side of the fade;
                      # 3 mm in from the top keeps clear of the round-over


def verify(obj, g, tol=1.0e-6):
    """Measure the acceptance checks.  Returns a plain dict of numbers."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    # Folded faces: edges whose two faces have doubled back on each other into a
    # zero-thickness fin.  Manifold, watertight, one shell -- and still wrong, which
    # is why none of the existing checks sees them.  They are made by the round-over
    # (measured: the lower collar's runout carries 0 of them before it and 78 after)
    # and they are what a chewed-looking surface actually is.  Reported rather than
    # gated, because the plate's edges and the witness notch have carried them since
    # long before the fillets existed; gating at zero today would fail a part that
    # has always printed.  At ROUND_R 1.0, ROUND_MIN_EDGE_FRAC took the count from
    # 302 to 117 on the nominal build by dropping the chains a 1.0 mm bevel could
    # never fit.  The count moves with ROUND_R and NOT in one direction: taking the
    # radius to 0.5 reads 107 / 133 / 104 on H_DROP 2 / 0 / 4 against 125 / 121 / 110
    # at 1.0 -- better on two variants, worse on H_DROP=0.  Read the run, not a
    # remembered number.  FACTS 7g.
    folds = [e for e in bm.edges
             if len(e.link_faces) == 2 and math.degrees(e.calc_face_angle(0.0)) > 170.0]
    collar_folds = sum(1 for e in folds
                       if all(4.0 < v.co.y < 9.0 and -2.0 < v.co.z < 2.5
                              and 8.0 < abs(v.co.x) < 17.0 for v in e.verts))
    # Two answers, deliberately kept side by side.  `topo_*` is what Blender
    # thinks -- faces per bmesh edge -- and it is the answer that was wrong all
    # session.  `pos` identifies vertices by POSITION, which is the only identity
    # an STL has, and it is what the acceptance checks below are gated on.
    topo_non_manifold = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    topo_boundary = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    topo_shells = _shell_count(bm)
    pos = positional_mesh(bm)
    loose_verts = sum(1 for v in bm.verts if not v.link_faces)
    loose_edges = sum(1 for e in bm.edges if not e.link_faces)
    edge_lengths = [e.calc_length() for e in bm.edges]
    min_edge = min(edge_lengths)

    # tape face: every face lying in Y = 0
    tape_faces = [f for f in bm.faces if all(abs(v.co.y) < tol for v in f.verts)]
    tape_verts = [v.co for f in tape_faces for v in f.verts]
    tape_area = sum(f.calc_area() for f in tape_faces)
    tape_w = max(v.x for v in tape_verts) - min(v.x for v in tape_verts)
    tape_h = max(v.z for v in tape_verts) - min(v.z for v in tape_verts)
    tape_z0 = min(v.z for v in tape_verts)
    tape_flat = max(abs(v.co.y) for f in tape_faces for v in f.verts)

    co = [v.co for v in bm.verts]
    bbox = dict(
        x=(min(c.x for c in co), max(c.x for c in co)),
        y=(min(c.y for c in co), max(c.y for c in co)),
        z=(min(c.z for c in co), max(c.z for c in co)),
    )
    plate_top = max(c.z for c in co)

    counts = dict(verts=len(bm.verts), edges=len(bm.edges), faces=len(bm.faces),
                  tris=sum(1 for f in bm.faces if len(f.verts) == 3))
    bm.free()

    # ---- ray-based measurements (independent of how the mesh was built) ----
    far = 500.0

    # trough rest point: straight down the bar axis onto the cradle
    hit, loc, _, _ = obj.ray_cast(Vector((0.0, g["Y_AXIS"], far)), Vector((0, 0, -1)))
    z_rest = loc.z if hit else float("nan")

    # trough profile: drop rays across the trough and fit a circle to the hits
    samples = []
    lo, hi = g["Y_TROUGH_BACK"], g["Y_AXIS"] + g["R_TROUGH"]
    for i in range(1, 80):
        y = lo + (hi - lo) * i / 80.0
        ok, p, _, _ = obj.ray_cast(Vector((0.0, y, far)), Vector((0, 0, -1)))
        if ok and p.z < g["Z_CUT"] - 1.0e-4:
            samples.append((p.y, p.z))
    fit_y, fit_z, fit_r = _fit_circle(samples) if len(samples) > 8 else (float("nan"),) * 3

    # wall thickness on the load path: from the trough surface, radially outward.
    # The sweep stops at HALF_FULL, not at the geometric half-wrap: past that the
    # mouth chamfer has deliberately taken the wall away, and a ray fired into
    # the chamfer would report ~0.9 mm and read as a structural failure.  What is
    # skipped is not dropped -- the chamfer itself is measured below and the wrap
    # that survives it is gated in derive() and reported.
    #
    # Two stations, not one.  Every ray in this file used to be fired in the X = 0
    # plane, which the relief deliberately keeps as a LAND -- so a single sweep
    # would measure 4.2 mm of wall and never once look at the groove floor, which
    # is the thinnest section on the part and the only one worth gating.  The
    # second sweep stands in a groove and starts its rays from the groove floor.
    def sweep_wall(x, r_start, lo_deg, hi_deg, n=181):
        out = []
        lo_phi, hi_phi = -math.radians(lo_deg), math.radians(hi_deg)
        for i in range(n):
            phi = lo_phi + (hi_phi - lo_phi) * i / (n - 1)
            dirn = Vector((0.0, math.sin(phi), -math.cos(phi)))
            start = Vector((x, g["Y_AXIS"], g["Z_AXIS"])) + dirn * (r_start + 0.01)
            ok, p, _, _ = obj.ray_cast(start, dirn)
            if ok:
                out.append(((p - start).length + 0.01, math.degrees(phi)))
        return out

    walls = sweep_wall(0.0, g["R_TROUGH"], g["PHI_WALL_MINUS"], g["PHI_WALL_PLUS"])
    min_land, land_phi = min(walls) if walls else (float("nan"), float("nan"))
    bands = g.get("RIB_BANDS") or []
    groove_walls, min_groove, groove_phi, groove_x = [], float("nan"), float("nan"), float("nan")
    if bands:
        groove_x = 0.5 * (bands[len(bands) // 2][0] + bands[len(bands) // 2][1])
        # Only sweep the arc the relief actually reaches; past Z_RIB_TOP the ray
        # would start inside solid material and come back RIB_DEPTH light for a
        # reason that has nothing to do with the wall.
        phi_rib = math.degrees(math.acos(max(-1.0, min(1.0,
            (g["Z_AXIS"] - g["Z_RIB_TOP"]) / g["R_TROUGH"])))) - 0.5
        groove_walls = sweep_wall(groove_x, g["R_TROUGH"] + RIB_DEPTH,
                                  min(phi_rib, g["PHI_WALL_MINUS"]),
                                  min(phi_rib, g["PHI_WALL_PLUS"]))
        if groove_walls:
            min_groove, groove_phi = min(groove_walls)
    min_wall, min_wall_phi = (min_land, land_phi)
    if groove_walls and min_groove < min_land:
        min_wall, min_wall_phi = min_groove, groove_phi

    # drop-in clearance: the bar must fall straight into the trough.  For each
    # column across the bar's width, the first material hit from above has to
    # sit at or below the bar's own lowest surface in that column.  This is what
    # proves the root fillet did not turn the cradle into a trap.
    drops = []
    for i in range(1, 60):
        y = g["Y_AXIS"] - g["R_BAR"] + 2.0 * g["R_BAR"] * i / 60.0
        dy = y - g["Y_AXIS"]
        z_bar_lo = g["Z_AXIS"] - math.sqrt(max(g["R_BAR"] ** 2 - dy * dy, 0.0))
        ok, p, _, _ = obj.ray_cast(Vector((0.0, y, far)), Vector((0, 0, -1)))
        drops.append((z_bar_lo - p.z, y) if ok else (float("inf"), y))
    drop_min, drop_y = min(drops)

    # mouth chamfer: fan rays out from the trough axis and find the two angles at
    # which the cradle gives up -- first the true trough surface, then the
    # chamfer ramp that now stands in front of it.  The arc between them IS the
    # chamfer, measured in millimetres off the finished mesh rather than assumed
    # from the bevel call, which is exactly the check the round-over needed and
    # did not have when it silently beveled at zero offset.
    axis = Vector((0.0, g["Y_AXIS"], g["Z_AXIS"]))
    mouth = {}
    # Walk the ray out from the trough axis and FOLLOW THE MOUTH RAMP until the
    # surface under the ray ends -- do not simply take the last hit inside some
    # cone.  A distance cone was the first rule here and it only worked while
    # nothing else lived in the sector past the rim.  Once R_ROOT grew, the root
    # fillet did: at R_ROOT = 14 its material sits 13.5 to 15.1 mm from the trough
    # axis at 94-95 degrees, inside the old R_OUT + 1 = 15.125 mm cone, so the
    # sweep walked straight off the cradle onto the fillet and reported the mouth
    # as 1.5 degrees wider than the envelope says it can be.  Every functional
    # number -- wall, wrap, chamfer, drop-in -- was bit-identical; only the
    # measurement moved, which is the worst kind of failure this file has.
    #
    # The ramp is a surface, so along it the hit distance changes smoothly: about
    # 0.01 mm per 0.05-degree step.  Leaving it is a cliff -- 2.7 mm at R_ROOT=14,
    # 7.8 mm at R_ROOT=8.  Break on the cliff and the sweep cannot wander onto a
    # neighbouring feature no matter what is built there.
    step_out = max(MOUTH_CHAM, 0.2)
    for sgn, side in ((1.0, "plus"), (-1.0, "minus")):
        phi_true = phi_any = 0.0
        prev = None
        phi = 0.0
        while phi <= 179.0:
            a = math.radians(phi)
            ok, p, _, _ = obj.ray_cast(axis, Vector((0.0, sgn * math.sin(a), -math.cos(a))))
            d = (p - axis).length if ok else float("inf")
            if prev is not None and d - prev > step_out:
                break                    # the ray has left the mouth ramp
            if d < g["R_TROUGH"] + 0.02:
                phi_true = phi
            if d < g["R_OUT"] + 1.0:     # the near wall, not the plate behind it
                phi_any = phi
            prev = d
            phi += 0.05
        mouth["true_" + side] = phi_true
        mouth["end_" + side] = phi_any
        # What the chamfer took is the arc between where the trough surface WOULD
        # have run to and where it now stops.  NOT (end - true): the ramp cuts
        # the rim corner off, so the outermost material sits at a smaller angle
        # from the axis than the sharp rim did, and end-true reads about 15% short.
        mouth["cham_" + side] = math.radians(g["rim_" + side] - phi_true) * g["R_TROUGH"]

    # witness notch: sighted straight down the plate's top face.
    notch = []
    for x in (-NOTCH_PROBE_X, NOTCH_PROBE_X, W_PLATE / 4.0):
        ok, p, _, _ = obj.ray_cast(Vector((x, NOTCH_PROBE_Y, far)), Vector((0, 0, -1)))
        notch.append(p.z if ok else float("nan"))

    # graded swell: the plate's own thickness low down and near the top.  Two
    # numbers are what separate a graded collar from a cylinder -- one alone
    # cannot tell them apart.
    face_probe = []
    for z in FACE_PROBE_Z:
        ok, p, _, _ = obj.ray_cast(Vector((FACE_PROBE_X, 0.5, z)), Vector((0, 1, 0)))
        face_probe.append(p.y if ok else float("nan"))

    # structural fillets: stand at each arc's centre and fan rays across the arc.
    # A tangent fillet puts its centre in open air exactly r from both surfaces, so
    # every ray in that fan has to come back at r -- and a fillet that silently
    # failed to cut, or came out at the wrong radius, cannot survive the fit.  This
    # is the same trick the trough and the fit-gauge notches are measured with, and
    # it is here because this file has twice shipped a feature that quietly did
    # nothing while a parameter said otherwise.
    fillets = {}
    for kind in ("upper", "lower"):
        fd = g.get("FILLET_" + kind)
        if not fd:
            continue
        centre = Vector((0.0, fd["c"][0], fd["c"][1]))
        hits, radii = [], []
        n, skip = 60, 2.0 / FILLET_SEG
        for i in range(n + 1):
            # Skip the two end facets at each end of the arc.  A tangent blend by
            # definition arrives parallel to the surface it lands on, so its last
            # facet stands microns proud of that surface -- 0.0076 mm at R = 8 --
            # which is under the weld distance.  Those facets are gone from the
            # finished mesh and a ray aimed into one comes back off the plate face
            # instead, reading 0.10 mm long.  Measured, that looked like a fillet
            # 0.10 mm out of round; it is nothing of the sort, and aiming the rays
            # where the feature actually has thickness says so.
            a = fd["a1"] + fd["sweep"] * (skip + (1.0 - 2.0 * skip) * i / n)
            dirn = Vector((0.0, math.cos(a), math.sin(a)))
            ok, p, _, _ = obj.ray_cast(centre, dirn)
            if ok:
                hits.append((p.y, p.z))
                radii.append((p - centre).length)
        fy, fz, fr = _fit_circle(hits) if len(hits) > 8 else (float("nan"),) * 3
        fillets[kind] = dict(
            r_built=fd["r"], r_requested=R_ROOT if kind == "upper" else R_ROOT_LOW,
            fit_r=fr, fit_c_err=math.hypot(fy - fd["c"][0], fz - fd["c"][1]),
            c_y=fd["c"][0], c_z=fd["c"][1], corner_y=fd["root"][0],
            r_min=min(radii) if radii else float("nan"),
            r_max=max(radii) if radii else float("nan"),
            rays=len(hits), theta=fd["theta"],
            t1=fd["t1"], t2=fd["t2"], cap=fd.get("cap", float("nan")))

    # layer-aligned relief: march along the bar axis firing straight down from the
    # trough axis, and read the texture back off the finished mesh -- how many
    # grooves there are, how deep they cut, how far apart they sit, and whether
    # every edge really did land on a layer boundary.  Nothing here is taken from
    # the parameters; rib_bands() proposes and the mesh disposes.
    def trough_depth(x):
        ok, p, _, _ = obj.ray_cast(Vector((x, g["Y_AXIS"], g["Z_AXIS"])),
                                   Vector((0, 0, -1)))
        return (g["Z_AXIS"] - p.z) if ok else float("nan")

    overhang = overhang_area(g)
    ribs = dict(planned=len(bands), pitch=RIB_PITCH, width=RIB_WIDTH,
                depth=RIB_DEPTH, layer=LAYER_H, x_limit=RIB_X_LIM,
                found=0, depth_meas=float("nan"), width_meas=float("nan"),
                pitch_meas=float("nan"), layer_err=float("nan"),
                land_r=float("nan"), edges=0)
    if bands and RIB_DEPTH > 0.0:
        cut = g["R_TROUGH"] + 0.5 * RIB_DEPTH        # halfway down a groove
        x_lim = max(abs(v) for b in bands for v in b) + RIB_PITCH
        step = 0.02
        n_march = int(2.0 * x_lim / step) + 1
        xs = [-x_lim + step * i for i in range(n_march)]
        deep = [trough_depth(x) > cut for x in xs]
        edges = []
        for i in range(n_march - 1):
            if deep[i] == deep[i + 1]:
                continue
            lo, hi = xs[i], xs[i + 1]
            for _ in range(30):                      # bisect onto the real edge
                mid = 0.5 * (lo + hi)
                if (trough_depth(mid) > cut) == deep[i]:
                    lo = mid
                else:
                    hi = mid
            edges.append(0.5 * (lo + hi))
        runs = [(edges[i], edges[i + 1]) for i in range(0, len(edges) - 1, 2)] \
            if edges and not deep[0] else []
        centres = [0.5 * (a + b) for a, b in runs]
        if runs:
            ribs["found"] = len(runs)
            ribs["depth_meas"] = max(trough_depth(c) for c in centres) - g["R_TROUGH"]
            ribs["width_meas"] = sum(b - a for a, b in runs) / len(runs)
            ribs["land_r"] = trough_depth(0.0)
            ribs["edges"] = len(edges)
            if len(centres) > 1:
                gaps = [centres[i + 1] - centres[i] for i in range(len(centres) - 1)]
                ribs["pitch_meas"] = sum(gaps) / len(gaps)
            # print height of an edge is x + W_PLATE/2, because export_stl turns the
            # part's X into the printer's Z and drops it onto the bed
            ribs["layer_err"] = max(
                abs((e + W_PLATE / 2.0) / LAYER_H
                    - round((e + W_PLATE / 2.0) / LAYER_H)) * LAYER_H for e in edges)

    return dict(
        params=dict(D_BAR=g["D_BAR"], H_DROP=g["H_DROP"], W_PLATE=W_PLATE,
                    H_PLATE=H_PLATE, T_PLATE=T_PLATE, T_WALL=T_WALL,
                    CLEAR=CLEAR, GAP=GAP, W_SADDLE=W_SADDLE, WRAP_DEG=WRAP_DEG),
        counts=counts,
        mesh=dict(non_manifold_edges=pos["non_manifold_edges"],
                  boundary_edges=pos["boundary_edges"],
                  loose_verts=loose_verts, loose_edges=loose_edges,
                  shells=pos["shells"], min_edge_len=min_edge,
                  degenerate_faces=pos["degenerate"], euler=pos["euler"],
                  topo_non_manifold_edges=topo_non_manifold,
                  topo_boundary_edges=topo_boundary, topo_shells=topo_shells,
                  folded_faces=len(folds), folded_in_collar=collar_folds),
        purge=g.get("PURGE", {}),
        tape=dict(width=tape_w, height=tape_h, z_min=tape_z0,
                  max_abs_y=tape_flat, faces=len(tape_faces),
                  area_mm2=tape_area, area_in2=tape_area / MM2_PER_IN2),
        bbox=bbox,
        plate_height=plate_top,
        trough=dict(z_rest_measured=z_rest, z_rest_expected=g["Z_REST"],
                    fit_y=fit_y, fit_z=fit_z, fit_r=fit_r,
                    y_axis_expected=g["Y_AXIS"], z_axis_expected=g["Z_AXIS"],
                    r_expected=g["R_TROUGH"], samples=len(samples)),
        wall=dict(min_mm=min_wall, at_phi_deg=min_wall_phi, required=T_WALL,
                  samples=len(walls) + len(groove_walls),
                  swept_deg=g["PHI_WALL_PLUS"] + g["PHI_WALL_MINUS"],
                  min_land=min_land, land_phi=land_phi,
                  min_groove=min_groove, groove_phi=groove_phi, groove_x=groove_x,
                  groove_samples=len(groove_walls)),
        fillet=fillets,
        ribs=ribs,
        mouth=dict(chamfer=MOUTH_CHAM,
                   wrap_meas_deg=g["WRAP_MEAS_DEG"], wrap_full_deg=g["WRAP_FULL_DEG"],
                   wrap_nominal_deg=WRAP_DEG, rim_plus=g["rim_plus"],
                   rim_minus=g["rim_minus"], **mouth),
        notch=dict(z_left=notch[0], z_right=notch[1], z_clear=notch[2],
                   z_expected=H_PLATE - NOTCH_D
                   + NOTCH_PROBE_X * NOTCH_D / (NOTCH_W / 2.0),
                   width=NOTCH_W, depth=NOTCH_D),
        bulge=dict(z_lo=FACE_PROBE_Z[0], z_hi=FACE_PROBE_Z[1], x=FACE_PROBE_X,
                   face_lo=face_probe[0], face_hi=face_probe[1],
                   expect_lo=plate_face_y(FACE_PROBE_X, FACE_PROBE_Z[0]),
                   expect_hi=plate_face_y(FACE_PROBE_X, FACE_PROBE_Z[1]),
                   amp_lo=bulge_at(FACE_PROBE_Z[0]), amp_hi=bulge_at(FACE_PROBE_Z[1])),
        root_void_scan=g.get("ROOT_VOID_SCAN", {}),
        moment_arm=g["Y_AXIS"],
        back_clear=g["BACK_CLEAR"],
        gap_eff=g["GAP_EFF"],
        projection=bbox["y"][1],
        print_overhang_mm2=overhang[0], print_overhang_at_x=overhang[1],
        drop_in=dict(min_clearance=drop_min, at_y=drop_y, r_root=g.get("R_ROOT_USED")),
        bending=bending_check(obj, g),
        expect=dict(w_plate=W_PLATE, h_plate=H_PLATE, h_cap=H_PLATE_CAP,
                    z_rest=g["Z_REST"], y_axis=g["Y_AXIS"], z_axis=g["Z_AXIS"],
                    r_trough=g["R_TROUGH"], t_wall=T_WALL, z_env_bot=g["Z_ENV_BOT"]),
    )


def acceptance(v, tol=2.0e-3):
    """Every acceptance check as (name, measured, expected, ok).

    The point of this function is that the verdict is computed from MEASURED
    numbers.  Printing a dimension next to the value it was built from proves
    nothing unless something actually compares them, so this does the comparing
    and report() gates on the result.
    """
    m, t, tr, w, e = v["mesh"], v["tape"], v["trough"], v["wall"], v["expect"]
    mo, no, bu = v["mouth"], v["notch"], v["bulge"]
    fi, rb = v["fillet"], v["ribs"]
    near = lambda a, b: abs(a - b) <= tol
    # The form features come through booleans and a loft, so they are held to a
    # looser tolerance than the dimension-bearing geometry above -- but they ARE
    # held: an unmeasured chamfer is a chamfer that silently did nothing, which is
    # exactly what both the round-over and the first attempt at this one produced.
    loose = 0.05
    return [
        # All POSITIONAL -- vertices identified by coordinate, which is the only
        # identity the shipped file has.  These four read 0/0/1 on the mesh that
        # would not slice, because they were counting bmesh edges and bmesh
        # shells, and the artifact has neither.  See positional_mesh().
        ("non-manifold edges", m["non_manifold_edges"], 0, m["non_manifold_edges"] == 0),
        ("boundary edges", m["boundary_edges"], 0, m["boundary_edges"] == 0),
        ("loose verts", m["loose_verts"], 0, m["loose_verts"] == 0),
        ("loose edges", m["loose_edges"], 0, m["loose_edges"] == 0),
        ("shells", m["shells"], 1, m["shells"] == 1),
        ("degenerate faces", m["degenerate_faces"], 0, m["degenerate_faces"] == 0),
        # Closed and genus 0.  Nothing in this part passes through it -- no
        # holes, the notch is a V and the relief is a groove -- so any other
        # value is a tunnel or a hole that nobody asked for.
        ("euler characteristic", m["euler"], 2, m["euler"] == 2),
        ("min edge length", m["min_edge_len"], "> " + str(MIN_EDGE_OK),
         m["min_edge_len"] > MIN_EDGE_OK),
        ("tape face width", t["width"], e["w_plate"], near(t["width"], e["w_plate"])),
        ("tape face height", t["height"], e["h_plate"], near(t["height"], e["h_plate"])),
        ("tape face planarity", t["max_abs_y"], 0.0, t["max_abs_y"] == 0.0),
        ("tape face at Z=0", t["z_min"], 0.0, near(t["z_min"], 0.0)),
        ("plate height <= cap", v["plate_height"], e["h_cap"], v["plate_height"] <= e["h_cap"] + tol),
        ("trough rest Z", tr["z_rest_measured"], e["z_rest"], near(tr["z_rest_measured"], e["z_rest"])),
        ("trough axis Y", tr["fit_y"], e["y_axis"], near(tr["fit_y"], e["y_axis"])),
        ("trough axis Z", tr["fit_z"], e["z_axis"], near(tr["fit_z"], e["z_axis"])),
        ("trough radius", tr["fit_r"], e["r_trough"], near(tr["fit_r"], e["r_trough"])),
        ("min wall on load path", w["min_mm"], ">= " + str(e["t_wall"]), w["min_mm"] >= e["t_wall"] - tol),
        ("bar drop-in clearance", v["drop_in"]["min_clearance"], "> 0", v["drop_in"]["min_clearance"] > 0.0),
        ("no material behind Y=0", v["bbox"]["y"][0], 0.0, v["bbox"]["y"][0] >= -tol),
        # Nothing may stand outside the envelope the plate and cradle define.  These
        # three are here because the part once shipped with an STL 3.9 mm wider than
        # the plate and 12.3 mm deeper than the cradle -- an unclamped round-over
        # sliding a vertex down a sliver -- and all thirty checks passed, because
        # not one of them was looking at the bounding box.
        ("within the plate in X", max(abs(v["bbox"]["x"][0]), v["bbox"]["x"][1]),
         "<= " + str(W_PLATE / 2.0), max(abs(v["bbox"]["x"][0]), v["bbox"]["x"][1])
         <= W_PLATE / 2.0 + tol),
        ("nothing above the plate", v["bbox"]["z"][1], e["h_plate"],
         v["bbox"]["z"][1] <= e["h_plate"] + tol),
        ("nothing below the cradle", v["bbox"]["z"][0], v["expect"]["z_env_bot"],
         v["bbox"]["z"][0] >= v["expect"]["z_env_bot"] - tol),
        ("bending safety factor", v["bending"]["sf"], ">= " + str(SF_MIN),
         v["bending"]["sf"] >= SF_MIN),
        ("mouth chamfer +Y", mo["cham_plus"], MOUTH_CHAM,
         abs(mo["cham_plus"] - MOUTH_CHAM) <= loose),
        ("mouth chamfer -Y", mo["cham_minus"], MOUTH_CHAM,
         abs(mo["cham_minus"] - MOUTH_CHAM) <= loose),
        # The ramp must stand between the shortened trough surface and the rim
        # the sharp cradle used to reach: past `true` (so a ramp is really there,
        # not just a shorter cradle) and no further than `rim` (so the chamfer
        # relieved the corner instead of adding material outside it).
        ("mouth ramp +Y", mo["end_plus"], f"{mo['true_plus']:.1f}..{mo['rim_plus']:.1f}",
         mo["true_plus"] < mo["end_plus"] <= mo["rim_plus"] + loose),
        ("mouth ramp -Y", mo["end_minus"], f"{mo['true_minus']:.1f}..{mo['rim_minus']:.1f}",
         mo["true_minus"] < mo["end_minus"] <= mo["rim_minus"] + loose),
        ("wrap at full radius", mo["wrap_full_deg"], ">= 160.0",
         mo["wrap_full_deg"] >= 160.0),
        ("witness notch left", no["z_left"], no["z_expected"],
         abs(no["z_left"] - no["z_expected"]) <= loose),
        ("witness notch right", no["z_right"], no["z_expected"],
         abs(no["z_right"] - no["z_expected"]) <= loose),
        ("top edge clear of notch", no["z_clear"], e["h_plate"],
         near(no["z_clear"], e["h_plate"])),
        ("swell low on the plate", bu["face_lo"], bu["expect_lo"],
         abs(bu["face_lo"] - bu["expect_lo"]) <= loose),
        ("swell faded up top", bu["face_hi"], bu["expect_hi"],
         abs(bu["face_hi"] - bu["expect_hi"]) <= loose),
        ("swell graded in Z", bu["face_lo"] - bu["face_hi"], "> 1.0",
         bu["face_lo"] - bu["face_hi"] > 1.0),
    ] + [
        # The fillets, measured off the mesh.  A radius that came out right proves
        # the blend was cut AND that it is tangent: a fillet that stopped short of
        # either surface leaves a step, and a step drags the least-squares radius
        # away from what was asked for.  The centre-error check is the second half
        # of that -- an arc of the right radius in the wrong place is not a fillet.
        check for kind in ("upper", "lower") if kind in fi for check in (
            (f"{kind} fillet radius", fi[kind]["fit_r"], fi[kind]["r_built"],
             abs(fi[kind]["fit_r"] - fi[kind]["r_built"]) <= loose),
            (f"{kind} fillet centred", fi[kind]["fit_c_err"], "<= 0.05",
             fi[kind]["fit_c_err"] <= loose),
            (f"{kind} fillet is round", fi[kind]["r_max"] - fi[kind]["r_min"], "<= 0.05",
             fi[kind]["r_max"] - fi[kind]["r_min"] <= loose),
        )
    ] + ([
        # The relief.  Counting the grooves is what stops the whole feature from
        # silently evaporating; measuring the depth is what stops it from being cut
        # at the wrong scale; and the layer check is the only one that proves the
        # thing it was built for, which is that no edge of this texture falls in the
        # middle of a printed layer.
        ("relief groove count", rb["found"], rb["planned"], rb["found"] == rb["planned"]),
        ("relief land at R_TROUGH", rb["land_r"], e["r_trough"],
         abs(rb["land_r"] - e["r_trough"]) <= tol),
        ("relief groove depth", rb["depth_meas"], rb["depth"],
         abs(rb["depth_meas"] - rb["depth"]) <= 0.01),
        ("relief groove width", rb["width_meas"], rb["width"],
         abs(rb["width_meas"] - rb["width"]) <= 0.01),
        ("relief pitch", rb["pitch_meas"], rb["pitch"],
         abs(rb["pitch_meas"] - rb["pitch"]) <= 0.01),
        ("relief on layer lines", rb["layer_err"], "<= 0.001",
         rb["layer_err"] <= 1.0e-3),
    ] if rb["planned"] else [])


def check_line(name, got, want, good):
    """One acceptance line.  Shared, so the STL gate cannot drift into a
    different format -- or a different verdict rule -- from every other check."""
    got_s = f"{got:.4f}" if isinstance(got, float) else str(got)
    want_s = f"{want:.4f}" if isinstance(want, float) else str(want)
    return (f"    [{'PASS' if good else 'FAIL'}] {name:24s} "
            f"measured {got_s:>12s}   expected {want_s}")


def report(tag, v):
    m, t, tr, w = v["mesh"], v["tape"], v["trough"], v["wall"]
    mo, no, bu = v["mouth"], v["notch"], v["bulge"]
    fi, rb = v["fillet"], v["ribs"]
    rv = v.get("root_void_scan") or {}
    pg = v.get("purge") or {}
    checks = acceptance(v)
    ok = all(c[3] for c in checks)
    lines = [
        f"== {tag} ==",
        f"  mesh      {v['counts']['verts']}v / {v['counts']['edges']}e / {v['counts']['faces']}f",
        f"  manifold  BY POSITION: non-manifold={m['non_manifold_edges']} "
        f"boundary={m['boundary_edges']} shells={m['shells']} "
        f"degenerate={m['degenerate_faces']} euler={m['euler']}; "
        f"loose_v={m['loose_verts']} loose_e={m['loose_edges']} "
        f"min_edge={m['min_edge_len']:.6f} mm  -> {'PASS' if ok else 'FAIL'}",
        f"            (Blender's own topological answer: non-manifold="
        f"{m['topo_non_manifold_edges']} boundary={m['topo_boundary_edges']} "
        f"shells={m['topo_shells']} -- printed beside it because it read 0/0/1 on "
        f"the build that would not slice, and only the positional numbers above "
        f"describe the file that ships)",
        f"  tape face {t['width']:.4f} x {t['height']:.4f} mm at Y=0 "
        f"(max|y|={t['max_abs_y']:.2e}, z_min={t['z_min']:.4f})",
        f"  adhesive  {t['area_mm2']:.1f} mm^2 = {t['area_in2']:.3f} in^2",
        f"  plate h   {v['plate_height']:.4f} mm (cap {H_PLATE_CAP})",
        f"  bbox      X {v['bbox']['x'][0]:.3f}..{v['bbox']['x'][1]:.3f}  "
        f"Y {v['bbox']['y'][0]:.3f}..{v['bbox']['y'][1]:.3f}  "
        f"Z {v['bbox']['z'][0]:.3f}..{v['bbox']['z'][1]:.3f}",
        f"  trough    rest Z={tr['z_rest_measured']:.4f} (expect {tr['z_rest_expected']:.4f})",
        f"            fitted axis Y={tr['fit_y']:.4f} Z={tr['fit_z']:.4f} R={tr['fit_r']:.4f} "
        f"(expect {tr['y_axis_expected']:.4f} / {tr['z_axis_expected']:.4f} / {tr['r_expected']:.4f}) "
        f"from {tr['samples']} rays",
        f"  min wall  {w['min_mm']:.4f} mm at phi={w['at_phi_deg']:.1f} deg "
        f"(require >= {w['required']}) over {w['samples']} rays spanning the "
        f"{w['swept_deg']:.1f} deg of full-thickness wrap; "
        f"{w['min_land']:.4f} on the land at X=0, {w['min_groove']:.4f} on the "
        f"groove floor at X={w['groove_x']:.2f} -- the groove is the section that "
        f"has to carry T_WALL, which is why R_OUT pays for RIB_DEPTH up front",
        f"  wrap      {mo['wrap_meas_deg']:.1f} deg delivered "
        f"(+Y arm to {mo['rim_plus']:.1f}, -Y arm to {mo['rim_minus']:.1f}); "
        f"WRAP_DEG={mo['wrap_nominal_deg']:.1f} is a ceiling the hull overrides, "
        f"not a description -- the bar still drops in, which is measured below",
        f"  mouth     {mo['chamfer']:.2f} mm 45-degree lead-in on both lips, "
        f"measured {mo['cham_plus']:.3f} / {mo['cham_minus']:.3f} mm of arc; "
        f"trough at full radius to {mo['true_plus']:.1f}/{mo['true_minus']:.1f} deg, "
        f"material to {mo['end_plus']:.1f}/{mo['end_minus']:.1f}, so "
        f"{mo['wrap_full_deg']:.1f} deg of cradle survives it",
        f"  swell     {bu['face_lo']:.3f} mm proud at Z={bu['z_lo']:.0f}, "
        f"{bu['face_hi']:.3f} at Z={bu['z_hi']:.1f} (X={bu['x']:.0f}); "
        f"amplitude on the centreline {BULGE:.2f} -> 0 over Z=0..{BULGE_FADE_Z:.2f}",
        f"  notch     {no['width']:.1f} x {no['depth']:.1f} mm V on the top edge "
        f"at X=0, floor measured at Z={no['z_left']:.3f}/{no['z_right']:.3f} "
        f"(expect {no['z_expected']:.3f}), top edge intact at {no['z_clear']:.3f}",
        f"  moment arm {v['moment_arm']:.3f} mm ({v['moment_arm']/MM_PER_IN:.3f} in), "
        f"projection {v['projection']:.3f} mm, back clearance "
        f"{v['back_clear']:.3f} mm ({v['back_clear']/MM_PER_IN:.3f} in)",
        f"  overhang  {v['print_overhang_mm2']:.1f} mm^2 springs into mid-air at "
        f"X=-{v['print_overhang_at_x']:.2f} (the first saddle-body section with "
        f"material in it, measured -- not the flare tip assumed); "
        f"arm is {W_SADDLE + 2*FLARE:.1f} mm wide at the plate, "
        f"{W_SADDLE:.1f} at the cradle",
        f"  root void {rv.get('tested', 0)} of {rv.get('stations', 0)} stations actually "
        f"tested ({rv.get('open_span', 0)} skipped as open span, {rv.get('inside', 0)} as "
        f"inside the plate, {rv.get('off_circle', 0)} off the cradle circle) -- a zero "
        f"here means the check passed without looking, not that it looked and found nothing",
        f"  purge     {pg.get('triangles', 0)} triangles in {pg.get('components', 0)} "
        f"positional components; dropped {pg.get('dropped_components', 0)} carrying "
        f"{pg.get('volume_dropped', 0.0):.6f} mm^3 across {pg.get('dropped_faces', 0)} "
        f"faces, kept {pg.get('triangles_kept', 0)} carrying "
        f"{pg.get('volume', 0.0):.4f} mm^3.  Null geometry only -- the volume is "
        f"asserted unchanged, this is not a shape repair",
        f"  drop-in   {v['drop_in']['min_clearance']:.4f} mm min clearance for the bar "
        f"to fall in, at Y={v['drop_in']['at_y']:.3f} (root fillet R="
        f"{v['drop_in']['r_root']:.2f})",
    ] + [
        f"  fillet {kind:<3s} R={fi[kind]['r_built']:.3f} mm across a "
        f"{fi[kind]['theta']:.1f} deg corner (asked {fi[kind]['r_requested']:.1f}, "
        f"geometry carried {fi[kind]['cap']:.3f}); measured R="
        f"{fi[kind]['fit_r']:.4f} from {fi[kind]['rays']} rays fanned out of the arc "
        f"centre at Y={fi[kind]['c_y']:.3f} Z={fi[kind]['c_z']:.3f}, centre error "
        f"{fi[kind]['fit_c_err']:.4f}, r {fi[kind]['r_min']:.4f}..{fi[kind]['r_max']:.4f}"
        for kind in ("upper", "lower") if kind in fi
    ] + ([
        f"  relief    {rb['found']}/{rb['planned']} grooves found on the trough; "
        f"{rb['depth_meas']:.4f} mm deep (asked {rb['depth']}), "
        f"{rb['width_meas']:.4f} mm wide (asked {rb['width']}), pitch "
        f"{rb['pitch_meas']:.4f} (asked {rb['pitch']}); land measured at "
        f"R={rb['land_r']:.4f}; every one of {rb['edges']} edges lands within "
        f"{rb['layer_err']*1000:.1f} um of a {rb['layer']} mm layer boundary",
    ] if rb["planned"] else []) + [
        f"  bending   worst section at Y={v['bending']['y']:.2f} mm: h="
        f"{v['bending']['section_h']:.2f} S={v['bending']['S']:.1f} mm^3, "
        f"sigma={v['bending']['sigma']:.3f} MPa at {v['bending']['load_lbf']} lbf "
        f"-> SF {v['bending']['sf']:.1f} on solid {MATERIAL}",
        f"  folds     {m['folded_faces']} edges folded past 170 deg (zero-thickness "
        f"fins), {m['folded_in_collar']} of them in the lower collar's runout.  Made "
        f"by the round-over, not by the booleans; the collar count is the one this "
        f"file fixed and the rest are the plate's top corners and the notch",
        "  acceptance:",
    ]
    for c in checks:
        lines.append(check_line(*c))
    print("\n".join(lines))
    return ok


# ===========================================================================
# export -- and the check on what was actually written
# ===========================================================================

STL_WELD = 1.0e-4    # mm; how far apart two corners of the EXPORTED triangle
                     # soup may lie and still be treated as one point when the
                     # file is checked below.  This number is the whole check:
                     # too tight and it misses the coincidences a slicer merges,
                     # too loose and it fuses geometry that is genuinely apart
                     # and invents faults.  Both bounds were measured on this
                     # part rather than guessed.
                     #
                     # FLOOR.  An STL stores float32.  At the largest coordinate
                     # this part reaches (76.2 mm, the plate along the print Z)
                     # one ulp is 2^-24 * 128 = 7.6e-6 mm, and at the 25 mm end
                     # 1.9e-6.  Two vertices that were one vertex in Blender come
                     # out bit-identical; two that differed by less than an ulp
                     # collapse in the writer.  So anything below ~1e-5 is inside
                     # the file's own rounding noise and buys nothing.
                     #
                     # CEILING.  The closest pair of genuinely DISTINCT vertices
                     # in the shipped nominal file is 0.005048 mm apart, and the
                     # whole low tail sits between 0.00505 and 0.0054.  That is
                     # not a coincidence: clean_mesh() has already welded this
                     # mesh at MERGE_DIST = 5.0e-3, so by construction nothing
                     # closer than that survives.  A weld at or above MERGE_DIST
                     # would start undoing the generator's own decisions.
                     #
                     # 1.0e-4 sits 13x above the worst-case float32 ulp and 50x
                     # below both the closest distinct pair and MERGE_DIST, i.e.
                     # in the middle of a two-and-a-half decade empty band.  And
                     # it is measurably not load-bearing: 0 (exact float
                     # equality), 1e-6, 1e-5, 1e-4, 1e-3 and 5e-3 all return the
                     # same vertex, edge and fault counts on all three variants.
                     # 1e-2 -- twice MERGE_DIST -- is where it breaks, fusing
                     # ~110 triangles to nothing and inventing a fault on h+2;
                     # that is what "too loose" looks like, and it is two decades
                     # away.  stl_manifold() reports the exact-equality counts
                     # alongside the welded ones on every run so that this stays
                     # a measurement and not an assumption.


def stl_triangles(path):
    """Every triangle's three corners, read straight out of a binary STL.

    Deliberately not bmesh and not the exporter's own data: the point of this
    function is to look at the bytes on disk the way a slicer does, so it must
    not share a single line of code with the thing that produced them.
    """
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if len(fh.read(80)) < 80:
            raise ValueError(f"{path}: {size} bytes, too short for an STL header")
        n = struct.unpack("<I", fh.read(4))[0]
        # The only reliable binary/ASCII discriminator: an ASCII file's leading
        # bytes can say "solid" and so can a binary one's 80-byte comment, but
        # only a binary file is exactly 84 + 50n long.
        if size != 84 + 50 * n:
            raise ValueError(
                f"{path}: not a binary STL -- header claims {n} triangles, which "
                f"needs {84 + 50 * n} bytes, and the file is {size}")
        body = fh.read(n * 50)
    return [struct.unpack_from("<12f", body, i * 50)[3:12] for i in range(n)]


def _weld_ids(points, tol):
    """Index per point, merging any two points within tol.  (ids, n_unique).

    Exact-equality first, because the exporter writes a shared corner as the
    same three floats every time and that collapses the list about sixfold, then
    a union-find over a grid of side tol on what is left.  All 27 neighbouring
    cells are searched: a bare round(x/tol) quantiser puts a pair straddling a
    cell boundary in different bins no matter how close it is, so it silently
    misses precisely the coincidences this is looking for.
    """
    exact, uniq = {}, []
    for p in points:
        i = exact.get(p)
        if i is None:
            i = exact[p] = len(uniq)
            uniq.append(p)
    ids = [exact[p] for p in points]
    if tol <= 0.0:
        return ids, len(uniq)

    parent = list(range(len(uniq)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    cells = collections.defaultdict(list)
    inv = 1.0 / tol
    for i, p in enumerate(uniq):
        cells[(math.floor(p[0] * inv), math.floor(p[1] * inv),
               math.floor(p[2] * inv))].append(i)
    t2 = tol * tol
    for cell, idxs in cells.items():
        near = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if (dx, dy, dz) > (0, 0, 0):
                        continue      # each unordered cell pair visited once
                    near.extend(cells.get((cell[0] + dx, cell[1] + dy,
                                           cell[2] + dz), ()))
        for i in idxs:
            pi = uniq[i]
            for j in near:
                if j >= i:
                    continue
                pj = uniq[j]
                if ((pi[0] - pj[0]) ** 2 + (pi[1] - pj[1]) ** 2
                        + (pi[2] - pj[2]) ** 2) <= t2:
                    ra, rb = find(i), find(j)
                    if ra != rb:
                        parent[rb] = ra
    remap = {}
    for i in range(len(uniq)):
        r = find(i)
        if r not in remap:
            remap[r] = len(remap)
    return [remap[find(i)] for i in ids], len(remap)


# ---------------------------------------------------------------------------
# DO NOT DEDUPLICATE ANYTHING BELOW THIS LINE AGAINST part_kit OR mesh_audit.
#
# It looks like obvious duplication and it is the opposite.  This half re-opens
# the exported BYTES, rebuilds topology by position from scratch, and computes its
# own vertex digest, sharing no code with either shipped auditor.  That makes it a
# genuine third opinion on the same artifact -- which is the whole method this
# repository is built on, and the reason `inspect_model.py` and `mesh_audit.py`
# overlap on purpose.  CLAUDE.md puts it plainly: if either ever imports the other,
# the evidence is gone.
#
# The construction half above may delegate to part_kit, and does.  This half may
# not.  A regression fixture whose verifier is the code under test proves nothing.
# ---------------------------------------------------------------------------

def stl_manifold(path, weld=None):
    """Is the file on disk watertight BY POSITION?  Counts, not opinions.

    This exists because Blender's answer and the slicer's answer are different
    questions and only one of them is about the artifact.  verify() counts faces
    per TOPOLOGICAL edge, so two distinct edges at identical coordinates are two
    edges with two faces each and the mesh reads manifold.  An STL has no vertex
    identity at all -- it is a bag of triangles -- so a slicer rebuilds the
    topology BY POSITION, those two edges become one edge with four faces, and
    the same part reads non-manifold and will not slice.  That is exactly what
    shipped: "non-manifold edges 0" from this script, "2 non-manifold edges"
    from Bambu Studio, both correct.

    So: reconstruct the topology the way the slicer does, and report
      open_edges     used by one triangle    -- a hole
      over_edges     used by three or more   -- the fault Bambu reported
      degenerate     triangles with two corners at the same welded point
      bodies         connected components, joined only across 2-face edges --
                     the convention a slicer uses, and the one that made the
                     debris visible: the file that shipped held one body of
                     25196 triangles and TWO null flaps of two triangles each
      euler          V - E + F over the welded soup; 2 for a closed genus-0
                     surface, which is what this part is
      winding_flips  edges whose two triangles run along them the same way, i.e.
                     one of the pair is inside out
      volume         enclosed, by the divergence theorem, per body
      vertex_digest  md5 over the sorted UNIQUE vertex coordinate set, .9g per
                     coordinate.  REPORTED, NOT GATED, and it is here because
                     hashing the file's BYTES proves nothing about this
                     generator: two runs of identical, unedited source produce
                     different STL bytes (FACTS 7j).  This digest is the thing
                     that does hold still -- verified identical across nine
                     consecutive runs of all three variants while every raw md5
                     differed -- so it is the number to compare when asking
                     whether an edit moved the solid.
    """
    weld = STL_WELD if weld is None else weld   # resolved at call time; a default
                                                # argument would freeze it at import
    tris = stl_triangles(path)
    pts = [t[k:k + 3] for t in tris for k in (0, 3, 6)]
    ids, n_welded = _weld_ids(pts, weld)
    _, n_exact = _weld_ids(pts, 0.0)

    tri_ids, degenerate = [], 0
    for i in range(len(tris)):
        a, b, c = ids[3 * i], ids[3 * i + 1], ids[3 * i + 2]
        if a == b or b == c or a == c:
            degenerate += 1
            continue
        tri_ids.append((a, b, c))

    owners = collections.defaultdict(list)
    flips = 0
    for i, (a, b, c) in enumerate(tri_ids):
        for u, v in ((a, b), (b, c), (c, a)):
            owners[(u, v) if u < v else (v, u)].append((i, u < v))
    for e, use in owners.items():
        if len(use) == 2 and use[0][1] == use[1][1]:
            flips += 1

    parent = list(range(len(tri_ids)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for e, use in owners.items():
        if len(use) == 2:
            ra, rb = find(use[0][0]), find(use[1][0])
            if ra != rb:
                parent[rb] = ra
    where = {}
    for i, vid in enumerate(ids):
        where.setdefault(vid, pts[i])
    comps = collections.defaultdict(list)
    for i in range(len(tri_ids)):
        comps[find(i)].append(i)
    bodies = []
    for fs in comps.values():
        vol = 0.0
        for i in fs:
            a, b, c = (where[q] for q in tri_ids[i])
            vol += (a[0] * (b[1] * c[2] - b[2] * c[1])
                    - a[1] * (b[0] * c[2] - b[2] * c[0])
                    + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        bodies.append(dict(tris=len(fs), volume=vol))
    bodies.sort(key=lambda b: -abs(b["volume"]))

    faults = sorted(((len(u), e) for e, u in owners.items() if len(u) != 2),
                    reverse=True)
    # Order-independent by construction: a set, then sorted.  Neither the
    # triangle emission order nor the diagonal a planar quad happens to be cut
    # on can move it, which is exactly why it is the digest worth printing.
    vset = sorted({tuple(f"{c:.9g}" for c in p) for p in pts})
    vertex_digest = hashlib.md5(
        "|".join(",".join(v) for v in vset).encode()).hexdigest()
    return dict(
        path=path, tris=len(tris), verts=n_welded, verts_exact=n_exact,
        vertex_digest=vertex_digest, unique_verts=len(vset),
        weld=weld, edges=len(owners), degenerate=degenerate,
        open_edges=sum(1 for u in owners.values() if len(u) == 1),
        over_edges=sum(1 for u in owners.values() if len(u) > 2),
        euler=n_welded - len(owners) + len(tri_ids),
        winding_flips=flips, bodies=bodies, solids=len(bodies),
        volume=sum(b["volume"] for b in bodies),
        null_volume=sum(abs(b["volume"]) for b in bodies[1:]) if bodies else 0.0,
        faults=[dict(faces=k,
                     a=tuple(round(q, 4) for q in where[e[0]]),
                     b=tuple(round(q, 4) for q in where[e[1]]))
                for k, e in faults[:8]],
    )


def stl_acceptance(st):
    """The exported file's checks, in the same (name, got, want, ok) shape as
    acceptance() so that they print, and gate, identically.

    Wider than "is it non-manifold", deliberately.  A single number can be
    dodged by whatever produces the next sliver; this asks the file the whole
    question -- closed, one body, right genus, consistently wound, and no null
    triangles -- so the class stays visible rather than the one instance of it.
    """
    return [
        ("stl non-manifold edges", st["over_edges"], 0, st["over_edges"] == 0),
        ("stl open edges", st["open_edges"], 0, st["open_edges"] == 0),
        ("stl degenerate tris", st["degenerate"], 0, st["degenerate"] == 0),
        ("stl bodies", st["solids"], 1, st["solids"] == 1),
        ("stl euler characteristic", st["euler"], 2, st["euler"] == 2),
        ("stl winding flips", st["winding_flips"], 0, st["winding_flips"] == 0),
        ("stl volume", st["volume"], "> 0", st["volume"] > 0.0),
        ("stl null volume", st["null_volume"], "<= " + str(NULL_VOLUME),
         st["null_volume"] <= NULL_VOLUME),
    ]


def export_stl(obj, filepath, print_orient=True):
    """Write a binary STL in millimetres.

    print_orient rotates the part -90 deg about Y so its X axis becomes the
    print Z: an X-normal face lands on the bed, the Y-Z profile lies in the
    layer plane, and the arm root is loaded within layers rather than across
    them.  The rotation is baked into a throwaway copy; the scene part keeps
    its identity transform.
    """
    tmp = obj.copy()
    tmp.data = obj.data.copy()
    tmp.name = "_tmp_export"
    bpy.context.scene.collection.objects.link(tmp)

    if print_orient:
        me = tmp.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(-90.0), 3, 'Y'))
        bm.to_mesh(me)
        bm.free()
    # drop onto the bed and centre in X/Y
    co = [v.co for v in tmp.data.vertices]
    off = Vector((-(min(c.x for c in co) + max(c.x for c in co)) / 2.0,
                  -(min(c.y for c in co) + max(c.y for c in co)) / 2.0,
                  -min(c.z for c in co)))
    tmp.data.transform(Matrix.Translation(off))

    for o in bpy.context.scene.objects:
        o.select_set(False)
    tmp.select_set(True)
    bpy.context.view_layer.objects.active = tmp
    bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True,
                          global_scale=1.0, use_scene_unit=False,
                          apply_modifiers=True, ascii_format=False,
                          forward_axis='Y', up_axis='Z')
    dims = tuple(round(x, 3) for x in tmp.dimensions)
    purge("_tmp_export")
    return dims


# ===========================================================================
# main
# ===========================================================================

def out_dir():
    env = os.environ.get("SADDLE_OUT_DIR")
    if env:
        return env
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.abspath(".")


def stash_reference(name="obj_0", coll_name="reference_draft"):
    """Keep the pre-existing traced draft, hidden, rather than destroying it."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return False
    coll = bpy.data.collections.get(coll_name)
    if coll is None:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)
    for c in list(obj.users_collection):
        if c is not coll:
            c.objects.unlink(obj)
    if obj.name not in coll.objects:
        coll.objects.link(obj)
    obj.hide_viewport = True
    obj.hide_render = True
    return True


def main():
    scene_setup()
    stash_reference()
    od = out_dir()
    results = {}

    obj, g = build_saddle()
    v = verify(obj, g)
    results[PART_NAME] = v
    ok_nominal = report(f"{PART_NAME}  (D_BAR={g['D_BAR']}, H_DROP={g['H_DROP']})", v)
    ok = ok_nominal

    gauge, gauge_ok = None, False
    if DO_GAUGE:
        gauge = build_gauge()
        gv = verify_gauge(gauge)
        results[GAUGE_NAME] = gv
        gauge_ok = report_gauge(gv)
        ok = gauge_ok and ok
    else:
        purge(GAUGE_NAME)          # so an old gauge cannot survive in a re-saved .blend

    if DO_EXPORT:
        # A part that failed its own acceptance checks does not get written.
        # Otherwise a printable STL lands on disk carrying a defect the script
        # already detected, and whoever picks the file up has no way to know.
        #
        # ...and then the FILE is checked, because passing the mesh checks is
        # not the same claim as being sliceable and this part has already shipped
        # a mesh that passed all 135 and would not slice.  See stl_manifold().
        #
        # ORDER.  A file check needs bytes on disk, so it can only run after the
        # write, which means there is unavoidably a moment when an unverified
        # STL exists at the path a human would pick up.  The only honest way to
        # close that window is to delete the file the instant it fails AND fail
        # the run -- both, not either.  A loud failure that leaves the bad STL
        # sitting there is exactly how this defect reached the owner: the run
        # said PASS, but even if it had said FAIL, saddle_h0.stl would still have
        # been the newest file in the directory.  Writing to a temp name and
        # renaming on success would keep the path clean, but then the artifact
        # that was verified and the artifact that ships are two different files
        # joined by a step nothing tests -- and every defect in this part's
        # history has been a check that measured something other than what
        # shipped.  So: write to the final path, parse that exact file, remove it
        # if it fails.
        exported, refused, stl_stats = {}, [], {}
        for fname, hd in VARIANTS:
            path = os.path.join(od, fname + ".stl")
            if abs(hd - H_DROP) < 1e-9:
                var, vg, var_ok = obj, g, ok_nominal
            else:
                var, vg = build_saddle(name=f"_tmp_var_{fname}", h_drop=hd)
                vv = verify(var, vg)
                results[fname] = vv
                var_ok = report(f"{fname}  (H_DROP={hd})", vv)
                ok = var_ok and ok
            if var_ok:
                dims = export_stl(var, path)
                st = stl_manifold(path)
                stl_stats[fname] = st
                checks = stl_acceptance(st)
                stl_ok = all(c[3] for c in checks)
                print(f"\n== {fname}.stl (as written) ==")
                print(f"  soup      {st['tris']} triangles, {st['edges']} edges, "
                      f"{st['verts']} points welded at {st['weld']:g} mm "
                      f"({st['verts_exact']} at exact float equality -- if these "
                      f"two differ the weld is doing work and its value matters)")
                print("  bodies    " + ", ".join(
                    f"{b['tris']} tris / {b['volume']:.4f} mm^3"
                    for b in st["bodies"][:4]))
                print(f"  geometry  vertex-set md5 {st['vertex_digest']} over "
                      f"{st['unique_verts']} unique points -- compare THIS across "
                      f"runs, never the file's bytes, which differ every run "
                      f"(FACTS 7j)")
                for c in checks:
                    print(check_line(*c))
                for f in st["faults"]:
                    print(f"      {f['faces']} triangles on the edge {f['a']} -- "
                          f"{f['b']}  (file coordinates: the part is in print "
                          f"orientation, X along the model's -Z)")
                if stl_ok:
                    exported[fname] = dict(path=path, dims=dims,
                                           tris=st["tris"], verts=st["verts"])
                else:
                    os.remove(path)
                    refused.append(fname)
                    ok = False
            else:
                refused.append(fname)
                # A refused variant must not leave the PREVIOUS run's file lying
                # around under the name it was refused for.  Nothing distinguishes
                # a stale good-looking STL from a fresh one on disk.
                if os.path.exists(path):
                    os.remove(path)
            if var is not obj:
                purge(var.name)
        if DO_GAUGE and gauge_ok:
            path = os.path.join(od, "fitgauge.stl")
            exported["fitgauge"] = dict(path=path,
                                        dims=export_stl(gauge, path, print_orient=False))
        elif DO_GAUGE:
            refused.append("fitgauge")
        results["_exports"] = exported
        results["_refused"] = refused
        results["_stl"] = stl_stats
        print("\n== exports ==")
        for k, e in exported.items():
            size = os.path.getsize(e["path"]) if os.path.exists(e["path"]) else -1
            print(f"  {k:12s} {e['dims']} mm  {size} bytes  {e['tris']} tris  "
                  f"{e['path']}")
        for k in refused:
            print(f"  {k:12s} NOT EXPORTED -- failed its own acceptance checks "
                  f"(any file at that path has been removed)")

    with open(os.path.join(od, "verify_report.json"), "w") as fh:
        json.dump(results, fh, indent=2, default=str)

    if DO_SAVE:
        blend = os.path.join(od, "saddle.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        print(f"\nsaved {blend}")

    print(f"\nOVERALL: {'PASS' if ok else 'FAIL'}")
    return ok


def verify_gauge(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    res = dict(
        counts=dict(verts=len(bm.verts), edges=len(bm.edges), faces=len(bm.faces)),
        mesh=dict(
            non_manifold_edges=sum(1 for e in bm.edges if len(e.link_faces) != 2),
            boundary_edges=sum(1 for e in bm.edges if len(e.link_faces) < 2),
            loose_verts=sum(1 for v in bm.verts if not v.link_faces),
            loose_edges=sum(1 for e in bm.edges if not e.link_faces),
            shells=_shell_count(bm),
            min_edge_len=min(e.calc_length() for e in bm.edges),
        ),
        dims=tuple(round(x, 4) for x in obj.dimensions),
        notches=GAUGE_DIAS,
    )
    bm.free()

    # Measure each notch the same way the trough was measured: stand at the
    # notch's arc centre (on the top edge) and fan rays down into the material,
    # then least-squares a circle through the hits.  A ray fired from a point
    # that already lies ON the surface reports a zero-length hit, so the origin
    # must be the arc centre, never the arc itself.
    dias = sorted(GAUGE_DIAS)
    width = sum(dias) + (len(dias) + 1) * GAUGE_WALL
    height = max(dias) / 2.0 + GAUGE_LABEL + 2.0 * GAUGE_MARG
    cursor, measured = -width / 2.0 + GAUGE_WALL, []
    for d in dias:
        cx = cursor + d / 2.0
        cursor += d + GAUGE_WALL
        centre = Vector((cx, height + GAUGE_Y_OFF, GAUGE_T / 2.0))
        # Sweep the middle 160 deg only, on a half-step phase offset.  Rays that
        # land exactly on a polygon vertex (straight down, or along the two
        # points where the arc meets the top edge) are missed by the BVH and
        # then run the full height of the part, which wrecks the fit.
        n_ray, span = 64, math.radians(160.0)
        hits, radii, misses = [], [], 0
        for i in range(n_ray):
            a = math.pi + math.pi / 2.0 - span / 2.0 + span * (i + 0.5) / n_ray
            dirn = Vector((math.cos(a), math.sin(a), 0.0))
            ok, p, _, _ = obj.ray_cast(centre + dirn * 1.0e-4, dirn)
            dist = (p - centre).length if ok else float("inf")
            if ok and dist < 1.25 * (d / 2.0):
                hits.append((p.x, p.y))
                radii.append(dist)
            else:
                misses += 1
        fx, fy, fr = _fit_circle(hits) if len(hits) > 8 else (float("nan"),) * 3
        measured.append(dict(nominal=d, fit_dia=2.0 * fr,
                             fit_cx_err=fx - cx,
                             fit_cy_err=fy - (height + GAUGE_Y_OFF),
                             r_min=min(radii) if radii else float("nan"),
                             r_max=max(radii) if radii else float("nan"),
                             rays=len(hits), misses=misses))
    res["measured"] = measured
    return res


def report_gauge(v):
    m = v["mesh"]
    ok = (m["non_manifold_edges"] == 0 and m["boundary_edges"] == 0
          and m["loose_verts"] == 0 and m["shells"] == 1 and m["min_edge_len"] > 0)
    print(f"== {GAUGE_NAME} ==")
    print(f"  mesh      {v['counts']['verts']}v / {v['counts']['edges']}e / "
          f"{v['counts']['faces']}f   dims {v['dims']} mm")
    print(f"  manifold  non-manifold={m['non_manifold_edges']} boundary={m['boundary_edges']} "
          f"loose_v={m['loose_verts']} loose_e={m['loose_edges']} shells={m['shells']} "
          f"min_edge={m['min_edge_len']:.6f} -> {'PASS' if ok else 'FAIL'}")
    for n in v["measured"]:
        err = n["fit_dia"] - n["nominal"]
        print(f"  notch {n['nominal']:>5.1f} mm  fitted dia={n['fit_dia']:.4f} "
              f"(err {err:+.4f})  centre err ({n['fit_cx_err']:+.4f}, "
              f"{n['fit_cy_err']:+.4f})  r {n['r_min']:.4f}..{n['r_max']:.4f}  "
              f"{n['rays']} rays / {n['misses']} missed")
        ok = ok and abs(err) < 0.05 and n["misses"] == 0
    return ok


if __name__ == "__main__":
    # Exit non-zero on failure so a caller can tell.  Note that Blender itself
    # swallows Python exceptions unless it is given --python-exit-code, so the
    # invocation in the module docstring includes it.
    sys.exit(0 if main() else 1)

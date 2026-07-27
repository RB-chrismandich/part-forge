# Measurement procedures

A procedure whose resolution is not stated cannot settle anything. Every method below is
given with its error budget, because "about 22 mm" and "22.0 +/- 0.3 mm" support completely
different decisions, and only the second one can be written into a parameter table.

## The paper-strip circumference method

For a round bar, tube, or rail that is **already mounted**, this beats callipers.

1. Wrap a strip of paper tightly around the bar until it overlaps itself.
2. Mark through both layers at the overlap, with a single knife cut or a pin.
3. Lay the strip flat and measure mark to mark. That is the circumference **C**.
4. Diameter = **C / pi**.

**Error budget.** Reading C to 1 mm gives diameter to 1/pi, about **0.3 mm**. Reading C to
0.5 mm gives about 0.16 mm. The division by pi is doing real work: it divides the reading
error by more than three, which is why a coarse measurement of a circumference beats a
careful measurement of a diameter.

**Discriminability check.** Before trusting any measurement, confirm the candidate answers
are further apart than the error:

| Nominal | Circumference |
|---|---|
| 1/2 in | ~40 mm |
| 5/8 in | ~50 mm |
| 3/4 in | ~60 mm |
| 7/8 in | ~70 mm |
| 1 in | ~80 mm |

Ten millimetres apart against a 1 mm reading error. Even a sloppy measurement is decisive,
and that is the property worth checking before spending effort on precision that changes no
conclusion.

**Why it beats callipers on a mounted bar.** Callipers need square, unobstructed access to a
true diameter. On a bar against a wall, in a bracket, or behind a curtain, the jaws land on a
chord instead and read short -- and read short *consistently*, so repeating the measurement
increases confidence in a wrong number. The paper strip needs only that the strip goes all
the way round.

**Failure modes.** A strip pulled tight around a compliant surface reads small. A strip
wrapped at a slant reads large -- it measures a helix, not a circle. Keep the strip
perpendicular to the axis and use its own edge as the guide.

## What each instrument can honestly resolve

Claiming a tolerance an instrument cannot deliver is worse than claiming none, because the
number then propagates as though it were real.

| Instrument | Honest resolution | Good for | Fails at |
|---|---|---|---|
| Steel rule, mm graduations | +/-0.5 mm | overall extents, spacings over 20 mm | anything under 5 mm; internal features |
| Tape measure | +/-1 mm, worse over 1 m | envelopes, spans, mounting spacings | anything needing better than a millimetre; hook slop adds 1 mm on its own |
| Dial or digital callipers | +/-0.05 mm outside, +/-0.1 mm inside | diameters, thicknesses, depths with clear access | mounted parts, deep bores, soft material |
| Feeler gauges | +/-0.01 mm | gaps and clearances | anything not a parallel gap |
| Thread pitch gauge | exact, it matches or it does not | thread identification | nothing, when access allows |
| Paper strip + rule | +/-0.3 mm | mounted round stock | non-circular sections |
| Photo with a scale in frame | +/-2 to 3 mm at best | rough envelopes, ruling options out | any dimension that decides a fit |
| Printed go/no-go gauge | half the step between notches | mounted stock, unknown standards | continuously variable dimensions |

Record the instrument in the tag: `[MEASURED +/-0.05 mm, digital callipers]`. A bare
`+/-0.05 mm` from a tape measure is fiction, and the only way to catch it later is if the
instrument was written down.

## Photo scaling, and its real error band

Scaling a dimension off a photograph against a ruler in frame is legitimate for ruling
options out and illegitimate for setting a parameter. The error sources compound: the ruler
and the feature are rarely in the same focal plane, lens distortion is worst at the frame
edges where the ruler usually is, and perspective foreshortens anything not parallel to the
sensor.

Two to three millimetres is a realistic band on a normal phone photo of a normal object. Tag
it `[PHOTO +/-3 mm]` and treat "confirm before printing" as part of the tag rather than
advice.

The reference project's most expensive measurement error came from a photo-derived chain, and
the lesson generalises past photography -- see below.

## Prefer the direct read to the longer chain

A diameter was inferred as *hook outer width minus twice an assumed wall thickness*. Two
clean, well-lit, independently measured edges, so it read as the strongest evidence
available. It was **2.95 mm wrong** -- the estimate said about 22 mm against a confirmed
19.05 mm.

A direct read of the inner opening gave 18 to 19 mm and was discounted for looking
foreshortened. It was closest to correct.

The mechanism: the chain had three inputs, and the middle one -- the wall thickness -- was
itself a guess that nobody had tagged. Each inference step silently imports its own
assumptions, and the composite inherits all of them while presenting a single confident
number. A one-step read that looks imprecise usually beats a two-step derivation that looks
rigorous.

Two working rules. Count the inference steps and prefer fewer. And when a chain and a direct
read disagree, do not average them -- find out which one is wrong.

## Dimensions fixed by hardware you did not install

**This class of dimension must never be derived.** It is the single most expensive rule in
this reference.

A mounting depth was computed as `plate_thickness + radius + gap` = 16.0 mm. The brief was
honest, calling the result "a floor, not a target". It was then used as the value. The actual
depth -- set by end brackets that had been on the wall for years and that nobody had measured
-- was **31.75 mm, 1.98x larger**. The part could not reach the thing it existed to support.
The parameter table now carries the annotation `this assumption cost a rebuild`.

The formula was not wrong. It correctly gave the minimum the geometry permits. The world sits
at that minimum only by coincidence.

How to recognise the class: ask *who decided this number*. If the answer is anything other
than "this project", it is an input. Existing brackets, stud spacing, an appliance's foot
pattern, a shaft that already exists, the bolt circle on a part being adapted to -- every one
of those is a measurement, tagged `[MEASURED]` or `[OPEN]`, never `[DERIVED]`.

Measuring one is often awkward, which is exactly why the temptation to derive it is strong.
Measure from a reference visible at the point of interest: for a bar height, measure down
from the top edge of a header band that is visible at mid-span, rather than trying to
transfer a datum across the room.

## Printed go/no-go gauges

When a dimension cannot be measured with what is on hand, print the question.

A **comb**: a flat bar with semicircular notches at each candidate size, each notch labelled
with embossed text. Try it against the object; the answer is the notch that fits.

Design notes:

- Space the notches by a **standard series**, not evenly. The worked example used
  19.0 / 20.6 / 22.2 / 23.8 / 25.4 mm -- the imperial sixteenths from 3/4 to 1 in -- because
  the bar was overwhelmingly likely to be one of those, and a gauge that can only return
  "between 20.6 and 22.2" has still eliminated four possibilities.
- Emboss the labels rather than engraving them. Embossed text survives a first layer that
  engraved text does not.
- Add clearance deliberately and state it. A notch cut at exactly nominal will not admit a
  nominal bar; cut at nominal plus 0.2 mm it will, and the reading is then "fits at +0.2".
- Resolution is half the step between notches. Say so on the gauge if there is room.

**When it is cheaper than measuring:** almost always, for mounted round stock. A comb is a
few minutes of print time and a few grams, against an afternoon of trying to get callipers
onto something behind a curtain rail. It also produces an artifact the owner can keep and
re-check against, which a one-off measurement does not.

**When to retire it:** once the dimension is confirmed by a better method, mark the gauge
retired in the ledger but keep it printable. The worked example did exactly this -- the gauge
stopped being a deliverable when the diameter was stated by the owner, and stayed in the
repository against the confirmation ever being doubted.

## Unit disambiguation by cross-check

An owner wrote "2 at the base". Two what? Not metres. Millimetres, centimetres and inches are
all physically plausible for the feature in question, and they differ by factors of 10 and
25.4 -- differences no tolerance absorbs.

The method: find a second, **independently derived** number that should coincide with the
first under the correct interpretation, and test the agreement.

Reading it as 2 mm, with the confirmed 19.05 mm diameter, put the bar centre within
**0.83 mm** of where an existing draft -- produced by a completely different route -- already
placed it. Under 2 cm the two would have disagreed by about 18 mm, and under 2 in by about
49 mm. The agreement is only explicable under one reading, so the reading is settled.

Two disciplines make this trustworthy:

- The cross-check must be **independent**. A second number derived from the first cannot
  corroborate it.
- **Re-validate when an input changes.** The cross-check above originally used a diameter of
  22 mm. When that was corrected to 19.05 mm, the cross-check was recomputed to confirm the
  conclusion did not depend on the since-corrected number. It did not. Had nobody rechecked,
  a settled conclusion would have been resting on a retracted fact.

## The closing rule

State the resolution alongside every number, and state it in the same breath as the method.
A measurement without a resolution cannot settle a question, cannot be compared against a
tolerance, and cannot be superseded cleanly later -- because nobody can tell whether the new
number disagrees with the old one or merely sits inside its error band.

"""The path the air actually takes through the engine.

One definition, read by two things: plumbing.py builds the runners and
primaries along these centrelines, and make_manifest.py writes them into the
viewer so the flow animation follows the ducts that exist rather than a
plausible-looking copy of them. Drawn from a second set of numbers they would
drift the first time a runner moved, and the flow would be running through
metal.

Everything is in millimetres, in the model's own frame.

Valve timing comes from spec.CAM, in a 720-degree cycle with 0 at firing TDC:

    exhaust centre   360 - lobe_centre_ex   (before the overlap TDC)
    intake centre    360 + lobe_centre_in   (after it)

which for this engine puts the exhaust open from 116 to 388 degrees and the
intake from 324 to 604 -- 64 degrees of overlap around the TDC between them,
which is what a 16,000 rpm engine wants.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec                                    # noqa: E402
from parts import common                       # noqa: E402

T = spec.TURBO
I = spec.INTAKE


def intake_port(bank, x):
    """Centre of the intake port face on the head."""
    # up the head's own face, not a fixed 30 mm above the deck: the head is
    # as tall as its valvetrain needs, and the port enters it four tenths of
    # the way up. Pinned to 30 mm, every intake runner ended inside the block.
    d, lat = common.bank_dir(bank), common.bank_lat(bank)
    h = spec.DECK_HEIGHT + spec.HEAD["height"] * 0.40
    return (x, d[1] * h + lat[1] * -50.0, d[2] * h + lat[2] * -50.0)


def exhaust_port(bank, x):
    """Centre of the exhaust port face -- inboard, because the turbos sit in
    the vee."""
    d, lat = common.bank_dir(bank), common.bank_lat(bank)
    h = spec.DECK_HEIGHT + spec.HEAD["height"] * 0.38
    return (x, d[1] * h + lat[1] * 58.0, d[2] * h + lat[2] * 58.0)


def runner_path(bank, x):
    """Plenum bellmouth inboard and down to the intake port.

    The plenum is outboard of the bank and the port is on the head's
    outboard face, so this is a short run down the outside of the engine --
    which is the point of putting the induction there. It used to start in
    the vee and cross the whole cylinder head.
    """
    port = intake_port(bank, x)
    sgn = -1.0 if bank == 0 else 1.0
    y_pl = sgn * (spec.INTAKE["plenum_y"] - spec.INTAKE["plenum_r"] * 0.35)
    z_pl = spec.INTAKE["plenum_z"]
    return [(x, y_pl, z_pl),
            (x, y_pl + (port[1] - y_pl) * 0.16, z_pl - 30.0),
            (x, y_pl + (port[1] - y_pl) * 0.55, port[2] + 10.0),
            port]


def collector_path(bank_pair):
    """Four primaries merging, and turning into the turbine inlet.

    The collector used to be a cone revolved about the turbo's own axis and
    dropped 16 mm above it, which meant it neither met the primaries nor
    pointed at the volute: it was a shape near the turbocharger. A merge
    collector is a duct with a mouth at one end and a flange at the other,
    and both ends are somewhere specific.
    """
    _, tx, _, ib = turbo_side(bank_pair)
    inlet = turbine_scroll(bank_pair)[0][0]
    # the mouth sits over the middle of the four cylinders it serves and
    # falls into the turbine inlet; the four primaries land on its rim
    # 92 mm above the shaft, not 66: the two inboard cylinders' primaries
    # have to pass over the compressor housing to reach the mouth, and the
    # top of that housing is 65 mm above the shaft. Not higher than 92
    # either -- the car this engine goes in has cooling louvres in its engine
    # cover 700 mm off the ground, and the collector is the tallest thing
    # here.
    return [(tx + ib * 16.0, 0.0, T["z"] + 92.0),
            (tx + ib * 4.0, 0.0, T["z"] + 78.0),
            (tx - ib * 12.0, 0.0, T["z"] + 58.0),
            (inlet[0] + ib * 8.0, 0.0, inlet[2] + 3.4),
            (inlet[0] - ib * 2.0, 0.0, inlet[2])]


# Four 25 mm primaries merging: 1,960 mm2, which is a 25 mm radius. The
# mouth is 30 so the four pipes land on its rim with room between them,
# and it necks to the turbine inlet from there.
COLLECTOR_RADII = [30.0, 29.0, 27.0, 25.0, 24.0]


def primary_path(pair, bank, x):
    """Exhaust port out into the vee and forward into the collector mouth.

    Each pipe arrives at its own place on the mouth, spread round it by the
    firing order's own spacing. Four pipes ending at one point on the axis is
    a node, not a merge, and it put the last 40 mm of every primary inside
    the other three.
    """
    start = exhaust_port(bank, x)
    i, tx, _, _ = turbo_side(pair)
    mouth = collector_path(pair)[0]
    # Where on the mouth ring this pipe lands: its own bank's side of it, and
    # the nearer of that bank's two cylinders takes the upper slot. Four pipes
    # ending at one point on the axis is a node, not a merge, and it put the
    # last 40 mm of every primary inside the other three.
    same = sorted(c[3] for c in spec.cylinders()
                  if (0 if c[1] < 2 else 1) == i and c[2] == bank)
    near = min(same, key=lambda v: abs(v - tx))
    base = 150.0 if bank == 0 else 30.0
    a = math.radians(base if x == near else
                     (210.0 if bank == 0 else -30.0))
    rr = COLLECTOR_RADII[0] * 0.56
    end = (mouth[0], mouth[1] + rr * math.cos(a), mouth[2] + rr * math.sin(a))
    # Straight up out of the port on the port's own lateral station, then
    # over into the mouth. A primary that starts turning inboard as it leaves
    # the head arrives in the middle of the vee at the height of the
    # turbocharger, which is where the turbocharger is.
    #
    # The two pipes on a bank step apart in x as they climb: the cylinder
    # outboard of its turbo leans further out, the inboard one leans in. That
    # opens a 90 mm corridor between them at the turbo's own station, which
    # is exactly what the charge pipe leaving the compressor needs -- it is
    # 60 mm across and has to get from the middle of the vee to the outside
    # of the engine through the plane these two climb in.
    lean = -0.18 if abs(x) > abs(tx) else 0.14
    return [start,
            (x + (tx - x) * lean, start[1] * 1.07, T["z"] + 46.0),
            (x + (tx - x) * 0.58, start[1] * 1.00, T["z"] + 96.0),
            end]


def cylinder_path(bank, x):
    """Down the bore and back: intake port, into the chamber, out the exhaust
    port. Short, but it is the part of the path where the gas changes."""
    d = common.bank_dir(bank)
    deck = (x, d[1] * spec.DECK_HEIGHT, d[2] * spec.DECK_HEIGHT)
    mid = (x, d[1] * (spec.DECK_HEIGHT - spec.STROKE * 0.5),
           d[2] * (spec.DECK_HEIGHT - spec.STROKE * 0.5))
    return [intake_port(bank, x), deck, mid, deck, exhaust_port(bank, x)]


def turbo_side(bank_pair):
    """Which turbo, which way its compressor discharges, and which way round
    it sits on the engine.

    Turbo 0 is at x = -118 and feeds the left bank, turbo 1 at +118 feeds the
    right. `sgn` is the bank it discharges to: the compressor scroll has to
    open towards the plenum it feeds, or the charge pipe leaves the housing on
    the wrong side and crosses the vee to get back.

    `ib` is the direction from the turbo towards the middle of the engine, and
    the two turbos are mirror images about it. Both were laid out facing the
    same way down +x before, which put the front turbo's collector mouth at
    x = -214, 50 mm off the front of the block, and made the whole vee
    asymmetric for no reason.

    Turbines face outboard, compressors inboard. That is the way round the
    exhaust decides: a radial turbine discharges along its own axis, so
    turbines facing each other means one of them discharges forwards into the
    other's downpipe. Facing out, the rear turbo goes straight out of the back
    and the front one turns once, which is what a front-mounted turbo does on
    any car that has one. The compressors then breathe from the middle of the
    vee -- through ducts that climb out of it, because the vee itself is full
    of exhaust.
    """
    i = 0 if bank_pair < 2 else 1
    return i, T["x"][i], (-1.0 if i == 0 else 1.0), (1.0 if i == 0 else -1.0)


def turbine_scroll(bank_pair):
    """The turbine volute, as (point, passage radius) round the spiral.

    This is the shape of the housing and the line the gas runs down, returned
    once so they cannot disagree. An inflow turbine's passage tightens as it
    goes: area falls with the mass still to be delivered, so the gas keeps its
    velocity all the way round to the cutwater instead of stalling in a
    constant-section ring.
    """
    _, tx, _, ib = turbo_side(bank_pair)
    x = tx - ib * T["housing_w"] * 0.6
    r = T["turb_r"]
    out = []
    for k in range(13):
        f = k / 12.0
        # The passage centreline has to clear the wheel: at 0.62 r it ran
        # through the blade tips, so the volute and the turbine it wraps were
        # the same metal.
        a = math.radians(90.0 - 300.0 * f)
        rr = r * (0.98 - 0.26 * f)
        out.append(((x, rr * math.cos(a), T["z"] + rr * math.sin(a)),
                    21.0 - 11.0 * f))
    return out


def compressor_scroll(bank_pair):
    """The compressor volute, as (point, passage radius) round the spiral.

    The mirror image of the turbine in every sense: the passage grows as more
    flow joins it, and it grows towards the bank this turbo feeds.
    """
    _, tx, sgn, ib = turbo_side(bank_pair)
    x = tx + ib * T["housing_w"] * 0.6
    r = T["comp_r"]
    out = []
    for k in range(13):
        f = k / 12.0
        # 342 degrees, discharging down and outboard rather than straight
        # out sideways. Sideways put the volute's mouth 42 mm from the line
        # this bank's inboard primary climbs, and a 60 mm charge pipe needs
        # 46. Downward-and-out is where the room is, and it is a perfectly
        # ordinary way for a compressor housing to be clocked.
        a = math.radians(-120.0 + 342.0 * f)
        pas = 9.0 + 7.5 * f
        # The spiral has to clear the wheel it wraps. At 0.78 of comp_r the
        # passage's inner edge was at 36.2 and the wheel tip is at 38.3, so
        # the volute wall ran through the blades for the first third of the
        # wrap. A turbo has a running clearance there, not an interference.
        r_tip = r * T["comp_wheel_frac"]
        rr = max(r * (0.78 + 0.18 * f), r_tip + T["wheel_tip_clear"] + pas)
        out.append(((x, sgn * -rr * math.cos(a), T["z"] + rr * math.sin(a)),
                    pas))
    return out


def turbine_path(bank_pair):
    """Primary outlet, round the turbine scroll and out of the wheel.

    The exhaust used to stop at the turbine inlet and the boost used to start
    at the compressor outlet, so the gas arrived at the turbocharger, vanished,
    and reappeared on the other side of it. The energy recovery is the whole
    reason the turbo is there, and it was the one part of the path the air did
    not travel.

    The shaft lies along x: turbine housing inboard, compressor outboard,
    centre section between them.
    """
    _, tx, _, ib = turbo_side(bank_pair)
    hw = T["housing_w"] * 0.6
    pts = [collector_path(bank_pair)[-1]]
    pts.extend(p for (p, _r) in turbine_scroll(bank_pair))
    # and out along the shaft axis, which is where a turbine discharges
    pts.append((tx - ib * (hw + 18.0), 0.0, T["z"]))
    pts.append((tx - ib * (hw + 52.0), 0.0, T["z"]))
    return pts


def compressor_path(bank_pair):
    """Air in through the compressor eye, round the scroll and out."""
    _, tx, _, ib = turbo_side(bank_pair)
    hw = T["housing_w"] * 0.6
    # 60 mm out: the eye has to clear the collector's mouth flange, which
    # stands over the compressor, and the other turbo's inlet duct, which is
    # coming up the other side of the middle of the vee
    pts = [(tx + ib * (hw + 60.0), 0.0, T["z"]),
           (tx + ib * (hw + 26.0), 0.0, T["z"])]
    pts.extend(p for (p, _r) in compressor_scroll(bank_pair))
    return pts


def compressor_outlet(bank_pair):
    """Where the charge pipe has to start: the mouth of the scroll."""
    (p, _r) = compressor_scroll(bank_pair)[-1]
    return p



def boost_path(side):
    """Compressor outlet, along the charge pipe, through the cooler and into
    the plenum. `side` is -1 for the left bank's cooler, +1 for the right."""
    tx = T["x"][0 if side < 0 else 1]
    hw = T["housing_w"] * 0.6
    # From the volute's actual mouth. The first point used to be at
    # +comp_r*0.92 whichever side the scroll discharged to, so on one bank the
    # pipe left the housing on the wrong side and crossed the vee centreline
    # to get back -- through the MGU-H, which is a 64 mm rotor sitting on the
    # shaft exactly there.
    return [compressor_outlet(0 if side < 0 else 2),
            (tx + hw * 0.4, side * 70.0, T["z"] - 18.0),
            (tx, side * 118.0, 216.0),
            (-152.0, side * 150.0, 250.0),
            (152.0, side * 150.0, 250.0),
            (120.0, side * 120.0, 300.0),
            (140.0, side * 50.0, 316.0),
            (140.0, 0.0, I["plenum_z"])]


def tailpipe_path(side):
    """Turbine outlet to the back of the tailpipe."""
    tx = T["x"][0 if side < 0 else 1]
    hw = T["housing_w"] * 0.6
    return [(tx - hw - 52.0, 0.0, T["z"]),
            (tx - hw - 90.0, side * 44.0, T["z"] - 26.0),
            (tx + 40.0, side * 70.0, T["z"] - 48.0),
            (300.0, side * 78.0, 150.0)]


def valve_windows():
    """(intake_open, intake_close, exhaust_open, exhaust_close) in degrees of
    a 720-degree cycle, 0 at firing TDC."""
    C = spec.CAM
    ic = 360.0 + C["lobe_centre_in"]
    ec = 360.0 - C["lobe_centre_ex"]
    return {
        "intake": [(ic - C["duration_in"] / 2) % 720.0,
                   (ic + C["duration_in"] / 2) % 720.0],
        "exhaust": [(ec - C["duration_ex"] / 2) % 720.0,
                    (ec + C["duration_ex"] / 2) % 720.0],
    }


def build():
    """Everything the viewer needs to draw the gas path."""
    order = spec.FIRING_ORDER
    cyls = []
    for (n, pair, bank, x, _a) in spec.cylinders():
        cyls.append({
            "n": n,
            "bank": bank,
            # degrees after this cylinder's own firing TDC at crank zero
            "phase": 90.0 * order.index(n),
            "intake": [list(p) for p in runner_path(bank, x)],
            "chamber": [list(p) for p in cylinder_path(bank, x)],
            "exhaust": [list(p) for p in primary_path(pair, bank, x)],
        })
    return {
        "cylinders": cyls,
        "turbine": [[list(p) for p in turbine_path(0)],
                    [list(p) for p in turbine_path(2)]],
        "compressor": [[list(p) for p in compressor_path(0)],
                       [list(p) for p in compressor_path(2)]],
        "boost": [[list(p) for p in boost_path(-1)],
                  [list(p) for p in boost_path(1)]],
        "tailpipe": [[list(p) for p in tailpipe_path(-1)],
                     [list(p) for p in tailpipe_path(1)]],
        "timing": valve_windows(),
        "firing_interval": 720.0 / spec.N_CYL,
    }

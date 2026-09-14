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


def primary_path(pair, bank, x):
    """Exhaust port out into the vee and forward into the turbine inlet."""
    start = exhaust_port(bank, x)
    tx = T["x"][0 if pair < 2 else 1]
    # into the top of the volute, at its outer radius. Ending on the
    # turbine's axis ends inside the turbine wheel, which is 41 mm across
    # and exactly there.
    return [start,
            (x + (tx - x) * 0.22, start[1] * 0.72, start[2] + 26.0),
            (x + (tx - x) * 0.40, start[1] * 0.62, T["z"] + 52.0),
            (tx - T["housing_w"] * 0.7, 0.0, T["z"] + T["turb_r"] * 0.95)]


def cylinder_path(bank, x):
    """Down the bore and back: intake port, into the chamber, out the exhaust
    port. Short, but it is the part of the path where the gas changes."""
    d = common.bank_dir(bank)
    deck = (x, d[1] * spec.DECK_HEIGHT, d[2] * spec.DECK_HEIGHT)
    mid = (x, d[1] * (spec.DECK_HEIGHT - spec.STROKE * 0.5),
           d[2] * (spec.DECK_HEIGHT - spec.STROKE * 0.5))
    return [intake_port(bank, x), deck, mid, deck, exhaust_port(bank, x)]


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
    tx = T["x"][0 if bank_pair < 2 else 1]
    hw = T["housing_w"] * 0.6
    zc = T["z"]
    r = T["turb_r"]
    pts = [(tx - 46.0, 0.0, zc + 16.0)]
    # round the volute, tightening as it feeds the wheel
    for k in range(7):
        f = k / 6.0
        a = math.radians(90.0 - 300.0 * f)
        rr = r * (0.92 - 0.46 * f)
        pts.append((tx - hw, rr * math.cos(a), zc + rr * math.sin(a)))
    # and out along the shaft axis, which is where a turbine discharges
    pts.append((tx - hw - 18.0, 0.0, zc))
    pts.append((tx - hw - 52.0, 0.0, zc))
    return pts


def compressor_path(bank_pair):
    """Air in through the compressor eye, round the scroll and out."""
    tx = T["x"][0 if bank_pair < 2 else 1]
    hw = T["housing_w"] * 0.6
    zc = T["z"]
    r = T["comp_r"]
    pts = [(tx + hw + 96.0, 0.0, zc), (tx + hw + 26.0, 0.0, zc)]
    for k in range(7):
        f = k / 6.0
        a = math.radians(-120.0 + 300.0 * f)
        rr = r * (0.34 + 0.58 * f)
        pts.append((tx + hw, rr * math.cos(a), zc + rr * math.sin(a)))
    return pts


def boost_path(side):
    """Compressor outlet, along the charge pipe, through the cooler and into
    the plenum. `side` is -1 for the left bank's cooler, +1 for the right."""
    tx = T["x"][0 if side < 0 else 1]
    hw = T["housing_w"] * 0.6
    return [(tx + hw, T["comp_r"] * 0.92, T["z"]),
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

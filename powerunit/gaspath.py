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
    d, lat = common.bank_dir(bank), common.bank_lat(bank)
    return (x,
            d[1] * (spec.DECK_HEIGHT + 30.0) + lat[1] * -50.0,
            d[2] * (spec.DECK_HEIGHT + 30.0) + lat[2] * -50.0)


def exhaust_port(bank, x):
    """Centre of the exhaust port face -- inboard, because the turbos sit in
    the vee."""
    d, lat = common.bank_dir(bank), common.bank_lat(bank)
    return (x,
            d[1] * (spec.DECK_HEIGHT + 34.0) + lat[1] * 44.0,
            d[2] * (spec.DECK_HEIGHT + 34.0) + lat[2] * 44.0)


def runner_path(bank, x):
    """Plenum bellmouth down to the intake port. Ordered along the flow, so
    the last point is the port."""
    port = intake_port(bank, x)
    top = (x, port[1] * 0.30, I["plenum_z"] - 26.0)
    return [(top[0], top[1] * 0.9, top[2] + 14.0),
            top,
            ((port[0] + top[0]) / 2, port[1] * 0.74, port[2] + 46.0),
            port]


def primary_path(pair, bank, x):
    """Exhaust port out into the vee and forward into the turbine inlet."""
    start = exhaust_port(bank, x)
    tx = T["x"][0 if pair < 2 else 1]
    return [start,
            (x + (tx - x) * 0.22, start[1] * 0.72, start[2] + 26.0),
            (x + (tx - x) * 0.58, start[1] * 0.34, T["z"] + 42.0),
            (tx - 46.0, 0.0, T["z"] + 16.0)]


def cylinder_path(bank, x):
    """Down the bore and back: intake port, into the chamber, out the exhaust
    port. Short, but it is the part of the path where the gas changes."""
    d = common.bank_dir(bank)
    deck = (x, d[1] * spec.DECK_HEIGHT, d[2] * spec.DECK_HEIGHT)
    mid = (x, d[1] * (spec.DECK_HEIGHT - spec.STROKE * 0.5),
           d[2] * (spec.DECK_HEIGHT - spec.STROKE * 0.5))
    return [intake_port(bank, x), deck, mid, deck, exhaust_port(bank, x)]


def boost_path(side):
    """Compressor outlet, along the charge pipe, through the cooler and into
    the plenum. `side` is -1 for the left bank's cooler, +1 for the right."""
    tx = T["x"][0 if side < 0 else 1]
    return [(tx, side * 70.0, T["z"] - 18.0),
            (tx, side * 118.0, 216.0),
            (-152.0, side * 150.0, 250.0),
            (152.0, side * 150.0, 250.0),
            (120.0, side * 120.0, 300.0),
            (140.0, side * 50.0, 316.0),
            (140.0, 0.0, I["plenum_z"])]


def tailpipe_path(side):
    """Turbine outlet to the back of the tailpipe."""
    tx = T["x"][0 if side < 0 else 1]
    return [(tx + 30.0, side * 40.0, T["z"] - 10.0),
            (tx + 90.0, side * 60.0, T["z"] - 40.0),
            (300.0, side * 70.0, 150.0)]


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
        "boost": [[list(p) for p in boost_path(-1)],
                  [list(p) for p in boost_path(1)]],
        "tailpipe": [[list(p) for p in tailpipe_path(-1)],
                     [list(p) for p in tailpipe_path(1)]],
        "timing": valve_windows(),
        "firing_interval": 720.0 / spec.N_CYL,
    }

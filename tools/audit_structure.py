"""Structural audit for the hypercar. See tools/_structure.py for the checks.

    python3 tools/audit_structure.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _structure as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CFG = {
    "gap_mm": 0.5,
    "exempt_attached": {},

    "mirror_tol_mm": 1.0,
    "exempt_mirror": {
        # the engine inside the car is a V8, and a V8's banks are offset
        # along the crank rather than mirrored
        "engine": "the power unit is a V8 with offset banks",
    },

    "distinct_tol_mm": 0.5,
    "exempt_distinct": {},
    "exempt_shape": {},

    # Joints that have to close. Both driveshafts used to stop 80 mm short of
    # their hubs while still touching the gearbox, so the generic "is this
    # part attached to anything" test passed them both.
    "joins": (
        ("driveshaft_rl", "upright_rl"), ("driveshaft_rr", "upright_rr"),
        ("driveshaft_rl", "gearbox"), ("driveshaft_rr", "gearbox"),
        ("pushrod_fl", "rocker_fl"), ("pushrod_fr", "rocker_fr"),
        ("pushrod_rl", "rocker_rl"), ("pushrod_rr", "rocker_rr"),
        ("trackrod_fl", "upright_fl"), ("trackrod_fr", "upright_fr"),
        ("trackrod_fl", "steering_rack"), ("trackrod_fr", "steering_rack"),
        ("steering_column", "steering_rack"),
        ("steering", "steering_column"),
        ("wishbone_fl_upper_fwd", "upright_fl"),
        ("wishbone_rr_lower_aft", "upright_rr"),
        ("rear_wing_main", "rear_pylon_l"),
        ("rear_wing_main", "rear_endplate_l"),
        ("front_wing_main", "front_endplate_l"),
        ("engine", "gearbox"),
        # he has to be holding the wheel and reaching the pedals
        ("driver", "steering"),
        ("driver", "pedal_box"),
        ("driver", "seat"),
        ("helmet", "driver"),
    ),

    # Things a car has exactly one of. The cockpit had two steering wheels,
    # 30 mm apart, built by chassis.py and systems.py independently; both
    # passed every geometric check there was.
    "singletons": {
        "steering wheel": (("steering", "steering_wheel", "wheel_display"), 1),
        "driver": (("driver",), 1),
        "gearbox": (("gearbox",), 1),
        "engine": (("engine",), 1),
        "floor panel": (("floor_surface",), 1),
        "plank": (("floor_plank",), 1),
        "halo": (("halo",), 1),
        "rear wing mainplane": (("rear_wing_main",), 1),
        "front wing mainplane": (("front_wing_main",), 1),
        "steering rack": (("steering_rack",), 1),
        "steering column": (("steering_column",), 1),

        # Counts, not just ones-of. The rear lower wishbones' aft legs were
        # named by the sign of their pickup offset -- `"fwd" if dx < 0 else
        # "aft"` -- so moving that pickup forward of the axle called both
        # legs `fwd` and the second overwrote the first. Two structural
        # members left the car and the only thing that noticed was the part
        # count in the manifest. `joins` names one of the sixteen legs, so
        # it would have caught that one; this catches any of them.
        "wishbone legs": (("wishbone_*",), 16),
        "uprights": (("upright_*",), 4),
        "toe and track rods": (("trackrod_*",), 4),
        "push/pull rods": (("pushrod_*", "pullrod_*"), 4),
        "rockers": (("rocker_*",), 4),
        "driveshafts": (("driveshaft_*",), 2),
        "rims": (("rim_*",), 4),
        "tyres": (("tyre_f*", "tyre_r*"), 4),
    },

}

if __name__ == "__main__":
    n = S.report(os.path.join(ROOT, "build", "parts.csv"), CFG, "Hypercar")
    sys.exit(0 if n == 0 else 1)

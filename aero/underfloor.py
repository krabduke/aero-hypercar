"""Three estimates of the floor's ClA, and the fan's share.

spec.AERO["cla_floor"] = 3.35 is 57 per cent of this car's downforce and it
has never been computed by anything. There is no CFD on this machine, so this
does not compute the truth: it bounds it, from three independent models whose
assumptions are stated, and it reports the spread between them as the
uncertainty rather than hiding it inside a single number.

Two earlier attempts failed for instructive reasons. A two-dimensional panel
solve put a stagnation point at the diffuser exit: it treats the underbody as
the OUTSIDE of a closed body in ground effect, so the Kutta condition at a
blunt base picked an arbitrary circulation and the flow stopped at the exit
instead of discharging. A one-dimensional duct solve then drove 195 m/s
through a 22 mm gap, because it treated the underfloor as a rigid duct with
the freestream's full mass flow forced through it. Neither failure is
surprising in hindsight. A ground-effect underfloor is not 2-D and it is not a
duct: it is an open channel that leaks around its edges, its walls carry
boundary layers that block a large fraction of a 22 mm throat, and its inlet
does not recover the freestream total pressure.

Agreement is a check, not a calibration target. Shared continuity assumptions
cannot make two reduced-order models independent evidence, and an unsourced
empirical estimate cannot validate either one. The fan needs its own leakage
and power balance, including a zero-road-speed result.

    python3 aero/underfloor.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec                                            # noqa: E402
from parts import floor as fl                          # noqa: E402

MM = 0.001
RHO = 1.225
NU = 1.45e-5            # air, 15 deg C, m2/s
F = spec.FLOOR
FAN = spec.FAN

V = 250 / 3.6           # 250 km/h reference speed for the Bernoulli models
Q = 0.5 * RHO * V * V
G = 9.81


# --------------------------------------------------------------------------
# 1. quasi-1-D channel with displacement thickness and an inlet Cd
# --------------------------------------------------------------------------

def height(x, entry=None):
    """Underfloor height at x, in mm -- the same roof line the floor is
    built to, so the model and the geometry cannot disagree."""
    e = F["entry_z"] if entry is None else entry
    if x <= F["throat_x"]:
        f = (x - F["x0"]) / (F["throat_x"] - F["x0"])
        return e - (e - F["throat_z"]) * f ** 1.3 + 18.0
    if x <= F["diffuser_x"]:
        return F["throat_z"] + 18.0
    f = (x - F["diffuser_x"]) / (F["x1"] - F["diffuser_x"])
    return (F["throat_z"] + 18.0
            + (F["diffuser_exit_z"] - F["throat_z"]) * f ** 1.25)

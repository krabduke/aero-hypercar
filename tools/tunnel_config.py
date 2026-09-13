"""Emit the wind-tunnel configuration the browser solver runs on.

The lattice is built from the same spec.py as the geometry and aero/analyse.py,
so the number on the web page and the number from `make aero` describe the same
car. The browser runs a coarser lattice because it has to re-solve while a
slider moves; tools/validate_js.mjs checks what that costs.

The car is solved in ground effect -- the track is made an exact streamline by
mirroring the vortex system in it -- which is most of the point.
"""

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))

import spec

MM = 0.001

FRONT_NS, FRONT_NC = 8, 3
REAR_NS, REAR_NC = 8, 3
BEAM_NS, BEAM_NC = 6, 2


def rear_element(k):
    RW = spec.REAR_WING
    chord = RW["chord"] * (1.0 - 0.42 * k)
    x = RW["x"] + k * RW["chord"] * 0.46
    z = RW["z"] + k * (RW["gap"] + 26.0)
    aoa = RW["aoa"] + k * 12.0
    return x, z, chord, aoa


def config():
    FW, RW, BW = spec.FRONT_WING, spec.REAR_WING, spec.BEAM_WING
    half = FW["span"] / 2
    neutral = FW["neutral_half_w"]
    surfaces = []

    # Front wing. Each element is its own surface: they sit at different
    # heights and incidences, and the mainplane is fixed while the flaps move.
    for k, (dx, dz, c_r, c_t, span_f, aoa_r, aoa_t, rise) in enumerate(
            FW["stack"]):
        tip = half * span_f
        z_root = FW["z"] + dz + (FW["arch"] if k == 0 else 0.0)
        s = {
            "name": f"front_{k}",
            "le_root": [(FW["x"] + dx) * MM, 0.0, z_root * MM],
            "c_root": c_r * MM,
            "le_tip": [(FW["x"] + dx) * MM, tip * MM, (FW["z"] + dz + rise) * MM],
            "c_tip": c_t * MM,
            "n_span": FRONT_NS, "n_chord": FRONT_NC,
            # the outboard wash-in is the wing's own twist
            "twist_root": -aoa_r, "twist_tip": -aoa_t,
        }
        if k > 0:
            # The flaps trim together; the mainplane does not move. Sign is
            # set so that a positive slider adds downforce, checked against
            # the solve rather than reasoned about -- see the range note.
            s["control"] = "front_flap"
            s["control_tau"] = 1.0          # the whole element rotates
            s["control_sign"] = 1.0
        surfaces.append(s)

    for k in range(RW["elements"]):
        x, z, chord, aoa = rear_element(k)
        s = {
            "name": f"rear_{k}",
            "le_root": [x * MM, 0.0, z * MM], "c_root": chord * MM,
            "le_tip": [x * MM, RW["span"] / 2 * MM, z * MM],
            "c_tip": chord * 0.95 * MM,
            "n_span": REAR_NS, "n_chord": REAR_NC,
            "twist_root": -aoa, "twist_tip": -aoa,
        }
        if k == 1:
            # the DRS element: it opens, shedding downforce and drag
            s["control"] = "drs"
            s["control_tau"] = 1.0
            s["control_sign"] = 1.0
        surfaces.append(s)

    for k in range(BW["elements"]):
        chord = BW["chord"] * (1.0 - 0.30 * k)
        x = BW["x"] + k * BW["chord"] * 0.5
        z = BW["z"] + k * 40.0
        surfaces.append({
            "name": f"beam_{k}",
            "le_root": [x * MM, 0.0, z * MM], "c_root": chord * MM,
            "le_tip": [x * MM, BW["span"] / 2 * MM, z * MM],
            "c_tip": chord * 0.92 * MM,
            "n_span": BEAM_NS, "n_chord": BEAM_NC,
            "twist_root": -BW["aoa"], "twist_tip": -BW["aoa"],
        })

    s_ref = 0.0
    for s in surfaces:
        span = abs(s["le_tip"][1] - s["le_root"][1])
        s_ref += 2.0 * span * 0.5 * (s["c_root"] + s["c_tip"])

    return {
        "units": "m",
        "kind": "car",
        "s_ref": s_ref,
        "c_ref": FW["chord"] * MM,
        "b_ref": FW["span"] * MM,
        "x_le_mac": FW["x"] * MM,
        "mass_kg": spec.MASS_KG,
        "v_default": 250 / 3.6, "v_min": 40 / 3.6, "v_max": 360 / 3.6,
        "v_unit": "km/h",
        "alpha_default": 0.0, "alpha_min": -2.0, "alpha_max": 3.0,
        # a car yaws in a crosswind and in a corner, and the balance
        # moves when it does
        "beta_default": 0.0, "beta_min": -10.0, "beta_max": 10.0,
        "stall_alpha": 99.0,
        "ground": True,
        "cg_frac": 0.0,
        "front_surfaces": ["front_0", "front_1", "front_2", "front_3"],
        "fan_kg": spec.FAN["downforce_kg"],
        "controls": [
            # Trim range only, and deliberately narrow. The stack already
            # runs to 34 degrees at the tip of the top flap, and a flat-panel
            # lattice stops being linear well before that: swept wider, the
            # response turns over and adding flap starts taking downforce off.
            # Plus or minus a few degrees is the real adjustment anyway.
            {"id": "front_flap", "label": "Front flap trim", "unit": "deg",
             "min": -4.0, "max": 5.0, "value": 0.0, "baked": 0.0,
             "objects": ["front_flap_1", "front_flap_2", "front_flap_3"],
             "sign": [1.0, 1.0, 1.0]},
            {"id": "drs", "label": "DRS / rear flap", "unit": "deg",
             "min": 0.0, "max": 28.0, "value": 0.0, "baked": 0.0,
             "objects": ["rear_flap"], "sign": [1.0]},
        ],
        "surfaces": surfaces,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(config(), indent=1))

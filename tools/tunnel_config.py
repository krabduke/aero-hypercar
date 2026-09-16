"""Emit the wind-tunnel configuration the browser solver runs on.

The lattice is built from the same spec.py as the geometry and aero/analyse.py,
so the number on the web page and the number from `make aero` describe the same
car. The browser runs a coarser lattice because it has to re-solve while a
slider moves; tools/validate_js.mjs checks what that costs.

The car is solved in ground effect -- the track is made an exact streamline by
mirroring the vortex system in it -- which is most of the point.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))

import spec

MM = 0.001

FRONT_NS, FRONT_NC = 8, 3
REAR_NS, REAR_NC = 8, 3
BEAM_NS, BEAM_NC = 6, 2



def _chord_line(s, f, frac):
    """A point on surface `s`'s chord line, at spanwise fraction f."""
    le = [s["le_root"][i] + (s["le_tip"][i] - s["le_root"][i]) * f
          for i in range(3)]
    c = s["c_root"] + (s["c_tip"] - s["c_root"]) * f
    tw = math.radians(s["twist_root"]
                      + (s["twist_tip"] - s["twist_root"]) * f)
    d = (frac - 0.25) * c
    return le[0] + 0.25 * c + d * math.cos(tw), le[2] - d * math.sin(tw)


def check_slots(surfaces, min_frac=0.02):
    """Refuse to emit a lattice whose surfaces are on top of each other.

    A vortex lattice is a set of infinitely thin sheets. Two of them a
    millimetre apart -- or crossing -- give an influence matrix that is
    near-singular in a way nothing downstream announces: the solve still
    returns, the lift is roughly right because the enormous equal-and-opposite
    circulations cancel to first order, and the induced drag, which is
    quadratic, comes out at forty times the real figure.

    That is exactly what the rear wing did. So measure the closest approach
    between every pair of chord lines and refuse anything under 2 % of chord,
    which is about the tightest slot gap a real multi-element wing runs.
    """
    def seg_dist(p, a, b):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-18 else max(0.0, min(
            1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
        return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dz))

    bad = []
    for i in range(len(surfaces)):
        for j in range(i + 1, len(surfaces)):
            A, B = surfaces[i], surfaces[j]
            worst, at = 1e9, 0.0
            for k in range(9):
                f = k / 8.0
                a0, a1 = _chord_line(A, f, 0.0), _chord_line(A, f, 1.0)
                b0, b1 = _chord_line(B, f, 0.0), _chord_line(B, f, 1.0)
                d = min([seg_dist(_chord_line(A, f, m / 20.0), b0, b1)
                         for m in range(21)]
                        + [seg_dist(_chord_line(B, f, m / 20.0), a0, a1)
                           for m in range(21)])
                if d < worst:
                    worst, at = d, f
            ref = 0.5 * (A["c_root"] + B["c_root"])
            if worst < min_frac * ref:
                bad.append((A["name"], B["name"], worst, worst / ref, at))
    if bad:
        lines = [f"    {a}/{b}: {d*1000:.1f} mm ({r*100:.1f} % of chord) "
                 f"at span fraction {f:.2f}" for a, b, d, r, f in bad]
        raise SystemExit(
            "lifting surfaces closer than "
            f"{min_frac*100:.0f} % of chord -- the lattice cannot resolve "
            "this and will not say so:\n" + "\n".join(lines))


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
        # the whole stack follows the nose -- see the note in car/parts/wings
        z_root = FW["z"] + dz + FW["arch"]
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
            # The flaps trim together; the mainplane does not move. Negative,
            # because the surface carries twist = -aoa: a positive slider has
            # to make the twist more negative to add incidence, and so
            # downforce. It read +1 while the mesh had its incidence the wrong
            # way round, and adding front flap took downforce off the front.
            s["control"] = "front_flap"
            s["control_tau"] = 1.0          # the whole element rotates
            s["control_sign"] = -1.0
        surfaces.append(s)

    for k, (x, z, chord, aoa) in enumerate(spec.rear_elements()):
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

    for k, (x, z, chord, aoa) in enumerate(spec.beam_elements()):
        surfaces.append({
            "name": f"beam_{k}",
            "le_root": [x * MM, 0.0, z * MM], "c_root": chord * MM,
            "le_tip": [x * MM, BW["span"] / 2 * MM, z * MM],
            "c_tip": chord * 0.92 * MM,
            "n_span": BEAM_NS, "n_chord": BEAM_NC,
            "twist_root": -aoa, "twist_tip": -aoa,
        })

    check_slots(surfaces)

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
        # The sealed floor's plan area, and the two numbers the underbody's
        # downforce is worked out from. The fan's pressure rise is its stated
        # downforce spread over that area -- 650 kg over 5.54 m2 is 1151 Pa --
        # and that is what lets the fan be compared with what the tunnels do
        # on their own, which is the comparison that was never made.
        "floor_plan_m2": round(((spec.FLOOR["x1"] - spec.FLOOR["x0"])
                                * 2 * spec.FLOOR["half_w"]) * MM * MM, 4),
        "cla_floor": spec.AERO["cla_floor"],
        "controls": [
            # Trim range only, and deliberately narrow. The stack already
            # runs to 34 degrees at the tip of the top flap, and a flat-panel
            # lattice stops being linear well before that: swept wider, the
            # response turns over and adding flap starts taking downforce off.
            # Plus or minus a few degrees is the real adjustment anyway.
            # Negative for the same reason as control_sign above: the viewer
            # turns a spanwise hinge by -ang*sign about three's z, which takes
            # the trailing edge DOWN for a positive sign. Adding front flap
            # has to take it up.
            {"id": "front_flap", "label": "Front flap trim", "unit": "deg",
             "min": -4.0, "max": 5.0, "value": 0.0, "baked": 0.0,
             "objects": ["front_flap_1", "front_flap_2", "front_flap_3"],
             "sign": [-1.0, -1.0, -1.0]},
            {"id": "drs", "label": "DRS / rear flap", "unit": "deg",
             "min": 0.0, "max": 28.0, "value": 0.0, "baked": 0.0,
             "objects": ["rear_flap"], "sign": [1.0]},
        ],
        "surfaces": surfaces,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(config(), indent=1))

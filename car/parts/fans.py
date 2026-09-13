"""The fans. This is the part that makes the car what it is.

Two electrically driven fans pull air out of the sealed underfloor plenums.
Because they move a roughly fixed mass flow, the suction they generate barely
depends on road speed -- so unlike a wing, they still work in a hairpin.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh

F = spec.FAN


def build():
    out = {}
    ducts, rotors, motors = [], [], []
    for sgn in (-1.0, 1.0):
        cx, cy, cz = F["x"], sgn * F["y"], F["z"]

        # shroud
        v, f = mesh.tube(-70.0, 70.0, F["duct_r"] - 22.0, F["duct_r"], 36)
        v = [(pz + cx, py + cy, px + cz) for (px, py, pz) in v]
        ducts.append((v, f))

        # plenum throat feeding the fan from the tunnels
        z_in = F["plenum_z0"]
        ducts.append(mesh.pipe([(cx - 620.0, cy * 0.55, z_in),
                                (cx - 260.0, cy * 0.85, z_in + 100.0),
                                (cx - 60.0, cy, cz - 30.0)],
                               F["plenum_r"], 16))

        # hub and blades
        hv, hf = mesh.tube(-60.0, 60.0, 0.0, 74.0, 24)
        hv = [(pz + cx, py + cy, px + cz) for (px, py, pz) in hv]
        rotors.append((hv, hf))
        for k in range(F["blades"]):
            a = 2 * math.pi * k / F["blades"]
            bv, bf = mesh.box(0.0, 0.0, (74.0 + F["duct_r"] - 26.0) / 2,
                              78.0, 15.0, F["duct_r"] - 26.0 - 74.0)
            # pitch the blade, then set it round the hub
            pitch = math.radians(32.0)
            bv = [(px * math.cos(pitch) - py * math.sin(pitch),
                   px * math.sin(pitch) + py * math.cos(pitch), pz)
                  for (px, py, pz) in bv]
            bv = [(px, py * math.cos(a) - pz * math.sin(a),
                   py * math.sin(a) + pz * math.cos(a)) for (px, py, pz) in bv]
            bv = [(px + cx, py + cy, pz + cz) for (px, py, pz) in bv]
            rotors.append((bv, bf))

        mv, mf = mesh.tube(-54.0, 54.0, 0.0, 62.0, 22)
        mv = [(pz + cx + 110.0, py + cy, px + cz) for (px, py, pz) in mv]
        motors.append((mv, mf))

    out["fanduct"] = mesh.join(*ducts)
    out["fan_rotors"] = mesh.join(*rotors)
    out["fan_motors"] = mesh.join(*motors)
    return out

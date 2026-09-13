"""Cylinder heads, camshafts, valves, cam covers, injectors and coils."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

H = spec.HEAD
V = spec.VALVE
CM = spec.CAM
SEG = spec.RES["revolve"]
SM = spec.RES["small_revolve"]


def build():
    out = {}
    out.update(_heads())
    out.update(_valves())
    out.update(_cams())
    out.update(_covers())
    out.update(_ignition())
    return out


def _heads():
    out = {}
    for bank in (0, 1):
        a = spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        v, f = mesh.box(0.0, 8.0, spec.DECK_HEIGHT + H["height"] / 2,
                        H["x_rear"] - H["x_front"], H["half_width"] * 2, H["height"])
        v = [(x, y * ca - z * sa, y * sa + z * ca) for (x, y, z) in v]
        # the box was built about the world origin; rotate then it already sits
        # on the bank axis because its centre was placed along +z
        out[f"head_{'lr'[bank]}"] = (v, f)
    return out


def _valves():
    """Four valves per cylinder in a narrow pent-roof, splayed by the included
    angle about the bore axis."""
    parts = []
    inc = math.radians(V["included_angle"] / 2)
    for (n, pair, bank, x, a) in spec.cylinders():
        for k, (is_in, sgn_x, sgn_y) in enumerate((
                (True,  -1, -1), (True,  -1, 1),
                (False,  1, -1), (False,  1, 1))):
            hr = V["intake_head_r"] if is_in else V["exhaust_head_r"]
            prof = [(0.0, 0.0), (0.0, hr), (-5.0, hr * 0.82), (-8.0, V["stem_r"]),
                    (-V["length"], V["stem_r"]), (-V["length"], 0.0)]
            vv, vf = mesh.revolve_open(prof, SM, cap_start=True, cap_end=True)
            # tilt by the included angle, then offset within the bore
            tilt = inc * (1 if is_in else -1)
            vv = [(px * math.cos(tilt) - py * math.sin(tilt),
                   px * math.sin(tilt) + py * math.cos(tilt), pz) for (px, py, pz) in vv]
            off_lat = sgn_y * (hr * 0.92)
            vv = [(px, py, pz + sgn_x * 0.0) for (px, py, pz) in vv]
            vv = common.along_bank(vv, x + sgn_y * hr * 0.95,
                                   spec.DECK_HEIGHT - 1.0, bank, off_lat * 0.0)
            parts.append((vv, vf))
    return {"valves": mesh.join(*parts)}


def _cams():
    """Four camshafts, one pair per bank, with a lobe per valve."""
    parts = []
    for bank in (0, 1):
        for side in (-1, 1):
            lat = side * H["cam_centres"] / 2
            cv, cf = mesh.tube(H["x_front"], H["x_rear"], 0.0, CM["journal_r"], SM)
            cv = [(z, y, px) for (px, y, z) in cv]
            cv = common.along_bank(cv, 0.0, spec.DECK_HEIGHT + H["cam_height"],
                                   bank, lat)
            parts.append((cv, cf))
            for (n, pair, bank2, x, a) in spec.cylinders():
                if bank2 != bank:
                    continue
                for dx in (-CM["lobe_w"] * 1.2, CM["lobe_w"] * 1.2):
                    lv, lf = mesh.revolve_closed(
                        [(-CM["lobe_w"] / 2, 0.0), (CM["lobe_w"] / 2, 0.0),
                         (CM["lobe_w"] / 2, CM["base_r"]),
                         (-CM["lobe_w"] / 2, CM["base_r"])], 24)
                    lv = [(z, y, px) for (px, y, z) in lv]
                    lv = common.along_bank(lv, x + dx,
                                           spec.DECK_HEIGHT + H["cam_height"], bank, lat)
                    parts.append((lv, lf))
    return {"camshafts": mesh.join(*parts)}


def _covers():
    out = {}
    for bank in (0, 1):
        a = spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        z = spec.DECK_HEIGHT + H["height"] + 20.0
        v, f = mesh.box(0.0, 8.0, z, H["x_rear"] - H["x_front"] - 14.0,
                        H["half_width"] * 1.78, 40.0)
        v = [(x, y * ca - zz * sa, y * sa + zz * ca) for (x, y, zz) in v]
        out[f"camcover_{'lr'[bank]}"] = (v, f)
    return out


def _ignition():
    """One direct injector and one coil per cylinder, entering the head."""
    inj, coils = [], []
    for (n, pair, bank, x, a) in spec.cylinders():
        iv, if_ = mesh.cylinder(0.0, 62.0, 7.0, 12)
        iv = [(z, y, px) for (px, y, z) in iv]
        iv = common.along_bank(iv, x, spec.DECK_HEIGHT + 6.0, bank,
                               spec.BORE * 0.40)
        inj.append((iv, if_))
        cv, cf = mesh.cylinder(0.0, 74.0, 11.0, 12)
        cv = [(z, y, px) for (px, y, z) in cv]
        cv = common.along_bank(cv, x, spec.DECK_HEIGHT + 10.0, bank, 0.0)
        coils.append((cv, cf))
    return {"injectors": mesh.join(*inj), "coils": mesh.join(*coils)}

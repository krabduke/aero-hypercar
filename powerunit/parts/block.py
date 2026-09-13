"""Cylinder block, bedplate, cylinder liners, sump."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

B = spec.BLOCK
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_banks())
    out.update(_liners())
    out.update(_crankcase())
    out.update(_bedplate())
    out.update(_sump())
    return out


def _banks():
    """Each bank is a slab standing on the crankcase at the bank angle, with
    the deck face at the top. Bores are cut through it by the liners."""
    out = {}
    for bank in (0, 1):
        along0 = spec.DECK_HEIGHT - B["vee_depth"]
        along1 = spec.DECK_HEIGHT
        half_len = (B["x_rear"] - B["x_front"]) / 2
        w = B["bank_half_width"]
        v, f = mesh.box(0.0, 0.0, (along0 + along1) / 2,
                        B["x_rear"] - B["x_front"], w * 2, along1 - along0)
        # push the slab a little outboard so the two banks leave a vee valley
        # between them for the turbos, instead of merging into one lump
        v = [(px, py + 8.0, pz) for (px, py, pz) in v]
        # box is built in world axes; rotate it onto the bank
        a = spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        v = [(x, y * ca - z * sa, y * sa + z * ca) for (x, y, z) in v]
        out[f"block_bank_{'lr'[bank]}"] = (v, f)
    return out


def _liners():
    """Wet liners: the actual bores the pistons run in."""
    parts = []
    r = spec.BORE / 2
    for (n, pair, bank, x, a) in spec.cylinders():
        along0 = spec.DECK_HEIGHT - B["vee_depth"] + 8.0
        v, f = common.bore_tube(x, along0, spec.DECK_HEIGHT, r, r + 5.5, bank)
        parts.append((v, f))
    return {"block_liners": mesh.join(*parts)}


def _crankcase():
    """The crankcase skirt below the vee, carrying the main bearing webs."""
    parts = []
    x0, x1 = B["x_front"], B["x_rear"]
    hw = B["half_width"] * 0.86
    parts.append(mesh.box(0.0, 0.0, -B["skirt_depth"] / 2 + 14.0,
                          x1 - x0, hw * 2, B["skirt_depth"] + 28.0))
    # main bearing webs
    span = (spec.CRANK["n_mains"] - 1)
    for i in range(spec.CRANK["n_mains"]):
        x = x0 + 26.0 + (x1 - x0 - 52.0) * i / span
        parts.append(mesh.box(x, 0.0, -B["skirt_depth"] * 0.30,
                              B["main_web_t"], hw * 1.9, B["skirt_depth"] * 1.1))
    return {"block_crankcase": mesh.join(*parts)}


def _bedplate():
    """Bedplate rather than individual main caps -- one stiff casting that ties
    all five mains together, which is what lets the block be a stressed member."""
    parts = []
    x0, x1 = B["x_front"], B["x_rear"]
    hw = B["half_width"] * 0.80
    z = -B["skirt_depth"]
    parts.append(mesh.box(0.0, 0.0, z - 11.0, x1 - x0, hw * 2, 22.0))
    for i in range(spec.CRANK["n_mains"]):
        x = x0 + 26.0 + (x1 - x0 - 52.0) * i / (spec.CRANK["n_mains"] - 1)
        parts.append(mesh.box(x, 0.0, z * 0.55, 20.0, 74.0, abs(z) * 0.9))
        for sgn in (-1, 1):
            parts.append(_stud(x, sgn * 44.0, z))
    return {"bedplate": mesh.join(*parts)}


def _stud(x, y, z):
    """Main bearing stud, standing vertically through the bedplate."""
    v, f = mesh.cylinder(0.0, 58.0, 6.0, 10)
    v = [(pz + x, py + y, px + z) for (px, py, pz) in v]   # +x axis -> +z
    return v, f


def _sump():
    a = spec.ANCILLARY
    z = -spec.BLOCK["skirt_depth"] - 22.0
    v, f = mesh.box(0.0, 0.0, z - a["sump_depth"] / 2,
                    a["sump_len"], a["sump_w"], a["sump_depth"])
    return {"sump": (v, f)}

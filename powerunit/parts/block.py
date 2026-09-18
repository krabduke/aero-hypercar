"""Cylinder block, bedplate, cylinder liners, sump."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh

SM = spec.RES["small_revolve"]
import shapes
from parts import common

B = spec.BLOCK
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_banks())
    out.update(_liners())
    out.update(_crankcase())
    out.update(_block_detail())
    out.update(_bedplate())
    out.update(_sump())
    out.update(_windage())
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
        # The slab runs the length of the block, the same on both banks.
        # It used to be centred on the bank's own cylinder offset instead,
        # so the right bank's casting ran from -222 to 241 -- 9 mm past the
        # block's rear face at 232, and 16 mm into the flywheel, which
        # starts at 225. A V8's bank offset staggers the BORES within the
        # casting; it does not stagger the casting. Both banks' outermost
        # bores need metal only out to 213.5, so both fit inside 232.
        v, f = shapes.rounded_box(
            (B["x_front"] + B["x_rear"]) / 2, 0.0,
            (along0 + along1) / 2,
            B["x_rear"] - B["x_front"], w * 2, along1 - along0,
            r=14.0, seg=5, draft=1.5)
        # box is built in world axes; rotate it onto the bank
        a = spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        v = [(x, y * ca - z * sa, y * sa + z * ca) for (x, y, z) in v]
        # push the slab a little outboard so the two banks leave a vee valley
        # between them for the turbos, instead of merging into one lump.
        #
        # Outboard is a direction in the BANK's frame, so it has to be taken
        # after the rotation. Applied before it, as a flat +8 mm in y, the
        # same shift came out as 5.66 outboard and 5.66 down on the right
        # bank and 5.66 INBOARD and 5.66 down on the left -- so the two banks
        # of a 90-degree V8 were not symmetric about the engine's own centre
        # plane, and the right one stood 11.3 mm higher than the left. The
        # vee floor went with it, and both of the rear turbo's oil lines ran
        # 14 mm down inside the block casting on their way to a union that
        # was supposed to be screwed into its face.
        lat = common.bank_lat(bank)          # inboard-positive
        v = [(x, y - lat[1] * 8.0, z - lat[2] * 8.0) for (x, y, z) in v]
        feats = []
        for (n2, pair2, b2, x2, a2) in spec.cylinders():
            if b2 != bank:
                continue
            # bore boss standing proud of the deck, and the jacket around it
            bv, bf = mesh.revolve_closed(
                [(-B["vee_depth"] * 0.5, spec.BORE * 0.5),
                 (0.0, spec.BORE * 0.5),
                 (0.0, spec.BORE * 0.5 + 9.0),
                 (-B["vee_depth"] * 0.5, spec.BORE * 0.5 + 7.0)], SM)
            feats.append((common.along_bank(bv, x2, spec.DECK_HEIGHT, bank), bf))
            for k in range(4):
                ang = math.pi / 4 + k * math.pi / 2
                sv, sf = mesh.revolve_closed(
                    [(-14.0, 0.0), (-14.0, 8.5), (0.0, 8.5), (0.0, 0.0)], SM)
                lat = math.cos(ang) * (spec.BORE * 0.5 + 14.0)
                dx = math.sin(ang) * (spec.BORE * 0.5 + 14.0)
                feats.append((common.along_bank(sv, x2 + dx,
                                                spec.DECK_HEIGHT, bank, lat), sf))
        out[f"block_bank_{'lr'[bank]}"] = mesh.join((v, f), *feats)
    return out


def _liners():
    """Wet liners: the actual bores the pistons run in."""
    parts = []
    r = spec.BORE / 2
    for (n, pair, bank, x, a) in spec.cylinders():
        # The liner stops above the crank's rotating envelope. It used to run
        # down to 37.5 mm from the crank axis while the counterweights sweep a
        # 58 mm circle, so the bores passed through the crankshaft.
        along0 = max(spec.DECK_HEIGHT - B["vee_depth"] + 8.0,
                     spec.CRANK["web_r"] + 20.0)
        v, f = common.bore_tube(x, along0, spec.DECK_HEIGHT, r, r + 5.5, bank)
        parts.append((v, f))
    return {"block_liners": mesh.join(*parts)}


def _crankcase():
    """The crankcase skirt below the vee, carrying the main bearing webs."""
    parts = []
    x0, x1 = B["x_front"], B["x_rear"]
    hw = B["half_width"] * 0.86
    # a casting, with radiused edges and draft, not a rectangular prism
    parts.append(shapes.rounded_box(0.0, 0.0, -B["skirt_depth"] / 2 + 14.0,
                                    x1 - x0, hw * 2, B["skirt_depth"] + 28.0,
                                    r=16.0, seg=5, draft=1.5))
    span = (spec.CRANK["n_mains"] - 1)
    for i in range(spec.CRANK["n_mains"]):
        x = x0 + 26.0 + (x1 - x0 - 52.0) * i / span
        parts.append(shapes.rounded_box(
            x, 0.0, -B["skirt_depth"] * 0.30,
            B["main_web_t"], hw * 1.9, B["skirt_depth"] * 1.1, r=7.0))
    return {"block_crankcase": mesh.join(*parts)}


def _block_detail():
    """The features a block actually has: water jacket outlets, oil gallery
    plugs, breathers and the bosses the ancillaries hang off.

    A block with nothing on its outside is a billet, not a casting."""
    out = {}
    x0, x1 = B["x_front"], B["x_rear"]
    # on the block's own flank, outboard of the bores: at 0.86 of the
    # half width the outlet bosses were inside the cylinders
    hw = B["half_width"] + 4.0

    ports = []
    for i in range(4):
        f = (i + 0.5) / 4
        x = x0 + (x1 - x0) * f
        for sgn in (-1.0, 1.0):
            # 34 long from z 40, not 18 from z 22. They stopped 19 mm short
            # of the head they are supposed to drain: a water outlet on the
            # block's flank with the joint it crosses nowhere near it.
            ol = spec.COOLANT["outlet_len"]
            v, fc = mesh.revolve_open(
                [(0.0, 0.0), (0.0, 15.0), (ol - 8.0, 16.5), (ol, 14.0),
                 (ol, 0.0)], SM, cap_start=True, cap_end=True)
            v = [(pz + x, sgn * (hw + py), px + spec.COOLANT["outlet_z"] - 18.0)
                 for (px, py, pz) in v]
            ports.append((v, fc))
    out["water_outlets"] = mesh.join(*ports)

    plugs = []
    for i in range(6):
        f = (i + 0.5) / 6
        x = x0 + (x1 - x0) * f
        for sgn in (-1.0, 1.0):
            v, fc = mesh.revolve_open(
                [(0.0, 0.0), (0.0, 8.0), (5.0, 8.0), (5.0, 0.0)], 8,
                cap_start=True, cap_end=True)
            v = [(pz + x, sgn * (hw + py), px - 42.0) for (px, py, pz) in v]
            plugs.append((v, fc))
    out["gallery_plugs"] = mesh.join(*plugs)

    # Four at the mount stations, not two on opposite banks 70 mm from
    # either of them. ancillaries.py hangs a bracket at x = -150 and +150 on
    # BOTH banks; the only two bosses down at mount height were at x -80 on
    # one bank and +80 on the other, so not one of the four brackets that
    # carry the engine had anything to bolt to.
    #
    # The other four were at x +/-172, z 60 and the note here said they were
    # "the upper brackets". There are no upper brackets: ancillaries builds
    # one bracket per side per station and nothing at z 60. What is at
    # x +/-172, z 22-64 is a water outlet -- the bosses were inside all four
    # of them, 60 voxels of 60.
    #
    # z 40, not 4: the bank's flank is what they bolt to, and at 4 they were
    # 20 mm below it, hanging off the crankcase joint with nothing under
    # them.
    #
    # There is one gap on this flank at mount height and it is 34 mm wide.
    # The knock sensors sit at x -102, 0 and 102 and reach out to 124; the
    # water outlets start at 158. The upper bosses go at x +/-141 between
    # them, low enough that the outlet above them is not in the way either.
    bosses = []
    for (x, y, z) in ((-141.0, hw, 40.0), (-141.0, -hw, 40.0),
                      (141.0, hw, 40.0), (141.0, -hw, 40.0),
                      (-150.0, hw, -30.0), (-150.0, -hw, -30.0),
                      (150.0, hw, -30.0), (150.0, -hw, -30.0)):
        bv, bf = shapes.bolt_boss(0, 0, 0, 12.0, 12.0)
        sgn = 1.0 if y > 0 else -1.0
        bosses.append(([(px * 0 + pz + x, y + sgn * py, px + z)
                        for (px, py, pz) in bv], bf))
    out["mount_bosses"] = mesh.join(*bosses)
    return out


def _bedplate():
    """Bedplate rather than individual main caps -- one stiff casting that ties
    all five mains together, which is what lets the block be a stressed member."""
    parts = []
    x0, x1 = B["x_front"], B["x_rear"]
    hw = B["half_width"] * 0.80
    z = -B["skirt_depth"]
    parts.append(shapes.rounded_box(0.0, 0.0, z - 11.0, x1 - x0, hw * 2, 22.0,
                                    r=12.0, seg=5, draft=1.0))
    for i in range(spec.CRANK["n_mains"]):
        x = x0 + 26.0 + (x1 - x0 - 52.0) * i / (spec.CRANK["n_mains"] - 1)
        parts.append(shapes.rounded_box(x, 0.0, z * 0.55, 20.0, 74.0,
                                        abs(z) * 0.9, r=8.0))
        for sgn in (-1, 1):
            parts.append(_stud(x, sgn * 44.0, z))
    return {"bedplate": mesh.join(*parts)}


def _stud(x, y, z):
    """Main bearing stud, standing vertically through the bedplate."""
    v, f = mesh.cylinder(0.0, 58.0, 6.0, 10)
    v = [(pz + x, py + y, px + z) for (px, py, pz) in v]   # +x axis -> +z
    return v, f


def _sump():
    """A dry-sump pan: a shallow tray with a deep local well, not a tank.

    The oil has to end up somewhere the pickup can reach it under braking, so
    the pan falls from a wide rail at the block face into a narrow keel. It
    was a rectangular box bolted to the bottom of the engine.
    """
    a = spec.ANCILLARY
    z = -spec.BLOCK["skirt_depth"] - 22.0
    out = {}
    out["sump"] = shapes.tapered_pan(
        -a["sump_len"] / 2, a["sump_len"] / 2,
        a["sump_w"] / 2 * 0.98, a["sump_w"] / 2 * 0.70,
        z, a["sump_depth"], a["sump_len"] * 0.26, a["sump_len"] * 0.18)
    dv, df = mesh.revolve_open(
        [(0.0, 0.0), (0.0, 11.0), (7.0, 13.0), (13.0, 11.0), (13.0, 0.0)],
        SM, cap_start=True, cap_end=True)
    out["sump_drain"] = ([(pz + a["sump_len"] * 0.18, py,
                           -px + z - a["sump_depth"] * 0.96)
                          for (px, py, pz) in dv], df)
    baff = []
    for i in range(4):
        f = (i + 0.5) / 4
        baff.append(shapes.rounded_box(
            -a["sump_len"] / 2 + a["sump_len"] * f, 0.0,
            z - a["sump_depth"] * 0.42, 5.0, a["sump_w"] * 0.72,
            a["sump_depth"] * 0.55, 3.0))
    out["sump_baffles"] = mesh.join(*baff)
    return out


def _windage():
    """The windage tray, between the crank and the oil in the sump.

    A dry sump still whips oil off the crank; the tray is what stops it being
    dragged round with the counterweights. There were baffles in the sump and
    nothing between them and the crankshaft.
    """
    C = spec.CRANK
    x0, x1 = -152.0, 152.0
    z = -(C["web_r"] + 34.0)
    parts = []
    # the tray itself: a dished sheet following the crank swing
    n = 26
    verts, faces = [], []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        for (y, dz) in ((-74.0, 10.0), (-40.0, 0.0), (0.0, -4.0),
                        (40.0, 0.0), (74.0, 10.0)):
            verts.append((x, y, z + dz))
            verts.append((x, y, z + dz - 3.0))
    for i in range(n):
        for j in range(4):
            a = (i * 5 + j) * 2
            b = (i * 5 + j + 1) * 2
            c = ((i + 1) * 5 + j) * 2
            d = ((i + 1) * 5 + j + 1) * 2
            faces.append((a, b, d, c))
            faces.append((a + 1, c + 1, d + 1, b + 1))
    for i in range(n):
        a, c = (i * 5) * 2, ((i + 1) * 5) * 2
        faces.append((a, c, c + 1, a + 1))
        a, c = (i * 5 + 4) * 2, ((i + 1) * 5 + 4) * 2
        faces.append((a + 1, c + 1, c, a))
    # and the two ends. The long edges were closed and the ends were not, so
    # the tray was a sheet with a rim down each side and nothing across the
    # front or the back of it.
    for i, flip in ((0, False), (n, True)):
        for j in range(4):
            a = (i * 5 + j) * 2
            b = (i * 5 + j + 1) * 2
            quad = (a, a + 1, b + 1, b)
            faces.append(quad if flip else tuple(reversed(quad)))
    parts.append((verts, faces))
    # the louvres punched into it, which are what let the oil through one way
    for i in range(9):
        x = x0 + (x1 - x0) * (i + 0.5) / 9
        for sy in (-1.0, 1.0):
            lv, lf = shapes.rounded_box(x, sy * 52.0, z + 8.0,
                                        20.0, 30.0, 7.0, r=2.0, seg=3)
            parts.append((lv, lf))
    # standoffs down to the main webs
    for x in (-110.0, 0.0, 110.0):
        for sy in (-1.0, 1.0):
            sv, sf = mesh.cylinder(0.0, 26.0, 7.0, 10)
            sv = [(py + x, pz + sy * 66.0, px + z - 26.0)
                  for (px, py, pz) in sv]
            parts.append((sv, sf))
    return {"windage_tray": mesh.join(*parts)}

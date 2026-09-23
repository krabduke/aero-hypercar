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
LINER_WALL = 5.5          # a wet liner's wall: the block's bore is its outside
MAIN_SHELL_WALL = 3.4     # the main shells' back is the webs' bore


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


def _r_bay():
    """The crank's swept radius, with room: counterweights reach
    throw * 0.62 + web_r, the big ends throw + big_end_r, and the rod bolts'
    heads a little further again."""
    return spec.CRANK["throw"] + spec.ROD["big_end_r"] + 9.0


def _bores(bank, along0):
    """Solid cylinders the size of the liners' outside, one per bore on a
    bank, from `along0` up through the deck: cutters for the castings the
    bores pass through."""
    r = spec.BORE / 2 + LINER_WALL
    return mesh.join(*[
        common.cylinder_along(x, along0, spec.DECK_HEIGHT + 30.0, r, bank)
        for (n, pair, b2, x, a) in spec.cylinders() if b2 == bank])


def _banks():
    """Each bank is a slab standing on the crankcase at the bank angle, with
    the deck face at the top, and a bore through it for every cylinder, which
    the wet liner sits in.

    The docstring used to say the bores were "cut through it by the liners".
    Nothing cut anything: the liners were separate parts and the slab was
    solid, so every piston, ring, pin and rod in the engine was 40-odd mm
    inside cast aluminium, and a list of permissions called that intended."""
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
        # both banks' bores, and the crank's swept space: the two slabs meet
        # low in the vee, so the other bank's rods swing through this one
        out[f"cut:block_bank_{'lr'[bank]}"] = mesh.join(
            _bores(0, 0.0), _bores(1, 0.0),
            mesh.cylinder(B["x_front"] - 1.0, B["x_rear"] + 1.0, _r_bay(), SEG))
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
        v, f = common.bore_tube(x, along0, spec.DECK_HEIGHT, r, r + LINER_WALL, bank)
        parts.append((v, f))
    return {"block_liners": mesh.join(*parts)}


def _crankcase():
    """The crankcase skirt below the vee, carrying the main bearing webs.

    It is hollow: a bay between each pair of main webs for the crank's
    counterweights and the rods' big ends to swing in, a bore through every
    web for the main shells, and the bank bores continued down into it so
    each rod has a way up to its piston. It was a solid box, with the crank
    inside it."""
    parts = []
    x0, x1 = B["x_front"], B["x_rear"]
    hw = B["half_width"] * 0.86
    # a casting, with radiused edges and draft, not a rectangular prism
    parts.append(shapes.rounded_box(0.0, 0.0, -B["skirt_depth"] / 2 + 14.0,
                                    x1 - x0, hw * 2, B["skirt_depth"] + 28.0,
                                    r=16.0, seg=5, draft=1.5))
    span = (spec.CRANK["n_mains"] - 1)
    webs = [x0 + 26.0 + (x1 - x0 - 52.0) * i / span
            for i in range(spec.CRANK["n_mains"])]
    for x in webs:
        parts.append(shapes.rounded_box(
            x, 0.0, -B["skirt_depth"] * 0.30,
            B["main_web_t"], hw * 1.9, B["skirt_depth"] * 1.1, r=7.0))

    C = spec.CRANK
    r_bay = _r_bay()
    r_main = C["main_r"] + MAIN_SHELL_WALL
    wt = B["main_web_t"] / 2.0
    cav = [mesh.cylinder(a + wt, b - wt, r_bay, SEG)
           for a, b in zip(webs, webs[1:])]
    # the end walls and every web are bored for the crank to pass
    cav.append(mesh.cylinder(x0 - 1.0, x1 + 1.0, r_main, SEG))
    cav += [_bores(bank, 0.0) for bank in (0, 1)]
    return {"block_crankcase": mesh.join(*parts),
            "cut:block_crankcase": mesh.join(*cav)}


def _block_detail():
    """The features a block actually has: water jacket outlets, oil gallery
    plugs, breathers and the bosses the ancillaries hang off.

    A block with nothing on its outside is a billet, not a casting."""
    out = {}
    x0, x1 = B["x_front"], B["x_rear"]
    # on the block's own flank, outboard of the bores: at 0.86 of the
    # half width the outlet bosses were inside the cylinders
    hw = B["half_width"] + 4.0

    # Head water outlets: one out of each head's rear outboard corner, down
    # into the end of the rail that carries the water forward (detail.py).
    ports = []
    K = spec.COOLANT
    for bank in (0, 1):
        xr = spec.head_rear_x(bank)
        ports.append(mesh.pipe(mesh.smooth_path([
            common.bank_point(xr - 6.0, K["outlet_along"], K["outlet_lat"], bank),
            common.bank_point(xr + 10.0, K["outlet_along"], K["outlet_lat"] - 30.0, bank),
            common.bank_point(xr + 10.0, K["rail_along"], K["rail_lat"], bank)], 2),
            K["rail_r"] * 0.85, SM))
    out["water_outlets"] = mesh.join(*ports)

    # Oil gallery plugs, screwed into the crankcase wall with their axes
    # through it. They were upright discs 20 mm off the wall.
    plugs = []
    wall_y = B["half_width"] * 0.86
    for i in range(6):
        f = (i + 0.5) / 6
        x = x0 + (x1 - x0) * f
        for sgn in (-1.0, 1.0):
            v, fc = mesh.cylinder(wall_y - 3.0, wall_y + 4.0, 8.0, 10)
            v = [(-ly, lx, lz) for (lx, ly, lz) in v]        # axis along +y
            if sgn < 0:
                v = [(-px, -py, pz) for (px, py, pz) in v]   # half turn
            plugs.append(([(px + x, py, pz - 42.0) for (px, py, pz) in v], fc))
    out["gallery_plugs"] = mesh.join(*plugs)

    # Engine-mount pads, one each side at each station in spec.MOUNTS, from
    # 1 mm inside the crankcase wall out to the face the bracket bolts to.
    # There used to be a second set higher up the bank flanks, for "upper
    # brackets" that were never built; bolted to nothing, they cut into the
    # head gaskets, the head studs and the liners, and they are gone.
    bosses = []
    M = spec.MOUNTS
    wall = B["half_width"] * 0.86 - 1.0
    for sgn in (-1.0, 1.0):
        for x in M["x"]:
            cv, cf = mesh.cylinder(wall, M["boss_face"], M["boss_r"], 20)
            # the cylinder's axis is its +x; turn it a quarter about z so it
            # runs along +y, then mirror by rotating a half turn for the left
            cv = [(-ly, lx, lz) for (lx, ly, lz) in cv]
            if sgn < 0:
                cv = [(-px, -py, pz) for (px, py, pz) in cv]
            bosses.append(([(px + x, py, pz + M["z"]) for (px, py, pz) in cv], cf))
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

"""Everything an engine needs that is not the block, the crank or the heads.

Exhaust primaries, intake runners, fuel rails and injectors' feeds, the
accessory drive, the bearing shells and caps, the fasteners that hold it all
together. These are not decoration: an engine without primaries has nowhere
for the exhaust to go, and one without bearing shells has nothing for the
crank to run on.

Each is its own object, because each is a separate part with its own material
and its own service life.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import common

B = spec.BLOCK
H = spec.HEAD
C = spec.CRANK
T = spec.TURBO
SM = spec.RES["small_revolve"]


def build():
    out = {}
    out.update(_primaries())
    out.update(_collectors())
    out.update(_runners())
    out.update(_fuel())
    out.update(_bearings())
    out.update(_fasteners())
    out.update(_accessories())
    out.update(_breathers())
    return out


# --------------------------------------------------------------------------

def _primaries():
    """One exhaust primary per cylinder, out of the head and into the vee.

    The turbos sit in the vee -- a hot-vee layout -- so the primaries turn
    inboard rather than outboard. Length is what tunes them; these are equal
    length to within what the packaging allows, which is the whole reason a
    header looks the way it does.
    """
    out = {}
    for (n, pair, bank, x, a) in spec.cylinders():
        d = common.bank_dir(bank)
        lat = common.bank_lat(bank)
        # port face, on the inboard side of the head
        start = (x,
                 d[1] * (spec.DECK_HEIGHT + 34.0) + lat[1] * 44.0,
                 d[2] * (spec.DECK_HEIGHT + 34.0) + lat[2] * 44.0)
        tx = T["x"][0 if pair < 2 else 1]
        path = [
            start,
            (x + (tx - x) * 0.22,
             start[1] * 0.72, start[2] + 26.0),
            (x + (tx - x) * 0.58,
             start[1] * 0.34, T["z"] + 42.0),
            (tx - 46.0, 0.0, T["z"] + 16.0),
        ]
        out[f"primary_{n}"] = mesh.pipe(path, 15.0, 12)
    return out


def _collectors():
    """Where four primaries meet before the turbine."""
    out = {}
    for i, tx in enumerate(T["x"]):
        out[f"collector_{i + 1}"] = mesh.revolve_open(
            [(tx - 60.0, 34.0), (tx - 24.0, 30.0), (tx - 6.0, 26.0)],
            16, cap_start=True, cap_end=True)
        out[f"collector_{i + 1}"] = (
            [(px, py, pz + T["z"] + 16.0)
             for (px, py, pz) in out[f"collector_{i + 1}"][0]],
            out[f"collector_{i + 1}"][1])
    return out


def _runners():
    """One intake runner per cylinder, from the plenum down to the port.

    Runner length tunes the induction the way primary length tunes the
    exhaust. Drawing the plenum and not the runners leaves the air with no
    way of getting from one to the other.
    """
    out = {}
    I = spec.INTAKE
    for (n, pair, bank, x, a) in spec.cylinders():
        d = common.bank_dir(bank)
        lat = common.bank_lat(bank)
        port = (x,
                d[1] * (spec.DECK_HEIGHT + 30.0) + lat[1] * -50.0,
                d[2] * (spec.DECK_HEIGHT + 30.0) + lat[2] * -50.0)
        top = (x, port[1] * 0.30, I["plenum_z"] - 26.0)
        out[f"runner_{n}"] = mesh.pipe(
            [port, ((port[0] + top[0]) / 2, port[1] * 0.74, port[2] + 46.0),
             top], 17.0, 12)
    return out


def _fuel():
    """Two fuel rails, the feed to each injector, and the high-pressure pump.

    Direct injection at 350 bar needs a rail stiff enough not to breathe with
    every injection event, which is why a real one is a thick-walled forging
    and not a tube.
    """
    out = {}
    for bank in (0, 1):
        d = common.bank_dir(bank)
        lat = common.bank_lat(bank)
        along = spec.DECK_HEIGHT + 54.0
        offs = 62.0
        p0 = (H["x_front"] + 10.0,
              d[1] * along + lat[1] * offs, d[2] * along + lat[2] * offs)
        p1 = (H["x_rear"] - 10.0, p0[1], p0[2])
        out[f"fuel_rail_{'lr'[bank]}"] = mesh.pipe([p0, p1], 14.0, 12)

        feeds = []
        for (n, pair, b2, x, a) in spec.cylinders():
            if b2 != bank:
                continue
            inj = (x, d[1] * (spec.DECK_HEIGHT + 6.0) + lat[1] * spec.BORE * 0.40,
                   d[2] * (spec.DECK_HEIGHT + 6.0) + lat[2] * spec.BORE * 0.40)
            feeds.append(mesh.pipe([(x, p0[1], p0[2]),
                                    (x, (p0[1] + inj[1]) / 2,
                                     (p0[2] + inj[2]) / 2 + 10.0),
                                    inj], 4.5, 8))
        out[f"fuel_feeds_{'lr'[bank]}"] = mesh.join(*feeds)

    out["hp_fuel_pump"] = shapes.finned_case(
        H["x_front"] + 26.0, 92.0, spec.DECK_HEIGHT - 26.0,
        72.0, 62.0, 84.0, n_fins=6, fin_h=5.0, fin_t=3.0, r=12.0)
    return out


def _bearings():
    """Main and big-end bearing shells, and the main caps that hold them.

    A crank has to run on something. Shells are a consumable -- they are
    inspected every rebuild -- so they are separate parts, in pairs.
    """
    out = {}
    x0, x1 = B["x_front"], B["x_rear"]
    n_m = C["n_mains"]
    for i in range(n_m):
        x = x0 + 26.0 + (x1 - x0 - 52.0) * i / (n_m - 1)
        for half, sgn in (("upper", 1.0), ("lower", -1.0)):
            v, f = mesh.revolve_closed(
                [(-B["main_web_t"] * 0.38, C["main_r"]),
                 (B["main_web_t"] * 0.38, C["main_r"]),
                 (B["main_web_t"] * 0.38, C["main_r"] + 3.4),
                 (-B["main_web_t"] * 0.38, C["main_r"] + 3.4)],
                20, sweep=math.pi)
            v = [(px + x, py, sgn * pz) for (px, py, pz) in v]
            out[f"main_shell_{i + 1}_{half}"] = (v, f)
        out[f"main_cap_{i + 1}"] = shapes.rounded_box(
            x, 0.0, -C["main_r"] - 22.0, B["main_web_t"] * 1.05,
            96.0, 42.0, 8.0)

    for (n, pair, bank, x, a) in spec.cylinders():
        for half, sgn in (("upper", 1.0), ("lower", -1.0)):
            v, f = mesh.revolve_closed(
                [(-9.0, C["pin_r"]), (9.0, C["pin_r"]),
                 (9.0, C["pin_r"] + 3.0), (-9.0, C["pin_r"] + 3.0)],
                18, sweep=math.pi)
            py_ = 0.0
            v = [(px + spec.cylinder_x(pair), py, sgn * pz)
                 for (px, py, pz) in v]
            out[f"rod_shell_{n}_{half}"] = (v, f)
    return out


def _fasteners():
    """Rod bolts, main studs, cam cap bolts. An engine is held together by
    fasteners and they are the parts most likely to be replaced."""
    out = {}
    bolts = []
    for (n, pair, bank, x, a) in spec.cylinders():
        for sgn in (-1.0, 1.0):
            v, f = mesh.revolve_open(
                [(0.0, 0.0), (0.0, 5.4), (7.0, 6.6), (9.0, 6.6), (9.0, 0.0)],
                6, cap_start=True, cap_end=True)
            v = [(pz + spec.cylinder_x(pair), py + sgn * 19.0, -px - 24.0)
                 for (px, py, pz) in v]
            bolts.append((v, f))
    out["rod_bolts"] = mesh.join(*bolts)

    caps = []
    for bank in (0, 1):
        for side in (-1, 1):
            lat = side * H["cam_centres"] / 2
            for (n, pair, b2, x, a) in spec.cylinders():
                if b2 != bank:
                    continue
                cv, cf = shapes.rounded_box(0.0, 0.0, 0.0, 24.0, 46.0, 20.0, 5.0)
                cv = common.along_bank(
                    cv, x - spec.CAM["lobe_w"] * 2.05,
                    spec.DECK_HEIGHT + H["cam_height"] + 14.0, bank, lat)
                caps.append((cv, cf))
    out["cam_caps"] = mesh.join(*caps)
    return out


def _accessories():
    """Alternator, starter, the belt that drives them and its pulleys."""
    out = {}
    # The accessory drive sits on the front face of the block and the units
    # hang off its sides, bolted to the crankcase -- not floating in front of
    # the engine, which is where these were.
    xf = B["x_front"] - 16.0
    out["alternator"] = shapes.finned_case(xf - 32.0, -96.0, 52.0,
                                           76.0, 80.0, 80.0,
                                           n_fins=9, fin_h=5.0, fin_t=3.0,
                                           r=18.0, axis="x")
    sv, sf = mesh.revolve_open(
        [(0.0, 0.0), (0.0, 40.0), (104.0, 40.0), (112.0, 28.0), (112.0, 0.0)],
        18, cap_start=True, cap_end=True)
    # axis along x, lying against the crankcase flank
    out["starter"] = ([(px + B["x_rear"] - 150.0, pz + 104.0, py - 46.0)
                       for (px, py, pz) in sv], sf)

    pulls = []
    for (y, z, r) in ((0.0, 0.0, 62.0), (-96.0, 52.0, 32.0),
                      (92.0, 44.0, 30.0), (0.0, 104.0, 26.0)):
        v, f = mesh.revolve_closed(
            [(-11.0, r * 0.42), (11.0, r * 0.42), (11.0, r), (-11.0, r)], 20)
        pulls.append(([(px + xf, py + y, pz + z) for (px, py, pz) in v], f))
    out["accessory_pulleys"] = mesh.join(*pulls)

    # The belt. Without it the accessories read as detached lumps floating
    # off the nose of the engine, which is exactly how they read before.
    #
    # A belt wraps the outside of every pulley, so its path is the convex hull
    # of the pulley circles: at each angle round the drive, take the furthest
    # any pulley reaches in that direction.
    ring = [(62.0, 0.0, 0.0), (32.0, -96.0, 52.0),
            (26.0, 0.0, 104.0), (30.0, 92.0, 44.0)]
    path = []
    for i in range(49):
        t = 2 * math.pi * i / 48
        cy, cz = math.cos(t), math.sin(t)
        reach = max(py * cy + pz * cz + r for (r, py, pz) in ring)
        path.append((xf - 4.0, reach * cy, reach * cz))
    path.append(path[0])
    out["accessory_belt"] = mesh.pipe(path, 7.0, 6, caps=False)
    return out


def _breathers():
    """Crankcase breathers, the catch tank they feed, and the dipstick.

    An engine at 16,000 rpm pumps a great deal of air around its crankcase and
    it has to go somewhere other than past the rings.
    """
    out = {}
    pipes = []
    for bank in (0, 1):
        d = common.bank_dir(bank)
        along = spec.DECK_HEIGHT + H["height"] + 40.0
        start = (H["x_front"] + 70.0, d[1] * along, d[2] * along)
        pipes.append(mesh.pipe([start, (start[0] - 60.0, start[1] * 0.5, 232.0),
                                (B["x_front"] + 40.0, 58.0, 236.0)], 11.0, 10))
    out["breathers"] = mesh.join(*pipes)
    out["catch_tank"] = mesh.revolve_open(
        [(0.0, 0.0), (0.0, 40.0), (132.0, 40.0), (132.0, 0.0)],
        18, cap_start=True, cap_end=True)
    # lying along the top of the block, not standing off the nose of it
    out["catch_tank"] = ([(px + B["x_front"] + 36.0, py + 58.0, pz + 236.0)
                          for (px, py, pz) in out["catch_tank"][0]],
                         out["catch_tank"][1])
    out["dipstick"] = mesh.pipe(
        [(B["x_rear"] - 60.0, 120.0, 60.0),
         (B["x_rear"] - 40.0, 130.0, -160.0)], 4.0, 6)
    return out

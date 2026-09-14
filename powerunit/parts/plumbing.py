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
import gaspath
from parts import common

B = spec.BLOCK
H = spec.HEAD
C = spec.CRANK
T = spec.TURBO
SM = spec.RES["small_revolve"]
SEG = spec.RES["revolve"]


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
        # the centreline lives in gaspath.py, so the flow animation in the
        # viewer runs down the pipe that is actually here
        path = gaspath.primary_path(pair, bank, x)
        start = path[0]
        # A primary is not a constant-diameter tube. It leaves the port at
        # port size, is stepped out at the head flange, and tapers down into
        # the collector so the pulse arrives with some velocity behind it.
        radii = [16.5, 15.5, 14.0, 12.5]
        tube = mesh.pipe(path, radii, spec.RES["pipe"], subdiv=7)
        flange = mesh.revolve_open(
            [(-4.0, 16.5), (-4.0, 26.0), (5.0, 26.0), (5.0, 16.5)],
            SM, cap_start=True, cap_end=True)
        # stand the flange on the port face, normal to the bank
        d = common.bank_dir(bank)
        lat = common.bank_lat(bank)
        fv = []
        for (px, py, pz) in flange[0]:
            fv.append((start[0] + px * 0.0 + pz * 0.0 + px,
                       start[1] + py * lat[1] + pz * d[1],
                       start[2] + py * lat[2] + pz * d[2]))
        out[f"primary_{n}"] = mesh.join(tube, (fv, flange[1]))
    return out


def _collectors():
    """Where four primaries meet before the turbine."""
    out = {}
    for i, tx in enumerate(T["x"]):
        # a merge collector: four pipes' worth of area, necked into the
        # turbine inlet, with the flange that bolts it there
        prof = [(tx - 86.0, 40.0), (tx - 70.0, 39.0), (tx - 52.0, 36.0),
                (tx - 34.0, 32.0), (tx - 18.0, 28.0), (tx - 8.0, 26.0),
                (tx - 8.0, 34.0), (tx + 2.0, 34.0), (tx + 2.0, 26.0)]
        v, f = mesh.revolve_open(prof, spec.RES["revolve"] // 2,
                                 cap_start=True, cap_end=True)
        out[f"collector_{i + 1}"] = (
            [(px, py, pz + T["z"] + 16.0) for (px, py, pz) in v], f)
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
        # same centreline the viewer animates the induction along
        flow = gaspath.runner_path(bank, x)
        port, top = flow[-1], flow[1]
        # Bellmouth at the plenum end, tapering down to port size. The
        # bellmouth is what makes the runner fill at all -- a plain tube end
        # separates the flow the moment it turns the corner into it.
        path = list(reversed(flow))
        radii = [15.0, 16.5, 18.0, 25.0]
        tube = mesh.pipe(path, radii, spec.RES["pipe"], subdiv=7)
        flange = mesh.revolve_open(
            [(-4.0, 15.0), (-4.0, 24.0), (5.0, 24.0), (5.0, 15.0)],
            SM, cap_start=True, cap_end=True)
        d = common.bank_dir(bank)
        lat = common.bank_lat(bank)
        fv = [(port[0] + px, port[1] + py * lat[1] + pz * d[1],
               port[2] + py * lat[2] + pz * d[2])
              for (px, py, pz) in flange[0]]
        out[f"runner_{n}"] = mesh.join(tube, (fv, flange[1]))
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
        # A 350 bar rail is a thick-walled forging with a boss at every
        # injector and a fitting at each end, not a length of tube. It was
        # twenty-four vertices.
        rail = [mesh.pipe([p0, p1], 14.0, spec.RES["pipe"], subdiv=4)]
        for (n2, pair2, b3, x2, a2) in spec.cylinders():
            if b3 != bank:
                continue
            bv, bf = mesh.revolve_closed(
                [(-9.0, 0.0), (-9.0, 19.0), (9.0, 19.0), (9.0, 0.0)], SM)
            rail.append(([(px + x2, py + p0[1], pz + p0[2])
                          for (px, py, pz) in bv], bf))
        for end, xx in ((p0, p0[0] - 12.0), (p1, p1[0] + 12.0)):
            ev, ef = mesh.revolve_open(
                [(0.0, 0.0), (0.0, 11.0), (14.0, 11.0), (18.0, 8.0),
                 (18.0, 0.0)], SM, cap_start=True, cap_end=True)
            sgn = -1.0 if xx < p0[0] else 1.0
            rail.append(([(sgn * px + xx, py + p0[1], pz + p0[2])
                          for (px, py, pz) in ev], ef))
        out[f"fuel_rail_{'lr'[bank]}"] = mesh.join(*rail)

        feeds = []
        for (n, pair, b2, x, a) in spec.cylinders():
            if b2 != bank:
                continue
            inj = (x, d[1] * (spec.DECK_HEIGHT + 6.0) + lat[1] * spec.BORE * 0.40,
                   d[2] * (spec.DECK_HEIGHT + 6.0) + lat[2] * spec.BORE * 0.40)
            feeds.append(mesh.pipe([(x, p0[1], p0[2]),
                                    (x, (p0[1] + inj[1]) / 2,
                                     (p0[2] + inj[2]) / 2 + 10.0),
                                    inj], 4.5, SM))
        out[f"fuel_feeds_{'lr'[bank]}"] = mesh.join(*feeds)

    out["hp_fuel_pump"] = shapes.finned_case(
        H["x_front"] + 26.0, 92.0, spec.DECK_HEIGHT - 26.0,
        72.0, 62.0, 84.0, n_fins=6, fin_h=5.0, fin_t=3.0, r=12.0)
    return out


def _bearings():
    """Main and big-end bearing shells, and the main caps that hold them.

    A crank has to run on something. Shells are a consumable -- they are
    inspected every rebuild -- so they are separate parts, in pairs. Each one
    is a steel back with a relieved lining, a tang at the parting face, and,
    on the fed half of a main, a circumferential groove.
    """
    out = {}
    x0, x1 = B["x_front"], B["x_rear"]
    n_m = C["n_mains"]
    for i in range(n_m):
        x = x0 + 26.0 + (x1 - x0 - 52.0) * i / (n_m - 1)
        for half, sgn in (("upper", 1.0), ("lower", -1.0)):
            out[f"main_shell_{i + 1}_{half}"] = shapes.bearing_shell(
                x, C["main_r"], 3.4, B["main_web_t"] * 0.76,
                groove=(half == "upper"), sgn=sgn)
        out[f"main_cap_{i + 1}"] = _main_cap(x)

    # Two rods share every crankpin, and they sit side by side on it. Their
    # shells go where their rods are -- which is the bank's own station, not
    # the pin's.
    for (n, pair, bank, x, a) in spec.cylinders():
        for half, sgn in (("upper", 1.0), ("lower", -1.0)):
            out[f"rod_shell_{n}_{half}"] = shapes.bearing_shell(
                x, C["pin_r"], 3.0, spec.BANK_OFFSET - 2.0,
                arc_seg=36, sgn=sgn)
    return out


def _main_cap(x):
    """A main cap is a girdle, not a brick: a saddle over the journal with a
    boss at each stud and a rib between them."""
    w = B["main_web_t"] * 1.05
    r = C["main_r"]
    parts = [shapes.rounded_box(x, 0.0, -r - 21.0, w, 92.0, 40.0, 7.0,
                                seg=8, draft=2.0)]
    # the saddle the shell sits in
    sv, sf = mesh.revolve_closed(
        [(-w / 2, r + 3.6), (w / 2, r + 3.6),
         (w / 2, r + 13.0), (-w / 2, r + 13.0)], SM, sweep=math.pi)
    parts.append(([(px + x, py, -pz) for (px, py, pz) in sv], sf))
    for sy in (-1.0, 1.0):
        y = sy * 37.0
        parts.append(shapes.rounded_box(x, y, -r - 18.0, w * 0.96, 21.0,
                                        30.0, 6.0, seg=8))
        bv, bf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 13.0), (9.0, 12.0), (9.0, 0.0)], SM // 2,
            cap_start=True, cap_end=True)
        parts.append(([(pz + x, y + py, -r - 40.0 - px)
                       for (px, py, pz) in bv], bf))
    return mesh.join(*parts)


def _fasteners():
    """Rod bolts, main studs, cam cap bolts. An engine is held together by
    fasteners and they are the parts most likely to be replaced."""
    out = {}
    bolts = []
    for (n, pair, bank, x, a) in spec.cylinders():
        for sgn in (-1.0, 1.0):
            v, f = mesh.revolve_open(
                [(0.0, 0.0), (0.0, 5.4), (7.0, 6.6), (9.0, 6.6), (9.0, 0.0)],
                SM // 2, cap_start=True, cap_end=True)
            v = [(pz + x, py + sgn * 19.0, -px - 24.0)
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
        SM, cap_start=True, cap_end=True)
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
                                (B["x_front"] + 40.0, 58.0, 236.0)], 11.0, SM))
    out["breathers"] = mesh.join(*pipes)
    out["catch_tank"] = _catch_tank()
    out["dipstick"] = mesh.pipe(
        [(B["x_rear"] - 60.0, 120.0, 60.0),
         (B["x_rear"] - 40.0, 130.0, -160.0)], 4.0, 6)
    return out


def _catch_tank():
    """The dry-sump tank: a swirl pot, not a bucket.

    Scavenged oil comes back full of air, and air in the bearings is the end
    of the engine. So it enters tangentially at the top, spins down the wall,
    and the air separates out through the breather in the lid while the oil
    leaves from the bottom. The ends are domed because the tank is pressurised
    by blow-by and a flat end would oil-can.
    """
    R = 40.0
    L = 132.0
    parts = [mesh.revolve_closed(
        [(0.0, 0.0), (3.0, 0.0),
         (5.0, R * 0.55), (9.0, R * 0.86), (16.0, R - 1.0),
         (19.0, R),                                  # domed lower end
         (L - 19.0, R), (L - 16.0, R - 1.0),
         (L - 9.0, R * 0.86), (L - 5.0, R * 0.55),
         (L - 3.0, 0.0), (L, 0.0),
         (L - 6.0, R * 0.50), (L - 12.0, R * 0.80),
         (L - 20.0, R - 2.4), (20.0, R - 2.4),       # wall, from inside
         (12.0, R * 0.80), (6.0, R * 0.50)], SEG)]
    # rolled weld beads where the ends join the barrel
    for x in (19.0, L - 19.0):
        parts.append(mesh.ring_torus(x, R + 0.6, 1.8, SEG, 8))
    # the tangential inlet that makes it a swirl pot
    iv, if_ = mesh.pipe([(L - 26.0, -R * 1.9, 6.0), (L - 26.0, -R * 1.0, 2.0),
                         (L - 26.0, -R * 0.15, -1.0)], [15.0, 14.0, 13.0],
                        SM, subdiv=3)
    parts.append((iv, if_))
    # filler neck and cap in the lid, breather union beside it
    parts.append(mesh.revolve_closed(
        [(L - 2.0, 0.0), (L + 22.0, 0.0), (L + 22.0, 15.0),
         (L + 26.0, 15.5), (L + 26.0, 19.0), (L + 21.0, 19.5),
         (L + 18.0, 17.0), (L + 4.0, 17.0), (L - 2.0, 21.0)], SEG))
    bv, bf = mesh.revolve_closed(
        [(0.0, 0.0), (26.0, 0.0), (26.0, 7.0), (22.0, 8.5),
         (18.0, 8.5), (18.0, 10.5), (13.0, 10.5), (13.0, 8.0),
         (0.0, 8.0)], SM)
    parts.append(([(pz + L - 4.0, py + 26.0, px) for (px, py, pz) in bv], bf))
    # feed union out of the bottom, where the pressure stage picks up
    fv, ff = mesh.revolve_closed(
        [(0.0, 0.0), (30.0, 0.0), (30.0, 9.0), (25.0, 11.0),
         (20.0, 11.0), (20.0, 13.0), (14.0, 13.0), (14.0, 10.0),
         (0.0, 10.0)], SM)
    parts.append(([(pz + 22.0, py, -px - R + 4.0) for (px, py, pz) in fv], ff))
    # the straps that hold it to the chassis
    for x in (28.0, L - 30.0):
        parts.append(mesh.ring_torus(x, R + 3.2, 3.0, SEG, 8))
        parts.append(shapes.rounded_box(x, 0.0, -R - 9.0, 14.0, 30.0, 9.0,
                                        2.5, seg=5))
    v, f = mesh.join(*parts)
    return ([(px + B["x_front"] + 36.0, py + 58.0, pz + 236.0)
             for (px, py, pz) in v], f)

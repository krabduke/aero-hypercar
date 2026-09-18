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
        flange = mesh.revolve_ring(
            [(-4.0, 16.5), (-4.0, 26.0), (5.0, 26.0), (5.0, 16.5)], SM)
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
    """Where four primaries meet before the turbine.

    Four pipes' worth of area at the mouth, necked to the turbine's inlet
    area at the flange, swept along the centreline gaspath declares so the
    duct ends pointing into the volute. The previous one was a cone revolved
    about the turbocharger's own axis and lifted 16 mm above it: it started
    where no primary ended and finished pointing along the shaft, which is
    the one direction a radial turbine does not take gas in.
    """
    out = {}
    for pair in (0, 2):
        i = 0 if pair < 2 else 1
        path = gaspath.collector_path(pair)
        parts = [mesh.pipe(path, gaspath.COLLECTOR_RADII,
                           spec.RES["pipe"], subdiv=6)]
        # the mouth the four primaries land in, and the flange at the turbine
        mouth, r0 = path[0], gaspath.COLLECTOR_RADII[0]
        mv, mf = mesh.revolve_ring(
            [(-6.0, r0), (-6.0, r0 + 3.0), (3.0, r0 + 3.0), (3.0, r0)], SM)
        parts.append(([(px + mouth[0], py + mouth[1], pz + mouth[2])
                       for (px, py, pz) in mv], mf))
        parts.append(_inlet_flange(path[-1], path[-2],
                                   gaspath.COLLECTOR_RADII[-1]))
        out[f"collector_{i + 1}"] = mesh.join(*parts)
    return out


def _inlet_flange(at, towards, r, thick=7.0, pad=11.0):
    """A square-ish bolted flange standing normal to the duct it ends."""
    d = [at[k] - towards[k] for k in range(3)]
    m = math.dist(at, towards) or 1.0
    d = [c / m for c in d]
    v, f = mesh.revolve_ring(
        [(-thick, r), (-thick, r + pad), (0.0, r + pad), (0.0, r)], SM)
    # the lathe runs along +x; swing it onto the duct's own direction
    up = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (0.0, 1.0, 0.0)
    n1 = mesh._normalise(mesh._cross(d, up))
    n2 = mesh._cross(d, n1)
    return ([(at[0] + d[0] * px + n1[0] * py + n2[0] * pz,
              at[1] + d[1] * px + n1[1] * py + n2[1] * pz,
              at[2] + d[2] * px + n1[2] * py + n2[2] * pz)
             for (px, py, pz) in v], f)


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
        flange = mesh.revolve_ring(
            [(-4.0, 15.0), (-4.0, 24.0), (5.0, 24.0), (5.0, 15.0)], SM)
        d = common.bank_dir(bank)
        lat = common.bank_lat(bank)
        fv = [(port[0] + px, port[1] + py * lat[1] + pz * d[1],
               port[2] + py * lat[2] + pz * d[2])
              for (px, py, pz) in flange[0]]
        out[f"runner_{n}"] = mesh.join(tube, (fv, flange[1]))
    return out


def _fuel():
    """The high-pressure side: two rails, a feed to each direct injector, and
    the pump that supplies them.

    Direct injection at 350 bar needs a rail stiff enough not to breathe with
    every injection event, which is why a real one is a thick-walled forging
    and not a tube.
    """
    out = {}
    rail_ends = {}
    for bank in (0, 1):
        d = common.bank_dir(bank)
        lat = common.bank_lat(bank)
        # On the INTAKE side, which on a hot vee is outboard. At +62 the rail
        # sat on the head's inner face, in the vee, where the exhaust
        # primaries leave -- and the primaries went through it.
        along = spec.DECK_HEIGHT + H["height"] * 0.12
        offs = -80.0
        # clear of the accessory drive on the front face
        p0 = (H["x_front"] + 46.0,
              d[1] * along + lat[1] * offs, d[2] * along + lat[2] * offs)
        p1 = (H["x_rear"] - 34.0, p0[1], p0[2])   # clear of the bellhousing
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
        out[f"fuel_rail_di_{'lr'[bank]}"] = mesh.join(*rail)
        rail_ends[bank] = (p0, p1)

        feeds = []
        for (n, pair, b2, x, a) in spec.cylinders():
            if b2 != bank:
                continue
            inj = (x, d[1] * (spec.DECK_HEIGHT + 20.0) - lat[1] * 40.0,
                   d[2] * (spec.DECK_HEIGHT + 20.0) - lat[2] * 40.0)
            feeds.append(mesh.pipe([(x, p0[1], p0[2]),
                                    (x, (p0[1] + inj[1]) / 2,
                                     (p0[2] + inj[2]) / 2 - 14.0),
                                    inj], 4.5, SM))
        out[f"fuel_feeds_di_{'lr'[bank]}"] = mesh.join(*feeds)

    # On the head's OUTBOARD face, driven off the exhaust cam's tail. At
    # 92 mm from the centreline and below the deck it was inside the block,
    # the number two bore, its rings and an intake valve.
    out["hp_fuel_pump"] = shapes.finned_case(
        # driven off the rear of the exhaust cam, on the cover's outer
        # face -- the plenum's throttle is on that end now
        # Between two cylinders, on the cover's outer face. The coil wells
        # reach y 188 and the car's bodywork closes to 248 at this height,
        # so this is the 60 mm of flank there is.
        #
        # x 8 and 60 long, not x 0 and 72. At 0 the case spanned -36 to 36
        # and cylinder 4's port injector, whose body is 9 mm across at
        # x -41.5, reached -32.5; moving it aft alone put the far end into
        # cylinder 6's connector at 43.5. The gap between those two is
        # 76 mm and the case is sized to sit inside it.
        8.0, 218.0, 165.0,
        60.0, 54.0, 84.0, n_fins=6, fin_h=5.0, fin_t=3.0, r=12.0)

    # The pipe that makes it a fuel system rather than three fuel parts.
    #
    # The pump was 345 mm from the nearest rail and the two rails were joined
    # to nothing, so a chain that should read pump-rail-feed-injector stopped
    # at the first link. Nothing complained: every audit here asks whether
    # parts overlap, and three parts that do not touch each other cannot.
    #
    # There is one route down. The plenum stands on the head's outboard face
    # from z 30 to 110 and closes right onto it, so the line cannot drop
    # straight off the pump; it runs aft along the top of the cam cover to
    # x 224, which is past the head's rear face at 218 and forward of the
    # bellhousing flange at 235, and comes down the back of the engine to the
    # rail's rear fitting.
    x_back = spec.BLOCK["x_rear"] - 8.0
    p0r, p1r = rail_ends[1]
    p0l, _p1l = rail_ends[0]
    # Outboard of the cam cover, and above the port rail.
    #
    # At y 226 the line ran along the top of the cover in the middle of the
    # bolt row, which spans y 145 to 234 and z 134 to 223: 48 of its
    # vertices inside them. At 243 it is in the port fuel rail instead,
    # which runs the length of this flank at y 238-252. Outboard of the
    # cover's own edge at 245 there is a band, and it is 8 mm wide: the
    # hypercar's bodywork closes to 253 at this height, and a 10 mm pipe put
    # 4.3 mm of itself through the car. Going over the cover instead is not
    # available -- its crown is at z 242 and the pump sits against its
    # flank, so a line leaving the pump is inside the cover until it climbs
    # out, and it meets the breather gallery, the intake camshaft's tail and
    # the charge pipes doing it. A direct-injection supply line is a 7 mm
    # pipe on a real engine, which is what fits.
    out["fuel_hp_line"] = mesh.pipe(
        [(24.0, 218.0, 180.0), (120.0, 249.0, 176.0),
         (x_back, 249.0, 150.0), (x_back, 190.0, 72.0),
         (p1r[0] + 12.0, p1r[1], p1r[2])], 3.5, SM, subdiv=3)

    # and the same station, 22 mm higher, carries the pressure across to the
    # other bank. Above the crankcase, which stops at z 28, and below the
    # inverter, which starts at 153.
    out["fuel_rail_di_crossover"] = mesh.pipe(
        [(p1r[0] + 12.0, p1r[1], p1r[2]), (x_back, p1r[1], p1r[2]),
         (x_back, p1r[1], 132.0), (x_back, p0l[1], 132.0),
         (x_back, p0l[1], rail_ends[0][1][2]),
         (rail_ends[0][1][0] + 12.0, rail_ends[0][1][1],
          rail_ends[0][1][2])], 4.0, SM, subdiv=3)
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
    # In front of the timing cover, which ends at x -266. Behind it the
    # belt was inside the cover it is supposed to run on the outside of.
    xf = B["x_front"] - 70.0
    # far enough out that its case clears the MGU-K rotor, which is 84 mm
    # in radius and shares this station on the crank nose
    out["alternator"] = shapes.finned_case(xf - 32.0, -150.0, 86.0,
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
    for (y, z, r) in ((0.0, 0.0, 62.0), (-150.0, 86.0, 32.0),
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
    # (radius, y, z) of every pulley the belt has to wrap. These have to be
    # the same circles `pulls` above puts metal on, and the alternator's was
    # not: the hull was computed round (-96, 52) while the pulley is at
    # (-150, 86), so the belt ran 65 mm inboard of the pulley it drives. The
    # water pump's nose pulley is the fourth -- it is at y 200 on the other
    # side of the engine and the belt did not reach within 69 mm of it, so
    # the one thing that makes the pump turn was not connected to it.
    ring = [(62.0, 0.0, 0.0), (32.0, -150.0, 86.0),
            (26.0, 0.0, 104.0), (30.0, 92.0, 44.0),
            (46.0, spec.COOLANT["pump_y"], spec.COOLANT["pump_z"])]
    path = []
    for i in range(49):
        t = 2 * math.pi * i / 48
        cy, cz = math.cos(t), math.sin(t)
        reach = max(py * cy + pz * cz + r for (r, py, pz) in ring)
        path.append((xf - 4.0, reach * cy, reach * cz))
    path.append(path[0])
    # capped: the path is a closed loop, so with caps off the two ends of the
    # sweep sat on top of each other with nothing joining them and the belt
    # was an open tube
    out["accessory_belt"] = mesh.pipe(path, 7.0, 6, caps=True)
    return out


def _breathers():
    """Crankcase breathers, the catch tank they feed, and the dipstick.

    An engine at 16,000 rpm pumps a great deal of air around its crankcase and
    it has to go somewhere other than past the rings.
    """
    out = {}
    pipes = []
    # A gallery along the top of each cam cover, forward to a collector.
    #
    # Each bank's pipe used to run from x_front+70 FORWARD to x_front+10 and
    # then back AFT to x_front+40, a hairpin in x with a hundred millimetres
    # of y swing across it -- and the right bank's then crossed the whole
    # engine to a junction on the left. Smoothed, the hairpin came out as a
    # ring standing over the cam cover, and it was the one thing in the hero
    # render that did not look like part of an engine.
    # The two banks join across the FRONT FACE, at x -284.
    #
    # Not over the vee: the tailpipes fill y +/-115 from z 229 to 322 for the
    # whole length of the engine, and the collectors and heat blankets fill
    # what is under them. Not across the front of the block either -- the cam
    # drive gears are at x -269 to -250 and stand 241 tall. Forward of the
    # gears and above the accessory drive there is a clear band, and that is
    # where a real engine would run it too.
    # +58, not +40: the high-pressure fuel pump stands on the right cover to
    # z 212 and the gallery was running straight through it at 211.7.
    along = spec.DECK_HEIGHT + H["height"] + 58.0
    junction = (B["x_front"] - 58.0, -132.0, 214.0)
    for bank in (0, 1):
        d = common.bank_dir(bank)
        way = [(H["x_rear"] - 90.0, d[1] * along, d[2] * along),
               (H["x_front"] + 120.0, d[1] * along, d[2] * along),
               # Outboard of the cam drive gears, which are 241 of half
               # width and stand to z 241, rather than over the top of them
               # -- and the whole transit across their station has to be
               # outboard, not just its ends. The gallery runs along the
               # cover at 238 of half width, three millimetres inside them,
               # and the run out to 258 happened at x -248 to -280, which is
               # the gear band. Going over the top instead is not available:
               # the tailpipes fill z 229 to 322 from y -115 to 115 and the
               # two galleries have to meet in there.
               (H["x_front"] + 16.0, d[1] * along * 1.02, d[2] * along * 1.02),
               (B["x_front"] - 14.0, d[1] * 268.0, 240.0),
               (B["x_front"] - 50.0, d[1] * 268.0, 236.0),
               (B["x_front"] - 58.0, d[1] * 228.0, 226.0)]
        if bank == 1:                      # the right bank crosses the front
            way.append((B["x_front"] - 58.0, 40.0, 216.0))
        way.append(junction)
        pipes.append(mesh.pipe(way, 11.0, SM, subdiv=3))
    # and down the front-left corner into the tank's lid.
    #
    # The two bank pipes met over the vee and stopped there, 300 mm from the
    # tank they are supposed to vent into. The route down is outboard of the
    # plenum, which stands on the head from z 30 to 110, and forward of the
    # block so it misses the engine mount and the oil pump.
    vent = spec.oil_tank_union("breather")
    # It also stays outboard until it is level with the tank's lid, at
    # y -252. Turning in at x -288 took it diagonally across the number one
    # scavenge line, which climbs from the pan at y -150 to the pump's port
    # at -200 and whose own wall reaches -234. Above z -120 the car allows
    # 293 of half width, so there is room to pass outside it.
    #
    # It comes back inboard BELOW the oil pump, not across it. The pump
    # fills y -250 to -155 from z -59 up, so anything crossing that band
    # above -59 goes through it, and the feed line landing on the pump's
    # own union sits at y -155, z -60. At z -86 the vent passes under both
    # and arrives at the tank's lid from underneath its own union.
    pipes.append(mesh.pipe(
        [junction, (B["x_front"] - 60.0, -186.0, 168.0),
         (B["x_front"] - 60.0, -242.0, 60.0), (B["x_front"] - 56.0, -252.0, -74.0),
         (vent[0] - 26.0, -252.0, vent[2] - 4.0),
         (vent[0] - 26.0, -146.0, vent[2] - 8.0), vent], 10.0, SM, subdiv=3))
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
    O = spec.OIL
    R = O["tank_r"]
    L = O["tank_len"]
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
    # the breather in the lid, standing proud of it and at the FRONT end.
    # It was 26 mm long from the tank's own axis, which on a 40 mm tank puts
    # the whole union inside the oil -- nothing to connect a hose to, and the
    # crankcase breathers 300 mm away venting to atmosphere.
    bv, bf = mesh.revolve_closed(
        [(0.0, 0.0), (32.0, 0.0), (32.0, 7.0), (27.0, 8.5),
         (22.0, 8.5), (22.0, 10.5), (16.0, 10.5), (16.0, 8.0),
         (0.0, 8.0)], SM)
    parts.append(([(pz + 18.0, py + 26.0, px + 30.0)
                   for (px, py, pz) in bv], bf))
    # and the tangential scavenge inlet at the top of the wall, which is what
    # makes this a swirl pot: oil comes back full of air and has to be spun
    # against the wall for the air to come out of it
    iv, if_ = mesh.revolve_closed(
        [(0.0, 0.0), (32.0, 0.0), (32.0, 9.0), (27.0, 11.0),
         (22.0, 11.0), (22.0, 13.0), (16.0, 13.0), (16.0, 10.0),
         (0.0, 10.0)], SM)
    parts.append(([(pz + L - 30.0, -px - 30.0, py + 12.0)
                   for (px, py, pz) in iv], if_))
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
    # Low on the left flank, against the head, clear of the vee -- the vee
    # is full of plenum, turbos and charge coolers, and the tank was inside
    # all three of them in turn.
    return ([(px + O["tank_x"], py + O["tank_y"], pz + O["tank_z"])
             for (px, py, pz) in v], f)

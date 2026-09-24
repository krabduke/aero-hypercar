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
        if len(path) == 6:            # the pipes that swing round a volute
            radii = [16.5, 15.8, 15.2, 14.6, 14.0, 12.5]
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
        # the drum the four primaries land in, across the vee, with domed
        # end caps the primaries come through
        parts.append(_collector_drum(path[0]))
        parts.append(_inlet_flange(path[-1], path[-2],
                                   gaspath.COLLECTOR_RADII[-1]))
        out[f"collector_{i + 1}"] = mesh.join(*parts)
    return out


def _collector_drum(centre):
    """A drum along y centred on the collector's mouth."""
    D = gaspath.COLLECTOR_DRUM
    hl, r = D["half_len"], D["r"]
    v, f = mesh.revolve_closed(
        [(-hl, 0.0), (-hl, r - 9.0), (-hl + 9.0, r), (hl - 9.0, r),
         (hl, r - 9.0), (hl, 0.0)], spec.RES["pipe"] * 2)
    v = mesh.rot_z(v, math.pi / 2)           # its axis along y
    return mesh.translate(v, *centre), f


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
        # the end fittings screw into the rail's ends; they started 12 mm
        # off them, and the front one was fastened to nothing
        for end, xx in ((p0, p0[0] + 2.0), (p1, p1[0] - 2.0)):
            ev, ef = mesh.revolve_open(
                [(0.0, 0.0), (0.0, 11.0), (14.0, 11.0), (18.0, 8.0),
                 (18.0, 0.0)], SM, cap_start=True, cap_end=True)
            sgn = -1.0 if end is p0 else 1.0
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

    # The pump is on the timing case's front plate, coaxial with the right
    # bank's intake cam gear and driven straight off it -- which is how a
    # direct-injection pump is driven: off a camshaft.
    #
    # It used to stand on the right cam cover's outboard flank, 21 mm into
    # the cover and 24 mm into the head, with the port fuel rail running
    # through it, and its supply line leaving from inside it and running
    # through the cover's edge and the port rail's crossover on the way to
    # the rail.
    F = spec.FRONT
    cy, cz, _r = spec.timing_train(1)[3]
    x1 = F["case_front"]
    parts = [mesh.revolve_closed(
        [(x1 - 44.0, 0.0), (x1 - 44.0, 20.0), (x1 - 40.0, 24.0),
         (x1 - 12.0, 24.0), (x1 - 12.0, 28.0), (x1 - 6.0, 28.0),
         (x1 - 6.0, 34.0), (x1, 34.0), (x1, 0.0)], SM)]
    # cooling fins round the barrel
    for k in range(4):
        xk = x1 - 38.0 + k * 6.5
        parts.append(mesh.tube(xk, xk + 2.5, 20.0, 29.0, SM))
    # the drive tang through the plate to the cam gear's hub
    parts.append(mesh.cylinder(x1 - 1.0, F["gear_x"] - 7.0, 7.0, 16))
    # three bolts through the flange
    for k in range(3):
        a = 2 * math.pi * (k + 0.25) / 3
        bv, bf = mesh.cylinder(x1 - 10.0, x1 - 6.0, 4.0, 10)
        parts.append((mesh.translate(bv, 0.0, 30.0 * math.cos(a),
                                     30.0 * math.sin(a)), bf))
    # the outlet union, on the barrel's outboard side
    ua = math.radians(-35.0)
    uv, uf = mesh.revolve_closed(
        [(18.0, 0.0), (18.0, 8.0), (30.0, 8.0), (30.0, 6.0), (36.0, 6.0),
         (36.0, 0.0)], SM)
    # the profile runs along x; turn it to point out along (cos ua, sin ua)
    uv = [(pz + x1 - 26.0, px * math.cos(ua) - py * math.sin(ua),
           px * math.sin(ua) + py * math.cos(ua)) for (px, py, pz) in uv]
    parts.append((uv, uf))
    pv, pf = mesh.join(*parts)
    out["hp_fuel_pump"] = ([(px, py + cy, pz + cz) for (px, py, pz) in pv], pf)
    union = (x1 - 26.0, cy + 36.0 * math.cos(ua), cz + 36.0 * math.sin(ua))

    # The supply line: from the pump's union out past the edge of the case,
    # back along the flank under the plenum's nose and into the front
    # fitting of the right-hand rail.
    x_back = spec.BLOCK["x_rear"] - 8.0
    p0r, p1r = rail_ends[1]
    p0l, _p1l = rail_ends[0]
    out["fuel_hp_line"] = mesh.pipe(
        [union,
         (union[0], union[1] + 16.0 * math.cos(ua),
          union[2] + 16.0 * math.sin(ua)),
         (x1 - 10.0, 245.0, 95.0), (-250.0, 245.0, 70.0),
         (-222.0, 190.0, 46.0), (p0r[0] - 12.0, p0r[1], p0r[2])],
        3.5, SM, subdiv=3)

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

    # The rod shells are built with the rods, in bottomend.py.
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
    """Main studs, cam cap bolts. An engine is held together by
    fasteners and they are the parts most likely to be replaced."""
    # The rod bolts are built with the rods, in bottomend.py, because they
    # lie along each rod's own axis. Here they were sixteen 9 mm pucks fixed
    # under the crank as if every rod were at bottom dead centre, 42 mm inside
    # the crankcase casting, attached to no rod.
    out = {}

    caps = []
    for bank in (0, 1):
        for side in (-1, 1):
            lat = side * H["cam_centres"] / 2
            for (n, pair, b2, x, a) in spec.cylinders():
                if b2 != bank:
                    continue
                # A cap is the top half of a split bearing: a block with a
                # half-bore that clamps the journal. It was a solid box
                # standing 4 mm above the cam's centreline, which put its
                # underside 11 mm down into a journal that turns inside it.
                # As wide as the journal it clamps: at 20 mm it overhung
                # the cam lobes either side, which turn.
                cv, cf = shapes.bearing_cap(spec.CAM["journal_r"] + 0.3,
                                            23.0, 26.0,
                                            spec.CAM["lobe_w"] * 0.7)
                cv = common.along_bank(
                    cv, x - spec.CAM["lobe_w"] * 2.05,
                    spec.DECK_HEIGHT + H["cam_height"], bank, lat)
                caps.append((cv, cf))
    out["cam_caps"] = mesh.join(*caps)
    return out


def _accessories():
    """Alternator, the belt that drives the alternator and water pump, and
    the alternator's pulley.

    The drive is one serpentine belt in one plane, spec.FRONT["belt_x"]: off
    the grooves of the crank damper, round the water pump, over the
    tensioner and the idler on the timing case's legs, and down round the
    alternator. It is a flat band -- 20 mm wide, 4.5 mm thick -- straight
    between pulleys and wrapped on each, from spec.belt_path.
    """
    out = {}
    F = spec.FRONT
    bx = F["belt_x"]
    ay, az, ar = F["alternator"]
    # the alternator's body stands behind its pulley and bolts to the case
    # plate's edge; its front face carries the pulley's shaft
    x_back = F["case_front"]
    x_front = bx + F["pulley_w"] / 2 + 3.0
    out["alternator"] = shapes.finned_case((x_front + x_back) / 2, ay, az,
                                           x_back - x_front, 80.0, 80.0,
                                           n_fins=7, fin_h=5.0, fin_t=3.0,
                                           r=18.0, axis="x")
    # There is no starter motor. The MGU-K on the crank nose turns the
    # engine over, as it does on a hybrid race engine. The starter this
    # engine had lay 29 mm inside the crankcase and 38 mm through its
    # gallery plugs: every station where its pinion could reach the
    # flywheel's ring gear is inside the block.

    pv, pf = pulley(bx, ar)
    shaft = mesh.cylinder(bx, x_front + 0.5, 8.0, 14)
    out["accessory_pulleys"] = mesh.join(
        ([(px, py + ay, pz + az) for (px, py, pz) in pv], pf),
        ([(px, py + ay, pz + az) for (px, py, pz) in shaft[0]], shaft[1]))

    out["accessory_belt"] = belt(spec.belt_path(spec.belt_circles()),
                                 bx, F["belt_w"], F["belt_t"])
    return out


def pulley(x, r, w=None, bore=None):
    """A flat-belt pulley on the x axis: a crowned rim between two low
    flanges that keep the belt on, a web and a hub."""
    w = spec.FRONT["pulley_w"] if w is None else w
    h = w / 2.0
    bore = 0.0 if bore is None else bore
    return mesh.revolve_closed(
        [(x - h, bore), (x - h, r + 3.0), (x - h + 1.0, r + 3.0),
         (x - h + 1.0, r), (x + h - 1.0, r), (x + h - 1.0, r + 3.0),
         (x + h, r + 3.0), (x + h, bore)], 40)


def belt(path, x, w, t):
    """Sweep a flat w-by-t section round a closed belt path of
    ((y, z), (ny, nz)) points, inner face on the path."""
    verts, faces = [], []
    for (y, z), (ny, nz) in path:
        for (dx, dn) in ((-w / 2, 0.0), (w / 2, 0.0), (w / 2, t), (-w / 2, t)):
            verts.append((x + dx, y + ny * dn, z + nz * dn))
    n = len(path)
    for i in range(n):
        j = (i + 1) % n
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((4 * i + k, 4 * j + k, 4 * j + k2, 4 * i + k2))
    return verts, faces


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
    # On the covers' crowns: at this height the 7 mm hose lies on them.
    along = spec.DECK_HEIGHT + H["height"] + 54.0
    # forward of the timing case's plate, which is at x -290
    xc = spec.FRONT["case_front"] - 9.0
    junction = (xc, -150.0, 222.0)
    for bank in (0, 1):
        d = common.bank_dir(bank)
        # out of a union let into the cover's crown: the gallery used to
        # start in the air above the cover, bore open
        way = [(H["x_rear"] - 72.0, d[1] * (along - 20.0), d[2] * (along - 20.0)),
               (H["x_rear"] - 90.0, d[1] * along, d[2] * along),
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
               (xc, d[1] * 250.0, 230.0),
               (xc, d[1] * 212.0, 224.0)]
        if bank == 1:                      # the right bank crosses the front
            way.append((xc, 40.0, 222.0))
        way.append(junction)
        # 7 mm, not 11: a breather is a light hose, and at 11 the crossover
        # and its drop read as a roll bar across the front of the engine
        pipes.append(mesh.pipe(way, 7.0, SM, subdiv=3))
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
        [junction, (xc, -196.0, 168.0),
         (xc, -250.0, 60.0), (xc + 8.0, -258.0, -74.0),
         (vent[0] - 26.0, -258.0, vent[2] - 4.0),
         (vent[0] - 26.0, -146.0, vent[2] - 8.0), vent], 7.0, SM, subdiv=3))
    out["breathers"] = mesh.join(*pipes)
    out["catch_tank"] = _catch_tank()
    # The dipstick is in the tank's filler cap, because this is a dry-sump
    # engine: the oil lives in the tank, and the sump is scavenged dry. It
    # was a rod from inside the right bank, through the engine mount and a
    # cylinder bore, ending 38 mm outside the sump -- measuring nothing.
    O = spec.OIL
    tx, ty, tz, L = O["tank_x"], O["tank_y"], O["tank_z"], O["tank_len"]
    # into the oil but short of the scavenge line that enters the lid end
    rod = mesh.pipe([(tx + L + 36.0, ty, tz), (tx + L - 18.0, ty, tz)], 2.2, 8)
    # a finger loop round the rod's end, touching it
    lv, lf = mesh.ring_torus(tx + L + 34.0, 4.0, 2.0, 24, 8)
    out["dipstick"] = mesh.join(rod, (mesh.translate(lv, 0.0, ty, tz), lf))
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

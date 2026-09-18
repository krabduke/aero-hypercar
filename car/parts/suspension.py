"""Wishbones, pushrods, pullrods, rockers, track rods and driveshafts.

Front is pushrod and rear is pullrod, which is the usual arrangement: it puts
the front springs high where there is room above the driver's feet, and the
rear springs low where the gearbox casing can carry them.

Every span between two spherical bearings is an aerofoil member. The front
upper wishbone is raked nose-DOWN by 6 degrees (outboard pickup raised above
the inboard): that is the anti-dive geometry -- braking throws the car
forward onto the front axle and the arm would fold the nose down, so the arm
is built so brake torque reacts against a rising wheel rate instead. The
same rake is the correct attitude for a member working in front-wing upwash,
which arrives already turning upward. The front lower legs and everything
behind the axle line sit flat.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import wheels, common, detail

S = spec.SUSP
P = spec.RES["pipe"]

# These aerofoil dimensions and pickup settings belong in spec.py.
AERO_LINK = {
    # The rear lower wishbone's aft pickup, relative to the rear axle.
    #
    # It has to miss four things at once. At +190 it was 162 mm behind the
    # gearbox casing, which ends at 4078, and 219 mm from the fan axis
    # against a 250 mm rotor tip -- bolted to nothing, inside the fan. At
    # +20 it lands on the casing but crosses the driveshaft, which runs
    # x 4000-4100 at z 294-396. Dropping the whole pickup under the shaft
    # does not work either: the rear anti-roll bar and its blade fill
    # z 140-289 right there, so the gap between them is five millimetres.
    # At -60 it is forward of the shaft in x and above the bar in z, on the
    # casing, and 437 mm from the fan axis.
    "rear_lower_aft_dx": -60.0,
    "wishbone_c": 130.0, "wishbone_t": 18.0,
    "pushrod_c": 110.0, "pushrod_t": 18.0,
    "trackrod_c": 100.0, "trackrod_t": 14.0,
    "incidence_deg": -3.0, "anti_dive_deg": 6.0,
    "pickup_dx": 190.0,
}


def _section(chord, thickness):
    """Thin teardrops: the flow sees a 14-18 mm member, not a fairing.

    `suspension_link` places a section point (u, v) as `(u - 0.35)` along the
    link and `v` normal to it, so the aerofoil's quarter-chord has to sit at
    u = 0.35 for the leading edge to land on the rod ends. The incidence here
    is part of the shape, not the attitude: the pickups stay where the
    geometry needs them, the fairing turns the flow.
    """
    a = math.radians(AERO_LINK["incidence_deg"])
    ca, sa = math.cos(a), math.sin(a)
    return [(0.35 + (u - 0.35) * ca - v * sa,
             (u - 0.35) * sa + v * ca)
            for u, v in common.section_points(
                spec.RES["airfoil_pts"], thickness / chord, 0.0)]


def build():
    out = {}
    arms, rods, rockers, shafts = [], [], [], []
    for (tag, x, y, w, od) in wheels.corners():
        front = tag.startswith("f")
        inb_y = S["inboard_front_y"] if front else S["inboard_rear_y"]
        sgn = -1.0 if y < 0 else 1.0
        hub = (x, y * 0.80, od / 2)

        # Upper and lower wishbones. Each leg is an aerofoil member, not a
        # tube: at 300 km/h a round member is pure drag and produces nothing.
        # It is an 18 mm teardrop on a 130 mm chord, which is the aspect a
        # front suspension member really has -- the old "fairings" were
        # 57 mm thick on a 190 mm chord, wider than the members they
        # replaced and fatter than the whole front wing.
        chord = AERO_LINK["wishbone_c"]
        sect = _section(chord, AERO_LINK["wishbone_t"])
        # Anti-dive: rake the FRONT UPPER legs, outboard end up, by 6 deg.
        # Braking puts a forward load into the front upper arm, which would
        # pitch the nose down; raking the arm so the wheel end is the higher
        # pickup geometrically couples brake torque into ride height the
        # other way. It is also the right attitude for a member sitting in
        # the front-wing upwash: the flow there is already turned upward.
        rake = math.radians(AERO_LINK["anti_dive_deg"]) if front else 0.0
        low_z = S["lower_z"] if front else S["lower_z_rear"]
        for (z_out, z_in) in ((S["upper_z"], S["upper_z"] + 40.0),
                              (low_z, low_z + 10.0)):
            # 0.77 of the wheel's own y, not 0.74. The uprights' inner faces
            # are at 623 front and 545 rear; at 0.74 the outboard rod ends
            # finished 10 mm inboard of the casting they pick up on, so the
            # upper wishbone and the rear pullrod were carrying load into
            # thin air.
            outb = (x, y * 0.77, z_out)
            # Both legs go on the gearbox. The note here used to say only
            # the forward one was moved because the aft one "would land at
            # x 4170, which is inside the fan rotor" -- but the code moved
            # both and the aft pickup came out at x 4240, y 150, which is
            # 219 mm from the fan axis against a 250 mm rotor tip. So it was
            # inside the rotor anyway, and 162 mm behind the gearbox's rear
            # face at 4078, which is to say bolted to nothing. A rear lower
            # wishbone picks up on the gearbox casing; there is nothing else
            # back there to pick up on.
            rear_low = (not front and z_out == low_z)
            lvl_y = S["lower_inboard_rear_y"] if rear_low else inb_y
            if rear_low:
                z_in = S["lower_inboard_rear_z"]
            dxs = (-AERO_LINK["pickup_dx"], AERO_LINK["pickup_dx"])
            if rear_low:
                dxs = (-AERO_LINK["pickup_dx"],
                       AERO_LINK["rear_lower_aft_dx"])
            for leg, dx in zip(("fwd", "aft"), dxs):
                # MINUS the rake, not plus. The comment above says outboard
                # end up, and adding it raised the inboard end instead --
                # which put the front upper wishbone's chassis pickup at
                # z 545, sixty millimetres above the top of the tub at that
                # station. Both front upper legs picked up on nothing.
                # ...and only on the UPPER legs, which is what the comment
                # above says and what anti-dive means. Applied to both, it
                # dragged the lower arm's pickup down to z 117 and out of the
                # tub as soon as the sign was corrected.
                lift = rake if z_out == S["upper_z"] else 0.0
                inb = (x + dx, sgn * lvl_y,
                       z_in - math.tan(lift) * abs(lvl_y - y * 0.77))
                # The leg is named by which one it is, not by the sign of
                # its offset. Once the rear lower aft pickup moved forward
                # of the axle, `"fwd" if dx < 0 else "aft"` called both legs
                # `fwd` and the second overwrote the first in the dict --
                # two wishbones silently gone out of the car.
                lvl = "upper" if z_out == S["upper_z"] else "lower"
                arms.append((f"wishbone_{tag}_{lvl}_{leg}",
                             shapes.suspension_link(
                                 outb, inb, sect, chord,
                                 chord * 0.86, n_sta=11,
                                 end_r=14.0 if lvl == "lower" else 12.0)))

        # push/pull rod into a rocker on the chassis
        if front:
            rod = [(x, y * 0.77, low_z), (x + 120.0, sgn * inb_y, 455.0)]
            rockers.append((f"rocker_{tag}",
                            _rocker(x + 130.0, sgn * inb_y, 475.0, 1.0)))
        else:
            # The rear rocker sits ON the gearbox casing, which is what
            # carries the load into the structure. At z 180 it hung below
            # the casing and reached down to 85 -- through the diffuser
            # roof, into the tunnel, and into the outermost strake.
            # +20, not +60: the rear upright tops out at z 492 and a pullrod
            # picking up at 522 was 30 mm above the casting it pulls on.
            rod = [(x, y * 0.77, S["upper_z"] + 20.0),
                   (x - 150.0, sgn * inb_y, S["rear_rocker_z"])]
            rockers.append((f"rocker_{tag}",
                            _rocker(x - 160.0, sgn * inb_y,
                                    S["rear_rocker_z"], -1.0)))
        # A pushrod is the most heavily loaded member on the car and it is
        # also right in the flow, so it is an aerofoil member with a rod end
        # at each end -- not a 40-vertex tube. It works in the wheel wake,
        # which is turbulent and decoupled, so it runs fat and thick; that
        # also gives it the depth it needs for the compressive load.
        rod_sect = _section(AERO_LINK["pushrod_c"], AERO_LINK["pushrod_t"])
        rods.append((f"pushrod_{tag}", shapes.suspension_link(
            rod[0], rod[1], rod_sect,
            AERO_LINK["pushrod_c"], AERO_LINK["pushrod_c"] * 0.88,
            n_sta=11, end_r=S["rod_r"] * 0.95)))

        # track rod / toe link
        # The rear toe link picks up on the gearbox, which ends at x 4078.
        # At x + 92 its rod end reached 4195: 117 mm behind the casing and
        # inside the fan fairing, which starts at 4106. Forward of that it
        # would run into the rear anti-roll blade -- x 3869 to 4059, z 216
        # to 280 -- so it goes UNDER the blade, at z 190, which is still
        # 46 mm clear of the tunnel roof at 144.
        trk_x = x + (-230.0 if front else -10.0)
        # Below the driveshaft, not across it. At low_z + 70 the rear toe link
        # ran at z 294-346 and the shaft is 294-396: the link went through it.
        # A rear toe link sits under the shaft on a real car for exactly this
        # reason.
        # The front track rod runs between the steering arm's outer end and
        # the rack, which is what a track rod is. It used to run from the
        # upright straight inboard to x - 230, which is 200 mm ahead of the
        # rack and nowhere near the arm.
        SA = spec.STEER_ARM
        t_out = ((SA["end_x"], sgn * SA["y_out"], SA["end_z"]) if front
                 else (x, y * 0.77, low_z + 42.0))
        t_in = ((x - 200.0, sgn * S["inboard_front_y"] * 0.72,
                 SA["end_z"] + 8.0) if front
                else (trk_x, sgn * inb_y * 0.8, low_z - 50.0))
        rods.append((f"trackrod_{tag}", shapes.suspension_link(
            t_out, t_in,
            _section(AERO_LINK["trackrod_c"], AERO_LINK["trackrod_t"]),
            AERO_LINK["trackrod_c"], AERO_LINK["trackrod_c"] * 0.9, n_sta=9,
            end_r=S["rod_r"] * 0.78)))

        if not front:
            shafts.append((f"driveshaft_{tag}", _driveshaft(x, sgn, y, od)))

    # One object per member. A wishbone leg, a pushrod and a track rod are
    # three different parts with three different loads and three different
    # lengths; joining them into one mesh called "wishbones" makes them
    # impossible to inspect and hides that there are sixteen of them.
    for k, m in arms:
        out[k] = m
    for k, m in rods:
        out[k] = m
    for k, m in rockers:
        out[k] = m
    for k, m in shafts:
        out[k] = m
    out.update(_inboard())
    return out


def _inboard():
    """What the pushrod actually pushes: torsion bars, dampers, the
    anti-roll bar and the heave element.

    A pushrod that ends at a box is a pushrod that does nothing. This is the
    part of a racing car's suspension that does the work, and it was missing
    entirely -- there were two boxes labelled "rockers" and nothing else.
    """
    out = {}
    for ax, tag in ((spec.FRONT_AXLE_X, "f"), (spec.REAR_AXLE_X, "r")):
        front = tag == "f"
        inb_y = S["inboard_front_y"] if front else S["inboard_rear_y"]
        # Referenced to what the bodywork does overhead, not picked.
        # At the front axle the body's top surface runs z 555 to 600, and this
        # group was placed at 560 with the anti-roll bar at 656 and the heave
        # element at 710 -- so the whole inboard suspension stood up to 160 mm
        # proud of the car, in clean air, ahead of the driver.
        z = 455.0 if front else 200.0
        dx = 130.0 if front else -160.0

        dampers = []
        for sgn in (-1.0, 1.0):
            dampers.append(_damper(ax + dx - 150.0, sgn * inb_y * 0.55, z))
        out[f"dampers_{tag}"] = mesh.join(*dampers)

        # torsion bars across the car, and the heave damper on the centreline
        out[f"torsion_bars_{tag}"] = _torsion_bars(
            ax + dx - 10.0, inb_y * 0.9, z - 36.0)
        # the heave element is a third damper, working only when both
        # wheels move together -- which is what holds the ride height under
        # aerodynamic load
        out[f"heave_{tag}"] = _damper(ax + dx - 165.0, 0.0, z + 38.0)

        # anti-roll bar: a blade each side on a cross tube
        out[f"antiroll_{tag}"] = _antiroll(ax + dx - 60.0, inb_y, z + 62.0)

    # steering: rack, column and track rods
    ax = spec.FRONT_AXLE_X
    # The rack goes at the steering arm's own station, 200 mm ahead of the
    # axle, so the track rod is a transverse link between the two. At ax - 40
    # it was 200 mm behind the arm's outer end and the rod reached neither.
    out["steering_rack"] = _rack(ax - 200.0, S["inboard_front_y"] * 0.85)
    out["steering_column"] = _steering_column(ax)
    return out


def _damper(x, y, z):
    """A damper, with the adjusters that are the point of it.

    Two concentric cylinders is a gas strut. A racing damper has a separate
    gas reservoir alongside the body because the fluid has to have somewhere
    to go as the rod displaces it, a bump and a rebound adjuster on that
    reservoir, a clevis at each end, and a bump rubber on the rod.
    """
    parts = []
    # body, with the seal head and eye at the closed end
    parts.append(mesh.revolve_closed(
        [(0.0, 0.0), (14.0, 0.0), (14.0, 30.0), (20.0, 34.0),
         (172.0, 34.0), (178.0, 30.0), (186.0, 29.0), (186.0, 21.0),
         (176.0, 20.0), (176.0, 15.0), (14.0, 15.0), (8.0, 22.0),
         (0.0, 26.0)], 34))
    # rod and its bump rubber
    parts.append(mesh.revolve_closed(
        [(176.0, 0.0), (268.0, 0.0), (268.0, 12.5), (176.0, 12.5)], 24))
    parts.append(mesh.revolve_closed(
        [(196.0, 13.0), (232.0, 13.0), (232.0, 24.0), (226.0, 27.0),
         (202.0, 27.0), (196.0, 24.0)], 24))
    # reservoir alongside, on its transfer union
    rv, rf = mesh.revolve_closed(
        [(0.0, 0.0), (96.0, 0.0), (96.0, 23.0), (90.0, 26.0),
         (8.0, 26.0), (0.0, 23.0)], 28)
    parts.append(([(px + 44.0, py, pz + 52.0) for (px, py, pz) in rv], rf))
    parts.append(mesh.pipe([(38.0, 0.0, 18.0), (40.0, 0.0, 36.0),
                            (48.0, 0.0, 50.0)], 8.0, 14, subdiv=3))
    # bump and rebound adjusters, one on each end of the reservoir
    for (ax_, hex_r) in ((140.0, 11.0), (44.0, 9.0)):
        kv, kf = mesh.revolve_closed(
            [(0.0, 0.0), (16.0, 0.0), (16.0, hex_r), (10.0, hex_r + 2.0),
             (0.0, hex_r + 2.0)], 12)
        parts.append(([(px + ax_, py, pz + 78.0)
                       for (px, py, pz) in kv], kf))
    # clevis eyes, top and bottom
    for (ax_, dirn) in ((0.0, -1.0), (268.0, 1.0)):
        ev, ef = shapes.rod_end((0.0, 0.0, 0.0), (dirn, 0.0, 0.0), 13.0)
        parts.append(([(px + ax_, py, pz) for (px, py, pz) in ev], ef))
    v, f = mesh.join(*parts)
    return ([(px + x, py + y, pz + z) for (px, py, pz) in v], f)


def _torsion_bars(x, half_y, z):
    """A torsion bar is a spring. It has splines at each end -- that is how
    the load gets into it -- and a lever arm the pushrod works through."""
    parts = []
    for sgn in (-1.0, 1.0):
        y0, y1 = sgn * half_y, sgn * half_y * 0.12
        parts.append(mesh.pipe(
            [(x, y0 + (y1 - y0) * f, z) for f in (0.0, 0.25, 0.5, 0.75, 1.0)],
            [19.0, 15.0, 14.0, 15.0, 19.0], 22, subdiv=2))
        # splines at the outer end
        for i in range(18):
            a = 2 * math.pi * i / 18
            sv, sf = mesh.box(0.0, 0.0, 0.0, 3.0, 26.0, 3.0)
            parts.append(([(x + px + 18.0 * math.cos(a),
                            y0 - sgn * 13.0 + py,
                            z + pz + 18.0 * math.sin(a))
                           for (px, py, pz) in sv], sf))
        # the lever arm the rocker pulls on
        parts.append(shapes.rounded_box(x + 36.0, y0 - sgn * 6.0, z + 4.0,
                                        96.0, 20.0, 40.0, 8.0, seg=6))
    return mesh.join(*parts)


def _steering_column(ax):
    """A column with a universal joint at each break in it, and the quick
    release the driver pulls the wheel off."""
    # From the rack's new station to the wheel's hub. It used to start at
    # ax - 40 and run on to ax + 620, which is past the wheel and 100 mm
    # under it: the column ended in mid-air behind the steering wheel.
    path = [(ax - 200.0, 0.0, 258.0), (ax + 150.0, 0.0, 360.0),
            (ax + 320.0, 0.0, 452.0), (ax + 433.0, 0.0, 562.0)]
    parts = [mesh.pipe(path, [15.0, 15.0, 17.0, 17.0], 22, subdiv=4)]
    for (i, p) in enumerate(path[1:3]):
        d = (path[i + 2][0] - path[i][0], 0.0, path[i + 2][2] - path[i][2])
        jv, jf = mesh.revolve_closed(
            [(-30.0, 0.0), (30.0, 0.0), (30.0, 16.0), (18.0, 26.0),
             (-18.0, 26.0), (-30.0, 16.0)], 22)
        parts.append((shapes.orient(jv, p, d), jf))
        yv, yf = mesh.revolve_closed(
            [(-8.0, 0.0), (8.0, 0.0), (8.0, 30.0), (-8.0, 30.0)], 20)
        parts.append((shapes.orient(
            [(py, pz, px) for (px, py, pz) in yv], p, d), yf))
    qv, qf = mesh.revolve_closed(
        [(0.0, 0.0), (34.0, 0.0), (34.0, 30.0), (28.0, 36.0),
         (8.0, 36.0), (0.0, 30.0)], 24)
    parts.append((shapes.orient(qv, path[-1],
                                (path[-1][0] - path[-2][0], 0.0,
                                 path[-1][2] - path[-2][2])), qf))
    return mesh.join(*parts)


def _driveshaft(x, sgn, y, od):
    """A driveshaft is a tube with a constant-velocity joint at each end.

    The joint is the whole reason the part exists: the wheel moves 60 mm up
    and down and steers, and the gearbox output does not, so the shaft has to
    change length and angle while transmitting the torque. A plain cylinder
    from the diff to the hub says none of that happens. Each end gets a
    tripod housing and the convoluted boot that keeps grease in it.
    """
    # the outboard joint sits in the upright, at the hub -- not 80 mm
    # inboard of it, which is where it used to stop
    # 95 inboard, not 180: the gearbox casing is a cylinder that has closed
    # to 101 mm of half width by the driveshaft's station, so an inboard
    # joint at 180 was 78 mm outside the case it takes drive from.
    y0, y1 = sgn * 95.0, y * 0.875
    z = od / 2
    parts = []
    # the bar itself, waisted between the two joints
    parts.append(mesh.pipe(
        [(x, y0 + (y1 - y0) * f, z) for f in (0.16, 0.32, 0.50, 0.68, 0.84)],
        [25.0, 21.0, 19.5, 21.0, 25.0], 24, subdiv=3))

    def place(verts, yy, dirn):
        return [(x + pz, yy + dirn * px, z + py) for (px, py, pz) in verts]

    # Each joint housing opens towards the middle of the shaft, so `dirn` is
    # the direction from that end towards the other one -- not a hard-coded
    # +1 and -1, which is what it was. On the left-hand corner, where the
    # shaft runs the other way in y, that put one bell inboard of the shaft
    # end and hung the other past the hub; the two shafts came out 98 mm from
    # being mirror images and neither reached its wheel.
    towards = 1.0 if y1 > y0 else -1.0
    for (yy, dirn) in ((y0, towards), (y1, -towards)):
        bv, bf = mesh.revolve_closed(
            [(0.0, 0.0), (56.0, 0.0), (56.0, 26.0), (50.0, 30.0),
             (44.0, 44.0), (16.0, 48.0), (8.0, 40.0), (0.0, 30.0)], 34)
        parts.append((place(bv, yy, dirn), bf))

        outer = []
        for i in range(13):
            f = i / 12.0
            r = 46.0 - 18.0 * f + (6.0 if i % 2 else -1.0)
            outer.append((44.0 + 54.0 * f, r))
        prof = [(px, r - 3.0) for (px, r) in outer] + list(reversed(outer))
        cv, cf = mesh.revolve_closed(prof, 30)
        parts.append((place(cv, yy, dirn), cf))
    return mesh.join(*parts)


def _rocker(x, y, z, dirn):
    """A bellcrank, which is a machined triangle and not a box.

    Three pickups -- pushrod in, damper out, torsion bar on the pivot -- so
    it is a triangle with a boss at each corner, machined out between them
    because every gram there is unsprung-adjacent mass that has to be
    accelerated twice per bump. Two plates with a spacer between them, which
    is how it takes the side load without twisting.
    """
    corners = [(x + dirn * 86.0, z + 48.0),      # pushrod
               (x - dirn * 74.0, z + 62.0),      # damper
               (x + dirn * 10.0, z - 70.0)]      # pivot
    parts = []
    for sgn in (-1.0, 1.0):
        yy = y + sgn * 21.0
        ctrl = []
        for i, c in enumerate(corners):
            nxt = corners[(i + 1) % 3]
            ctrl.append(c)
            # waist the edge in between: the machined-out flank
            mx = (c[0] + nxt[0]) / 2
            mz = (c[1] + nxt[1]) / 2
            cx = sum(p[0] for p in corners) / 3
            cz = sum(p[1] for p in corners) / 3
            ctrl.append((mx + (cx - mx) * 0.34, mz + (cz - mz) * 0.34))
        parts.append(shapes.shaped_panel(
            shapes.panel_outline(ctrl, subdiv=5), yy, 13.0, rim_seg=4))
    for (cx, cz) in corners:
        bv, bf = mesh.revolve_closed(
            [(-30.0, 11.0), (30.0, 11.0), (30.0, 21.0), (26.0, 25.0),
             (-26.0, 25.0), (-30.0, 21.0)], 24)
        parts.append(([(pz + cx, px + y, py + cz)
                       for (px, py, pz) in bv], bf))
    return mesh.join(*parts)


def _antiroll(x, half_y, z):
    """A blade anti-roll bar: a cross tube on bearings, a lever arm each side,
    and a flat blade the driver can rotate to change the rate."""
    parts = [mesh.pipe([(x, -half_y * 0.86, z), (x, half_y * 0.86, z)],
                       15.0, 22, subdiv=4)]
    for sgn in (-1.0, 1.0):
        yy = sgn * half_y * 0.86
        # bearing block
        parts.append(shapes.rounded_box(x, sgn * half_y * 0.60, z,
                                        54.0, 30.0, 54.0, 9.0, seg=6))
        # lever arm, and the blade sticking out of it on edge
        parts.append(shapes.rounded_box(x + 40.0, yy, z, 96.0, 22.0, 40.0,
                                        8.0, seg=6))
        parts.append(shapes.rounded_box(x + 104.0, yy, z + 4.0,
                                        86.0, 7.0, 42.0, 2.5, seg=5))
        # drop link down to the rocker
        parts.append(shapes.suspension_link(
            (x + 140.0, yy, z - 6.0), (x + 150.0, yy * 0.86, z - 108.0),
            common.section_points(20, 0.34, 0.0), 26.0, 24.0,
            n_sta=7, end_r=9.0))
    return mesh.join(*parts)


def _rack(x, half_y):
    """A rack housing: the pinion comes in at an angle on its own boss, the
    ends are gaitered, and it bolts to the tub on two feet."""
    z = 240.0
    parts = [mesh.revolve_closed(
        [(-half_y * 0.82, 0.0), (half_y * 0.82, 0.0),
         (half_y * 0.82, 22.0), (half_y * 0.74, 30.0),
         (half_y * 0.30, 34.0), (-half_y * 0.30, 34.0),
         (-half_y * 0.74, 30.0), (-half_y * 0.82, 22.0)], 30)]
    parts = [([(x + pz, px, z + py) for (px, py, pz) in parts[0][0]],
              parts[0][1])]
    # gaiters on the rack ends
    for sgn in (-1.0, 1.0):
        prof = []
        for i in range(11):
            f = i / 10.0
            prof.append((half_y * 0.82 + 62.0 * f,
                         30.0 - 12.0 * f + (5.0 if i % 2 else -1.0)))
        loop = [(px, r - 2.5) for (px, r) in prof] + list(reversed(prof))
        gv, gf = mesh.revolve_closed(loop, 24)
        parts.append(([(x + pz, sgn * px, z + py)
                       for (px, py, pz) in gv], gf))
    # pinion boss and the two mounting feet
    parts.append(mesh.pipe([(x + 10.0, -40.0, z + 20.0),
                            (x + 40.0, -70.0, z + 96.0)], [26.0, 21.0],
                           20, subdiv=3))
    for sgn in (-1.0, 1.0):
        parts.append(shapes.rounded_box(x - 30.0, sgn * half_y * 0.44,
                                        z - 30.0, 70.0, 36.0, 40.0, 8.0,
                                        seg=6))
    return mesh.join(*parts)

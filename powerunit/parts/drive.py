"""Flywheel, clutch, bellhousing, oil and water pumps.

These were five tubes. A clutch with no diaphragm cannot be released, and a water pump that is a
cylinder is a tin can -- a real one is a spiral scroll, because the passage
has to gain area as flow joins it or the impeller just churns.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes

SM = spec.RES["small_revolve"]
from parts import common

A = spec.ANCILLARY
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_flywheel())
    out.update(_clutch())
    out.update(_bellhousing())
    out.update(_oil_pump())
    out.update(_water_pump())
    return out


def _flywheel():
    """A stepped disc. It carries no starter ring gear: the MGU-K starts
    the engine.

    The friction face is flat and the back is relieved to get the weight out
    of it, because every gram at 96 mm radius is inertia the engine has to
    accelerate twice per gearchange.
    """
    # On the crank's flywheel flange, whose rear face is spec.FLYWHEEL_X.
    # It was 26 mm behind it, bolted to nothing: `audit_intersect` has
    # ("crankshaft", "flywheel") on its list of parts that share material on
    # purpose, but that entry is a permission and not a requirement, so when
    # the flywheel drifted off the flange the entry simply stopped applying
    # and no test had anything to say. The flywheel and the clutch were a
    # two-part assembly floating inside the bellhousing.
    x = spec.FLYWHEEL_X
    t = A["flywheel_t"]
    R = A["flywheel_r"]
    # meridian, counter-clockwise in (x, r): hub, relieved back, rim
    v, f = mesh.revolve_closed(
        [(x, 0.0), (x + t, 0.0),
         (x + t, 26.0), (x + t - 3.0, 30.0),        # friction face side
         (x + t - 3.0, R - 14.0), (x + t, R - 10.0),
         (x + t, R - 1.5), (x + t - 1.5, R),
         (x + 1.5, R), (x, R - 1.5),                 # rim
         (x, R - 12.0), (x + 5.0, R - 16.0),         # relieved back
         (x + 5.0, 34.0), (x, 28.0)], SEG)
    parts = [(v, f)]
    # crank flange bolts and the lightening pockets between them
    parts.append(mesh.bolt_ring(x + t, 30.0, 8, head_r=7.0, head_h=5.0))
    for i in range(8):
        a = 2 * math.pi * (i + 0.5) / 8
        pv, pf = mesh.revolve_closed(
            [(x + t - 3.0, 0.0), (x + t - 3.0, 15.0),
             (x + t - 9.0, 15.0), (x + t - 9.0, 0.0)], 14)
        parts.append(([(px, py + math.cos(a) * (R * 0.62),
                        pz + math.sin(a) * (R * 0.62))
                       for (px, py, pz) in pv], pf))
    return {"flywheel": mesh.join(*parts)}


def _clutch():
    """A carbon multiplate clutch: a cover, a diaphragm with fingers cut into
    it, the pressure plate and the pack of plates it squeezes."""
    # 24 mm behind the flywheel's front face: the cover bolts to the
    # flywheel rim, so the two move together.
    x = spec.FLYWHEEL_X + 24.0
    R = A["flywheel_r"] * 0.86
    parts = []
    # cover: a pressing with a bolt flange at the rim
    parts.append(mesh.revolve_closed(
        [(x, 38.0), (x + 4.0, 38.0),
         (x + 4.0, R - 16.0), (x + 15.0, R - 10.0),
         (x + 15.0, R), (x + 18.0, R),
         (x + 18.0, R - 6.0), (x + 11.0, R - 12.0),
         (x + 11.0, 42.0), (x, 42.0)], SEG))
    # and the drum skirt from that flange forward to the flywheel's face,
    # which is what the cover bolts to. The flange stood 12 mm aft of the
    # flywheel, fastened to nothing.
    # (its friction face, which is recessed 3 mm under the clutch)
    fly_face = spec.FLYWHEEL_X + A["flywheel_t"] - 3.0
    parts.append(mesh.revolve_closed(
        [(fly_face, R - 4.0), (x + 16.0, R - 4.0),
         (x + 16.0, R), (fly_face, R)], SEG))
    # diaphragm fingers -- the thing you actually push on
    for i in range(18):
        a = 2 * math.pi * i / 18
        fv, ff = mesh.revolve_closed(
            [(x - 9.0, 0.0), (x - 9.0, 4.5), (x + 2.0, 4.5), (x + 2.0, 0.0)],
            8)
        fv = [(px, py + math.cos(a) * 26.0, pz + math.sin(a) * 26.0)
              for (px, py, pz) in fv]
        # taper each finger outward by shearing it along its own radius
        fv = [(px, py * (1.0 + 0.9 * max(0.0, (x + 2.0 - px) / 11.0)),
               pz * (1.0 + 0.9 * max(0.0, (x + 2.0 - px) / 11.0)))
              for (px, py, pz) in fv]
        parts.append((fv, ff))
    # plate pack: four carbon plates with drive lugs, on a splined hub --
    # clamped face to face, which is what an engaged clutch is. With a gap
    # between each the last plate touched nothing at all.
    for k in range(4):
        px0 = x - 16.0 + k * 2.4
        parts.append(mesh.tube(px0, px0 + 2.4, 30.0, R - 14.0, SEG))
    parts.append(mesh.revolve_closed(
        [(x - 22.0, 22.0), (x - 2.0, 22.0), (x - 2.0, 30.0),
         (x - 22.0, 30.0)], SM))
    for i in range(24):                       # splines on the hub
        a = 2 * math.pi * i / 24
        sv, sf = mesh.box(0.0, 0.0, 0.0, 20.0, 2.6, 3.4)
        parts.append(([(px + x - 12.0, py + math.cos(a) * 23.0,
                        pz + math.sin(a) * 23.0) for (px, py, pz) in sv], sf))
    return {"clutch": mesh.join(*parts)}


def _bellhousing():
    """The housing that carries the clutch and bolts the gearbox on. It is a
    structural member on this car, so it gets a bolt flange at each end and
    ribs down the barrel."""
    x = spec.BLOCK["x_rear"] + 8.0
    L = A["bellhousing_len"]
    R = A["bellhousing_r"]
    # The bell.
    #
    # This was a barrel with a flange at each end and a 29 mm gap between its
    # front flange and the block, because a flange at r 140 has nothing to
    # land on: the crankcase rear face stops at r 101. A bellhousing is not a
    # barrel, it is a bell -- it opens out from the block's rear face to the
    # gearbox's bolt circle, and that cone IS the joint. Without it the
    # gearbox and clutch hung off the back of the engine touching nothing.
    #
    # The cone starts at r 104, clear of the flywheel's rim,
    # and lands 2 mm inside the block's rear face. The crankcase is a box
    # 202 mm across and 124 deep, so its rear face reaches r 139 at the
    # bottom corners and r 105 at the top ones -- that corner is what the
    # bell bolts to, and a circular flange at r 140 sailed past all of it.
    # On the bedplate's rear face, which stands 0.2 mm proud of the block's:
    # at 2 mm inside it the cone was 3 mm into the bedplate.
    xb = spec.BLOCK["x_rear"]
    parts = [mesh.revolve_closed(
        [(xb, 104.0), (xb, 116.0),
         (x + 6.0, R - 2.0), (x + 6.0, R - 13.0)], SEG)]
    parts.append(mesh.revolve_closed(
        [(x, R - 11.0), (x + L, R - 11.0),
         (x + L, R - 2.0), (x + L - 9.0, R - 4.0),
         (x + 9.0, R - 6.0), (x, R)], SEG))
    parts.append(mesh.flange(x, R - 12.0, R + 14.0, 9.0, 12, bolt_r=6.5))
    parts.append(mesh.flange(x + L - 9.0, R - 12.0, R + 12.0, 9.0, 12,
                             bolt_r=6.5))
    for i in range(10):                        # stiffening ribs
        a = 2 * math.pi * i / 10
        rv, rf = shapes.rounded_box(0.0, 0.0, 0.0, L - 22.0, 9.0, 12.0, 3.0)
        parts.append(([(px + x + L / 2, py + math.cos(a) * (R + 3.0),
                        pz + math.sin(a) * (R + 3.0))
                       for (px, py, pz) in rv], rf))
    return {"bellhousing": mesh.join(*parts)}


def _oil_pump():
    """A dry-sump pump: one pressure stage and four scavenge stages stacked on
    a common shaft, each its own body with its own port.

    A wet sump has one pump. A dry sump has to pull oil back out of the
    crankcase faster than the rings throw it in, which is why the stack is
    longer than the pressure section it feeds.
    """
    # driven off the crank nose but lying back alongside the pan, which is
    # where there is room for a stack this long. The station and the stage
    # widths come from spec.OIL, because detail.py has to land four scavenge
    # pipes and two tank lines on the ports they imply -- it used to guess,
    # and missed the pump by 25 mm.
    O = spec.OIL
    x0 = O["pump_x"]
    # outboard of the MGU-K rotor, which is 84 mm in radius on the crank
    # nose and shares this station
    cy, cz = O["pump_y"], O["pump_z"]
    R = A["oil_pump_r"]
    parts = []
    x = 0.0
    for k in range(len(O["stage_w"])):
        w = O["stage_w"][k]                # the pressure stage is wider
        r = R if k else R * 1.08
        parts.append(mesh.revolve_closed(
            [(x, 11.0), (x + w, 11.0),
             (x + w, r - 3.0), (x + w - 2.0, r),
             (x + 2.0, r), (x, r - 3.0)], SM))
        parts.append(mesh.tube(x + w, x + w + 2.4, 11.0, r * 0.94, SM))
        # the port out of each stage, clocked round so they do not collide
        a = math.radians(O["port_a"][k])
        pl = O["port_len"]
        pv, pf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 10.5), (pl - 6.0, 10.5), (pl - 4.0, 13.0),
             (pl, 13.0), (pl, 0.0)], SM // 2, cap_start=True,
            cap_end=True)
        parts.append(([(pz + x + w / 2, py + math.cos(a) * px,
                        math.sin(a) * px) for (px, py, pz) in pv], pf))
        x += w + O["stage_gap"]
    # the tank connections, on the end faces: the pressure stage is fed from
    # the tank at the front and the scavenge stages discharge into it at the
    # back. Without these two the pump had five ports facing the pan and no
    # way in or out of the tank at all.
    span = sum(O["stage_w"]) + O["stage_gap"] * (len(O["stage_w"]) - 1)
    for (sgn, mouth) in ((-1.0, -16.0), (1.0, span + 16.0)):
        uv, uf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 12.0), (16.0, 12.0), (18.0, 15.0),
             (24.0, 15.0), (24.0, 0.0)], SM, cap_start=True, cap_end=True)
        # the profile runs 0..24 along its own axis; put the far end on the
        # union point spec.oil_pump_union names, so the pipes drawn to it in
        # detail.py land on metal
        base = mouth - sgn * 24.0            # rooted in the body, not beside it
        parts.append(([(base + sgn * px, py, pz + 20.0)
                       for (px, py, pz) in uv], uf))
    # through shaft and the drive gear on the end
    parts.append(mesh.tube(-14.0, x + 12.0, 0.0, 9.0, SM))
    parts.append(shapes.gear_ring(-14.0, -4.0, 24.0, 29.0, 34, 9.0))
    parts.append(mesh.flange(-4.0, 9.0, 30.0, 7.0, 4, bolt_r=5.0))
    v, f = mesh.join(*parts)
    # the stack lies along the engine already; drop it into place
    return {"pump_oil": ([(px + x0, py + cy, pz + cz) for (px, py, pz) in v],
                        f)}


def _water_pump():
    """A centrifugal pump: a spiral scroll, a vaned impeller inside it, an
    axial inlet eye and a tangential outlet."""
    # Low on the right beside the timing case, well outboard of the MGU-K.
    C = spec.COOLANT
    x0 = C["pump_x"]
    # Outboard of the MGU-K, which is a 84.5 mm radius rotor on the crank
    # axis at this station -- the pump used to reach in to y = 1 and pass
    # straight through it.
    cy, cz = C["pump_y"], C["pump_z"]
    R = A["water_pump_r"]
    parts = [shapes.volute(0.0, R * 0.62, R * 1.18, 11.0, 20.0, seg=56,
                           sect=16)]
    # back plate and bearing housing
    parts.append(mesh.revolve_closed(
        [(-16.0, 0.0), (-4.0, 0.0), (-4.0, R * 1.30), (-7.0, R * 1.34),
         (-13.0, R * 1.34), (-16.0, R * 1.30)], SM))
    parts.append(mesh.revolve_closed(
        [(-40.0, 0.0), (-16.0, 0.0), (-16.0, 20.0), (-24.0, 17.0),
         (-24.0, 13.0), (-40.0, 13.0)], SM))
    # the nose and its belt pulley
    # The pulley is on the accessory belt's plane, spec.FRONT["belt_x"].
    from parts.plumbing import pulley
    xp = spec.FRONT["belt_x"] - x0
    parts.append(mesh.tube(xp - 8.0, -38.0, 0.0, 12.0, SM))
    parts.append(pulley(xp, 46.0, bore=11.0))
    # impeller: a hub with six curved vanes
    parts.append(mesh.revolve_closed(
        [(-3.0, 0.0), (10.0, 0.0), (10.0, 9.0), (-1.0, 13.0),
         (-3.0, R * 0.74)], SM))
    for i in range(6):
        a0 = 2 * math.pi * i / 6
        rings = []
        for j in range(7):
            t = j / 6.0
            r = 12.0 + (R * 0.72 - 12.0) * t
            a = a0 + 0.62 * t                  # backswept
            ca, sa = math.cos(a), math.sin(a)
            nx, ny = -sa, ca                   # across the vane
            ring = []
            for (dx, dn) in ((-1.0, -1.3), (8.0 - 6.0 * t, -1.3),
                             (8.0 - 6.0 * t, 1.3), (-1.0, 1.3)):
                ring.append((dx, r * ca + nx * dn, r * sa + ny * dn))
            rings.append(ring)
        parts.append(shapes._loft_closed(rings))
    # inlet eye and the tangential outlet off the big end of the scroll
    parts.append(mesh.revolve_closed(
        [(10.0, 13.0), (30.0, 13.0), (30.0, 19.0), (33.0, 19.0),
         (33.0, 23.0), (10.0, 23.0)], SM))
    # the outlet runs inboard and down, toward the crankcase's front face
    # under the timing case, which is where the water goes in
    ov, of = mesh.pipe([(0.0, -R * 1.18, 0.0), (0.0, -R * 1.55, -8.0),
                        (6.0, -R * 1.9, -14.0)], [20.0, 18.5, 17.0], SM,
                       subdiv=3)
    parts.append((ov, of))
    parts.append(mesh.flange(0.0, 0.0, 0.0, 0.0, 0) if False else
                 mesh.tube(-16.0, -12.0, 13.0, 21.0, SM))
    v, f = mesh.join(*parts)
    return {"pump_water": ([(px + x0, py + cy, pz + cz)
                            for (px, py, pz) in v], f)}

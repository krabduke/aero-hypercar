"""Flywheel, clutch, bellhousing, oil and water pumps.

These were five tubes. A flywheel with no ring gear cannot be started, a
clutch with no diaphragm cannot be released, and a water pump that is a
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
    """A stepped disc with a starter ring gear shrunk onto it.

    The friction face is flat and the back is relieved to get the weight out
    of it, because every gram at 96 mm radius is inertia the engine has to
    accelerate twice per gearchange.
    """
    x = spec.BLOCK["x_rear"] + 20.0
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
    parts.append(shapes.gear_ring(x - 1.0, x + 9.0, R, R + 7.5, 104, R - 2.0))
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
    x = spec.BLOCK["x_rear"] + 44.0
    R = A["flywheel_r"] * 0.86
    parts = []
    # cover: a pressing with a bolt flange at the rim
    parts.append(mesh.revolve_closed(
        [(x, 38.0), (x + 4.0, 38.0),
         (x + 4.0, R - 16.0), (x + 15.0, R - 10.0),
         (x + 15.0, R), (x + 18.0, R),
         (x + 18.0, R - 6.0), (x + 11.0, R - 12.0),
         (x + 11.0, 42.0), (x, 42.0)], SEG))
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
    # plate pack: four carbon plates with drive lugs, on a splined hub
    for k in range(4):
        px0 = x - 16.0 + k * 3.6
        parts.append(mesh.tube(px0, px0 + 2.2, 30.0, R - 14.0, SEG))
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
    parts = [mesh.revolve_closed(
        [(x, R - 11.0), (x + L, R - 11.0),
         (x + L, R - 2.0), (x + L - 9.0, R - 4.0),
         (x + 9.0, R - 6.0), (x, R)], SEG)]
    parts.append(mesh.flange(x, R - 12.0, R + 14.0, 9.0, 12, bolt_r=6.5))
    parts.append(mesh.flange(x + L - 9.0, R - 12.0, R + 12.0, 9.0, 12,
                             bolt_r=6.5))
    for i in range(10):                        # stiffening ribs
        a = 2 * math.pi * i / 10
        rv, rf = shapes.rounded_box(0.0, 0.0, 0.0, L - 22.0, 9.0, 12.0, 3.0)
        parts.append(([(px + x + L / 2, py + math.cos(a) * (R + 3.0),
                        pz + math.sin(a) * (R + 3.0))
                       for (px, py, pz) in rv], rf))
    # starter aperture: a boss on the barrel with the pinion poking through
    a = math.radians(215.0)
    cy, cz = math.cos(a) * (R - 4.0), math.sin(a) * (R - 4.0)
    bv, bf = mesh.revolve_open(
        [(0.0, 0.0), (0.0, 30.0), (16.0, 27.0), (16.0, 0.0)], SM,
        cap_start=True, cap_end=True)
    parts.append(([(pz + x + 26.0, py + cy * 1.06, px * 0.0 + cz * 1.06)
                   for (px, py, pz) in bv], bf))
    return {"bellhousing": mesh.join(*parts)}


def _oil_pump():
    """A dry-sump pump: one pressure stage and four scavenge stages stacked on
    a common shaft, each its own body with its own port.

    A wet sump has one pump. A dry sump has to pull oil back out of the
    crankcase faster than the rings throw it in, which is why the stack is
    longer than the pressure section it feeds.
    """
    # driven off the crank nose but lying back alongside the pan, which is
    # where there is room for a stack this long
    x0 = spec.BLOCK["x_front"] + 4.0
    # outboard of the MGU-K rotor, which is 84 mm in radius on the crank
    # nose and shares this station
    cy, cz = -192.0, -14.0
    R = A["oil_pump_r"]
    parts = []
    x = 0.0
    for k in range(5):
        w = 15.0 if k else 21.0            # the pressure stage is wider
        r = R if k else R * 1.08
        parts.append(mesh.revolve_closed(
            [(x, 11.0), (x + w, 11.0),
             (x + w, r - 3.0), (x + w - 2.0, r),
             (x + 2.0, r), (x, r - 3.0)], SM))
        parts.append(mesh.tube(x + w, x + w + 2.4, 11.0, r * 0.94, SM))
        # the port out of each stage, clocked round so they do not collide
        a = math.radians(40.0 + 62.0 * k)
        pv, pf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 10.5), (17.0, 10.5), (19.0, 13.0),
             (23.0, 13.0), (23.0, 0.0)], SM // 2, cap_start=True,
            cap_end=True)
        parts.append(([(pz + x + w / 2, py + math.cos(a) * px,
                        math.sin(a) * px) for (px, py, pz) in pv], pf))
        x += w + 2.4
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
    # Aft of the MGU-K rotor, which occupies x -340..-232 on the crank
    # nose. The pump's outlet scroll swings inboard to 62 mm from the
    # centreline, so it cannot share a station with an 84 mm rotor.
    x0 = spec.BLOCK["x_front"] + 14.0
    # Outboard of the MGU-K, which is a 84.5 mm radius rotor on the crank
    # axis at this station -- the pump used to reach in to y = 1 and pass
    # straight through it.
    cy, cz = 200.0, -34.0
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
    ov, of = mesh.pipe([(0.0, -R * 1.18, 0.0), (0.0, -R * 1.6, 26.0),
                        (0.0, -R * 1.7, 62.0)], [20.0, 18.5, 17.0], SM,
                       subdiv=3)
    parts.append((ov, of))
    parts.append(mesh.flange(0.0, 0.0, 0.0, 0.0, 0) if False else
                 mesh.tube(-16.0, -12.0, 13.0, 21.0, SM))
    v, f = mesh.join(*parts)
    return {"pump_water": ([(px + x0, py + cy, pz + cz)
                            for (px, py, pz) in v], f)}

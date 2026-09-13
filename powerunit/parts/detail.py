"""The hardware that makes an engine an engine rather than a shape.

Valve springs and their retainers, the timing gear train, oil and water pumps
with their pickups and housings, turbo rotating assemblies, fasteners, sensors,
heat shields and the dry-sump plumbing.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import common

H = spec.HEAD
V = spec.VALVE
CM = spec.CAM
T = spec.TURBO
A = spec.ANCILLARY
SM = spec.RES["small_revolve"]


def build():
    out = {}
    out.update(_valve_gear())
    out.update(_timing())
    out.update(_pumps())
    out.update(_turbo_internals())
    out.update(_fasteners())
    out.update(_sensors())
    out.update(_heat_shields())
    out.update(_dry_sump())
    return out


# --------------------------------------------------------------------------

def _coil_spring(r, length, turns, wire_r, segs=8):
    """A real helical spring, swept along its own helix."""
    pts = []
    n = max(int(turns * segs), 8)
    for i in range(n + 1):
        t = i / n
        a = 2 * math.pi * turns * t
        pts.append((length * t, r * math.cos(a), r * math.sin(a)))
    return mesh.pipe(pts, wire_r, 7, caps=True)


def _valve_gear():
    """Two springs, a retainer and a bucket tappet per valve."""
    springs, retainers, buckets = [], [], []
    inc = math.radians(V["included_angle"] / 2)
    for (n, pair, bank, x, a) in spec.cylinders():
        for k, (is_in, sgn_y) in enumerate(((True, -1), (True, 1),
                                            (False, -1), (False, 1))):
            hr = V["intake_head_r"] if is_in else V["exhaust_head_r"]
            tilt = inc * (1 if is_in else -1)
            xo = x + sgn_y * hr * 0.95

            sv, sf = _coil_spring(9.0, 34.0, 6.0, 1.7)
            sv = [(px * math.cos(tilt) - py * math.sin(tilt),
                   px * math.sin(tilt) + py * math.cos(tilt), pz)
                  for (px, py, pz) in sv]
            sv = common.along_bank(sv, xo, spec.DECK_HEIGHT + 26.0, bank)
            springs.append((f"{n}_{k}", (sv, sf)))

            rv, rf = mesh.tube(-3.0, 3.0, 3.2, 12.5, 16)
            rv = [(pz, py, px) for (px, py, pz) in rv]
            rv = common.along_bank(rv, xo, spec.DECK_HEIGHT + 62.0, bank)
            retainers.append((f"{n}_{k}", (rv, rf)))

            bv, bf = mesh.tube(-9.0, 9.0, 11.0, 14.0, 18)
            bv = [(pz, py, px) for (px, py, pz) in bv]
            bv = common.along_bank(bv, xo, spec.DECK_HEIGHT + 74.0, bank)
            buckets.append((f"{n}_{k}", (bv, bf)))
    out = {}
    # one object per valve: a spring is a service item, not a texture
    for (tag, m) in springs:
        out[f"valve_spring_{tag}"] = m
    for (tag, m) in retainers:
        out[f"retainer_{tag}"] = m
    for (tag, m) in buckets:
        out[f"tappet_{tag}"] = m
    return out


def _timing():
    """Gear train off the crank nose driving all four camshafts. A gear train
    rather than a belt or chain: at 16,000 rpm valve timing has to be exact."""
    parts = []
    x = spec.BLOCK["x_front"] - 30.0
    # crank gear
    parts.append(_gear(x, 0.0, 0.0, 54.0, 28))
    # idlers up each side of the vee
    for bank in (0, 1):
        for k, (along, r) in enumerate(((70.0, 40.0), (140.0, 40.0))):
            p = common.bank_point(x, along, 0.0, bank)
            parts.append(_gear(x, p[1], p[2], r, 20))
        # cam gears
        for lat in (-H["cam_centres"] / 2, H["cam_centres"] / 2):
            p = common.bank_point(x, spec.DECK_HEIGHT + H["cam_height"],
                                  lat, bank)
            parts.append(_gear(x, p[1], p[2], 46.0, 24))
    # covers the gear train without swallowing the whole front of the engine
    cover = mesh.tube(x - 22.0, x - 4.0, 0.0, 152.0, 40)
    return {"timing_gears": mesh.join(*parts), "timing_cover": cover}


def _gear(x, y, z, r, teeth):
    parts = [mesh.tube(x - 7.0, x + 7.0, r * 0.28, r * 0.88, 26)]
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        tv, tf = shapes.rounded_box(x, r * 0.94, 0.0, 13.0, r * 0.16, 5.2, 0.7)
        tv = mesh.rot_x(tv, a)
        parts.append(([(px, py + y, pz + z) for (px, py, pz) in tv], tf))
    v, f = mesh.join(*parts)
    v = [(px, py + (0.0 if abs(y) < 1e-9 else 0.0), pz) for (px, py, pz) in v]
    # the hub was built about the axis; shift it to the gear centre
    hub_v, hub_f = mesh.tube(x - 7.0, x + 7.0, r * 0.28, r * 0.88, 26)
    hub_v = [(px, py + y, pz + z) for (px, py, pz) in hub_v]
    return mesh.join((hub_v, hub_f), (v, f))


def _pumps():
    """Oil and water pumps with their pickups and housings."""
    out = {}
    parts = []
    xo = spec.BLOCK["x_front"] - 16.0
    # oil pump body, pickup and pressure line
    parts.append(mesh.pipe([(xo, -86.0, -46.0), (xo + 60.0, -96.0, -110.0),
                            (xo + 190.0, -60.0, -132.0)], 13.0, 12))
    pv, pf = shapes.rounded_box(xo + 200.0, -50.0, -140.0, 120.0, 70.0, 26.0,
                                   9.0, draft=2.0)
    parts.append((pv, pf))
    out["oil_pickup"] = mesh.join(*parts)

    wp = []
    wp.append(mesh.pipe([(xo, 86.0, -34.0), (xo - 40.0, 120.0, 30.0),
                         (xo - 30.0, 130.0, 120.0)], 17.0, 12))
    tv, tf = mesh.tube(xo - 50.0, xo - 10.0, 0.0, 44.0, 22)
    tv = [(px, py + 130.0, pz + 150.0) for (px, py, pz) in tv]
    wp.append((tv, tf))
    out["coolant_plumbing"] = mesh.join(*wp)
    return out


def _turbo_internals():
    """Compressor and turbine wheels on the shaft inside each housing."""
    parts = []
    for i, x in enumerate(T["x"]):
        shaft = mesh.tube(x - T["housing_w"], x + T["housing_w"],
                          0.0, T["shaft_r"], 16)
        parts.append(([(px, py, pz + T["z"]) for (px, py, pz)
                       in shaft[0]], shaft[1]))
        for (xc, r, blades, back) in ((x - T["housing_w"] * 0.6,
                                       T["turb_r"] * 0.64, 11, True),
                                      (x + T["housing_w"] * 0.6,
                                       T["comp_r"] * 0.66, 9, False)):
            hub = mesh.revolve_open(
                [(xc - 16.0, 0.001), (xc - 16.0, 15.0), (xc + 16.0, 9.0),
                 (xc + 16.0, 0.001)], 18, cap_start=True, cap_end=True)
            parts.append(([(px, py, pz + T["z"]) for (px, py, pz) in hub[0]],
                          hub[1]))
            for k in range(blades):
                a = 2 * math.pi * k / blades
                bv, bf = shapes.rounded_box(xc, (15.0 + r) / 2, 0.0, 22.0, r - 15.0, 3.4, 1.0)
                pitch = math.radians(34.0 if back else -30.0)
                bv = [(px * math.cos(pitch) - pz * math.sin(pitch), py,
                       px * math.sin(pitch) + pz * math.cos(pitch))
                      for (px, py, pz) in bv]
                bv = mesh.rot_x(bv, a)
                parts.append(([(px, py, pz + T["z"]) for (px, py, pz) in bv], bf))
    return {"turbo_wheels": mesh.join(*parts)}


def _fasteners():
    """Head studs, cam cover bolts and sump bolts."""
    parts = []
    for bank in (0, 1):
        for (n, pair, b2, x, a) in spec.cylinders():
            if b2 != bank:
                continue
            for sgn in (-1, 1):
                sv, sf = mesh.cylinder(0.0, 132.0, 5.0, 8)
                sv = [(pz, py, px) for (px, py, pz) in sv]
                sv = common.along_bank(sv, x, spec.DECK_HEIGHT - 10.0, bank,
                                       sgn * (spec.BORE / 2 + 13.0))
                parts.append((sv, sf))
    sump = []
    a = spec.ANCILLARY
    z = -spec.BLOCK["skirt_depth"] - 22.0
    for k in range(18):
        f = k / 17
        x = -a["sump_len"] / 2 + a["sump_len"] * f
        for sgn in (-1, 1):
            bv, bf = mesh.cylinder(0.0, 14.0, 4.4, 8)
            bv = [(pz + x, py + sgn * a["sump_w"] / 2, px + z - 14.0)
                  for (px, py, pz) in bv]
            sump.append((bv, bf))
    return {"head_studs": mesh.join(*parts), "sump_bolts": mesh.join(*sump)}


def _sensors():
    """Crank and cam position sensors, knock sensors, oil and coolant pickups."""
    parts = []
    spots = [(spec.BLOCK["x_front"] + 20.0, 150.0, -40.0),
             (spec.BLOCK["x_rear"] - 40.0, -150.0, -30.0),
             (0.0, 168.0, 20.0), (-90.0, -168.0, 20.0),
             (120.0, 0.0, -spec.BLOCK["skirt_depth"] - 30.0)]
    for (x, y, z) in spots:
        v, f = mesh.cylinder(0.0, 46.0, 9.0, 10)
        v = [(pz + x, px + y, py + z) for (px, py, pz) in v]
        parts.append((v, f))
        cv, cf = shapes.rounded_box(x, y * 1.12, z + 26.0, 26.0, 22.0, 20.0, 4.0)
        parts.append((cv, cf))
    return {"sensors": mesh.join(*parts)}


def _sheet(rows, t):
    """Give a grid of stations thickness in z and close it into a solid."""
    nr, nc = len(rows), len(rows[0])
    lo = [(x, y, z - t/2) for r in rows for (x, y, z) in r]
    hi = [(x, y, z + t/2) for r in rows for (x, y, z) in r]
    verts = lo + hi
    o = len(lo)
    faces = []
    for i in range(nr - 1):
        for j in range(nc - 1):
            k = i*nc + j
            faces.append((k, k+nc, k+nc+1, k+1))
            faces.append((o+k, o+k+1, o+k+nc+1, o+k+nc))
    for i in range(nr - 1):
        for j in (0, nc - 1):
            k = i*nc + j
            faces.append((k, k+nc, o+k+nc, o+k) if j == 0
                         else (k+nc, k, o+k, o+k+nc))
    for j in range(nc - 1):
        for i in (0, nr - 1):
            k = i*nc + j
            faces.append((k+1, k, o+k, o+k+1) if i == 0
                         else (k, k+1, o+k+1, o+k))
    return verts, faces


def _heat_shields():
    """Shields over the hot vee, keeping radiant heat off the plenum."""
    parts = []
    for sgn in (-1.0, 1.0):
        # a heat shield is pressed sheet that wraps what it shields, with a
        # swaged rib down it for stiffness -- not a flat plate floating above
        x0 = spec.BLOCK["x_front"] + 45.0
        x1 = spec.BLOCK["x_rear"] - 45.0
        rows = []
        for i in range(9):
            fx = i / 8
            x = x0 + (x1 - x0) * fx
            row = []
            for j in range(7):
                fy = j / 6
                y = sgn * (52.0 + 62.0 * fy)
                # curve it around the manifold below
                dz = -26.0 * (1 - math.cos((fy - 0.5) * 2.2)) \
                     - 5.0 * math.sin(fx * math.pi * 3.0)
                row.append((x, y, T["z"] + 62.0 + dz))
            rows.append(row)
        parts.append(_sheet(rows, 2.4))
    return {"heat_shields": mesh.join(*parts)}


def _dry_sump():
    """Scavenge and pressure lines running to the tank."""
    parts = []
    z = -spec.BLOCK["skirt_depth"] - 40.0
    for i, sgn in enumerate((-1.0, 1.0)):
        parts.append(mesh.pipe(
            [(spec.BLOCK["x_rear"] - 40.0, sgn * 110.0, z),
             (60.0, sgn * 150.0, z - 16.0),
             (spec.BLOCK["x_front"] + 10.0, sgn * 120.0, -10.0)],
            11.0, 10))
    return {"dry_sump_lines": mesh.join(*parts)}

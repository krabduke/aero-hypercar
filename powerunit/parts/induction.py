"""Twin airboxes, eight individual throttles and secondary port injection.

The direct injectors belong to heads.py; port injectors use distinct names
so assembly cannot silently replace the direct-injection meshes.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh

SM = spec.RES["small_revolve"]
import shapes
import gaspath
from parts import common

I = spec.INTAKE
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_plenum())
    out.update(_trumpets())
    out.update(_injection())
    return out


def _injection():
    """Port injection: one injector into each runner, on its own low-pressure
    rail.

    `_pfi_`, because heads.py already has a direct injector in every chamber
    and both were called `injector_n`. Two systems is deliberate -- direct
    injection alone cannot keep a 350 bar chamber clean of intake-valve
    deposits, and port injection alone cannot cool the charge in the cylinder,
    so a high-output engine that has to idle and to pull 16,000 rpm carries
    both and crosses over between them with load. What was not deliberate was
    giving them the same names, which left assembly building two objects per
    injector and the high-pressure feeds pointing at the low-pressure rail.
    """
    out = {}
    rail_points = {0: [], 1: []}
    for n, pair, bank, x, a in spec.cylinders():
        port = gaspath.intake_port(bank, x)
        runner = gaspath.runner_path(bank, x)[-2]
        d, lat = common.bank_dir(bank), common.bank_lat(bank)
        tip = tuple((port[k] + runner[k]) / 2 for k in range(3))
        profile = [(0.0, 0.0), (0.0, 3.0), (12.0, 3.0),
                   (14.0, 7.0), (38.0, 7.0), (40.0, 9.0),
                   (46.0, 9.0), (48.0, 4.0), (48.0, 0.0)]
        verts, faces = mesh.revolve_closed(profile, SM)
        verts = [(tip[0] + py,
                  tip[1] - lat[1] * px + d[1] * pz,
                  tip[2] - lat[2] * px + d[2] * pz)
                 for px, py, pz in verts]
        if lat[1] * d[2] - lat[2] * d[1] < 0.0:
            faces = [tuple(reversed(face)) for face in faces]
        out[f"pfi_injector_{n}"] = (verts, faces)
        plug = (tip[0] + 10.0, tip[1] - lat[1] * 28.0,
                tip[2] - lat[2] * 28.0)
        out[f"pfi_plug_{n}"] = shapes.connector(*plug, 14.0, 12.0, 10.0, 2)
        inlet = tuple(tip[k] - lat[k] * 48.0 for k in range(3))
        rail = tuple(tip[k] - lat[k] * 68.0 for k in range(3))
        rail_points[bank].append(rail)
        out[f"pfi_feed_{n}"] = mesh.pipe([inlet, rail], 3.5, SM)
    ends = []
    for bank, tag in ((0, "l"), (1, "r")):
        points = sorted(rail_points[bank])
        start = (points[0][0] - 18.0, *points[0][1:])
        end = (points[-1][0] + 18.0, *points[-1][1:])
        out[f"fuel_rail_pfi_{tag}"] = mesh.pipe([start, *points, end], 7.0, SM)
        ends.append(end)
        # 24 segments, not 6. At 6 this was a 32-vertex hexagonal stub, well
        # under the 120-vertex floor the geometry audit sets -- invisible
        # until the build was current enough for the audit to see it.
        out[f"fuel_rail_pfi_union_{tag}"] = mesh.pipe(
            [(end[0] - 6.0, *end[1:]), (end[0] + 6.0, *end[1:])], 10.0, 24)
    # Behind the block, not through it.
    #
    # This ran straight across the engine at the rails' own height, z 49,
    # which at y = 0 is inside the crankshaft's counterweight circle: a fuel
    # line through the crank, with block_bank_l and block_bank_r on the way.
    # `audit_intersect` allowed it, because ("fuel_rail_", "block_") and the
    # crank are both on its list of overlaps that are meant to be there.
    #
    # x 226 is aft of the block banks (222), the heads (218) and the water
    # outlets, and forward of the bellhousing flange (235). 110 mm up clears
    # the crankcase, which stops at z 28, and stays under the inverter at 153.
    rear = spec.BLOCK["x_rear"] - 6.0
    over = 110.0
    out["fuel_rail_pfi_crossover"] = mesh.pipe(
        [ends[0], (rear, *ends[0][1:]), (rear, ends[0][1], over),
         (rear, ends[1][1], over), (rear, *ends[1][1:]), ends[1]], 4.0, SM,
        subdiv=3)
    return out


def _plenum():
    """A plenum outboard of each bank, feeding that bank's four ports.

    See the note in `spec.INTAKE`: the hot vee puts the intake ports on the
    outside of the heads, so this is where the air has to come from.
    """
    out = {}
    for bank, tag in ((0, "l"), (1, "r")):
        sgn = -1.0 if bank == 0 else 1.0
        y = sgn * I["plenum_y"]
        # A closed vessel with domed ends and a bolted end cap, not an
        # open-ended tube: as a tube it showed two black holes down the
        # front of the engine and held no pressure at all.
        L, R = I["plenum_len"] / 2, I["plenum_r"]
        v, f = mesh.revolve_closed(
            [(-L - 26.0, 0.0), (-L - 24.0, R * 0.34), (-L - 16.0, R * 0.72),
             (-L - 6.0, R * 0.94), (-L, R), (-L + 8.0, R * 1.04),
             (L - 8.0, R * 1.04), (L, R), (L + 6.0, R * 0.94),
             (L + 16.0, R * 0.72), (L + 24.0, R * 0.34), (L + 26.0, 0.0)],
            SEG)
        v = [(x, py + y, pz + I["plenum_z"]) for (x, py, pz) in v]
        out[f"plenum_{tag}"] = (v, f)
        # throttle body on the front face of each
        # body, mounting flange and the butterfly on its spindle
        tr = I["throttle_r"]
        # A stub on the plenum's OUTBOARD face at mid-length.
        #
        # Nowhere else will take it. The front of this engine is a gear
        # tower reaching 241 mm out to drive the cams; aft of the block the
        # car's bodywork has closed in to 252 mm; and the intake camshaft
        # sits directly above the plenum's crown. Outboard is the sidepod,
        # which is 456 mm of room at this height.
        tr = I["throttle_r"]
        h0 = I["plenum_r"] * 0.86
        tparts = [mesh.tube(h0, h0 + 56.0, tr - 7.0, tr, 32)]
        tparts.append(mesh.tube(h0 + 48.0, h0 + 56.0, tr, tr + 10.0, 32))
        tparts.append(mesh.tube(h0, h0 + 7.0, tr, tr + 10.0, 32))
        bv, bf = mesh.revolve_closed(
            [(-2.0, 0.0), (-2.0, tr - 8.0), (2.0, tr - 8.0), (2.0, 0.0)], 32)
        tparts.append(([(px + h0 + 27.0, py, pz) for (px, py, pz) in bv], bf))
        sv, sf = mesh.cylinder(-tr, tr, 4.0, 14)
        tparts.append(([(pz + h0 + 27.0, py, px) for (px, py, pz) in sv], sf))
        tv, tf = mesh.join(*tparts)
        # the lathe runs along its own +x; point it outboard, along y
        tv = [(pz, sgn * px + y, py + I["plenum_z"]) for (px, py, pz) in tv]
        out[f"throttle_{tag}"] = (tv, tf)
    return out


def _trumpets():
    """One velocity stack per cylinder, standing inside its bank's plenum and
    pointing at that cylinder's runner mouth."""
    parts = []
    for (n, pair, bank, x, a) in spec.cylinders():
        sgn = -1.0 if bank == 0 else 1.0
        prof = [(0.0, I["trumpet_r_in"]),
                (I["trumpet_len"] * 0.62, I["trumpet_r_in"]),
                (I["trumpet_len"], I["trumpet_r_out"]),
                (I["trumpet_len"], I["trumpet_r_out"] - 3.0),
                (I["trumpet_len"] * 0.62, I["trumpet_r_in"] - 3.0),
                (0.0, I["trumpet_r_in"] - 3.0)]
        tv, tf = mesh.revolve_closed(prof, 26)
        # the lathe runs along its own +x; the stack points inboard, from the
        # outboard wall of the plenum towards the runner mouth
        tv = [(pz + x,
               sgn * (I["plenum_y"] + I["plenum_r"] * 0.6 - px),
               py + I["plenum_z"])
              for (px, py, pz) in tv]
        parts.append((tv, tf))
    return {"trumpets": mesh.join(*parts)}

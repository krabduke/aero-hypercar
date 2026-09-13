"""Vortex-lattice analysis of the VX-1's wings, in ground effect.

What this does and does not do, stated up front because it decides how the
numbers should be read:

  * It solves the front wing (four elements), the rear wing (two elements) and
    the beam wing as a coupled lattice, with the track modelled exactly as a
    streamline via image vortices. That gives a real answer for how much
    downforce the wings make, how it splits front to rear, and how both change
    with ride height.

  * It does NOT model the floor, the venturi tunnels, the diffuser or the
    fans. Those are the car's main downforce source and they are viscous,
    ducted and fan-driven -- none of which a potential-flow lattice can touch.
    The floor and fan figures in spec.py come from the performance model, not
    from here, and this analysis does not attempt to confirm them.

  * It is inviscid: no profile drag, no separation, no stall. Induced drag is
    taken from the Trefftz plane; total drag will be higher than CDi.

Run:  python3 aero/analyse.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "car"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import spec
import vlm

MM = 0.001
RHO = vlm.RHO


# --------------------------------------------------------------------------
# Build the lattice from the same spec the geometry is built from
# --------------------------------------------------------------------------

def surfaces(ride_height_mm=0.0):
    """Every wing element as a VLM surface, in metres, above the track.

    `ride_height_mm` raises the whole car, so the same model answers "what
    happens if the car runs 10 mm higher" without editing anything.
    """
    dz = ride_height_mm * MM
    out = []
    FW = spec.FRONT_WING
    half = FW["span"] / 2 * MM
    neutral = FW["neutral_half_w"] * MM

    for k, (dx, dzf, c_r, c_t, span_f, aoa_r, aoa_t, rise) in enumerate(
            FW["stack"]):
        tip = half * span_f
        z_root = (FW["z"] + dzf) * MM + dz
        if k == 0:
            z_root += FW["arch"] * MM
        z_tip = (FW["z"] + dzf + rise) * MM + dz
        # the element is split at the neutral station, because inboard of it
        # the chord, incidence and height are all constant and outboard they
        # all vary -- one linear panel cannot represent both
        out.append(vlm.Surface(
            f"front_{k}", (FW["x"] * MM + dx * MM, 0.0, z_root), c_r * MM,
            (FW["x"] * MM + dx * MM, neutral, z_root), c_r * MM,
            n_span=2, n_chord=3, twist_root=-aoa_r, twist_tip=-aoa_r))
        out.append(vlm.Surface(
            f"front_{k}", (FW["x"] * MM + dx * MM, neutral, z_root), c_r * MM,
            (FW["x"] * MM + dx * MM, tip, z_tip), c_t * MM,
            n_span=6, n_chord=3, twist_root=-aoa_r, twist_tip=-aoa_t))

    RW = spec.REAR_WING
    for k in range(RW["elements"]):
        chord = RW["chord"] * (1.0 - 0.42 * k) * MM
        x = (RW["x"] + k * RW["chord"] * 0.46) * MM
        z = (RW["z"] + k * (RW["gap"] + 26.0)) * MM + dz
        aoa = RW["aoa"] + k * 12.0
        b = RW["span"] / 2 * MM
        out.append(vlm.Surface(f"rear_{k}", (x, 0.0, z), chord,
                               (x, b, z), chord * 0.95,
                               n_span=7, n_chord=3,
                               twist_root=-aoa, twist_tip=-aoa))

    BW = spec.BEAM_WING
    for k in range(BW["elements"]):
        chord = BW["chord"] * (1.0 - 0.30 * k) * MM
        x = (BW["x"] + k * BW["chord"] * 0.5) * MM
        z = (BW["z"] + k * 40.0) * MM + dz
        b = BW["span"] / 2 * MM
        out.append(vlm.Surface(f"beam_{k}", (x, 0.0, z), chord,
                               (x, b, z), chord * 0.92,
                               n_span=5, n_chord=3,
                               twist_root=-BW["aoa"], twist_tip=-BW["aoa"]))
    return out


def reference():
    """s_ref, c_ref, b_ref -- total planform area of the modelled elements."""
    s = 0.0
    for surf in surfaces():
        span = abs(surf.le_tip[1] - surf.le_root[1])
        s += 2.0 * span * 0.5 * (surf.chord_root + surf.chord_tip)
    return s, spec.FRONT_WING["chord"] * MM, spec.FRONT_WING["span"] * MM


def split(surfs, gamma, v_inf):
    """Fraction of the bound circulation carried by each wing group.

    Strip theory on the bound segments (dL = rho V Gamma dy) is enough to
    split the total: it is a ratio, so the solver's internal scaling cancels.
    """
    panels = []
    for s in surfs:
        panels.extend(s.panels())
    tot = {}
    for p, g in zip(panels, gamma):
        key = p["surface"].split("_")[0]
        tot[key] = tot.get(key, 0.0) + g * p["dy"]
    grand = sum(tot.values())
    return {k: v / grand for k, v in tot.items()} if grand else {}


# --------------------------------------------------------------------------

def kph(v):
    return v * 3.6


def main():
    s_ref, c_ref, b_ref = reference()
    print(f"\n{spec.NAME} -- vortex-lattice analysis of the wings")
    print("=" * 70)
    print(f"  modelled elements   {len(surfaces())} panels groups, "
          f"{sum(len(s.panels()) for s in surfaces())} panels")
    print(f"  reference area      {s_ref:.3f} m^2 (wings only)")
    print(f"  reference chord     {c_ref:.3f} m")
    print(f"  reference span      {b_ref:.3f} m")

    v = 250 / 3.6
    surfs = surfaces()
    ge = vlm.solve(surfs, 0.0, v, s_ref, c_ref, b_ref, ground=True)
    free = vlm.solve(surfs, 0.0, v, s_ref, c_ref, b_ref, ground=False)

    q = 0.5 * RHO * v * v
    df_ge = -ge.CL * q * s_ref
    df_free = -free.CL * q * s_ref

    print("\nGROUND EFFECT (at 250 km/h, wings only)")
    print(f"  in free air         {df_free / 9.81:8.1f} kg    CL {free.CL:+.3f}")
    print(f"  over the track      {df_ge / 9.81:8.1f} kg    CL {ge.CL:+.3f}")
    print(f"  gain from the ground{(df_ge / df_free - 1) * 100:+8.1f} %")
    print(f"  induced drag        {ge.CDi * q * s_ref / 9.81:8.1f} kg-force"
          f"    CDi {ge.CDi:.4f}")
    print(f"  lift/induced drag   {abs(ge.CL / ge.CDi):8.1f}")

    fr = split(surfs, ge.gamma, v)
    front = fr.get("front", 0.0)
    rear = fr.get("rear", 0.0) + fr.get("beam", 0.0)
    print("\nBALANCE (share of wing downforce)")
    for k in ("front", "rear", "beam"):
        if k in fr:
            print(f"  {k:18s}{fr[k] * 100:8.1f} %")
    print(f"  front of the wings  {front / (front + rear) * 100:8.1f} % front")
    print(f"  spec aero balance   {spec.AERO['aero_balance'] * 100:8.1f} %"
          f" front (whole car, incl. floor and fans)")
    print("  NOTE: read the front share as a floor, not a figure. A lattice")
    print("  cannot model a slotted multi-element wing -- the slot flow that")
    print("  makes the four front elements work is viscous, so they shadow")
    print("  each other here and the front wing is under-read. The real")
    print("  front balance also comes mostly from the floor, not the wing.")

    # Incompressible potential flow has no Reynolds or Mach dependence, so CL
    # and CDi are the same at every speed and the forces scale with V^2. This
    # is the one solve, scaled -- not six identical solves.
    print("\nSPEED SWEEP (wings only, in ground effect; CL scaled by V^2)")
    print(f"  {'km/h':>6} {'downforce kg':>14} {'CDi drag kg':>13}"
          f" {'% of car mass':>15}")
    for kmh in (100, 150, 200, 250, 300, 350):
        vv = kmh / 3.6
        qq = 0.5 * RHO * vv * vv
        d = -ge.CL * qq * s_ref / 9.81
        dr = ge.CDi * qq * s_ref / 9.81
        print(f"  {kmh:6d} {d:14.1f} {dr:13.1f} "
              f"{d / spec.MASS_KG * 100:15.1f}")

    print("\nRIDE HEIGHT SENSITIVITY (250 km/h)")
    print(f"  {'raise mm':>9} {'downforce kg':>14} {'change':>9}")
    base = None
    for raise_mm in (0, 10, 25, 50):
        s = vlm.solve(surfaces(raise_mm), 0.0, v, s_ref, c_ref, b_ref,
                      ground=True)
        d = -s.CL * q * s_ref / 9.81
        base = d if base is None else base
        print(f"  {raise_mm:9d} {d:14.1f} {(d / base - 1) * 100:8.1f} %")

    print("\nWhat this does not cover: the floor, the venturi tunnels, the")
    print("diffuser and the fans -- the car's main downforce source. They are")
    print("viscous, ducted and fan-driven; a potential-flow lattice cannot")
    print("model them, and no number above should be read as confirming them.")
    print("Drag here is induced drag only: no profile or pressure drag.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

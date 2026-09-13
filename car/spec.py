"""
VX-1 "Vortex" — ground-effect fan car, built to beat Formula 1 on an F1 circuit.

ALL dimensions are millimetres, masses kilograms, speeds km/h unless stated.
Origin is on the ground at the front axle centreline. +x is rearward, +y right,
+z up.

Every other module consumes this file. No geometry module contains a literal
dimension; if a number describes the car, it lives here.

THE ARGUMENT
------------
An F1 car is not slow because nobody can build a faster one. It is slow because
the regulations cap it: minimum mass 798 kg, a fixed floor geometry, no movable
aero beyond DRS, no fans, and a power unit limited to roughly 1000 hp. Remove
the rulebook and there are four places to take time, in order of value:

1. FAN-DRIVEN DOWNFORCE. Wings make downforce proportional to v^2, so they give
   almost nothing in slow corners -- exactly where lap time is lost. Two
   electrically driven fans extract air from sealed underfloor plenums and make
   downforce that barely varies with speed. This is the single biggest win and
   it is why the car is shaped around it.
2. GROUND EFFECT WITHOUT A RULEBOOK. Full-length venturi tunnels with a steep
   diffuser, sealed by skirts that the fans keep loaded.
3. ACTIVE AERO. Front and rear elements trim continuously, so the car is not
   forced to compromise between a low-drag straight and a high-downforce corner.
4. MASS AND POWER. 700 kg against F1's 798 kg minimum, and the RX-8V hybrid V8
   from the sibling project at 935 kW against roughly 750 kW.

Every number below is a design target, not a measurement.
"""

import math

NAME = "VX-1 Vortex"
CLASS = "Ground-effect fan car, hybrid V8"

# --------------------------------------------------------------------------
# Principal dimensions
# --------------------------------------------------------------------------

LENGTH = 4980.0
WIDTH = 1980.0
HEIGHT = 1015.0
WHEELBASE = 3150.0
TRACK_FRONT = 1660.0
TRACK_REAR = 1600.0

MASS_KG = 700.0                # with driver and fuel
MASS_DIST_REAR = 0.565         # fraction on the rear axle
CG_HEIGHT = 258.0

RIDE_HEIGHT_FRONT = 22.0
RIDE_HEIGHT_REAR = 58.0        # rake, which the tunnels need

# F1 reference, for the comparison the whole project is about
F1 = {
    "mass": 798.0, "power_kw": 750.0, "cla": 5.1, "cda": 1.45,
    "fan_downforce": 0.0, "mu": 1.75,
}

# --------------------------------------------------------------------------
# Aerodynamics
# --------------------------------------------------------------------------

AERO = {
    "cla_wings": 2.55,         # both wings, trimmed for a medium-downforce track
    "cla_floor": 3.35,         # venturi tunnels and diffuser
    "cda": 1.62,
    "frontal_area": 1.52,      # m^2, already folded into the coefficients
    "aero_balance": 0.445,     # fraction of downforce on the front axle
    "drs_cla_drop": 1.25,      # active aero shed on a straight
    "drs_cda_drop": 0.52,
}

FAN = {
    "n": 2,
    "diameter": 560.0,
    "x": 4180.0,
    "y": 460.0,
    "z": 330.0,
    "blades": 13,
    "rpm": 7200.0,
    "power_kw": 62.0,          # drawn from the hybrid system
    "downforce_kg": 650.0,     # near-constant, this is the point of the car
    "duct_r": 310.0,
}

TYRE_MU = 1.80                 # bespoke slick at the reference load
TYRE_LOAD_SENS = 0.12          # mu falls as (load / static load) ^ -k
DRIVER_G_LIMIT = 7.0           # sustained lateral g a trained driver can work at

# --------------------------------------------------------------------------
# Wheels and tyres
# --------------------------------------------------------------------------

WHEEL = {
    "rim_d": 457.2,            # 18 inch
    "front_w": 305.0, "front_od": 670.0,
    "rear_w": 405.0,  "rear_od": 690.0,
    "spokes": 7,
    "disc_r": 180.0, "disc_t": 32.0,
    "caliper_r": 205.0,
}

# --------------------------------------------------------------------------
# Chassis
# --------------------------------------------------------------------------

TUB = {
    "x_front": 620.0, "x_rear": 2360.0,
    "top_z": 720.0, "floor_z": 60.0,
    "half_w_front": 240.0, "half_w_rear": 390.0,
    "cockpit_x0": 1180.0, "cockpit_x1": 1980.0,
    "cockpit_half_w": 235.0,
}

NOSE = {
    "tip_x": 0.0, "tip_z": 265.0, "tip_half_w": 52.0,
    "base_x": 760.0, "base_z": 430.0,
}

FLOOR = {
    "x0": 600.0, "x1": 4620.0,
    "half_w": 850.0,
    "tunnel_half_w": 330.0,
    "tunnel_inner_y": 210.0,
    "throat_x": 2600.0, "throat_z": 96.0,
    "diffuser_x": 3780.0, "diffuser_exit_z": 392.0,
    "skirt_depth": 26.0,
    "n_strakes": 4,
}

FRONT_WING = {
    "x": 150.0, "z": 112.0,
    "span": 1780.0, "chord": 470.0,
    "elements": 4, "gap": 16.0,
    "endplate_h": 240.0, "endplate_t": 9.0,
    "aoa_root": 6.0, "aoa_tip": 14.0,
}

REAR_WING = {
    "x": 4620.0, "z": 880.0,
    "span": 1420.0, "chord": 360.0,
    "elements": 2, "gap": 22.0,
    "endplate_h": 360.0, "endplate_t": 10.0,
    "aoa": 17.0, "drs_aoa": 2.0,
    "pylon_t": 26.0,
}

SIDEPOD = {
    "x0": 1720.0, "x1": 3560.0,
    "inlet_h": 190.0, "inlet_w": 250.0,
    "max_half_w": 760.0,
    "top_z": 560.0,
}

HALO = {
    "x_front": 1160.0, "x_rear": 2000.0,
    "z": 960.0, "half_w": 330.0, "tube_r": 26.0,
}

# --------------------------------------------------------------------------
# Suspension
# --------------------------------------------------------------------------

SUSP = {
    "front_x": 0.0, "rear_x": WHEELBASE,
    "upper_z": 340.0, "lower_z": 150.0,
    "inboard_front_y": 250.0, "inboard_rear_y": 300.0,
    "upright_h": 300.0,
    "arm_r": 17.0, "rod_r": 13.0,
    "front_layout": "pushrod", "rear_layout": "pullrod",
}

POWERTRAIN = {
    "engine_x": 2980.0, "engine_z": 330.0,
    "gearbox_x": 3760.0, "gearbox_len": 520.0, "gearbox_r": 175.0,
    "radiator": (600.0, 96.0, 330.0),
    "rad_x": 2320.0, "rad_y": 336.0, "rad_z": 320.0,
    "battery": (760.0, 300.0, 110.0),
    "battery_x": 2420.0, "battery_z": 150.0,
    "fuel_x": 2380.0, "fuel": (560.0, 420.0, 320.0),
}

# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

MATERIAL_MAP = {
    "tub": "carbon_gloss", "nose": "carbon_gloss", "floor": "carbon_matte",
    "tunnel": "carbon_matte", "diffuser": "carbon_matte", "strake": "carbon_matte",
    "wing": "carbon_gloss", "endplate": "carbon_gloss", "flap": "carbon_gloss",
    "pylon": "carbon_gloss", "sidepod": "carbon_gloss", "engine_cover": "carbon_gloss",
    "airbox": "carbon_gloss", "halo": "titanium", "skirt": "rubber_seal",
    "tyre": "rubber_tyre", "rim": "alu_dark", "disc": "cf_disc",
    "caliper": "alu_bright", "upright": "alu_bright",
    "wishbone": "carbon_matte", "pushrod": "carbon_matte", "pullrod": "carbon_matte",
    "trackrod": "carbon_matte", "rocker": "alu_bright",
    "fan": "alu_bright", "fanduct": "carbon_matte",
    "radiator": "rad_core", "battery": "anodised", "fuel": "anodised",
    "gearbox": "magnesium", "driveshaft": "steel",
    "seat": "carbon_matte", "wheelrim": "alu_dark", "steering": "carbon_matte",
    "engine": "alu_cast",
}
DEFAULT_MATERIAL = "carbon_matte"

PALETTE = {
    "carbon_gloss": ((0.042, 0.044, 0.050), 0.45, 0.16),
    "carbon_matte": ((0.052, 0.054, 0.060), 0.30, 0.48),
    "titanium":     ((0.372, 0.386, 0.408), 1.00, 0.34),
    "rubber_tyre":  ((0.030, 0.030, 0.032), 0.00, 0.82),
    "rubber_seal":  ((0.050, 0.048, 0.046), 0.00, 0.88),
    "alu_dark":     ((0.120, 0.124, 0.132), 1.00, 0.38),
    "alu_bright":   ((0.412, 0.424, 0.440), 1.00, 0.30),
    "alu_cast":     ((0.318, 0.326, 0.338), 1.00, 0.62),
    "magnesium":    ((0.276, 0.272, 0.258), 1.00, 0.58),
    "cf_disc":      ((0.090, 0.086, 0.082), 0.10, 0.66),
    "rad_core":     ((0.180, 0.130, 0.080), 0.90, 0.52),
    "anodised":     ((0.108, 0.136, 0.170), 1.00, 0.40),
    "steel":        ((0.480, 0.492, 0.510), 1.00, 0.28),
}

RES = {"revolve": 40, "small_revolve": 18, "pipe": 12,
       "airfoil_pts": 30, "wing_stations": 8}

RHO = 1.225      # kg/m^3


# --------------------------------------------------------------------------
# Performance model -- first-order, but consistent
# --------------------------------------------------------------------------

def cla(drs=False):
    v = AERO["cla_wings"] + AERO["cla_floor"]
    return v - AERO["drs_cla_drop"] if drs else v


def cda(drs=False):
    return AERO["cda"] - AERO["drs_cda_drop"] if drs else AERO["cda"]


def aero_downforce_kg(kph, drs=False):
    v = kph / 3.6
    return 0.5 * RHO * v * v * cla(drs) / 9.81


def downforce_kg(kph, drs=False, with_fan=True):
    return aero_downforce_kg(kph, drs) + (FAN["downforce_kg"] if with_fan else 0.0)


def drag_kg(kph, drs=False):
    v = kph / 3.6
    return 0.5 * RHO * v * v * cda(drs) / 9.81


def f1_downforce_kg(kph):
    v = kph / 3.6
    return 0.5 * RHO * v * v * F1["cla"] / 9.81


def _mu(load_kg, static_kg, mu0, k):
    """Tyres lose grip coefficient as vertical load rises. Without this the
    model happily predicts twenty lateral g, which is nonsense."""
    return mu0 * (load_kg / static_kg) ** (-k)


def lateral_g(kph):
    load = MASS_KG + downforce_kg(kph)
    return _mu(load, MASS_KG, TYRE_MU, TYRE_LOAD_SENS) * load / MASS_KG


def f1_lateral_g(kph):
    load = F1["mass"] + f1_downforce_kg(kph)
    return _mu(load, F1["mass"], F1["mu"], TYRE_LOAD_SENS) * load / F1["mass"]


def _corner_speed(radius_m, mass, mu0, cla_v, fan_kg, k=TYRE_LOAD_SENS,
                  g_cap=None):
    """Steady-state cornering speed, solved by iteration because the grip
    coefficient depends on the load, which depends on the speed."""
    v = 20.0
    for _ in range(200):
        df = 0.5 * RHO * v * v * cla_v / 9.81 + fan_kg
        load = mass + df
        mu = _mu(load, mass, mu0, k)
        a_lat = mu * load / mass                       # in g
        if g_cap is not None:
            a_lat = min(a_lat, g_cap)
        v_new = math.sqrt(a_lat * 9.81 * radius_m)
        if abs(v_new - v) < 1e-4:
            v = v_new
            break
        v = v * 0.5 + v_new * 0.5
    return v * 3.6


def corner_speed_kph(radius_m):
    return _corner_speed(radius_m, MASS_KG, TYRE_MU, cla(),
                         FAN["downforce_kg"], g_cap=DRIVER_G_LIMIT)


def f1_corner_speed_kph(radius_m):
    return _corner_speed(radius_m, F1["mass"], F1["mu"], F1["cla"], 0.0,
                         g_cap=DRIVER_G_LIMIT)


def power_to_weight():
    return 935.0 / MASS_KG      # kW/kg, engine from the sibling project


def f1_power_to_weight():
    return F1["power_kw"] / F1["mass"]


def top_speed_kph(power_kw=935.0):
    """Where drag power equals available power, with active aero shed."""
    lo, hi = 50.0, 600.0
    for _ in range(80):
        mid = (lo + hi) / 2
        v = mid / 3.6
        p = 0.5 * RHO * v ** 3 * cda(drs=True) / 1000.0
        if p < power_kw * 0.90:      # 10 % to driveline and fans
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

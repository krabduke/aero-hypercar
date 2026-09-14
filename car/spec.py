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
# Where the axles actually sit along the body. Both were previously left at
# x = 0 and x = WHEELBASE, which put the front axle at the nose tip: no front
# overhang at all, the front wing behind the front wheels, and 1.4 m of car
# hanging off the back. The nose is the x datum; the axles are placed on it.
FRONT_AXLE_X = 900.0
REAR_AXLE_X = FRONT_AXLE_X + WHEELBASE
# Both tracks are set so the outside of the tyre lands on the 2000 mm width
# limit exactly, which is where a racing car is built to. The rear was 1 mm
# wide, and verify.py had a 2100 mm band that let it through.
TRACK_FRONT = 1660.0
TRACK_REAR = 1598.0

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
    "diameter": 520.0,
    # Behind the rear tyres and inboard of them. At x = 4180, y = 460 with a
    # 310 mm duct the shrouds ran straight through both rear wheels.
    "x": 4400.0,
    "y": 300.0,
    "z": 320.0,
    "blades": 13,
    "rpm": 7200.0,
    "power_kw": 62.0,          # drawn from the hybrid system
    "downforce_kg": 650.0,     # near-constant, this is the point of the car
    "duct_r": 280.0,
    # the plenum that feeds each fan from its tunnel. Its centreline has to
    # clear its own radius above the track, or the duct digs into the surface.
    "plenum_r": 150.0,
    "plenum_z0": 200.0,
    # blade geometry. A fan blade is twisted: to pull a uniform axial velocity
    # the blade angle has to fall with radius, beta = atan(Va / (omega r)).
    "hub_r": 74.0,
    "blade_root_chord": 96.0,
    "blade_tip_chord": 62.0,
    "blade_thickness": 0.10,
    "blade_camber": 0.045,
    "blade_beta_root": 52.0,     # deg from the disc plane
    "blade_beta_tip": 24.0,
    "blade_rake": 16.0,          # deg of sweep, for noise
    "stator_vanes": 9,           # straighten the swirl before the exit
    "axial_velocity": 42.0,      # m/s through the disc, sets the twist
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
    "caliper_r": 196.0,
    # rim: flange, drop centre, spoke and centre-lock geometry
    "flange_r": 240.0,         # outer lip, just proud of the bead seat
    "bead_r": 228.6,
    "drop_r": 198.0,           # drop centre, so a tyre can be fitted at all
    "hub_r": 62.0,
    "spoke_root_r": 74.0,
    "spoke_w_root": 54.0,
    "spoke_w_tip": 34.0,
    "spoke_t": 15.0,
    "nut_r": 44.0, "nut_h": 34.0,
    "cover_dish": 26.0,        # how far the wheel cover is dished inboard
    "cover_r": 214.0,
    "cover_vanes": 9,
    # tyre carcass: a slick still has a shoulder radius and a sidewall bulge
    "shoulder_frac": 0.80,     # of half width, where the tread rolls off
    "bulge": 14.0,             # how far the sidewall stands out past the bead
    "lettering_r": 292.0,
    "lettering_h": 3.0,
    # brakes
    "disc_vanes": 36,
    "disc_face_t": 8.0,
    "caliper_pistons": 6,
    "caliper_arc": 62.0,       # deg of disc the caliper wraps
    "pad_t": 14.0,
    # hub and bearing pack: it lives inside the upright barrel, carries the
    # disc bell on its inboard register and the wheel on its outboard flange
    "hub_journal_r": 28.0,
    "hub_flange_r": 112.0,
    "hub_bell_bore": 64.0,
    "bearing_r": 52.0,         # pitch radius of the bearing pack
    "bearing_wr": 9.0,
    # the stud pattern the wheel bolts to
    "studs": 5,
    "stud_r": 5.5,
    "stud_bc_r": 78.0,         # bolt circle
    "stud_len": 62.0,
    "pad_r_in": 140.0,
    "pad_r_out": 184.0,
    "pad_seg": 5,
}

# --------------------------------------------------------------------------
# Chassis
# --------------------------------------------------------------------------

# The central body is one continuous surface from nose tip to the rear crash
# structure. Defining it as a station table rather than three separate lofts is
# what lets it be waisted and curvature-continuous -- which is what makes it
# look, and behave, aerodynamic.
# (x, half_width, z_bottom, z_top, section exponent, shoulder bias)
BODY = [
    (   0.0,  38.0, 242.0, 292.0, 2.2,  0.00),
    (  90.0,  72.0, 214.0, 318.0, 2.3,  0.02),
    ( 210.0, 116.0, 176.0, 352.0, 2.5,  0.05),
    ( 380.0, 158.0, 132.0, 392.0, 2.7,  0.08),
    ( 560.0, 196.0,  96.0, 430.0, 2.9,  0.10),
    ( 760.0, 224.0,  74.0, 486.0, 3.1,  0.12),
    ( 980.0, 240.0,  64.0, 556.0, 3.2,  0.12),
    (1180.0, 248.0,  60.0, 618.0, 3.3,  0.10),
    (1420.0, 252.0,  58.0, 690.0, 3.3,  0.06),
    (1680.0, 256.0,  58.0, 742.0, 3.2,  0.02),
    (1980.0, 262.0,  60.0, 772.0, 3.1, -0.02),
    (2260.0, 268.0,  66.0, 742.0, 3.0, -0.06),
    (2560.0, 300.0,  74.0, 706.0, 2.9, -0.08),
    (2880.0, 292.0,  86.0, 722.0, 2.8, -0.10),
    # The cover has to clear the plenum and the turbos in the vee, which is
    # why a real one bulges over the engine instead of running straight from
    # the airbox to the rear wing. It used to cut 32 mm into the plenum.
    (3240.0, 268.0, 104.0, 738.0, 2.9, -0.10),
    (3560.0, 240.0, 122.0, 668.0, 2.8, -0.08),
    (3860.0, 206.0, 140.0, 566.0, 2.6, -0.06),
    (4140.0, 168.0, 158.0, 434.0, 2.4, -0.04),
    (4380.0, 140.0, 176.0, 392.0, 2.3, -0.02),
    (4560.0, 118.0, 194.0, 358.0, 2.2,  0.00),
]

# Sidepod: its own table, because the undercut is the whole point. The lower
# surface climbs steeply aft of the inlet to feed the tunnel, and the plan view
# waists into a coke-bottle so the rear wing and beam wing see clean air.
# (x, y_inboard, y_outboard, z_bottom, z_top, exponent)
SIDEPOD_TABLE = [
    (1700.0, 250.0, 300.0, 180.0, 300.0, 2.6),
    (1790.0, 258.0, 560.0, 156.0, 430.0, 2.8),
    (1900.0, 262.0, 700.0, 146.0, 500.0, 3.0),
    (2080.0, 268.0, 762.0, 150.0, 534.0, 3.1),
    (2320.0, 272.0, 770.0, 172.0, 540.0, 3.1),
    (2600.0, 268.0, 742.0, 214.0, 524.0, 3.0),
    (2900.0, 252.0, 664.0, 268.0, 494.0, 2.9),
    (3200.0, 224.0, 552.0, 322.0, 452.0, 2.8),
    (3480.0, 190.0, 424.0, 366.0, 414.0, 2.6),
    (3700.0, 162.0, 316.0, 392.0, 392.0, 2.4),
]

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

# The floor's plan outline. A rectangle is what makes a car look like it was
# never in a wind tunnel: a real floor is narrow at its leading edge, full
# width alongside the sidepod, and waisted hard in front of the rear tyres so
# the tyre wake is kept off the diffuser. (x, half_width)
FLOOR_PLAN = [
    (1300.0, 630.0),
    (1560.0, 800.0),
    (1900.0, 866.0),
    (2500.0, 876.0),
    (3100.0, 862.0),
    (3450.0, 764.0),
    (3760.0, 612.0),
    (4020.0, 548.0),   # tightest point, alongside the rear tyre
    (4280.0, 556.0),
    (4560.0, 620.0),   # diffuser exit
]

FLOOR = {
    # starts behind the front tyre and ends with the bodywork
    "x0": 1300.0, "x1": 4560.0,
    "half_w": 850.0,
    "tunnel_half_w": 330.0,
    "tunnel_inner_y": 210.0,
    "throat_x": 2600.0, "throat_z": 96.0,
    # A 96 mm throat opening to 392 mm is a four-to-one expansion: no
    # diffuser holds flow through that, and the roof climbed straight into
    # the rear suspension on the way. 250 mm is a real exit height.
    "diffuser_x": 3860.0, "diffuser_exit_z": 250.0,
    "skirt_depth": 26.0,
    "n_strakes": 4, "strake_t": 9.0,
}

# Front wing. A real one is not a stack of flat panels: the mainplane is
# nearly neutral across the mandated centre section, then works harder and
# harder outboard, and every element rises towards the endplate so the tip
# vortex is thrown outside the front tyre instead of into it.
#
# Per element: (x offset, z offset, chord at root, chord at tip, span
# fraction, root AoA, tip AoA, tip rise). Offsets are from the wing datum.
FRONT_WING = {
    # far enough forward that the endplate's trailing edge clears the front
    # tyre; at x = 150 the whole outboard stack was inside the wheel
    "x": 60.0, "z": 112.0,
    "span": 1780.0, "chord": 470.0,
    "elements": 4, "gap": 16.0,
    # 280 mm, not 500. An endplate only has to enclose the flap stack, which
    # tops out at 367 mm from a datum of 16; taller than that it stops being
    # an endplate and becomes a wall, and it looked like one.
    "endplate_h": 366.0, "endplate_t": 9.0,
    "aoa_root": 6.0, "aoa_tip": 14.0,
    "neutral_half_w": 250.0,   # regulated flat centre section
    "arch": 44.0,              # how much the mainplane arches over the nose
    "stack": [
        # dz raised from 34/76/124. A cascade only works if the elements are
        # separated: the slot is what re-energises the boundary layer over
        # the one behind. At the old spacing ten per cent of element 1 was
        # inside element 0 -- the slot was closed over part of the span, so
        # there the two were one thick section instead of two thin ones.
        #  dx     dz   c_root  c_tip  span_f  aoa_r  aoa_t  tip_rise
        (   0.0,   0.0, 330.0, 250.0, 1.000,   2.0,   5.0,   46.0),
        (  96.0,  64.0, 190.0, 168.0, 0.985,   9.0,  17.0,   72.0),
        ( 186.0, 106.0, 152.0, 138.0, 0.965,  16.0,  26.0,   96.0),
        ( 262.0, 168.0, 118.0, 110.0, 0.940,  23.0,  34.0, 116.0),
    ],
    "endplate_x0": -60.0, "endplate_x1": 420.0,
    # No cascades. They were floating 130 mm above the top flap attached to
    # nothing, which read as debris rather than aerodynamics -- and they have
    # been illegal in Formula 1 since 2019 for exactly the reason they looked
    # wrong here: they throw structure into a region that belongs to the
    # outwash. The endplate does the job instead.
    #
    # Y250 vanes sit on the mainplane, just outboard of the mandated neutral
    # section, and turn the vortex that forms at its edge.
    "y250_x0": 0.24, "y250_x1": 0.76,      # of the wing's chord
    "y250_h": 118.0,
    "diveplane_span": 92.0,
    "footplate_h": 58.0,
    "diveplanes": 2,
}

REAR_WING = {
    "x": 4480.0, "z": 880.0,
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

BARGEBOARD = {
    "x0": 1180.0, "x1": 1760.0,
    "y": 430.0, "z0": 90.0, "z1": 400.0,
    "elements": 4, "gap": 42.0, "t": 8.0, "sweep": 26.0,
}

TURNING_VANE = {
    # ends ahead of the side impact tube, which starts at x 1658
    "x0": 1320.0, "x1": 1638.0,
    # The tub is 256 mm half width here and the seat fills it. At y 250 the
    # inboard vane was inside the driver's seat; a turning vane hangs under
    # the chassis OUTBOARD of the cell, where the flow it turns actually is.
    "y": 350.0, "z0": 110.0, "z1": 330.0,
    "elements": 2, "t": 7.0,
}

FLOOR_EDGE = {
    "x0": 1900.0, "x1": 3640.0,
    "fences": 5, "fence_h": 48.0, "t": 7.0,
    # the edge wing runs ALONG the floor edge, so its chord is measured
    # across the section -- inboard root to outboard tip -- and `rise` is how
    # far it climbs over that chord
    "edge_chord": 132.0, "edge_rise": 0.82, "edge_t": 7.0,
    "edge_root_dy": -18.0, "edge_root_z": 58.0,
}

BEAM_WING = {
    "x": 4280.0, "z": 430.0, "span": 1100.0, "chord": 210.0,
    "elements": 2, "aoa": 12.0,
}

BRAKE_DUCT = {
    "front_r": 210.0, "rear_r": 232.0,
    "width": 120.0, "inlet_h": 130.0,
}

DETAIL = {
    "mirror_x": 1620.0, "mirror_y": 330.0, "mirror_z": 690.0,
    "sharkfin_x0": 3100.0, "sharkfin_x1": 4180.0,
    "sharkfin_z": 760.0, "sharkfin_t": 9.0,
    "camera_x": 700.0, "camera_z": 430.0,
    "rainlight_x": 4470.0, "rainlight_z": 330.0,
    "exhaust_x": 4400.0, "exhaust_r": 62.0,
    # above the beam wing and clear of the diffuser exit; built about
    # z = 0 it sat half under the track surface
    # above the beam wing, which tops out at 489 -- the tailpipe used to
    # end inside it
    "exhaust_z": 560.0, "wastegate_z": 528.0,
}

# Surface and hardware detail. These are the parts that separate a shape from
# a car: cooling exits, the pylons that hold the front wing on, the fairings
# over the suspension, the crash structures, and the driver in the seat.
BODY_DETAIL = {
    # (x0, x1, clock angle, count, length, height) -- louvre banks, each one
    # mirrored to both flanks. Angles are measured from +y, so 36 and -36 are
    # both on the same side; the mirror is applied in code, not by sign here.
    # engine-cover louvres, on the central body: (x0, x1, angle, n, len, h)
    "gills": [
        (3060.0, 3520.0,  52.0, 7, 120.0, 22.0),
        (3160.0, 3600.0,  22.0, 6, 110.0, 20.0),
    ],
    # sidepod cooling exits, on the flank: (x0, x1, f_z, n, len, h)
    "sidepod_gills": [
        (2620.0, 3180.0, 0.74, 8, 150.0, 30.0),
        (2700.0, 3180.0, 0.50, 7, 130.0, 26.0),
    ],
    "nose_pylon_x": 300.0, "nose_pylon_y": 96.0, "nose_pylon_t": 34.0,
    "cape_x0": 340.0, "cape_x1": 760.0, "cape_y": 300.0,
    "susp_fairing_c": 190.0, "susp_fairing_t": 0.30,
    "crash_r": 78.0,
    "jack_r": 46.0,
    "driver": {
        "helmet_r": 132.0, "helmet_x": 1760.0, "helmet_z": 690.0,
        "shoulder_x": 1900.0, "shoulder_w": 190.0,
        "arm_r": 58.0, "leg_r": 72.0,
        "knee_x": 1400.0, "foot_x": 1160.0,
    },
    "airbox_x": 2060.0, "airbox_w": 168.0, "airbox_h": 146.0,
    "airbox_len": 340.0,
    "tow_r": 34.0, "tow_z_front": 250.0, "tow_z_rear": 330.0,
    "wing_mirror_stalk_r": 16.0,
}

HALO = {
    "x_front": 1160.0, "x_rear": 2000.0,
    "z": 960.0, "half_w": 330.0, "tube_r": 26.0,
}

# --------------------------------------------------------------------------
# Suspension
# --------------------------------------------------------------------------

SUSP = {
    "front_x": FRONT_AXLE_X, "rear_x": REAR_AXLE_X,
    # The upper wishbone picks up at the TOP of the upright, above the
    # driveshaft. At 340 it was level with the hub centre (335) and the rear
    # shaft ran straight through both legs of it.
    "upper_z": 462.0, "lower_z": 150.0,
    # and the rear lower arm has to clear the diffuser roof, which is at
    # 172 mm under the rear axle
    "lower_z_rear": 240.0,
    "inboard_front_y": 250.0, "inboard_rear_y": 300.0,
    "upright_h": 300.0,
    "arm_r": 17.0, "rod_r": 13.0,
    "front_layout": "pushrod", "rear_layout": "pullrod",
    "rear_rocker_z": 250.0,
}

POWERTRAIN = {
    "engine_x": 3240.0, "engine_z": 314.0,
    "gearbox_x": 3600.0, "gearbox_len": 520.0, "gearbox_r": 175.0,
    # The gearbox hangs off the back of the engine on the crank centreline.
    # Without this it was built about z = 0 -- half of it under the track.
    "gearbox_z": 330.0,
    "radiator": (600.0, 96.0, 330.0),
    "rad_x": 2320.0, "rad_y": 336.0, "rad_z": 320.0,
    "battery": (760.0, 300.0, 110.0),
    "battery_x": 2420.0, "battery_z": 150.0,
    "fuel_x": 2380.0, "fuel": (560.0, 420.0, 320.0),
}

# --------------------------------------------------------------------------
# Component hardware
# --------------------------------------------------------------------------

# The mandated wheel tether: a braided strap from the upright into a strong
# point on the survival cell, long enough to let the wheel walk but not to
# let it leave the car.
TETHER = {
    "width": 26.0, "thick": 5.0, "braid": 7,   # stations across the braid
}

# The main roll structure. It stands behind the driver's head, is braced
# forward into the headrest structure, and its legs are cast into the cover
# over the gearbox bellhousing line.
ROLL_HOOP = {
    "x": 2450.0,             # hoop plane, at the rear of the airbox
    "top_z": 952.0,
    "half_w": 206.0,         # legs stand either side of the airbox intake
    "leg_r": 26.0,
    "plate_len": 190.0, "plate_w": 260.0, "plate_t": 16.0,
    "brace_z": 640.0,        # where the forward braces meet the headrest
}

# Shaft and bevel gears taking fan drive off the gearbox case. The fans can
# be driven mechanically as well as electrically; this is the mechanical path.
FAN_DRIVE = {
    "shaft_r": 16.0,
    "pinion_r": 26.0, "pinion_t": 18.0,
    "crown_r": 52.0, "crown_t": 16.0,
    "teeth": 13,
    "input_z": 552.0,        # layshaft height above the floor line
    "gearbox_y": 150.0,      # where the flange leaves the case
}

# DRS: the actuator is a body, a rod and a clevis on the flap underside just
# ahead of its trailing edge. It stands under the mainplane's lower surface,
# which it touches, and reaches up-aft to the flap, which it moves.
DRS = {
    "body_r": 17.0, "body_x0": 4650.0, "body_len": 100.0, "body_z": 806.0,
    "rod_r": 8.0,
    "clevis_x": 4762.0, "clevis_z": 868.0,
}

# Front steering arm: a forged lever from the upright's steering pickup to
# the trackrod end. It sits inboard of the wheel band so it never fouls the
# tyre.
STEER_ARM = {
    "t": 20.0, "y_out": 668.0,
    "pivot_x": 856.0, "pivot_z": 302.0,
    "end_x": 662.0, "end_z": 230.0,
}

# Coil springs over the dampers. The rear rides lower and takes more load,
# so it has a tighter pitch and a deeper coil.
SPRING = {
    "wire_r": 9.0, "turns_f": 9.0, "turns_r": 8.0,
    "pitch_f": 21.0, "pitch_r": 24.0,
    "r_f": 52.0, "r_r": 58.0,
    "per_turn": 13,
}

# Adjustable anti-roll blades: a clamp collar on the lever arm and a stepped
# indicator plate the crew rotates to pick the rate.
ANTIROLL_BLADE = {
    "collar_r": 26.0, "plate_t": 9.0, "plate_h": 64.0, "steps": 6,
}

# Pitot rake behind the front wheels, feeding the aero map.
AERO_RAKE = {
    "x": 1285.0, "half_y": 296.0,
    "mast_z0": 468.0, "mast_z1": 700.0,
    "boom_len": 250.0, "probe_r": 4.0, "booms": 3,
}

# ERS accumulator in the tub, beside the fuel cell, with its cooling duct.
ACCUMULATOR = {
    "x0": 2000.0, "x1": 2098.0,
    "half_w": 176.0, "z0": 232.0, "z1": 438.0,
    "fins": 9,
}

# FIA rain-light backing plate on the rear bodywork.
LIGHT_PANEL = {
    "x0": 4440.0, "x1": 4466.0,
    "half_w": 104.0, "z0": 258.0, "z1": 392.0, "t": 8.0, "bolts": 6,
}

# Swan-neck fittings from the rear pylons onto the wing mainplane.
WING_MOUNT = {
    "collar_r0": 30.0, "collar_r1": 44.0,
    "foot_x0": 4432.0, "foot_x1": 4528.0, "foot_z": 902.0, "foot_t": 10.0,
    "y": 148.0, "bolts": 4,
}

# Rear gurney: an L-section tape with rivets on the flap trailing edge.
GURNEY = {
    "tape_len": 56.0, "tab_h": 34.0, "t": 4.0, "rivets": 24,
    "aoa": 29.0,             # matches the flap setting, rear_element(1)
}

# Sidepod inlet: a rolled lip, an internal diffuser and a splitter vane.
INLET = {
    # x_lip was 1702, one millimetre ahead of the sidepod's own leading edge
    # at 1700, so the duct stood out in front of the bodywork as a snout
    # rather than reading as a mouth cut into it. Recessed 26 mm behind the
    # face now, and the throat moved aft so the duct actually diffuses over
    # its length instead of stepping down in 110 mm.
    "x_lip": 1728.0, "x_throat": 1910.0,
    "y0": 336.0, "y1": 508.0, "z0": 206.0, "z1": 398.0,
    "lip_r": 7.0, "wall": 10.0, "throat_f": 0.68, "vane_t": 7.0,
}

# Fan motors: finned case, end bells, terminal block, mounting feet.
FAN_MOTOR = {
    "bore_r": 25.0,          # the drive shaft passes through the case
    "fin_h": 8.0, "fins": 14, "bell_r": 46.0,
    "foot_w": 18.0, "term": (34.0, 24.0, 20.0),
}

# Pit-lane and service hardware
SERVICE = {
    "gun_bore_r": 46.0, "gun_lug_r": 10.0, "gun_lugs": 9, "gun_len": 30.0,
    "starter_bezel_r": 40.0, "starter_drive": 19.0,
    "jack_puck_r": 48.0, "jack_strap_w": 34.0,
    "tow_throat_r": 62.0, "tow_shank_r": 17.0, "hook_seg": 22,
    # a -3 braided hose is 4 mm across the braid and about 15 mm across the
    # crimped fitting, so the two get their own numbers
    "line_r": 4.2, "line_fitting_r": 7.5, "line_clip_every": 2,
    "loom_r": 16.0, "loom_ties": 8,
}

# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

MATERIAL_MAP = {
    "hub_": "alu_dark",
    "wheel_stud": "titanium",
    "brake_pad": "cf_disc",
    "tether": "strap",
    "roll_hoop": "titanium",
    "fan_drive": "steel",
    "drs_": "alu_bright",
    "steering_arm": "alu_bright",
    "spring": "strap",
    "antiroll_blade": "alu_bright",
    "aero_rake": "titanium",
    "accumulator": "anodised",
    "rear_light": "alu_bright",
    "wing_mount": "alu_bright",
    "halo_mounts": "titanium",
    "halo_pillar": "titanium",
    "exit_louvres": "carbon_matte",
    "tyre_sensors": "alu_dark",
    "fuel_coupling": "alu_bright",
    "starter_socket": "alu_bright",
    "gun_socket": "alu_bright",
    "side_intrusion": "carbon_matte",
    "bulkhead_": "carbon_matte",
    "drink_bottle": "suit",
    "extinguisher": "alu_bright",
    "dash": "carbon_matte",
    "harness": "suit",
    "control_boxes": "alu_dark",
    "wiring_loom": "hose",
    "pedal_box": "alu_bright",
    "master_cylinders": "alu_bright",
    "brake_lines": "steel",
    "bduct_": "carbon_matte",
    "steering_column": "steel",
    "steering_rack": "alu_bright",
    "antiroll_": "steel",
    "heave_": "alu_bright",
    "torsion_bars": "steel",
    "dampers_": "alu_bright",
    "fuel_fittings": "alu_bright",
    "battery_modules": "alu_dark",
    "rad_hoses": "hose",
    "rad_tanks": "alu_bright",
    "radiator_": "rad_core",
    "tub": "carbon_gloss", "nose": "carbon_gloss", "floor": "carbon_matte",
    "tunnel": "carbon_matte", "diffuser": "carbon_matte", "strake": "carbon_matte",
    "wing": "carbon_gloss", "endplate": "carbon_gloss", "flap": "carbon_gloss",
    "pylon": "carbon_gloss", "sidepod": "carbon_gloss", "engine_cover": "carbon_gloss",
    "airbox": "carbon_gloss", "halo": "titanium", "skirt": "rubber_seal",
    "tyre": "rubber_tyre", "rim": "alu_dark", "disc": "cf_disc",
    "caliper": "alu_bright", "upright": "alu_bright",
    "wheelcover": "carbon_gloss", "wheelnut": "alu_bright",
    "wishbone": "carbon_matte", "pushrod": "carbon_matte", "pullrod": "carbon_matte",
    "trackrod": "carbon_matte", "rocker": "alu_bright",
    "fan": "alu_bright", "fanduct": "carbon_matte",
    "radiator": "rad_core", "battery": "anodised", "fuel": "anodised",
    "gearbox": "magnesium", "driveshaft": "steel",
    "seat": "carbon_matte", "wheelrim": "alu_dark", "steering": "carbon_matte",
    "engine": "alu_cast",
    "bargeboard": "carbon_gloss", "turning_vane": "carbon_gloss",
    "floor_fence": "carbon_matte", "brake_duct": "carbon_matte",
    "mirror": "carbon_gloss", "camera": "carbon_matte",
    "rainlight": "rubber_tyre", "exhaust": "steel",
    "gills": "carbon_matte", "nose_pylon": "carbon_gloss",
    "nose_cape": "carbon_gloss", "susp_fairing": "carbon_gloss",
    "crash_structure": "carbon_matte", "jack_point": "alu_bright",
    "helmet": "helmet", "driver": "suit", "airbox": "carbon_gloss",
    "tow_hook": "alu_bright", "floor_plank": "wood",
    "cooling_louvre": "carbon_matte", "sharkfin": "carbon_gloss",
    "coaming": "carbon_matte", "headrest": "carbon_matte",
    "cascade": "carbon_gloss", "y250": "carbon_gloss",
    "louvre": "carbon_gloss", "gurney": "carbon_gloss",
    "beam": "carbon_gloss", "inlet": "carbon_gloss",
}
DEFAULT_MATERIAL = "carbon_matte"

PALETTE = {
    "carbon_gloss": ((0.048, 0.050, 0.056), 0.22, 0.30),
    "carbon_matte": ((0.056, 0.058, 0.064), 0.14, 0.56),
    "titanium":     ((0.360, 0.372, 0.398), 1.00, 0.20),
    "rubber_tyre":  ((0.030, 0.030, 0.032), 0.00, 0.82),
    "rubber_seal":  ((0.050, 0.048, 0.046), 0.00, 0.88),
    "alu_dark":     ((0.120, 0.124, 0.132), 1.00, 0.38),
    "alu_bright":   ((0.470, 0.482, 0.500), 1.00, 0.16),
    "alu_cast":     ((0.318, 0.326, 0.338), 1.00, 0.62),
    "magnesium":    ((0.276, 0.272, 0.258), 1.00, 0.58),
    "rad_core":     ((0.140, 0.120, 0.095), 0.60, 0.62),
    "hose":         ((0.055, 0.056, 0.060), 0.00, 0.78),
    "cf_disc":      ((0.090, 0.086, 0.082), 0.10, 0.66),
    "helmet":       ((0.480, 0.086, 0.062), 0.05, 0.16),
    "suit":         ((0.052, 0.056, 0.070), 0.00, 0.72),
    "wood":         ((0.300, 0.232, 0.140), 0.00, 0.80),
    "rad_core":     ((0.180, 0.130, 0.080), 0.90, 0.52),
    "anodised":     ((0.108, 0.136, 0.170), 1.00, 0.40),
    "steel":        ((0.480, 0.492, 0.510), 1.00, 0.28),
    "strap":        ((0.520, 0.075, 0.050), 0.10, 0.55),
}

# Resolution. Eight spanwise stations and thirty section points made the rear
# wing -- the most looked-at surface on the car -- a 240-vertex object, which
# is fewer points than the engine spends on a single valve spring. These are
# the same numbers the sibling turbofan project uses, and they are what makes
# a tip look turned rather than chamfered.
TESS = 1.8   # global tessellation multiplier, applied in mesh.py

RES = {"revolve": 88, "small_revolve": 28, "pipe": 20,
       "airfoil_pts": 72, "wing_stations": 26}

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

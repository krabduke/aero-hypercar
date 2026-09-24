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

# The wings came down from 2.55 to 1.20 and the reason is in
# docs/research/R2-limits.md. Total ClA of 5.90 was past the optimum: sweeping
# it against lap time puts the fastest configuration at 4.13 and the curve is
# flat out to 4.55, so 1.20 + 3.35 sits inside the flat region and leaves
# enough wing to trim the aero balance with. It is worth 1.05 s a lap.
#
# The reason is NOT the driver limit, which is what the first study concluded.
# Removing the driver's 7 g cap altogether is worth 0.04 s, because the tyre
# saturates at almost the same place -- driver and rubber run out together.
# What actually sets the optimum is load sensitivity: past about ClA 4.5 the
# extra vertical load buys so little extra grip that the drag to make it is a
# straight loss. The optimum holds at 4.13 for every driver limit from 6 g up.
AERO = {
    "cla_wings": 1.20,         # both wings, trimmed for a medium-downforce track
    "cla_floor": 3.35,         # venturi tunnels and diffuser
    "cda": 1.28,   # follows the wing coming off
    "frontal_area": 1.52,      # m^2, already folded into the coefficients
    "aero_balance": 0.445,     # fraction of downforce on the front axle
    "drs_cla_drop": 1.25,      # active aero shed on a straight
    "drs_cda_drop": 0.52,
}

FAN = {
    "n": 2,
    # 340 mm, horizontal axes, at the tail -- see parts/fans.py for why. At
    # 520 mm on vertical axes they needed an exhaust duct that could not be
    # built, and they were sized for four times the flow the skirts leak.
    "diameter": 340.0,
    # Behind the rear wheels (rims end at x 4290), outboard of the rear
    # pylons (y 241) and inboard of the endplates, above the diffuser's lip
    # (z 269) and below the endplates' foot (z 627).
    "x": 4490.0,
    "y": 446.0,
    "z": 452.0,
    "blades": 11,
    "rpm": 7200.0,             # full speed; the controller runs it slower
    # 8 m3/s at 1.2 kPa of suction plus the jet's own head is 25 kW of air;
    # 38 kW at the shaft is that at 0.65 efficiency. It was 62 for a fan
    # sized for four times the leakage the skirts let in.
    "power_kw": 38.0,          # drawn from the hybrid system, both fans
    "downforce_kg": 650.0,     # near-constant, this is the point of the car
    "duct_r": 170.0,
    # blade geometry. A fan blade is twisted: to pull a uniform axial velocity
    # the blade angle has to fall with radius, beta = atan(Va / (omega r)).
    "hub_r": 56.0,
    "blade_root_chord": 66.0,
    "blade_tip_chord": 46.0,
    "blade_thickness": 0.10,
    "blade_camber": 0.045,
    "blade_beta_root": 52.0,     # deg from the disc plane
    "blade_beta_tip": 24.0,
    "blade_rake": 16.0,          # deg of sweep, for noise
    "stator_vanes": 7,           # straighten the swirl before the exit
    "axial_velocity": 50.0,      # m/s through the disc, sets the twist
}

TYRE_MU = 1.80                 # bespoke slick at the reference load
# mu falls as (load / static load) ^ -k. 0.18 is the centre of the sourced
# band in docs/research/ANCHORS.md, 0.15-0.25; it was 0.12, outside the band
# on the side that flatters a car making several times its weight in
# downforce, while the lap simulation already used the band.
TYRE_LOAD_SENS = 0.18
DRIVER_G_LIMIT = 7.0           # sustained lateral g a trained driver can work at

# --------------------------------------------------------------------------
# Wheels and tyres
# --------------------------------------------------------------------------

WHEEL = {
    "rim_d": 457.2,            # 18 inch
    "front_w": 305.0, "front_od": 670.0,
    "rear_w": 405.0,  "rear_od": 690.0,
    "spokes": 7,
    # Sized to fit the wheel: the rim's drop well is 193 mm inside, and a
    # 360 mm disc put the caliper 16 mm into it. 316 mm is about what an
    # 18-inch F1 front runs.
    "disc_r": 158.0, "disc_t": 32.0,
    "caliper_r": 168.0,
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
    # The chassis stands tall over the front axle, the way a single-seater's
    # does, because the front suspension's rockers, heave damper and
    # anti-roll bar live under its top. It was 50 mm lower here and all
    # three stood out through the skin.
    ( 560.0, 196.0,  96.0, 452.0, 2.9,  0.10),
    ( 760.0, 224.0,  74.0, 540.0, 3.1,  0.12),
    ( 980.0, 250.0,  64.0, 612.0, 3.2,  0.12),
    (1180.0, 248.0,  60.0, 652.0, 3.3,  0.10),
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
    (3560.0, 240.0, 122.0, 678.0, 2.8, -0.08),
    # Behind the engine the cover stays up as a spine over the exhaust,
    # which runs inside it to the exit at the tail. It used to fall away to
    # 392 mm here, below the top of the gearbox, and the 104 mm tailpipe ran
    # along the outside of it for 600 mm.
    (3860.0, 206.0, 140.0, 662.0, 2.6, -0.06),
    (4140.0, 168.0, 158.0, 628.0, 2.4, -0.04),
    (4380.0, 140.0, 176.0, 616.0, 2.3, -0.02),
    (4560.0, 118.0, 194.0, 612.0, 2.2,  0.00),
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

    # The tub ends where the engine bolts on. It ended at 2360, 500 mm
    # short of the engine's front face, with its bulkhead through the middle
    # of the fuel cell and the battery.
    "x_front": 620.0, "x_rear": 2850.0,
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
    # The height the tunnel roof STARTS at, before the throat.
    #
    # This used to be a bare 78.0 inside _floor_z, and it has to be at least
    # throat_z or the expression that reads
    #
    #     entry - (entry - throat_z) * f**1.3 + 18
    #
    # rises instead of falling. At 78 against a throat of 96 it did exactly
    # that: the roof went 96 -> 114 mm, so the floor's minimum AREA sat at its
    # own leading edge -- 1210 cm2 at x = 1300 against 1347 at the diffuser --
    # and the duct was inlet-limited. Everything downstream was expansion and
    # the suction peak sat at the entry, which is the least useful and most
    # ride-height-sensitive place to put it. The docstring said "pinched at
    # the throat" and the arithmetic did the opposite.
    #
    # At 96 the roof is flat at 114 mm and the plan shape does the
    # converging: 1436 cm2 at the inlet, 1347 at x = 3866 where the floor has
    # narrowed to 1144 mm, then 3323 at the exit. A converging-diverging duct
    # with its throat at the diffuser, and a 2.47 expansion over a 6.3 degree
    # half-angle, which stays attached.
    #
    # It cannot go higher than this. The turning vanes sit at z = 110 and the
    # bargeboards at 116, so a taller inlet swallows them -- raising it to 168
    # put six parts inside the tunnels. A stronger contraction needs those
    # moved, which is a design change rather than a bug fix, and is left as
    # one.
    "entry_z": 96.0,
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
    #
    # 418, though, not 366: with the tip rises below, the top flap reaches
    # z 428, which is 412 above the datum. At 366 the endplate stopped 46 mm
    # under the element it is supposed to enclose.
    "endplate_h": 418.0, "endplate_t": 9.0,
    "aoa_root": 6.0, "aoa_tip": 14.0,
    "neutral_half_w": 250.0,   # regulated flat centre section
    "arch": 44.0,              # how much the mainplane arches over the nose
    "stack": [
        # dz raised from 34/76/124. A cascade only works if the elements are
        # separated: the slot is what re-energises the boundary layer over
        # the one behind. At the old spacing ten per cent of element 1 was
        # inside element 0 -- the slot was closed over part of the span, so
        # there the two were one thick section instead of two thin ones.
        # span_f is 1.000 for all four. It used to taper 1.000/0.985/0.965/
        # 0.940, which left the three flaps short of the endplate; the tips
        # are now run out to the plate's swept inner face by
        # wings.endplate_sweep. The taper that matters on a front wing is in
        # chord and incidence, and both are still here.
        #  dx     dz   c_root  c_tip  span_f  aoa_r  aoa_t  tip_rise
        (   0.0,   0.0, 330.0, 250.0, 1.000,   2.0,   5.0,   46.0),
        (  96.0,  64.0, 190.0, 168.0, 1.000,   9.0,  17.0,   72.0),
        ( 186.0, 106.0, 152.0, 138.0, 1.000,  16.0,  26.0,   96.0),
        ( 262.0, 168.0, 118.0, 110.0, 1.000,  23.0,  34.0, 116.0),
    ],
    "endplate_x0": -60.0, "endplate_x1": 440.0,
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
    "elements": 2, "gap": 22.0, "overlap": 8.0,
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
    # y 452, not 430. The cascade sweeps inboard, and its innermost element
    # reached y 298 -- through the turning vane at 350, which cannot move:
    # the tub is 256 mm half width here and there is not 48 mm of lane
    # between the two.
    # z0 120, not 90. The tunnel roof at the floor's leading edge is 114 mm
    # now that the inlet is no longer the duct's narrowest section, and a
    # bargeboard at 90 had its bottom 24 mm inside the tunnel. It belongs
    # above the roof in any case: a bargeboard works the flow OUTSIDE the
    # tunnel and conditions what goes in, it does not sit in the stream.
    "y": 452.0, "z0": 120.0, "z1": 400.0,
    "elements": 4, "gap": 42.0, "t": 8.0, "sweep": 26.0,
}

TURNING_VANE = {
    # ends ahead of the side impact tube, which starts at x 1658
    "x0": 1320.0, "x1": 1638.0,
    # The tub is 256 mm half width here and the seat fills it. At y 250 the
    # inboard vane was inside the driver's seat; a turning vane hangs under
    # the chassis OUTBOARD of the cell, where the flow it turns actually is.
    # z0 86, not 110. The tunnel roof under the nose falls from z 106 on the
    # centreline to 92 at y 300, so at 110 the inboard vane's foot hung clear
    # of the floor it turns the flow onto -- attached to nothing at all,
    # while the outboard one was held only by the bargeboards it brushes.
    "y": 350.0, "z0": 86.0, "z1": 330.0,
    "elements": 2, "t": 7.0,
}

FLOOR_EDGE = {
    "x0": 1900.0, "x1": 3640.0,
    "fences": 5, "fence_h": 48.0, "t": 7.0,
    # the edge wing runs ALONG the floor edge, so its chord is measured
    # across the section -- inboard root to outboard tip -- and `rise` is how
    # far it climbs over that chord
    "edge_chord": 132.0, "edge_rise": 0.82, "edge_t": 7.0,
    # the root sits on the floor's top face, z 53.9 along the edge: at 58
    # its underside was 3.8 mm above it and the wing was attached to nothing
    "edge_root_dy": -18.0, "edge_root_z": 53.0,
}

# Above the fans, which now lie across its old place at the tail, and below
# the rear wing's main plane at z 839: it still works the diffuser exit and
# the rear wing together, and the fan jets underneath it pump the diffuser
# as well.
BEAM_WING = {
    "x": 4280.0, "z": 690.0, "span": 1100.0, "chord": 210.0,
    "elements": 2, "aoa": 12.0, "gap": 18.0, "overlap": 6.0,
}


# ------------------------------------------------------------ slotted wings

"""Where the elements of a multi-element wing actually go.

Every element is a flat chord line rotated about its quarter chord -- the same
convention the mesh, aero/analyse.py and the browser lattice all use, so these
two functions are the one place the stack-up is decided.

The rear wing used to be placed by stepping the flap 46 % of chord aft and a
flat 48 mm up. That takes no account of the mainplane's own incidence: at 17
degrees its chord line climbs 50.6 mm over that step, so the flap's leading
edge finished 2.4 mm BELOW the element it was supposed to sit behind. The two
elements interpenetrated. A vortex lattice has no way to represent two sheets
that cross, and it did not fail quietly -- strip circulation came out
alternating +219 and -239 across the span and the induced drag read 2,247 kg
against a physical figure near 60. Measuring the slot where a slot is actually
measured fixes the geometry and the solve together.
"""


def chord_point(x, z, chord, aoa, frac):
    """A point at `frac` of the chord, in the x-z plane.

    x, z name the quarter-chord reference the section rotates about, not the
    leading edge: that is where the lattice puts its bound vortex and where
    the mesh builder puts the DRS hinge.
    """
    a = math.radians(aoa)
    d = (frac - 0.25) * chord
    return x + 0.25 * chord + d * math.cos(a), z + d * math.sin(a)


def slot_place(x, z, chord, aoa, chord2, aoa2, gap, overlap):
    """Place the element behind a slot, and return its own (x, z) reference.

    `gap` is measured perpendicular to the upstream element's chord line and
    `overlap` along it, both from that element's trailing edge -- which is how
    a slot gap and an overlap are defined on a real multi-element wing, and
    what keeps the passage open as either element is trimmed.
    """
    te_x, te_z = chord_point(x, z, chord, aoa, 1.0)
    a = math.radians(aoa)
    # along the chord, pointing aft; and normal to it, towards the flap
    ax, az = math.cos(a), math.sin(a)
    nx, nz = -math.sin(a), math.cos(a)
    le_x = te_x - overlap * ax + gap * nx
    le_z = te_z - overlap * az + gap * nz
    # invert chord_point at frac 0 to recover the quarter-chord reference
    a2 = math.radians(aoa2)
    return (le_x - 0.25 * chord2 * (1.0 - math.cos(a2)),
            le_z + 0.25 * chord2 * math.sin(a2))


def rear_elements():
    """(x, z, chord, aoa) for each rear wing element, root section."""
    RW = REAR_WING
    out = []
    x, z = RW["x"], RW["z"]
    for k in range(RW["elements"]):
        chord = RW["chord"] * (1.0 - 0.42 * k)
        aoa = RW["aoa"] + k * 12.0
        if k:
            px, pz, pc, pa = out[-1]
            x, z = slot_place(px, pz, pc, pa, chord, aoa,
                              RW["gap"], RW["overlap"])
        out.append((x, z, chord, aoa))
    return out


def beam_elements():
    """(x, z, chord, aoa) for each beam wing element, root section."""
    BW = BEAM_WING
    out = []
    x, z = BW["x"], BW["z"]
    for k in range(BW["elements"]):
        chord = BW["chord"] * (1.0 - 0.30 * k)
        aoa = BW["aoa"] + k * 8.0
        if k:
            px, pz, pc, pa = out[-1]
            x, z = slot_place(px, pz, pc, pa, chord, aoa,
                              BW["gap"], BW["overlap"])
        out.append((x, z, chord, aoa))
    return out

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
    "exhaust_z": 548.0,           # just over the crash structure, at 476
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
    "nose_pylon_x": 300.0, "nose_pylon_y": 96.0, "nose_pylon_t": 34.0,
    "cape_x0": 340.0, "cape_x1": 760.0, "cape_y": 300.0,
    "susp_fairing_c": 190.0, "susp_fairing_t": 0.30,
    "crash_r": 78.0,
    "jack_r": 46.0,
    "driver": {
        "helmet_r": 132.0, "helmet_x": 1760.0, "helmet_z": 710.0,
        # Lying back the way a single-seater driver does: feet forward at
        # the pedals, hips low in the seat, back reclined up to shoulders
        # just under and behind the helmet. It used to be the other way
        # round -- head forward, shoulders behind it and hips furthest aft,
        # 70 mm through the rear bulkhead.
        "shoulder_x": 1850.0, "shoulder_z": 510.0, "shoulder_w": 190.0,
        "hip_x": 1480.0, "hip_z": 300.0,
        "arm_r": 58.0, "leg_r": 72.0,
        "knee_x": 1210.0, "knee_z": 362.0, "foot_x": 965.0,
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
    # 195, not 250. The tub is 215 mm of half width at the front axle but
    # only at mid-height; down at the lower arm's pickup the section has
    # closed well inside that, so at 250 both front wishbones picked up
    # outboard of the chassis and carried wheel load into nothing.
    # The rear rockers, torsion bars and anti-roll bar hang off the gearbox
    # at this half width, inside the engine cover. At 300 the rockers stood
    # 124 mm outside the cover, in the open above the floor.
    "inboard_front_y": 195.0, "inboard_rear_y": 190.0,
    # and the rear lower arm picks up on the gearbox casing. The case is a
    # 175 mm cylinder on the crank line, so its usable width runs out fast
    # below the centre -- at z 155 it is a knife edge -- while the dampers
    # fill z 166-291 and the anti-roll tube 247-277. The one clear band is
    # just above the bar, where the case is still 172 wide. At (300, 250) the
    # arm picked up 116 mm clear of the car entirely.
    "lower_inboard_rear_y": 150.0, "lower_inboard_rear_z": 340.0,
    # ...and the aft leg's pickup goes below the driveshaft, which leaves
    # the casing right beside it: at 340 the leg was 11 mm into each shaft.
    "lower_inboard_rear_aft_y": 160.0, "lower_inboard_rear_aft_z": 282.0,
    "upright_h": 300.0,
    "arm_r": 17.0, "rod_r": 13.0,
    "front_layout": "pushrod", "rear_layout": "pullrod",
    "rear_rocker_z": 330.0,
}

POWERTRAIN = {
    "engine_x": 3240.0, "engine_z": 314.0,
    "gearbox_x": 3600.0, "gearbox_len": 520.0, "gearbox_r": 175.0,
    # where the gearbox's front face actually is: on the bellhousing, which
    # powertrain.py places from the engine and checks against this.
    # gearbox_x is 42 mm aft of it and is the station the rear hardware --
    # crash structure, jacking point, tow hook -- is laid out from.
    "gearbox_front_x": 3558.0,
    # The gearbox hangs off the back of the engine on the crank centreline.
    # Without this it was built about z = 0 -- half of it under the track.
    "gearbox_z": 330.0,
    # A U-flow crossflow core: tanks at the fore and aft ends, both hoses
    # on the aft tank. It was 600 x 330 with tanks top and bottom, a stack
    # 428 tall in a sidepod with 312 inside it where the core had to go --
    # it came out through the pod's floor and, at y 288, 46 mm into the
    # body. Outboard at y 480, where the pod's floor is lowest, and aft of
    # the side-impact tubes, a 400 x 280 core fits inside the skin with its
    # tanks, and it is thicker to keep the heat it rejects.
    "radiator": (400.0, 120.0, 280.0),
    "rad_x": 2336.0, "rad_y": 480.0, "rad_z": 358.0,
    # back to the engine bulkhead, which carries it
    "battery": (792.0, 300.0, 110.0),
    "battery_x": 2436.0, "battery_z": 150.0,
    # on top of the battery, not round it: at z 330 and 320 tall its sump
    # was 35 mm down into the pack
    "fuel_x": 2380.0, "fuel": (560.0, 420.0, 300.0), "fuel_z": 366.0,
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

# DRS: the actuator is a body, a rod and a clevis on the flap underside just
# ahead of its trailing edge. It stands under the mainplane's lower surface,
# which it touches, and reaches up-aft to the flap, which it moves.
DRS = {
    "body_r": 17.0, "body_x0": 4700.0, "body_len": 100.0, "body_z": 985.0,
    "rod_r": 8.0,
    "clevis_x": 4850.0, "clevis_z": 1010.0,
}

# Front steering arm: a forged lever from the upright's steering pickup to
# the trackrod end. It sits inboard of the wheel band so it never fouls the
# tyre.
STEER_ARM = {
    # y_out 740, not 668. The upright's inner face at this height is at 728,
    # so an arm at 668 hung 60 mm inboard of the casting it is supposed to be
    # the lever on -- and the whole steering chain, rack to rod to arm to
    # upright, was four parts in a row that did not touch.
    # y_out 740 and end_x 772. The upright's inner face never comes inboard
    # of 723 at any height, so an arm at 668 could not reach it -- but run
    # forward to 662 at 740 it goes straight through the tyre, whose carcass
    # starts 180 mm from the hub. 772 keeps the whole lever inside the wheel's
    # bore, which is what "inboard of the wheel band" was always meant to say.
    "t": 20.0, "y_out": 740.0,
    "pivot_x": 856.0, "pivot_z": 245.0,
    "end_x": 772.0, "end_z": 232.0,
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
    # 45, not 104. The fans' rotors start at y 51 and the rain light is on
    # the centreline between them; at 104 the panel was inside both of them.
    "half_w": 45.0, "z0": 258.0, "z1": 392.0, "t": 8.0, "bolts": 6,
}

# Swan-neck fittings from the rear pylons onto the wing mainplane.
WING_MOUNT = {
    "collar_r0": 30.0, "collar_r1": 44.0,
    "foot_x0": 4432.0, "foot_x1": 4528.0, "foot_z": 866.0, "foot_t": 10.0,
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
    "pylon": "carbon_gloss", "rear_frame": "carbon_gloss", "sidepod": "carbon_gloss", "engine_cover": "carbon_gloss",
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


# --------------------------------------------------------------------------
# Where the fan's air goes
# --------------------------------------------------------------------------
# The fans were exhausting straight up, into the underside of the beam wing
# and the rear wing. At 200 km/h the rear wing carries about 290 kg and the
# whole fan jet turned vertically is worth 101 kg. It is the worst trade
# available.
#
# Turned aft and up, the same 23.6 kg/s at 42 m/s gives 47 kg of downforce AND
# 874 N of thrust, and the exit can be placed where the jet's shear layer runs
# along the diffuser's outflow and entrains it -- an ejector on the thing that
# makes most of the downforce.
#
# A WARNING, because it cost a wrong answer already: the `x` in REAR_WING and
# BEAM_WING is the **leading edge**, not the centre. Reading it as a centre
# put the rear wing at x 4300-4660 when the built geometry is:
#
#     beam wing       x 4281 - 4615      rear pylons  x 4265 - 4581
#     rear mainplane  x 4484 - 4828, z 839 - 959
#     rear flap       x 4814 - 4996, z 974 - 1079
#     rear endplates  x 4354 - 5101, z 627 - 1147, at y +/- 710
#
# so a nozzle at x 4700 is not behind the rear wing at all, it is underneath
# it, and its outer edge lands on the endplates. Take these numbers from the
# built parts, not from the dicts.
#
# The exit that actually clears everything sits behind the beam wing, below
# the mainplane, and inboard of the endplates.
# How the fans are run. Below `full_kph` they are flat out -- that is where
# a fan earns its place, where a wing has nothing. Above it the controller
# eases them back, linearly in suction, to `min_frac` by `taper_kph`: by then
# the tunnels and wings are making most of the load and the car is at the
# driver's g limit in the fast corners anyway, and a fan's power goes as the
# cube of its speed, so the suction it keeps costs a fraction of the power.
# `kerb_seal_loss` is the band of suction lost where the car rides the kerbs
# on corner entry and exit and the skirts lift; the lap is run at both ends.
FAN_CONTROL = {
    "full_kph": 180.0, "taper_kph": 280.0, "min_frac": 0.35,
    "kerb_seal_loss": (0.0, 0.30), "kerb_frac": 0.15,
}

FAN_EXHAUST = {
    # Straight aft along each fan's own axis, over the diffuser's exit: the
    # jet pumps the diffuser the way a beam wing does. The nozzle runs from
    # the end of the shroud to `exit_a` behind the disc and contracts from the
    # duct's bore to `exit_r`, which keeps the exit area within a couple of
    # per cent of the fan annulus -- a contraction is back pressure, and back
    # pressure moves the fan up its own curve and down in flow.
    "exit_a": 200.0,           # mm aft of the disc
    "exit_r": 162.0,
}

# --------------------------------------------------------------------------
# The box this car lives in
# --------------------------------------------------------------------------
# Stated by the owner, in full:
#
#   "no rules -- just needs 4 wheels, a combustion engine / hybrid engine,
#    and needs to do the lap fairly. the car in itself has no other rules
#    except following the track."
#
# That is a much larger design space than it first sounds, and most of what
# makes a modern racing car the shape it is turns out to be regulation rather
# than physics. Everything in the second column below is *allowed here* and is
# banned in Formula 1, and each one is a lever this car is entitled to pull.
RULESET = {
    "wheels":            4,
    "propulsion":        "internal combustion, hybrid permitted",
    "must":              "complete the lap on the track, unaided",
    # what is NOT constrained, and what each unlocks
    "no_minimum_mass":   "F1 sets 798 kg. Nothing sets ours.",
    "no_tyre_spec":      "bespoke compound and construction, and any width.",
    "movable_aero":      "active wings and active ride height, both banned "
                         "in F1 since 1969 and 1994 respectively.",
    "ground_effect":     "sliding skirts and a fully sealed floor, banned "
                         "in 1983.",
    "fan":               "a fan whose primary effect is aerodynamic, banned "
                         "the week after the Brabham BT46B won with one.",
    "no_fuel_flow_limit": "F1 caps fuel flow at 100 kg/h above 10,500 rpm.",
    "no_power_limit":    "no MGU deployment cap, no energy-store cap.",
    "no_dimensional_box": "F1 fixes length, width, wheelbase and floor plan.",
    # and the things that are still real, because physics does not care
    # about rulebooks
    "binding":           ("tyre contact patch and load sensitivity, the "
                          "driver's tolerance to sustained g, the power it "
                          "takes to drive a fan, cooling, and whether the "
                          "structure survives the downforce it makes"),
}

# The lap is a single flying lap. Tyre wear, fuel load and heat soak over a
# race distance are a different and much harder question, and claiming a race
# pace this car has not been shown to hold would be dishonest. One lap, stated
# as one lap.
LAP_FORMAT = "single flying lap, car already at speed and at temperature"

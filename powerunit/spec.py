"""
RX-8V "Vertex" — 2.0 L V8 twin-turbo hybrid power unit.

ALL dimensions are millimetres, angles degrees, masses kilograms.
Crank centreline is the origin. +x is toward the front of the engine (the
accessory end is -x, the flywheel is +x). +z is up, +y is right.

Every other module consumes this file. No geometry module contains a literal
dimension; if a number describes the engine, it lives here.

WHY THIS ENGINE
---------------
The brief is a car that beats Formula 1 cars on a Formula 1 circuit. F1's
current power unit is a 1.6 L V6 turbo hybrid capped near 1000 hp by
regulation. Nothing here is regulated, so the constraint is physics and
packaging instead: this is a 2.0 L V8, flat-plane, hot-vee twin turbo, with a
larger hybrid system than F1 permits.

A V8 rather than a bigger V12: eight cylinders at this bore/stroke revs to
16,000 rpm with a mean piston speed still inside what steel and titanium can
live with, and a flat-plane V8 is short, stiff and light enough to be a fully
stressed chassis member -- which is what lets the car around it be small.

Every number below is a design choice, not a measurement of a real engine.
"""

import math

NAME = "RX-8V Vertex"
CONFIG = "90-degree V8, flat-plane crank, twin-turbo, hybrid"

# --------------------------------------------------------------------------
# Core architecture
# --------------------------------------------------------------------------

N_CYL = 8
V_ANGLE = 90.0                 # degrees included
BORE = 84.0
STROKE = 45.1                  # gives 250.0 cc/cylinder -> 2.0 L
ROD_LENGTH = 86.0              # rod/stroke 1.91, inside the usual 1.6-2.1
COMPRESSION_RATIO = 14.2       # high, with direct injection and heavy boost control
BORE_SPACING = 102.0
BANK_OFFSET = 19.0             # bank-to-bank stagger: the two rods
                               # on a shared crankpin, side by side
DECK_HEIGHT = 127.5            # = throw + rod + compression height + 0.5 deck clearance
REDLINE_RPM = 16000.0
BOOST_BAR = 3.4

# Flat-plane V8: four crankpins, two cylinders each, pins at 0/180/180/0.
# With a 90-degree bank angle that gives an even 90-degree firing interval.
CRANKPIN_ANGLES = [0.0, 180.0, 180.0, 0.0]
FIRING_ORDER = [1, 8, 3, 6, 4, 5, 2, 7]

# --------------------------------------------------------------------------
# Output (design targets)
# --------------------------------------------------------------------------

ICE_POWER_KW = 735.0           # 986 hp at 15,500 rpm
MGUK_POWER_KW = 200.0
MGUH_POWER_KW = 80.0
COMBINED_KW = 935.0            # 1254 hp deployable
MASS_KG = 146.0

# --------------------------------------------------------------------------
# Block and bottom end
# --------------------------------------------------------------------------

BLOCK = {
    "x_front": -232.0,
    "x_rear": 232.0,
    "vee_depth": 98.0,         # from deck plane down into the vee
    "skirt_depth": 96.0,       # below crank centreline
    "wall": 7.0,
    "half_width": 118.0,      # crankcase
    "bank_half_width": 64.0,  # the slab each bank of bores sits in
    "main_web_t": 16.0,
    # the valley between the banks, where the turbo oil unions screw in
    "vee_face_z": 86.0,
}

CRANK = {
    "main_r": 27.0,
    "pin_r": 24.0,
    "throw": STROKE / 2.0,
    "web_r": 42.0,   # small: a 22.5 mm throw with a light rotating assembly
                     #        needs little counterweight, and the skirts have to clear it
    "web_t": 13.0,
    "n_mains": 5,
    "nose_len": 128.0,
    "nose_r": 20.0,
    "flange_r": 62.0,
    "flange_t": 14.0,
    "counterweights": 8,
}

PISTON = {
    "crown_t": 6.5,
    "skirt_len": 18.0,   # short: at BDC the skirt has to clear the counterweights
    "pin_r": 9.5,
    "dome": 2.4,               # crown dome height, for the compression ratio
    "ring_grooves": 3,
}

ROD = {
    "big_end_r": 31.0,
    "small_end_r": 14.0,
    "beam_w": 17.0,
    "beam_t": 9.5,
}

# --------------------------------------------------------------------------
# Heads and valvetrain
# --------------------------------------------------------------------------

HEAD = {
    # A head has to contain its own valvetrain. At 74 mm this one did not:
    # the cams ran at 50 mm above the deck, the buckets were placed at 74 --
    # ABOVE the cams that are supposed to push them -- and an 86 mm valve
    # hanging off a 74 mm head is 12 mm longer than the casting it lives in,
    # which is why the valves had been turned round to point down the bore
    # into the crankcase instead. The stack sets the height: bucket under
    # lobe, lobe on base circle, journal above that, cover over the journal.
    "height": 132.0,
    "half_width": 59.0,
    "x_front": -228.0,
    "x_rear": 228.0,
    "cam_centres": 78.0,       # between intake and exhaust cam axes
    "cam_height": 108.0,       # above the deck face
}

VALVE = {
    "n_per_cyl": 4,
    "seat_angle": 45.0,          # the classic seat, cut into head and valve
    "margin": 1.4,               # flat land at the head's outer edge
    "tulip": 0.62,               # how far the underhead blends into the stem
    "keeper_groove": 1.1,        # where the collets grip the tip
    "intake_head_r": 17.0,
    "exhaust_head_r": 14.5,
    "stem_r": 2.6,
    "length": 92.0,
    "included_angle": 22.0,    # narrow, for a compact pent-roof chamber
    "lift": 12.5,
}

CAM = {
    "journal_r": 15.0,
    "base_r": 13.5,
    "lobe_lift": 12.5,
    "lobe_w": 11.0,
    "n_cams": 4,
    # A lobe is not a circle. Duration is the crank angle over which the valve
    # is off its seat; the lobe occupies half that in cam angle, because the
    # cam turns at half crank speed. 280 degrees at 16,000 rpm is a racing
    # profile -- long enough to fill the cylinder at peak power, and the
    # reason this engine has no low-speed manners to speak of.
    "duration_in": 280.0,        # crank degrees
    "duration_ex": 272.0,
    "lobe_centre_in": 104.0,     # crank degrees after TDC overlap
    "lobe_centre_ex": 108.0,     # before TDC
    "ramp": 0.06,                # fraction of duration spent on the quiet ramp
}

# --------------------------------------------------------------------------
# Induction, turbos, exhaust -- hot vee
# --------------------------------------------------------------------------

INTAKE = {
    # Two plenums, one outboard of each bank.
    #
    # This is a hot vee: the turbochargers sit between the banks and the
    # exhaust ports face inboard, which leaves the intake ports low on the
    # OUTBOARD face of each head. A single plenum over the vee therefore had
    # to reach across its own cylinder head to get to them, and every one of
    # the eight runners went through the fuel rail, the exhaust valves, the
    # camshaft, the MGU-H and a turbocharger on the way. Induction on a hot
    # vee goes outboard, which is where every engine built this way puts it.
    "plenum_r": 38.0,
    "plenum_len": 372.0,
    # Beside the heads, BELOW the cam covers rather than outboard of
    # them. Outboard the engine came out 795 mm across, which is wider
    # than the car it goes in; tucked under the covers it is 630, and the
    # runner into the port is a short horizontal one instead of a hook
    # over the top of the head.
    "plenum_y": 232.0,
    "plenum_z": 70.0,     # under the cam cover and under the cam itself
    "trumpet_r_in": 24.0,
    "trumpet_r_out": 33.0,
    "trumpet_len": 52.0,   # the plenum is 62 mm off the port, not 130
    "throttle_r": 46.0,
}

TURBO = {
    "n": 2,
    "x": [-118.0, 118.0],
    # In the vee, above the heads' inner faces. The head is 58 mm taller
    # than it was, so the floor of the vee rose 41 mm with it.
    "z": 255.0,
    "comp_r": 58.0,            # compressor housing
    "comp_wheel_frac": 0.66,   # wheel tip radius, as a fraction of comp_r
    "wheel_tip_clear": 1.6,    # running clearance from the wheel to the volute
    "comp_wheel_len": 37.0,    # inducer face to exducer face
    "turb_r": 64.0,            # turbine housing
    "turb_wheel_frac": 0.62,   # wheel tip radius, as a fraction of turb_r
    "wheel_depth_frac": 0.96,  # inducer face to exducer face, over tip radius
    "housing_w": 46.0,
    "shaft_r": 9.0,
    "inlet_r": 36.0,
    "outlet_r": 30.0,
    "wastegate_r": 19.0,
}

EXHAUST = {
    "primary_r": 15.5,
    "wall": 1.4,
    "collector_r": 27.0,
    "tailpipe_r": 41.0,
}

# --------------------------------------------------------------------------
# Hybrid system
# --------------------------------------------------------------------------

HYBRID = {
    "mguk_r": 74.0,
    "mguk_len": 108.0,
    "mguk_x": -286.0,          # on the crank nose
    # The rotor rides on the turbo shaft, so it lives inside the bearing
    # housing's waist -- 72 mm long at 40 mm radius put it through both
    # wheels and out of both ends of the housing it is supposed to be in.
    # 48 mm across, not 64. The charge pipe leaves the compressor volute 56 mm
    # from the shaft axis and is 60 mm across itself, so a 64 mm rotor in
    # between left 24 mm for a pipe that needs 30 -- the motor was inside the
    # charge pipe. An MGU-H rotor on an 18 mm shaft is about this size.
    "mguh_r": 24.0,
    "mguh_len": 44.0,
    # 120 mm along the crank, not 196: the exhaust primaries converge on
    # the turbochargers at x = +/-118 and climb over them, and a box that
    # long in the vee is in the way of four of them.
    "inverter": (100.0, 158.0, 74.0),
    # On the bellhousing at the back, where there is room for it. In the
    # vee it was the tallest thing on the engine and in the exhaust's way;
    # outboard it made the engine wider than the car.
    "inverter_pos": (276.0, 0.0, 190.0),
    "battery": (392.0, 300.0, 56.0),   # overall; built as two lobes
    # Two lobes either side of the sump keel: clear of the pan, clear of the
    # drain plug hanging out of it, and high enough that the engine still
    # fits the car's engine bay when it is installed.
    # Below the sump, which reaches z -180. At -132 the pack was inside it,
    # inside the oil pickup and inside the scavenge lines.
    "battery_pos": (0.0, 0.0, -244.0),   # tight under the sump
}

# --------------------------------------------------------------------------
# Ancillaries
# --------------------------------------------------------------------------

ANCILLARY = {
    "sump_depth": 62.0,
    "sump_len": 392.0,
    "sump_w": 188.0,
    "oil_pump_r": 34.0,
    "water_pump_r": 40.0,
    "flywheel_r": 96.0,
    "flywheel_t": 22.0,
    "bellhousing_r": 152.0,
    "bellhousing_len": 78.0,
    "ecu": (168.0, 88.0, 34.0),   # flat, so it can lie on a plenum
}

# --------------------------------------------------------------------------
# The oil circuit
# --------------------------------------------------------------------------
#
# Where the pump's ports and the tank's unions are, in one place, because
# three modules draw parts that have to meet at them: drive.py builds the
# pump, plumbing.py builds the tank, and detail.py runs the lines between.
#
# Each of those had its own idea of where the others were. The pump ended up
# 66 mm from the pickup, 25 mm from the lines and 51 mm from the cooler, and
# the tank was 300 mm from the breathers that vent into it -- five parts of
# one circuit, none of them joined, and every audit green because they were
# only ever asked whether they collided.
OIL = {
    # the pump lies along the pan's left flank, driven off the crank nose:
    # five stages on a common shaft, the pressure stage first
    "pump_x": BLOCK["x_front"] + 4.0,
    "pump_y": -192.0,
    "pump_z": -14.0,
    "stage_w": (21.0, 15.0, 15.0, 15.0, 15.0),
    "stage_gap": 2.4,
    # 46, not 23. The barrel is 34 mm in radius, so a boss reaching 23 from
    # the axis is inside the casting -- five ports that nothing could be
    # connected to because there was nothing sticking out to connect to.
    "port_len": 46.0,
    "port_a": (152.0, 188.0, 222.0, 256.0, 292.0),  # clocked apart, outboard
    # the dry-sump tank, on the left flank under the head
    "tank_x": BLOCK["x_front"] + 36.0,
    "tank_y": -162.0,
    "tank_z": -140.0,
    "tank_r": 40.0,
    "tank_len": 132.0,
}


# --------------------------------------------------------------------------
# The coolant circuit
# --------------------------------------------------------------------------
#
# Same reason as OIL above: the pump is built in drive.py, the thermostat in
# ancillaries.py, the outlets in block.py and the pipework in detail.py, and
# all four had their own idea of where the others were. Measured: pump to
# plumbing 31 mm, head to outlets 19 mm, outlets to thermostat 148 mm,
# thermostat to plumbing 52 mm. Nothing in the circuit touched anything else
# in it, and the thermostat was up in the vee resting on an exhaust flange.
COOLANT = {
    # the pump hangs off the front of the block on the right, aft of the
    # MGU-K rotor on the crank nose
    "pump_x": BLOCK["x_front"] + 14.0,
    "pump_y": 200.0,
    "pump_z": -34.0,
    # the thermostat housing sits on the engine's front face on the
    # centreline. 110, not 190: at 190 it was in the vee with the exhaust
    # flanges, and at anything under about 90 it is on the crank nose.
    "stat_x": BLOCK["x_front"] - 16.0,
    "stat_y": 0.0,
    "stat_z": 110.0,
    # the outlets stand up out of the block's flanks into the heads
    "outlet_z": 40.0,
    "outlet_len": 42.0,
}


def coolant_node(which):
    """World point at one of the circuit's connections."""
    C = COOLANT
    if which == "pump_out":
        return (C["pump_x"], C["pump_y"] - 68.0, C["pump_z"] + 62.0)
    if which == "pump_in":
        return (C["pump_x"] + 32.0, C["pump_y"], C["pump_z"])
    if which == "stat_top":
        return (C["stat_x"], C["stat_y"], C["stat_z"])
    if which == "stat_hose":       # the stub the radiator hose clamps to
        return (C["stat_x"] - 50.0, C["stat_y"], C["stat_z"])
    raise KeyError(which)


def oil_pump_port(k):
    """World point at the mouth of stage k's port. Stage 0 is pressure."""
    x = OIL["pump_x"]
    for w in OIL["stage_w"][:k]:
        x += w + OIL["stage_gap"]
    x += OIL["stage_w"][k] / 2.0
    a = math.radians(OIL["port_a"][k])
    r = OIL["port_len"]
    return (x, OIL["pump_y"] + math.cos(a) * r, OIL["pump_z"] + math.sin(a) * r)


def oil_pump_union(which):
    """World point at the pump's tank connections.

    The five stage ports face out of the barrel and take the pipes from the
    pan. These two are on the end faces: the pressure stage is fed from the
    tank at the front, and the four scavenge stages discharge into it from
    the back.
    """
    span = sum(OIL["stage_w"]) + OIL["stage_gap"] * (len(OIL["stage_w"]) - 1)
    if which == "feed":
        return (OIL["pump_x"] - 16.0, OIL["pump_y"], OIL["pump_z"] + 20.0)
    return (OIL["pump_x"] + span + 16.0, OIL["pump_y"], OIL["pump_z"] + 20.0)


def oil_tank_union(which):
    """World point at one of the tank's three connections.

    `scavenge` is tangential at the top, which is what makes it a swirl pot
    rather than a bucket; `feed` is the pressure stage's pickup at the very
    bottom; `breather` is the vent in the lid the crankcase breathes into.
    """
    if which == "feed":
        return (OIL["tank_x"] + 22.0, OIL["tank_y"],
                OIL["tank_z"] - OIL["tank_r"] - 26.0)
    if which == "scavenge":
        return (OIL["tank_x"] + OIL["tank_len"] - 30.0,
                OIL["tank_y"] - OIL["tank_r"] - 22.0, OIL["tank_z"] + 12.0)
    return (OIL["tank_x"] + 18.0, OIL["tank_y"] + 26.0,
            OIL["tank_z"] + OIL["tank_r"] + 22.0)

# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

MATERIAL_MAP = {
    "accessory_belt": "rubber_blk",
    "head_gasket": "steel_nitrided",
    "valve_guide": "copper_wound",
    "valve_seat": "steel_nitrided",
    "timing_chain": "steel_nitrided",
    "timing_chain_guides": "alu_forged",
    "timing_tensioner": "alu_forged",
    "crank_damper": "steel_nitrided",
    "flywheel_ring_gear": "steel_nitrided",
    "oil_filter": "anodised",
    "oil_cooler": "anodised",
    "thermostat": "alu_cast",
    "blowoff": "rubber_blk",
    "intercooler": "anodised",
    "charge_pipes": "rubber_blk",
    "engine_mount": "rubber_blk",
    "main_cap_bolts": "titanium",
    "windage_tray": "steel_nitrided",
    "scavenge_pumps": "alu_forged",
    "belt_tensioner": "alu_forged",
    "belt_idler": "steel_nitrided",
    "knock_sensor": "anodised",
    "cam_sensor": "anodised",
    "exhaust_flange": "inconel",
    "exhaust_gasket": "steel_nitrided",
    "collets_": "steel_nitrided",
    "ring_oil": "steel_nitrided",
    "ring_second": "steel_nitrided",
    "ring_top": "steel_nitrided",
    "dipstick": "steel_nitrided",
    "catch_tank": "alu_forged",
    "breathers": "alu_forged",
    "accessory_pulleys": "alu_forged",
    "starter": "alu_cast",
    "alternator": "alu_cast",
    "cam_caps": "alu_forged",
    "rod_bolts": "titanium",
    "main_cap": "alu_forged",
    "rod_shell": "copper_wound",
    "main_shell": "copper_wound",
    "hp_fuel_pump": "alu_cast",
    "fuel_feeds": "steel_nitrided",
    "fuel_rail": "alu_forged",
    "runner_": "alu_forged",
    "collector_": "inconel",
    "primary_": "inconel",
    "ecu_connector": "rubber_blk",
    "battery_terminal": "copper_wound",
    "battery_module": "anodised",
    "inverter_conn": "rubber_blk",
    "oil_filler": "anodised",
    "camcover_bolt": "titanium",
    "sump_baffle": "alu_forged",
    "sump_drain": "steel_nitrided",
    "mount_boss": "alu_cast",
    "gallery_plug": "steel_nitrided",
    "water_outlet": "alu_cast",
    "tappet_": "steel_nitrided",
    "retainer_": "titanium",
    "valve_spring": "spring_steel",
    "coil_": "rubber_blk",
    "injector_": "steel_nitrided",
    "pfi_injector": "steel_nitrided",
    "pfi_plug": "rubber_blk",
    "pfi_feed": "steel_nitrided",
    "sparkplug": "anodised",
    "cam_journals": "steel_nitrided",
    "camlobe": "steel_nitrided",
    "camshaft": "steel_nitrided",
    "valve_ex": "inconel",
    "valve_in": "titanium",
    "block":      "alu_cast",
    "bedplate":   "alu_cast",
    "head":       "alu_cast",
    "camcover":   "magnesium",
    "sump":       "magnesium",
    "crank":      "steel_nitrided",
    "rod":        "titanium",
    "piston":     "alu_forged",
    "valve":      "titanium",
    "spring":     "spring_steel",
    "cam":        "steel_nitrided",
    "plenum":     "carbon",
    "trumpet":    "carbon",
    "throttle":   "alu_forged",
    "turbo":      "inconel",
    "turbine_housing": "inconel",
    "turbine_wheel":   "inconel",
    "turbo_centre":    "alu_cast",
    "turbo_shaft":     "steel_nitrided",
    "turbo_oil":       "braided",
    # the cold side is aluminium, not Inconel: nothing on it ever
    # sees more than about 200 degrees
    "compressor_housing": "alu_cast",
    "compressor_wheel":   "anodised",
    "compressor_inlet":   "rubber_blk",
    "exhaust":    "inconel",
    "tailpipe":   "inconel",
    "wastegate":  "inconel",
    "mguk":       "copper_wound",
    "mguh":       "copper_wound",
    "inverter":   "anodised",
    "battery":    "anodised",
    "ecu":        "anodised",
    "flywheel":   "steel_nitrided",
    "bellhousing":"magnesium",
    "pump":       "alu_forged",
    "injector":   "steel_nitrided",
    "coil":       "rubber_blk",
    "spring":     "spring_steel", "retainer": "titanium",
    "bucket":     "steel_nitrided", "timing": "magnesium",
    "gear":       "steel_nitrided", "stud": "steel_nitrided",
    "bolt":       "steel_nitrided", "pickup": "alu_forged",
    "plumbing":   "alu_forged", "sensor": "anodised",
    "shield":     "inconel", "wheel": "titanium",
    "ring":       "steel_nitrided", "cap": "titanium",
    "gudgeon":    "steel_nitrided", "sump_line": "alu_forged",
}
DEFAULT_MATERIAL = "alu_cast"

PALETTE = {
    "alu_cast":       ((0.318, 0.326, 0.338), 1.00, 0.62),
    "alu_forged":     ((0.440, 0.450, 0.466), 1.00, 0.28),
    "magnesium":      ((0.276, 0.272, 0.258), 1.00, 0.58),
    "steel_nitrided": ((0.226, 0.232, 0.244), 1.00, 0.34),
    "titanium":       ((0.360, 0.372, 0.398), 1.00, 0.22),
    "spring_steel":   ((0.340, 0.348, 0.362), 1.00, 0.18),
    "carbon":         ((0.056, 0.058, 0.064), 0.30, 0.36),
    "inconel":        ((0.318, 0.246, 0.192), 1.00, 0.54),
    "copper_wound":   ((0.430, 0.226, 0.108), 1.00, 0.44),
    "anodised":       ((0.108, 0.136, 0.170), 1.00, 0.40),
    "rubber_blk":     ((0.042, 0.042, 0.046), 0.00, 0.86),
    # stainless overbraid: the oil and coolant lines that have to take
    # gallery pressure at 150 degrees are not rubber hose
    "braided":        ((0.404, 0.414, 0.430), 0.90, 0.46),
}

# Matched to the F110 project's resolutions. That engine reads as real and
# this one did not, and a large part of the difference was simply that its
# surfaces of revolution have 96 segments and these had 48.
TESS = 2.65  # global tessellation multiplier, applied in mesh.py

RES = {
    "revolve": 96,
    "small_revolve": 28,
    "pipe": 20,
}


# --------------------------------------------------------------------------
# Derived
# --------------------------------------------------------------------------

def swept_volume_cc():
    return math.pi * (BORE / 2.0) ** 2 * STROKE * N_CYL / 1000.0


def bore_stroke_ratio():
    return BORE / STROKE


def rod_stroke_ratio():
    return ROD_LENGTH / STROKE


def mean_piston_speed(rpm=REDLINE_RPM):
    """metres per second"""
    return 2.0 * (STROKE / 1000.0) * rpm / 60.0


def firing_interval():
    return 720.0 / N_CYL


def specific_power_kw_per_litre():
    return ICE_POWER_KW / (swept_volume_cc() / 1000.0)


def power_to_weight_kw_per_kg():
    return COMBINED_KW / MASS_KG


def compression_height():
    """Gudgeon pin centre to piston crown."""
    return PISTON["crown_t"] + 12.0


def required_deck_height(clearance=0.5):
    """Crank centreline to deck face, if the piston is to reach the deck."""
    return CRANK["throw"] + ROD_LENGTH + compression_height() + clearance


def bank_angle_rad(bank):
    """bank 0 = left (-y), bank 1 = right (+y)."""
    half = math.radians(V_ANGLE / 2.0)
    return half if bank else -half


def cylinder_x(i, bank=None):
    """Axial station of cylinder pair i (0..3), front to back.

    With `bank`, the station of that bank's cylinder -- which is NOT the same
    as the pair's. Both rods on a shared crankpin have to fit on it side by
    side, so the two banks are offset along the crank by one big-end width.
    Without that offset the two rods of every pair are modelled inside each
    other, which is exactly what this engine did: conrod_1 and conrod_2 had
    identical bounding boxes, and so did all four pairs of rod caps.
    """
    span = (N_CYL // 2 - 1) * BORE_SPACING
    x = -span / 2.0 + i * BORE_SPACING
    if bank is None:
        return x                      # the crankpin, centred between the two
    return x + (-1.0 if bank == 0 else 1.0) * BANK_OFFSET / 2.0


def cylinders():
    """(index 1-8, pair, bank, x, bank_angle) for every cylinder.

    `x` is the bank's own station, offset from the crankpin's.
    """
    out = []
    n = 1
    for pair in range(N_CYL // 2):
        for bank in (0, 1):
            out.append((n, pair, bank, cylinder_x(pair, bank),
                        bank_angle_rad(bank)))
            n += 1
    return out

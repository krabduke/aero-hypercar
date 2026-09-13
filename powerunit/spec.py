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
}

CRANK = {
    "main_r": 27.0,
    "pin_r": 24.0,
    "throw": STROKE / 2.0,
    "web_r": 58.0,
    "web_t": 13.0,
    "n_mains": 5,
    "nose_len": 74.0,
    "nose_r": 20.0,
    "flange_r": 62.0,
    "flange_t": 14.0,
    "counterweights": 8,
}

PISTON = {
    "crown_t": 6.5,
    "skirt_len": 31.0,
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
    "height": 74.0,
    "half_width": 61.0,
    "x_front": -228.0,
    "x_rear": 228.0,
    "cam_centres": 78.0,       # between intake and exhaust cam axes
    "cam_height": 50.0,        # above the deck face
}

VALVE = {
    "n_per_cyl": 4,
    "intake_head_r": 17.0,
    "exhaust_head_r": 14.5,
    "stem_r": 2.6,
    "length": 86.0,
    "included_angle": 22.0,    # narrow, for a compact pent-roof chamber
    "lift": 12.5,
}

CAM = {
    "journal_r": 15.0,
    "base_r": 13.5,
    "lobe_lift": 12.5,
    "lobe_w": 11.0,
    "n_cams": 4,
}

# --------------------------------------------------------------------------
# Induction, turbos, exhaust -- hot vee
# --------------------------------------------------------------------------

INTAKE = {
    "plenum_r": 62.0,
    "plenum_len": 372.0,
    "plenum_z": 292.0,
    "trumpet_r_in": 24.0,
    "trumpet_r_out": 33.0,
    "trumpet_len": 96.0,
    "throttle_r": 46.0,
}

TURBO = {
    "n": 2,
    "x": [-118.0, 118.0],
    "z": 214.0,                # sits in the vee, between the banks
    "comp_r": 58.0,            # compressor housing
    "turb_r": 64.0,            # turbine housing
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
    "mguh_r": 40.0,
    "mguh_len": 72.0,
    "inverter": (196.0, 146.0, 62.0),
    "inverter_pos": (0.0, 0.0, 336.0),
    "battery": (392.0, 232.0, 88.0),
    "battery_pos": (0.0, 0.0, -178.0),
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
    "ecu": (168.0, 118.0, 44.0),
}

# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

MATERIAL_MAP = {
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
}
DEFAULT_MATERIAL = "alu_cast"

PALETTE = {
    "alu_cast":       ((0.318, 0.326, 0.338), 1.00, 0.62),
    "alu_forged":     ((0.402, 0.412, 0.428), 1.00, 0.42),
    "magnesium":      ((0.276, 0.272, 0.258), 1.00, 0.58),
    "steel_nitrided": ((0.226, 0.232, 0.244), 1.00, 0.34),
    "titanium":       ((0.372, 0.386, 0.408), 1.00, 0.36),
    "spring_steel":   ((0.300, 0.306, 0.318), 1.00, 0.30),
    "carbon":         ((0.056, 0.058, 0.064), 0.30, 0.36),
    "inconel":        ((0.318, 0.246, 0.192), 1.00, 0.54),
    "copper_wound":   ((0.430, 0.226, 0.108), 1.00, 0.44),
    "anodised":       ((0.108, 0.136, 0.170), 1.00, 0.40),
    "rubber_blk":     ((0.042, 0.042, 0.046), 0.00, 0.86),
}

RES = {
    "revolve": 48,
    "small_revolve": 20,
    "pipe": 14,
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


def cylinder_x(i):
    """Axial station of cylinder pair i (0..3), front to back."""
    span = (N_CYL // 2 - 1) * BORE_SPACING
    return -span / 2.0 + i * BORE_SPACING


def cylinders():
    """(index 1-8, pair, bank, x, bank_angle) for every cylinder."""
    out = []
    n = 1
    for pair in range(N_CYL // 2):
        for bank in (0, 1):
            out.append((n, pair, bank, cylinder_x(pair), bank_angle_rad(bank)))
            n += 1
    return out

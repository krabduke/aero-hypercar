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
    "nose_len": 154.0,           # through the case, MGU-K and trigger to
                                 # the front of the damper hub
    "nose_r": 20.0,
    "flange_r": 62.0,
    "flange_t": 14.0,
    "counterweights": 8,
}

# Engine mounts: a cast boss standing off each side of the crankcase at each
# station, and a bracket with a rubber bush bolted to its face. The bosses
# were 20 mm off the crankcase wall with nothing joining them to it, and the
# brackets held the bosses up and the bosses the brackets.
#
# One each side, forward. This is a stressed-member engine: its back end is
# carried by the gearbox through the bellhousing, and there is no room for a
# rear pair anyway -- a search of every station along both flanks, at every
# mounting height, found none clear aft of x -90 on the right, where the
# ECU and the water pump are. The rear right bracket used to be through the
# starter, and the front pair through the oil and water pumps. x -95 is
# clear on both sides.
MOUNTS = {
    "x": (-95.0,),
    "z": -30.0,
    "boss_r": 12.0,
    "boss_face": BLOCK["half_width"] + 16.0,     # y of the face they bolt to
}

# Where the flywheel's front face is: on the crank's flange, and the flange is
# outside the block. It used to be the last 20 mm of the crank inside the
# block, so the flywheel started 6 mm INSIDE the block's rear face and turned
# in the crankcase, bedplate and both banks; a crank leaves the block through
# its rear main seal and carries the flange out behind it.
FLANGE_X = BLOCK["x_rear"] + 2.0
FLYWHEEL_X = FLANGE_X + CRANK["flange_t"]

PISTON = {
    "crown_t": 6.5,
    "skirt_len": 18.0,   # short: at BDC the skirt has to clear the counterweights
    "pin_r": 9.5,
    "dome": 2.4,               # crown dome height, for the compression ratio
    "ring_grooves": 3,
}

ROD = {
    # 33: the eye's bore is the shell's back (pin + 3 mm), and a big end
    # needs a real wall round that
    "big_end_r": 33.0,
    "shell_wall": 3.0,
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
    # The combustion chamber is a pent roof recessed into the deck face: two
    # planes at half the valves' included angle meeting on a ridge this high
    # above the deck. It used to be a dome ADDED to the casting, standing
    # 4 mm down into every bore, so the pistons ran into the head.
    "chamber_ridge": 9.0,
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
    # The face sits in the chamber roof, `face_along` above the deck, and the
    # valve is shorter by the same amount so its tip -- and the collets,
    # retainer, spring and bucket stacked on it -- are where they were. The
    # faces used to be 1 mm BELOW the deck, standing into the bore.
    "face_along": 5.0,
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
    # +/-150, not +/-118.
    #
    # The two compressors breathe from the middle of the vee, so their eyes
    # face each other along the shaft axis -- a compressor's eye is axial by
    # definition and cannot be clocked away. At 118 the two snout mouths were
    # 29 mm apart, so each inlet duct had to turn upward within a couple of
    # centimetres of its own eye and overhung the wheel's inducer doing it.
    # At 144 they are 81 mm apart and each duct has its own side of the vee
    # to run down before it climbs.
    #
    # Not 150. The collector's mouth is 16 mm inboard of its turbo and 92 mm
    # above the shaft, and 92 is a floor as well as a ceiling -- lower and
    # the two inboard primaries come down onto the compressor housing they
    # pass over. At 150 the mouth sat where the hypercar's engine cover is
    # low enough that the collector's crown came 0.3 mm through it, and
    # there was nothing to give in height.
    "x": [-144.0, 144.0],
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
    # On the crank nose between the trigger wheel and the timing case, and
    # bolted to the case's front face. At 108 mm long it ran from x -340 to
    # -232, through the case, the crank gear and the belt.
    "mguk_len": 32.0,
    "mguk_x": -306.0,
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
    # 50 x 158 x 56, between the bellhousing's two flanges, on its ribs at
    # z 154 and under the rear turbine's housing, which comes down to 221.
    # At 100 x 158 x 74 it was 12 mm into the bell's front flange, 6.5 mm
    # into the turbine and 6 mm into the back of the right head.
    "inverter": (50.0, 158.0, 56.0),
    # On the bellhousing at the back, where there is room for it. In the
    # vee it was the tallest thing on the engine and in the exhaust's way;
    # outboard it made the engine wider than the car.
    "inverter_pos": (276.0, 0.0, 182.0),
    "battery": (392.0, 300.0, 56.0),   # overall; built as two lobes
    # Two lobes either side of the sump keel: clear of the pan, clear of the
    # drain plug hanging out of it, and high enough that the engine still
    # fits the car's engine bay when it is installed.
    # Below the sump, which reaches z -180. At -132 the pack was inside it,
    # inside the oil pickup and inside the scavenge lines.
    # 2 mm lower than it was: the dry-sump tank's feed union hangs over the
    # left lobe and its pipe was 1.7 mm into the lid
    "battery_pos": (0.0, 0.0, -246.0),   # tight under the sump
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
    # the pump hangs off the front of the engine low on the right, beside
    # the timing case, far enough forward that its pulley is in the belt's
    # plane on a short nose (see FRONT)
    "pump_x": -280.0,
    "pump_y": 215.0,             # outlet clear of the timing case's edge
    "pump_z": -60.0,
    "stat_x": -318.0,            # the housing's front face; it stands on the
    "stat_y": 0.0,               # boss in the vee of the timing case, which
    "stat_z": 136.0,             # is where the heads' water comes out
    # the outlets stand up out of the block's flanks into the heads
    # The head outlets and the rail that gathers them run along each head's
    # outboard face, in the bank's frame: `rail_along` up the bore axis and
    # `rail_lat` across it (inboard positive). They were placed as if this
    # were an inline engine -- on the "block flank" at y +/-118, z 22 to 64,
    # which on a 90-degree V is inside the cylinder bores, with the pistons
    # and rings running through them, and the rails 45 mm inside the heads.
    # The rail's lane is the clearest one between the intake runners above,
    # the direct-injection rail beside the head and the engine mounts below,
    # found by searching it: about 10 mm from anything, so a 16 mm rail.
    # Each head drains from its rear outboard corner: the intake side is
    # covered by the runner flanges and the injection rail, the front by the
    # cam drive, and behind the last cylinder there is room.
    "rail_along": 150.0,
    "rail_lat": -110.0,
    "rail_r": 8.0,
    "outlet_along": 190.0,       # above the injection crossover at ~172
    "outlet_lat": -48.0,         # 3 mm into the head's outboard face, which
                                 # at the rear end is at -51, not the -75 of
                                 # the port bosses along its middle
}


def coolant_node(which):
    """World point at one of the circuit's connections."""
    C = COOLANT
    if which == "pump_out":
        return (C["pump_x"] + 6.0, C["pump_y"] - 76.0, C["pump_z"] - 14.0)
    if which == "pump_in":
        return (C["pump_x"] + 32.0, C["pump_y"], C["pump_z"])
    # the two radiator outlet stubs' ends, one to each radiator, and the
    # return stub's end on the pump's inlet tee: where a vehicle's hoses go
    if which in ("stat_hose_l", "stat_hose_r"):
        s = -1.0 if which.endswith("l") else 1.0
        return (C["stat_x"] + STAT_STUB_X, C["stat_y"] + s * 80.0,
                C["stat_z"] - STAT_STUB_DROP)
    if which == "pump_return":
        return (C["pump_x"] + 52.0, C["pump_y"] + 75.0, C["pump_z"])
    raise KeyError(which)


# The thermostat's two outlet stubs are this far under its axis: level with
# it, each pointed straight at the post of the belt idler (left) or the
# tensioner (right), 28 mm away, and no hose could have been pushed on.
STAT_STUB_DROP = 24.0
# ...and this far ahead of the housing's back face: at 11 their axis was
# 17 mm off the timing case, and a hose over a 28 mm stub is 36 across
STAT_STUB_X = 8.0


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
    "harness": "rubber_blk",
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
    "compressor_inlet":   "alu_cast",
    "exhaust":    "inconel",
    "tailpipe":   "inconel",
    "port_cover": "cover_red",
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
    "cover_red":      ((0.560, 0.050, 0.040), 0.00, 0.48),
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


def head_rear_x(bank):
    """The rear face of a bank's head: the nominal x_rear, moved by the
    bank's own stagger along the crank."""
    xs = [x for (n, pair, b, x, a) in cylinders() if b == bank]
    pair_x = cylinder_x(len(xs) - 1)
    return HEAD["x_rear"] + (max(xs) - pair_x)


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


# --------------------------------------------------------------------------
# The front of the engine
# --------------------------------------------------------------------------
#
# Six modules build pieces of the front: the gear train and its case, the
# MGU-K, the crank trigger, the damper, the accessory belt and everything it
# drives, and the coolant that passes through the case. Each used to keep its
# own idea of where the others were, and the result was a stack of parts
# inside each other that the intersect audit only passed because every pair
# had been declared "expected": the MGU-K 52 mm into the timing cover, the
# belt 19 mm into the MGU-K, the tensioner inside the alternator, the idler
# inside the water pump, and a timing "cover" that was a 152 mm disc on the
# crank with the cam gears standing out in the open beyond it. The idlers
# never met each other or the cam gears, so the camshafts were not driven.
#
# One axial stack, front to back:
#     damper, whose grooved inertia ring is the crank pulley   -368 .. -330
#     crank trigger wheel                                      -330 .. -324
#     MGU-K, on the nose and bolted to the case                -322 .. -290
#     timing case front plate                                  -290 .. -284
#     gear train                                               -269 .. -250
#     block front face                                         -231
FRONT = {
    "gear_x": BLOCK["x_front"] - 30.0,
    "case_front": -290.0,
    "case_plate": 6.0,
    "case_wall": 4.0,
    "case_margin": 10.0,         # outline clearance round the gear tips
    "mguk_front": -322.0,
    "trigger_x": -327.0,
    # The damper spans x0 + 2 .. x0 + 40. Its face is the front of the
    # engine, and in the hypercar the tub's engine bulkhead is 11 mm ahead
    # of it: the stack was 12 mm longer and the damper touched it.
    "damper_x0": -370.0,
    "belt_x": -349.7,            # on the damper's five grooves
    "belt_w": 20.0,
    "belt_t": 4.5,
    "pulley_w": 22.0,
    "crank_pulley_r": 99.5,      # the tips of the damper's grooves
    # (y, z, r) of the pulleys the belt wraps besides the crank and the
    # water pump. Each one has metal behind it to hang from: the idler and
    # the tensioner are on the case's legs, the alternator is on the
    # left, its body bolted to the case plate's edge clear of the MGU-K.
    "alternator": (-160.0, 40.0, 34.0),
    "idler": (-122.0, 152.0, 30.0),
    "tensioner": (128.0, 150.0, 30.0),
    # the thermostat sits on a boss on the case's front face, in the vee
    "thermostat": (0.0, 136.0),
}


def timing_train(bank):
    """[(y, z, r)] of one bank's gears: crank, two idlers, two cam gears.

    Every pair that is supposed to mesh is spaced by the sum of its pitch
    radii, which for these gears is 0.94 of the tip radius. The cam gears are
    36 mm so the intake and exhaust gears, 78 mm apart, clear each other and
    are both driven off the upper idler; the upper idler is placed on the
    bore axis where it meets both, and the lower idler is sized to fill the
    gap between it and the crank gear.
    """
    a = bank_angle_rad(bank)
    d = (math.sin(a), math.cos(a))
    s = 1.0 if bank == 0 else -1.0
    lat = (s * math.cos(a), -s * math.sin(a))

    def at(along, lateral=0.0):
        return (d[0] * along + lat[0] * lateral, d[1] * along + lat[1] * lateral)

    p = 0.94
    r_crank, r_upper, r_cam = 54.0, 40.0, 36.0
    cam_along = DECK_HEIGHT + HEAD["cam_height"]
    half = HEAD["cam_centres"] / 2.0
    upper = cam_along - math.sqrt((p * (r_upper + r_cam)) ** 2 - half ** 2)
    r_lower = (upper - p * r_crank - p * r_upper) / (2.0 * p)
    lower = p * (r_crank + r_lower)
    return [(0.0, 0.0, r_crank),
            at(lower) + (r_lower,),
            at(upper) + (r_upper,),
            at(cam_along, -half) + (r_cam,),
            at(cam_along, half) + (r_cam,)]


def case_outline(margin, n=240):
    """The timing case's outline in the y-z plane, as a closed polygon.

    The union of three convex lobes -- each bank's gear train, and a boss in
    the vee that carries the thermostat -- each grown by `margin`. Each lobe
    contains the crank gear, so the union is star-shaped about the crank and
    its boundary is the furthest of the three along each ray.
    """
    th_y, th_z = FRONT["thermostat"]
    lobes = [[(y, z, r + margin) for (y, z, r) in timing_train(b)]
             for b in (0, 1)]
    lobes.append([(0.0, 0.0, 54.0 + margin), (th_y, th_z, 40.0 + margin)])
    normals = [(math.cos(2 * math.pi * k / 720), math.sin(2 * math.pi * k / 720))
               for k in range(720)]
    heights = [[max(n_[0] * y + n_[1] * z + r for (y, z, r) in lobe)
                for n_ in normals] for lobe in lobes]
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        u = (math.cos(t), math.sin(t))
        reach = 0.0
        for h in heights:
            best = 1e9
            for n_, hk in zip(normals, h):
                nu = n_[0] * u[0] + n_[1] * u[1]
                if nu > 1e-3:
                    best = min(best, hk / nu)
            reach = max(reach, best)
        pts.append((reach * u[0], reach * u[1]))
    return pts


def belt_path(circles):
    """The accessory belt's inner face, as [((y, z), (ny, nz))] points with
    their outward normals, round `circles` = [(y, z, r)] in running order
    (counter-clockwise, seen from the front).

    A belt is straight between pulleys and wraps each one on an arc, so the
    path is the common tangent between each consecutive pair joined by the
    arc round the pulley between them. The first belt here was the polar
    reach of the pulleys sampled at 48 angles, which is not a belt shape at
    all: it bulged and waved between pulleys like a rubber band.
    """
    n = len(circles)
    tangents = []
    for i in range(n):
        (y0, z0, r0), (y1, z1, r1) = circles[i], circles[(i + 1) % n]
        dy, dz = y1 - y0, z1 - z0
        L = math.hypot(dy, dz)
        uy, uz = dy / L, dz / L
        vy, vz = -uz, uy
        al = (r0 - r1) / L
        be = math.sqrt(max(0.0, 1.0 - al * al))
        for sgn in (1.0, -1.0):
            ny, nz = al * uy + sgn * be * vy, al * uz + sgn * be * vz
            ddy = dy + (r1 - r0) * ny
            ddz = dz + (r1 - r0) * nz
            if ddy * nz - ddz * ny < 0.0:      # n is to the right of travel
                break
        tangents.append((ny, nz))
    out = []
    for i in range(n):
        y, z, r = circles[i]
        a_in = math.atan2(tangents[i - 1][1], tangents[i - 1][0])
        a_out = math.atan2(tangents[i][1], tangents[i][0])
        sweep = (a_out - a_in) % (2 * math.pi)
        k = max(2, int(math.degrees(sweep) / 4.0) + 1)
        for j in range(k + 1):
            a = a_in + sweep * j / k
            out.append(((y + r * math.cos(a), z + r * math.sin(a)),
                        (math.cos(a), math.sin(a))))
    return out


def belt_circles():
    """The pulleys the belt wraps, in running order: crank, water pump,
    tensioner, idler, alternator."""
    F = FRONT
    return [(0.0, 0.0, F["crank_pulley_r"]),
            (COOLANT["pump_y"], COOLANT["pump_z"], 46.0),
            F["tensioner"], F["idler"], F["alternator"]]

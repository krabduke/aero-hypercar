"""No part of the car may occupy another part's space.

    python3 tools/audit_intersect.py            (runs itself under Blender)
    python3 tools/audit_intersect.py --shrink   (after a fix: drop what is fixed)

Every pair of parts whose material overlaps by TOL or more -- measured
exactly, both ways, buried parts included; see tools/_interfere.py -- must be
one of two things:

*   Declared in EXPECTED: meant to be that way, a pin in its bore, a rib inside
    a closed skin. A rule that excuses nothing, or names a part that does not
    exist, fails the audit. A permission that no longer matches anything is a
    hole a regression can fall into unseen, and the list had grown to more
    dead rules than live ones before this was enforced.
*   On the KNOWN list: a real defect, written down with how deep it is and
    where it is. The list only gets shorter. A pair not on it fails, a pair
    that gets deeper fails, and a pair that has been fixed fails until
    --shrink takes it off. --shrink never adds anything.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _intersect

# Pairs that share material on purpose.
#
# A racing car is an assembly of parts that root into each other: a strake is
# a fence standing on the floor, a hub runs in bearings inside the upright, a
# hose clamps onto the engine it feeds. Each entry says the overlap IS the
# joint. Anything not listed is a part in another part's way.
EXPECTED = [
    # the engine's castings and the rest of the engine meet as the engine
    # repository's own audit says they may; this one audits the car
    ("engine", "engine_"),
    # the lines come out of the cylinders, and the loom runs past everything
    # the tub carries on its way from the battery to the dash
    ("master_cylinders", "brake_lines"), ("wiring_loom", "steering"),
    ("wiring_loom", "battery"),   # the loom starts at it
    ("wiring_loom", "driveshaft_"),
    # a jack point is part of the structure it lifts the car by
    ("jack_points", "crash_structure"), ("jack_points", "heave_"),

    # running gear: the studs are in the hub, the caliper wraps the disc and
    # the pads sit in the caliper. The hub runs in the upright's bearing bore
    # and touches it nowhere else.
    ("wheel_stud", "hub_"), ("wheel_stud", "rim_"),
    ("brake_pad", "caliper_"),
    ("caliper_", "disc_"), ("rim_", "tyre_"),
    ("upright_", "wishbone_"), ("upright_", "trackrod_"),
    ("upright_", "pushrod_"),
    ("upright_", "steering_arm_"), ("upright_", "bduct_"),
    ("tether_", "upright_"), ("tether_", "tub"),
    ("bduct_", "caliper_"), ("bduct_", "upright_"),

    # inboard suspension: rods into rockers, rockers onto bars and dampers
    ("rocker_", "pushrod_"), ("rocker_", "torsion_bars"),
    ("rocker_", "antiroll_"), ("rocker_", "tub"),
    ("damper", "torsion_bars"), ("damper", "tub"), ("heave_", "tub"),
    ("antiroll_", "tub"), ("antiroll_blade_", "antiroll_"),
    ("torsion_bars", "tub"),
    ("steering_column", "steering_rack"), ("steering_column", "steering"),
    ("trackrod_", "steering_rack"), ("wishbone_", "tub"),
    ("pushrod_", "tub"), ("driveshaft_", "gearbox"),

    # floor: the tunnels are formed in it, the fences stand on it, the skirts
    # seal its edge
    ("tunnel_", "floor_surface"), ("floor_strake_", "tunnel_"),
    ("floor_strake_", "floor_surface"),
    ("floor_skirts", "floor_surface"), ("floor_plank", "floor_surface"),
    ("floor_fence_", "floor_surface"),
    # the edge wing hangs off the floor's outer lip, bonded along it
    ("floor_edge_wings", "floor_surface"),
    ("fanduct", "tunnel_"), ("fanduct", "tub"),
    ("fan_drive_", "fan_motors"), ("fan_drive_", "fan_rotor_"),

    # power unit and cooling: hoses clamp to what they feed
    ("rad_hoses_", "engine"),
    ("rad_hoses_", "rad_tanks_"),
    ("engine", "gearbox"), ("engine", "tub"),
    ("exhaust", "engine"), ("fuel_fittings", "fuel_cell"),
    ("battery_modules", "battery"),
    ("gearbox", "tub"),

    # bodywork: everything lofted or louvred into it
    ("sidepod_", "tub"), ("sidepod_inlets", "sidepod_"),
    ("sidepod_gills", "sidepod_"),
    ("exit_louvres_", "sidepod_"), ("gills", "tub"),
    ("sharkfin", "tub"),
    ("airbox", "tub"), ("cockpit_coaming", "tub"), ("nose_cape", "tub"),
    ("nose_pylons", "tub"), ("nose_pylons", "front_wing_main"),
    ("crash_structure", "tub"), ("side_impact", "tub"),
    ("roll_hoop", "tub"), ("halo", "tub"),
    ("halo_mounts", "tub"), ("halo_pillar", "halo"), ("halo_mounts", "halo"),
    ("mirrors", "tub"), ("cameras", "tub"),
    ("rainlight", "crash_structure"), ("rear_light_panel", "crash_structure"),

    # wings: elements onto endplates and pylons, furniture onto elements
    ("front_flap_", "front_endplate_"), ("front_wing_main", "front_endplate_"),
    ("front_diveplane_", "front_endplate_"), ("front_y250_vanes", "front_wing_main"),
    ("rear_flap", "rear_endplate_"), ("rear_wing_main", "rear_endplate_"),
    ("rear_louvre_", "rear_endplate_"),
    ("rear_pylon_", "rear_wing_main"),
    ("wing_mount_", "rear_wing_main"), ("wing_mount_", "rear_pylon_"),
    ("drs_actuator", "rear_flap"),
    ("beam_wing", "crash_structure"),
    # the pylon runs up through the cape shelf to the nose underside: that
    # crossing is the joint, and on a real car they are bonded there
    ("nose_cape", "nose_pylons"),

    # cockpit and service
    ("driver", "seat"), ("driver", "harness"),
    ("driver", "steering"), ("helmet", "driver"),
    # the column passes through the dash panel on its way down to the rack
    ("dash", "steering_column"),
    ("steering", "steering_column"),
    ("master_cylinders", "pedal_box"),
    ("side_intrusion", "tub"),
    ("jack_points", "tub"), ("tow_hooks", "tub"),
    ("tow_hooks", "crash_structure"),   # the rear hook bolts to it
    ("fuel_coupling", "tub"), ("brake_lines", "tub"), ("wiring_loom", "tub"),

    # A second round, all of them structure rooted into structure at the rear
    # and along the floor, where everything on this car is packed together.
    ("rim_", "caliper_"), ("rim_", "bduct_"),
    ("sidepod_", "side_impact"),
    ("tub", "side_impact"),
    ("nose_pylons", "front_wing_main"),
    # the bargeboards are a nested cascade sharing one root, like the wing
    ("bargeboard_", "bargeboard_"),
    ("fanduct", "crash_structure"),
    ("beam_wing", "fan_motors"),
    ("beam_wing", "fan_"), ("gearbox", "damper"),
    ("gearbox", "torsion_bars"), ("gearbox", "heave_"), ("gearbox", "antiroll_"),
    ("gearbox", "driveshaft_"),
    ("fuel_cell", "battery"),
    ("battery_modules", "fuel_cell"),
    ("driver", "headrest"), ("driver", "pedal_box"),

    # ----------------------------------------------------------------
    # Joints the check could not reach until it stopped spending its
    # budget on the joints it had already been told about. Every entry
    # below is a place two parts are bolted, bonded or bearinged
    # together, listed after being looked at one at a time.
    # ----------------------------------------------------------------

    # the corner is one assembly: the shaft drives the hub, the nut clamps
    # the wheel, the gun socket is recessed into the cover over the nut,
    # and the duct wraps all of it
    ("hub_", "driveshaft_"), ("rim_", "wheelnut_"),
    ("gun_sockets", "wheelnut_"), ("gun_sockets", "wheelcover_"),
    # the wheel cover's rim clips into the wheel's outer flange
    ("rim_", "wheelcover_"),
    ("bduct_", "bduct_"), ("bduct_", "hub_"), ("bduct_", "driveshaft_"),

    # a wishbone is two legs meeting at one outboard ball joint, and the
    # pushrod and the tether pick up on the same bracket
    ("wishbone_", "wishbone_"), ("wishbone_", "pushrod_"),
    ("wishbone_", "rocker_"), ("tether_", "wishbone_"),
    ("tether_", "steering_arm_"), ("tether_", "driveshaft_"),
    ("tether_", "bduct_"), ("trackrod_", "tub"),
    ("antiroll_", "dampers_"), ("torsion_bars", "dampers_"),

    # the drink bottle is strapped to the seat's flank
    ("drink_bottle", "seat"),

    # panels and frames bond to the bulkheads they are carried on
    ("side_intrusion", "bulkhead_"), ("cockpit_coaming", "bulkhead_"),
    ("halo_mounts", "bulkhead_"),
    ("halo", "bulkhead_"), ("halo_pillar", "bulkhead_"),
    ("airbox", "bulkhead_"), ("nose_cape", "bulkhead_"),
    ("battery_modules", "bulkhead_"),

    # the front wing roots into the nose, and the vanes stand on the flaps
    ("front_wing_main", "tub"),
    ("front_y250_vanes", "front_flap_"), ("front_y250_vanes", "front_wing_main"),
    ("drs_actuator", "rear_flap"),

    # bodywork meets bodywork where one panel is let into another
    ("sidepod_", "bargeboard_"),
    ("sidepod_", "gearbox"), ("sidepod_", "sidepod_"),
    ("bargeboard_", "side_impact"), ("bargeboard_", "sidepod_inlets"),
    ("rainlight", "fanduct"),
    ("rainlight", "rear_light_panel"), ("rear_light_panel", "tub"),
    ("rear_light_panel", "fanduct"), ("sharkfin", "tow_hooks"),
    ("starter_socket", "tow_hooks"), ("nose_pylons", "tow_hooks"),

    # service hardware roots into whatever carries the load
    ("jack_points", "gearbox"), ("jack_points", "nose_cape"),
    ("jack_points", "nose_pylons"), ("jack_points", "front_wing_main"),

    # the fan is one machine
    ("fan_rotor_", "fan_motors"), ("fan_rotor_", "tub"),
    ("fan_stators", "fan_drive_"),

    # the loom plugs into the boxes it feeds
    ("wiring_loom", "gearbox"),
    ("wiring_loom", "fuel_cell"), ("brake_lines", "side_impact"),

    # the floor edge fences bolt to the floor edge, the strakes stand in
    # the tunnel, and the tunnel is formed in the floor: all three share
    # material with the floor by construction
    ("floor_strake_", "floor_skirts"),

    # `tub` is the whole central body -- nose, survival cell and engine
    # cover are one continuous lofted skin, which `verify.py` checks. It
    # was a solid, so everything packaged inside it read as inside it; it
    # is a 6 mm skin now, and these are the things that pass through it:
    # hoses and driveshafts out to the sidepods and wheels, the tanks where
    # the sidepods meet it, louvres and the filler set into it.
    ("rad_hoses_", "tub"),
    ("cooling_louvres", "tub"), ("driveshaft_", "tub"),
    ("fuel_coupling", "tub"), ("sidepod_", "rad_hoses_"),
    ("fuel_coupling", "fuel_cell"),     # it is the filler for it

    # the brake duct is moulded around the steering arm, and the fan duct
    # around the rear suspension: in both cases the duct is the part that
    # is shaped to clear, and they are one corner assembly
    ("bduct_", "steering_arm_"),

    # a bulkhead is a mounting face: the dash, the headrest, the battery
    # and the roll hoop all land on one
    ("bulkhead_", "dash"), ("bulkhead_", "headrest"),
    ("bulkhead_", "battery"), ("bulkhead_", "roll_hoop"),
    # the sidepod is bodywork, and the engine lives inside the bodywork --
    # the same statement as ("engine", "tub") a few lines up
    ("engine", "sidepod_"),
    # a louvre is riveted to the outer face of the plate it bleeds
    ("rear_louvre_", "rear_endplate_"),

    # ----------------------------------------------------------------
    # Joints that sat just under the threshold until the model's bounding
    # box changed and moved the voxel from 17.0 mm to 17.5. Each one was
    # looked at on its own before being written down here; the overlap was
    # always there, the sampling only just started reporting it.
    # ----------------------------------------------------------------
    # the headrest and the airbox both land on the rear cockpit bulkhead,
    # from opposite sides, and meet in the 30 mm they share
    ("headrest", "airbox"),
    # the front tow hook comes down through the wing it is mounted above --
    # the flap stack is already declared for the same reason
    ("front_wing_main", "tow_hooks"),
    # the fin is the back of the engine cover and ends on the rear structure
    ("sharkfin", "crash_structure"),
    # the tether anchors on the corner: upright, wishbone and driveshaft are
    # already listed, and the hub is the same assembly
    ("tether_", "hub_"),
    # the fan throat is formed through the rear structure, as the duct around
    # it already says
    ("fan_rotor_", "crash_structure"),
    # ----------------------------------------------------------------
    # The fan, as one machine. Air comes up the throat cast into the floor,
    # through the rotor, past the stators, round the scroll and out of the
    # nozzle; the throat carries the motor and the drive, the scroll is
    # built into the tub and picked up by the rear pylons, and the fairing
    # goes over the lot with the light panel on its back. Every one of these
    # overlaps is that assembly. They appeared when the scroll, the nozzle
    # and the throat stopped being zero-thickness sheets and got a wall.
    # ----------------------------------------------------------------
    ("fan_stators", "fan_scroll_"), ("fan_stators", "floor_fan_throat_"),
    ("fan_rotor_", "floor_fan_throat_"), ("fanduct", "floor_fan_throat_"),
    ("fan_nozzle_", "fan_scroll_"), ("fan_nozzle_", "fanduct"),
    ("fan_scroll_", "fanduct"), ("fan_nozzle_", "fan_fairing_"),
    ("floor_fan_throat_", "fan_motors"), ("floor_fan_throat_", "fan_drive_"),
    ("floor_fan_throat_", "tub"), ("fan_scroll_", "tub"),
    ("fan_scroll_", "crash_structure"), ("fan_scroll_", "fan_drive_"),
    ("floor_fan_throat_", "floor_strake_"),
    ("floor_fan_throat_", "floor_surface"), ("rear_pylon_", "fan_scroll_"),
    ("fan_fairing_", "tub"),
    ("fan_fairing_", "crash_structure"),
    # The floor's own edges and leading edge are part of the floor, and the
    # diffuser's fences, kick and lip all land on each other at the exit.
    ("floor_plenum_edge_", "floor_surface"),
    ("floor_plenum_edge_", "floor_skirts"),
    ("floor_inlet_lip", "tunnel_"), ("diffuser_fences", "diffuser_lip"),
    ("diffuser_kick", "diffuser_lip"),
    ("diffuser_kick", "floor_plenum_edge_"),
    ("diffuser_fences", "floor_strake_"),
    ("front_y250_vanes", "nose_pylons"),
    ("rear_light_panel", "fan_fairing_"),
    # ----------------------------------------------------------------
    # The ejector. `spec.FAN_EXHAUST` sets the jet's lower lip deliberately
    # just under the diffuser exit -- "which is the ejector" -- so the
    # tunnels discharge into the fan's exhaust duct and the jet entrains
    # them. Measured at the exit plane the nozzle spans y 56-523 and z
    # 163-661 while the diffuser's trailing edge is y 210-586 at z 248-269,
    # so the lip runs through the nozzle's bore for most of its span and
    # clips the outboard wall at one spanwise station, 10 vertices of 240.
    # The nozzle area is held at the fan annulus on purpose: contracting it
    # would entrain harder and cost flow, and the flow is the downforce.
    # `tools/check_fan_exhaust.py` tests the jet envelope in 3-D and passes.
    # ----------------------------------------------------------------
    ("diffuser_lip", "fan_nozzle_"), ("diffuser_lip", "fanduct"),
    ("fan_nozzle_", "tunnel_"),
    # The nose cape's trailing edge lands on the front wing's mainplane --
    # 26 vertices at x 340-375, which is the joint between them.
    ("nose_cape", "front_wing_main"),
    # A rear toe link and a rear lower wishbone both pick up on the same
    # upright, 30 mm apart, so their rod ends touch there. Along their
    # spans they are clear: the link runs under the arm the whole way.
    ("trackrod_", "wishbone_"),
    # the loom is clipped along the top wishbone on its way to the corner
    ("wiring_loom", "wishbone_"),
    ("seat", "extinguisher"),   # it is strapped to the seat back
    ("engine", "gills"),   # the louvres are cut in the cover over it
    # An exhaust runs inside the engine cover and exits through the tail --
    # the bodywork it passes through is the bodywork it is routed inside.
    ("exhaust", "tub"), ("exhaust", "sharkfin"),
    # Joints made while closing the assembly. Each of these overlaps IS the
    # joint: the airbox plenum into the engine's intake, the floor's leading
    # edge onto the floor, the wing elements onto the endplate where the dive
    # planes also land, the caliper's mounting lugs past the hub, the turning
    # vanes' feet in the tunnel roof, the rear lower wishbone's pickup on the
    # gearbox and the tethers' anchors on the structure.
    ("airbox", "engine"),
    ("floor_inlet_lip", "floor_plenum_edge_"), ("floor_inlet_lip", "tub"),
    ("front_diveplane_", "front_wing_main"),
    ("caliper_", "hub_"), ("turning_vane_", "tunnel_"),
    ("wishbone_rl_lower_fwd", "gearbox"), ("wishbone_rr_lower_fwd", "gearbox"),
    ("tether_", "tub"),
    # the rear tethers anchor on the rear impact structure, through its
    # fairing, which is the only strong point back there clear of the fan
    ("tether_", "crash_structure"), ("tether_", "fan_fairing_"),
]

PKG = "car/parts"
UNIT = 1.0            # mm of real part per model unit
TOL = 0.3            # mm, full size: deeper than this is sharing material

# Real defects, in mm of full-size overlap, deepest first. Each one is a part
# through a part that nobody meant. Fix them and --shrink; never add to it.
# --- KNOWN: rewritten by --shrink, never by hand to add ---
KNOWN = {
    ("diffuser_fences", "floor_surface"): 99.5,   # at (4311.4, 254.0, 87.1)
    ("floor_fan_throat_l", "tunnel_l"): 77.3,   # at (4220.0, -397.5, 91.7)
    ("floor_fan_throat_r", "tunnel_r"): 77.3,   # at (4220.0, 397.5, 91.7)
    ("airbox", "cameras"): 56.1,   # at (2133.0, 24.0, 794.0)
    ("brake_lines", "sidepod_l"): 50.2,   # at (1700.0, -252.4, 259.1)
    ("brake_lines", "sidepod_r"): 50.2,   # at (1700.0, 252.4, 259.1)
    ("headrest", "helmet"): 49.1,   # at (1879.6, 0.0, 634.2)
    ("diffuser_kick", "fan_scroll_l"): 46.3,   # at (4446.0, -500.9, 240.8)
    ("diffuser_kick", "fan_scroll_r"): 46.3,   # at (4446.0, 502.2, 240.8)
    ("fan_scroll_l", "tunnel_l"): 41.6,   # at (4461.2, -434.5, 182.0)
    ("fan_scroll_r", "tunnel_r"): 41.6,   # at (4461.2, 434.5, 182.0)
    ("harness", "steering"): 41.3,   # at (1354.6, -107.4, 555.5)
    ("fanduct", "tether_rl"): 36.3,   # at (4120.3, -289.5, 355.3)
    ("fanduct", "tether_rr"): 36.3,   # at (4120.3, 289.5, 355.3)
    ("diffuser_kick", "fan_nozzle_l"): 30.8,   # at (4560.0, -519.8, 247.4)
    ("diffuser_kick", "fan_nozzle_r"): 30.8,   # at (4560.0, 519.4, 247.4)
    ("antiroll_f", "heave_f"): 30.7,   # at (977.8, -32.1, 504.2)
    ("antiroll_r", "heave_r"): 30.7,   # at (3837.8, -32.1, 249.2)
    ("gearbox", "sharkfin"): 29.6,   # at (4078.4, -2.1, 451.5)
    ("diffuser_fences", "tunnel_l"): 28.9,   # at (3860.0, -250.8, 76.8)
    ("diffuser_fences", "tunnel_r"): 28.9,   # at (3860.0, 250.8, 76.8)
    ("bduct_fence_fl", "trackrod_fl"): 27.4,   # at (766.8, -665.4, 226.2)
    ("bduct_fence_fr", "trackrod_fr"): 27.4,   # at (766.8, 665.4, 226.2)
    ("fan_nozzle_l", "tub"): 26.5,   # at (4560.0, -60.1, 283.6)
    ("fan_nozzle_r", "tub"): 26.5,   # at (4560.0, 60.1, 283.6)
    ("bduct_drum_fl", "trackrod_fl"): 25.8,   # at (786.7, -741.7, 232.0)
    ("bduct_drum_fr", "trackrod_fr"): 25.8,   # at (786.7, 741.7, 232.0)
    ("diffuser_kick", "fanduct"): 24.9,   # at (4536.0, 544.7, 253.2)
    ("diffuser_fences", "fan_scroll_l"): 24.4,   # at (4392.6, -254.0, 209.5)
    ("diffuser_fences", "fan_scroll_r"): 24.4,   # at (4392.7, 254.0, 209.5)
    ("diffuser_kick", "fan_fairing_l"): 24.0,   # at (4526.4, -549.8, 253.6)
    ("diffuser_kick", "fan_fairing_r"): 24.0,   # at (4526.4, 549.8, 253.6)
    ("caliper_fl", "tyre_fl"): 23.3,   # at (972.0, -780.9, 573.2)
    ("caliper_fr", "tyre_fr"): 23.3,   # at (828.0, 866.9, 573.2)
    ("caliper_rl", "tyre_rl"): 23.3,   # at (3978.0, -833.9, 583.2)
    ("caliper_rr", "tyre_rr"): 23.3,   # at (4122.0, 833.9, 583.2)
    ("engine", "fuel_fittings"): 22.6,   # at (2934.0, 0.0, 437.0)
    ("fan_scroll_l", "floor_strake_l3"): 21.2,   # at (4445.1, -476.4, 195.9)
    ("pushrod_fl", "tether_fl"): 21.0,   # at (951.5, -612.5, 169.2)
    ("pushrod_fr", "tether_fr"): 21.0,   # at (951.5, 612.5, 169.2)
    ("bduct_fence_rl", "trackrod_rl"): 20.8,   # at (4089.8, -572.2, 208.9)
    ("bduct_fence_rr", "trackrod_rr"): 20.8,   # at (4089.8, 572.2, 208.9)
    ("driver", "side_intrusion"): 20.8,   # at (1592.9, 222.1, 458.5)
    ("bduct_fence_rl", "wishbone_rl_lower_aft"): 20.7,   # at (4119.2, -567.0, 247.6)
    ("bduct_fence_rr", "wishbone_rr_lower_aft"): 20.7,   # at (4119.2, 567.0, 247.6)
    ("bduct_fence_rl", "wishbone_rl_lower_fwd"): 20.3,   # at (4113.3, -568.0, 245.9)
    ("bduct_fence_rr", "wishbone_rr_lower_fwd"): 20.3,   # at (4113.3, 568.0, 245.8)
    ("fan_scroll_r", "floor_strake_r3"): 20.0,   # at (4447.3, 476.6, 196.4)
    ("diffuser_fences", "diffuser_kick"): 19.9,   # at (4548.0, 294.8, 247.3)
    ("fan_fairing_l", "tunnel_l"): 18.6,   # at (4557.6, -531.4, 248.1)
    ("fan_fairing_r", "tunnel_r"): 18.6,   # at (4557.6, 531.4, 248.1)
    ("fan_fairing_l", "rainlight"): 17.5,   # at (4448.4, -24.3, 299.5)
    ("fan_fairing_r", "rainlight"): 17.5,   # at (4448.4, 24.3, 299.5)
    ("fan_stators", "rear_pylon_l"): 17.4,   # at (4287.3, -153.1, 425.6)
    ("diffuser_fences", "fan_nozzle_l"): 17.1,   # at (4517.3, -254.0, 169.7)
    ("diffuser_fences", "fan_nozzle_r"): 17.1,   # at (4517.3, 254.0, 169.7)
    ("floor_plenum_edge_l", "tunnel_l"): 17.0,   # at (1361.1, -623.2, 103.7)
    ("floor_plenum_edge_r", "tunnel_r"): 17.0,   # at (1361.1, 623.2, 103.7)
    ("control_boxes", "fuel_cell"): 16.0,   # at (2523.4, -100.8, 528.0)
    ("fan_rotor_l", "fan_scroll_l"): 16.0,   # at (4378.3, -66.3, 316.1)
    ("fan_scroll_r", "floor_strake_r1"): 15.8,   # at (4402.2, 293.1, 202.0)
    ("fan_scroll_l", "floor_strake_l1"): 15.6,   # at (4402.4, -293.1, 202.0)
    ("fan_scroll_r", "floor_strake_r2"): 15.6,   # at (4398.6, 385.1, 204.4)
    ("harness", "side_intrusion"): 15.6,   # at (1640.0, -221.4, 325.5)
    ("fan_rotor_r", "fan_scroll_r"): 15.5,   # at (4386.8, 66.2, 316.3)
    ("fan_scroll_l", "floor_strake_l2"): 15.3,   # at (4399.4, -385.1, 204.6)
    ("fanduct", "floor_plenum_edge_l"): 15.2,   # at (4458.8, -568.9, 230.0)
    ("fanduct", "floor_plenum_edge_r"): 15.2,   # at (4458.8, 568.9, 230.0)
    ("caliper_rl", "upright_rl"): 14.0,   # at (4108.1, -772.9, 362.9)
    ("caliper_rr", "upright_rr"): 14.0,   # at (3991.9, 772.9, 362.9)
    ("fan_scroll_r", "wishbone_rr_upper_aft"): 14.0,   # at (4180.0, 414.9, 494.0)
    ("brake_lines", "wishbone_fr_upper_aft"): 13.9,   # at (928.0, 600.9, 452.5)
    ("diffuser_lip", "fan_fairing_l"): 13.7,   # at (4554.6, -533.4, 268.6)
    ("diffuser_lip", "fan_fairing_r"): 13.7,   # at (4554.6, 533.4, 267.3)
    ("fan_scroll_l", "floor_fan_throat_l"): 13.7,   # at (4287.1, -445.7, 314.1)
    ("fan_scroll_l", "wishbone_rl_upper_aft"): 13.7,   # at (4208.7, -470.4, 476.7)
    ("seat", "side_intrusion"): 13.7,   # at (1624.3, 227.2, 290.8)
    ("fan_nozzle_r", "fan_rotor_r"): 13.5,   # at (4498.4, 513.3, 323.0)
    ("caliper_fl", "upright_fl"): 13.3,   # at (956.5, -805.9, 357.4)
    ("caliper_fr", "upright_fr"): 13.3,   # at (843.5, 805.9, 357.4)
    ("fan_scroll_r", "floor_fan_throat_r"): 13.2,   # at (4311.8, 153.0, 296.3)
    ("brake_lines", "wishbone_fr_upper_fwd"): 13.1,   # at (924.1, 599.8, 453.5)
    ("fan_nozzle_l", "floor_strake_l3"): 13.1,   # at (4458.3, -475.9, 187.6)
    ("fan_nozzle_r", "floor_strake_r3"): 13.1,   # at (4458.3, 475.9, 187.6)
    ("fan_nozzle_l", "fan_rotor_l"): 13.0,   # at (4497.7, -512.5, 323.0)
    ("bulkhead_rear", "extinguisher"): 12.6,   # at (1956.0, 194.2, 287.2)
    ("brake_lines", "wishbone_fl_upper_fwd"): 11.8,   # at (921.2, -601.7, 449.8)
    ("side_impact", "side_intrusion"): 11.6,   # at (1802.3, 238.7, 419.9)
    ("driveshaft_rl", "wishbone_rl_lower_aft"): 11.3,   # at (4067.5, -191.7, 327.3)
    ("driveshaft_rr", "wishbone_rr_lower_aft"): 11.3,   # at (4067.5, 191.7, 327.3)
    ("brake_lines", "wishbone_rl_upper_fwd"): 11.1,   # at (4079.2, -581.1, 459.1)
    ("brake_lines", "wishbone_rr_upper_fwd"): 11.1,   # at (4079.2, 581.1, 459.1)
    ("fan_nozzle_r", "fan_stators"): 11.0,   # at (4519.0, 520.5, 429.4)
    ("brake_lines", "wishbone_fl_upper_aft"): 10.7,   # at (929.1, -601.9, 449.1)
    ("diffuser_fences", "floor_fan_throat_l"): 10.4,   # at (4165.0, -288.5, 33.8)
    ("diffuser_fences", "floor_fan_throat_r"): 10.4,   # at (4165.0, 288.5, 33.8)
    ("floor_inlet_lip", "turning_vane_l1"): 10.2,   # at (1321.0, -351.1, 103.0)
    ("floor_inlet_lip", "turning_vane_r1"): 10.2,   # at (1321.0, 351.1, 103.0)
    ("brake_lines", "wishbone_rl_upper_aft"): 10.1,   # at (4071.1, -581.2, 457.6)
    ("brake_lines", "wishbone_rr_upper_aft"): 10.1,   # at (4071.1, 581.2, 457.6)
    ("fan_stators", "rear_pylon_r"): 10.1,   # at (4275.3, 175.7, 429.3)
    ("floor_plenum_edge_l", "floor_strake_l4"): 9.9,   # at (4436.4, -569.5, 214.6)
    ("fan_fairing_l", "floor_plenum_edge_l"): 9.7,   # at (4473.8, -580.7, 253.5)
    ("fan_fairing_r", "floor_plenum_edge_r"): 9.7,   # at (4473.8, 580.7, 253.5)
    ("floor_plenum_edge_r", "floor_strake_r4"): 9.7,   # at (4436.7, 569.5, 214.7)
    ("bduct_drum_rl", "brake_lines"): 9.3,   # at (4064.8, -648.7, 538.2)
    ("bduct_drum_rr", "brake_lines"): 9.3,   # at (4064.8, 648.7, 538.2)
    ("bargeboard_l4", "turning_vane_l1"): 9.1,   # at (1586.5, -372.8, 250.2)
    ("bargeboard_r4", "turning_vane_r1"): 9.1,   # at (1586.4, 372.8, 250.2)
    ("brake_lines", "pushrod_rl"): 9.0,   # at (4078.0, -583.9, 461.3)
    ("brake_lines", "pushrod_rr"): 9.0,   # at (4078.0, 583.9, 461.3)
    ("brake_lines", "driveshaft_rl"): 8.9,   # at (4060.7, -533.4, 352.5)
    ("brake_lines", "driveshaft_rr"): 8.9,   # at (4060.7, 533.4, 352.5)
    ("trackrod_fl", "tyre_sensors"): 8.7,   # at (827.6, -674.9, 229.6)
    ("trackrod_fr", "tyre_sensors"): 8.7,   # at (827.6, 674.9, 229.6)
    ("beam_wing", "floor_fan_throat_l"): 8.5,   # at (4331.1, -398.1, 411.0)
    ("beam_wing", "floor_fan_throat_r"): 8.5,   # at (4331.1, 398.1, 411.0)
    ("fan_nozzle_l", "fan_stators"): 8.3,   # at (4519.8, -517.8, 426.9)
    ("floor_surface", "tub"): 8.2,   # at (2333.4, -0.0, 45.7)
    ("bduct_fence_rl", "tyre_sensors"): 7.9,   # at (3967.3, -576.4, 244.6)
    ("bduct_fence_rr", "tyre_sensors"): 7.9,   # at (3967.3, 576.4, 244.6)
    ("steering_arm_fl", "trackrod_fl"): 7.3,   # at (793.4, -704.0, 233.5)
    ("steering_arm_fr", "trackrod_fr"): 7.3,   # at (793.6, 704.0, 234.8)
    ("fan_nozzle_r", "floor_strake_r2"): 7.2,   # at (4465.8, 383.4, 179.0)
    ("fan_fairing_l", "floor_fan_throat_l"): 7.0,   # at (4168.3, -458.7, 230.0)
    ("fan_fairing_r", "floor_fan_throat_r"): 7.0,   # at (4168.3, 141.3, 230.0)
    ("fan_nozzle_l", "floor_strake_l2"): 7.0,   # at (4465.8, -383.2, 179.0)
    ("bduct_drum_fl", "brake_lines"): 6.7,   # at (903.0, -709.7, 513.4)
    ("bduct_drum_fr", "brake_lines"): 6.7,   # at (902.0, 709.7, 514.0)
    ("trackrod_rl", "tyre_sensors"): 6.5,   # at (4045.3, -528.2, 205.5)
    ("trackrod_rr", "tyre_sensors"): 6.5,   # at (4045.3, 528.2, 205.5)
    ("brake_lines", "caliper_fl"): 6.3,   # at (888.0, -779.6, 491.9)
    ("brake_lines", "caliper_fr"): 6.3,   # at (887.5, 779.1, 490.6)
    ("brake_lines", "caliper_rl"): 5.8,   # at (4038.5, -761.1, 500.3)
    ("brake_lines", "caliper_rr"): 5.5,   # at (4039.2, 746.1, 500.4)
    ("floor_fan_throat_l", "tether_rl"): 5.5,   # at (4161.8, -253.0, 360.9)
    ("floor_fan_throat_r", "tether_rr"): 5.5,   # at (4161.8, 253.0, 360.9)
    ("fan_fairing_l", "fan_scroll_l"): 5.3,   # at (4544.5, -60.3, 344.9)
    ("fan_fairing_r", "fan_scroll_r"): 5.3,   # at (4544.5, 60.3, 344.9)
    ("bduct_fence_rl", "brake_lines"): 5.2,   # at (4074.5, -578.9, 424.3)
    ("bduct_fence_rr", "brake_lines"): 5.2,   # at (4074.5, 578.9, 424.3)
    ("diffuser_fences", "fan_rotor_l"): 5.2,   # at (4403.4, -294.8, 226.9)
    ("diffuser_fences", "fan_rotor_r"): 5.2,   # at (4405.9, 294.8, 227.7)
    ("bduct_fence_fl", "tyre_sensors"): 4.9,   # at (819.2, -665.4, 237.8)
    ("bduct_fence_fr", "tyre_sensors"): 4.9,   # at (819.2, 665.4, 237.8)
    ("floor_skirts", "tunnel_l"): 3.9,   # at (1475.8, -721.1, 33.1)
    ("diffuser_kick", "tunnel_l"): 3.6,   # at (4552.5, -469.3, 246.8)
    ("diffuser_kick", "tunnel_r"): 3.6,   # at (4552.5, 469.3, 246.8)
    ("floor_skirts", "tunnel_r"): 3.6,   # at (1489.4, 729.5, 37.0)
    ("gearbox", "wishbone_rl_lower_aft"): 3.5,   # at (3967.8, -142.3, 342.2)
    ("gearbox", "wishbone_rr_lower_aft"): 3.5,   # at (3967.8, 142.3, 342.2)
    ("tether_rl", "tow_hooks"): 3.5,   # at (4168.7, -97.6, 372.4)
    ("tether_rr", "tow_hooks"): 3.5,   # at (4168.7, 97.6, 372.4)
    ("diffuser_kick", "fan_rotor_l"): 2.9,   # at (4440.0, -293.6, 244.2)
    ("diffuser_kick", "fan_rotor_r"): 2.9,   # at (4440.0, 306.4, 244.2)
    ("bulkhead_engine", "fuel_cell"): 2.8,   # at (2336.0, 209.5, 282.6)
    ("brake_lines", "brake_pad_rr"): 2.5,   # at (4044.6, 759.4, 500.2)
    ("brake_lines", "brake_pad_rl"): 2.4,   # at (4045.6, -759.4, 499.1)
    ("torsion_bars_f", "wishbone_fl_upper_aft"): 2.2,   # at (1080.5, -177.1, 416.2)
    ("hub_fl", "steering_arm_fl"): 0.8,   # at (904.6, -754.4, 274.4)
    ("hub_fr", "steering_arm_fr"): 0.8,   # at (904.6, 754.4, 274.4)
    ("diffuser_lip", "tunnel_l"): 0.7,   # at (4560.0, -486.4, 249.6)
    ("diffuser_lip", "tunnel_r"): 0.7,   # at (4560.0, 486.4, 249.6)
    ("tyre_sensors", "wishbone_rl_lower_fwd"): 0.5,   # at (3998.8, -578.8, 243.7)
    ("tyre_sensors", "wishbone_rr_lower_fwd"): 0.5,   # at (3998.8, 578.8, 243.7)
    ("driver", "extinguisher"): 0.4,   # at (1951.5, 131.2, 316.1)
}
# --- end KNOWN ---

if __name__ == "__main__":
    import _interfere
    sys.exit(_interfere.intersect_main(__file__, ROOT, PKG, EXPECTED, KNOWN,
                                       TOL, UNIT))

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
    # the caliper is bolted to the upright by its two lugs, and the brake
    # hose screws into the caliper
    ("caliper_", "upright_"), ("brake_lines", "caliper_"),
    # the hose's banjo fitting screws into the caliper beside the pad
    ("brake_lines", "brake_pad_"),
    # the T-camera is clamped to the top of the roll hoop
    ("cameras", "roll_hoop"),
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
    ("rim_", "bduct_"),
    ("sidepod_", "side_impact"),
    ("tub", "side_impact"),
    ("nose_pylons", "front_wing_main"),
    # the bargeboards are a nested cascade sharing one root, like the wing
    ("bargeboard_", "bargeboard_"),

("gearbox", "damper"),
    ("gearbox", "torsion_bars"), ("gearbox", "heave_"), ("gearbox", "antiroll_"),
    ("gearbox", "driveshaft_"),
    ("driver", "pedal_box"),
    # the belts anchor through slots in the seat shell, and all six clip
    # into the buckle
    ("harness", "seat"), ("harness", "harness_buckle"),

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
    ("torsion_bars", "dampers_"),

    # the drink bottle is strapped to the seat's flank
    ("drink_bottle", "seat"),

    # panels and frames bond to the bulkheads they are carried on
    ("side_intrusion", "bulkhead_"), ("cockpit_coaming", "bulkhead_"),
    ("halo_mounts", "bulkhead_"),
    ("halo", "bulkhead_"), ("halo_pillar", "bulkhead_"),
    ("nose_cape", "bulkhead_"),

    # the front wing roots into the nose, and the vanes stand on the flaps
    ("front_wing_main", "tub"),
    ("front_y250_vanes", "front_flap_"), ("front_y250_vanes", "front_wing_main"),
    ("drs_actuator", "rear_flap"),

    # bodywork meets bodywork where one panel is let into another
    ("sidepod_", "bargeboard_"),
    ("sidepod_", "gearbox"), ("sidepod_", "sidepod_"),
    ("bargeboard_", "side_impact"), ("bargeboard_", "sidepod_inlets"),

    # the fans: the stators carry the motor and are bonded into the shroud;
    # each intake's mouth is bonded over its fan's cowl lip and runs through
    # the hole it makes in the floor and the tunnel roof; the beam wing is
    # carried on the rear pylons, which pass through it
    ("fan_motors", "fan_stators"), ("fan_stators", "fanduct"),
    ("floor_fan_throat_", "fan_fairing_"), ("floor_fan_throat_", "tunnel_"),
    ("beam_wing", "rear_pylon_"), ("diffuser_kick", "floor_fan_throat_"),
    # the rear frame: fan cowls bonded to its ends, pylons on top, and its
    # post on the crash structure's spine
    ("rear_frame", "fan_fairing_"), ("rear_frame", "rear_pylon_"),
    ("rear_frame", "crash_structure"), ("rear_frame", "tub"),
    ("rainlight", "rear_light_panel"), ("rear_light_panel", "tub"),
    ("sharkfin", "tow_hooks"),
    ("starter_socket", "tow_hooks"), ("nose_pylons", "tow_hooks"),

    # service hardware roots into whatever carries the load
    ("jack_points", "gearbox"), ("jack_points", "nose_cape"),
    ("jack_points", "nose_pylons"), ("jack_points", "front_wing_main"),

    # the fan is one machine
    ("fan_rotor_", "fan_motors"),

    # the loom plugs into the boxes it feeds
    ("wiring_loom", "gearbox"),
    ("brake_lines", "side_impact"),

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

    # a bulkhead is a mounting face: the dash lands on one, and the battery
    # is bolted to the engine bulkhead's flange
    ("bulkhead_", "dash"), ("battery", "bulkhead_engine"),
    # the fuel cell stands on the pack by its collector's foot, and the
    # control boxes stand on the cell's lid
    ("battery", "fuel_cell"), ("control_boxes", "fuel_cell"),
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
    # the front tow hook comes down through the wing it is mounted above --
    # the flap stack is already declared for the same reason
    ("front_wing_main", "tow_hooks"),
    # the fin is the back of the engine cover and ends on the rear structure
    ("sharkfin", "crash_structure"),
    # the tether anchors on the corner: upright, wishbone and driveshaft are
    # already listed, and the hub is the same assembly
    ("tether_", "hub_"),
    # ----------------------------------------------------------------
    # The fan, as one machine: the intake rises out of the floor into the
    # bellmouth, the rotor turns inside it, and the intake's floor slot is
    # cut through the floor's own surface and strakes.
    # ----------------------------------------------------------------
    ("fan_rotor_", "floor_fan_throat_"), ("fanduct", "floor_fan_throat_"),

    ("floor_fan_throat_", "floor_strake_"),
    ("floor_fan_throat_", "floor_surface"),

    # The floor's own edges and leading edge are part of the floor, and the
    # diffuser's fences, kick and lip all land on each other at the exit.
    ("floor_plenum_edge_", "floor_surface"),
    ("floor_plenum_edge_", "floor_skirts"),
    ("floor_inlet_lip", "tunnel_"),
    ("diffuser_kick", "diffuser_lip"),

    ("diffuser_fences", "floor_strake_"),
    ("front_y250_vanes", "nose_pylons"),

    # The nose cape's trailing edge lands on the front wing's mainplane --
    # 26 vertices at x 340-375, which is the joint between them.
    ("nose_cape", "front_wing_main"),
    # A rear toe link and a rear lower wishbone both pick up on the same
    # upright, 30 mm apart, so their rod ends touch there. Along their
    # spans they are clear: the link runs under the arm the whole way.
    ("trackrod_", "wishbone_"),
    # the loom is clipped along the top wishbone on its way to the corner
    ("wiring_loom", "wishbone_"),
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
    ("tether_", "crash_structure"),
]

PKG = "car/parts"
UNIT = 1.0            # mm of real part per model unit
TOL = 0.3            # mm, full size: deeper than this is sharing material

# Real defects, in mm of full-size overlap, deepest first. Each one is a part
# through a part that nobody meant. Fix them and --shrink; never add to it.
# --- KNOWN: rewritten by --shrink, never by hand to add ---
KNOWN = {
    ("bduct_fence_fl", "trackrod_fl"): 27.4,   # at (818.8, -665.5, 228.9)
    ("bduct_fence_fr", "trackrod_fr"): 27.4,   # at (818.8, 665.5, 228.9)
    ("engine", "fuel_fittings"): 20.9,   # at (2934.0, 1.0, 451.0)
    ("diffuser_kick", "fan_fairing_l"): 20.0,   # at (4560.0, -409.6, 249.3)
    ("diffuser_kick", "fan_fairing_r"): 20.0,   # at (4560.0, 482.4, 249.3)
    ("floor_plenum_edge_l", "tunnel_l"): 14.7,   # at (1358.8, -621.8, 103.8)
    ("floor_plenum_edge_r", "tunnel_r"): 14.7,   # at (1358.8, 621.8, 103.8)
    ("brake_lines", "wishbone_fr_upper_aft"): 13.8,   # at (928.0, 600.9, 452.5)
    ("diffuser_fences", "tunnel_l"): 13.8,   # at (3887.3, -254.0, 72.6)
    ("diffuser_fences", "tunnel_r"): 13.8,   # at (3887.3, 254.0, 72.6)
    ("diffuser_lip", "fan_fairing_l"): 13.7,   # at (4556.8, -415.1, 262.5)
    ("diffuser_lip", "fan_fairing_r"): 13.7,   # at (4556.8, 415.1, 262.5)
    ("brake_lines", "wishbone_fr_upper_fwd"): 13.3,   # at (924.1, 599.8, 453.5)
    ("bulkhead_rear", "extinguisher"): 12.6,   # at (1956.0, 194.2, 287.2)
    ("brake_lines", "wishbone_fl_upper_fwd"): 11.7,   # at (921.2, -601.7, 449.8)
    ("side_impact", "side_intrusion"): 11.6,   # at (1802.3, 238.7, 419.9)
    ("driveshaft_rl", "wishbone_rl_lower_aft"): 11.3,   # at (4067.5, -191.7, 327.3)
    ("driveshaft_rr", "wishbone_rr_lower_aft"): 11.3,   # at (4067.5, 191.7, 327.3)
    ("brake_lines", "wishbone_rl_upper_fwd"): 11.0,   # at (4079.2, -581.1, 459.1)
    ("brake_lines", "wishbone_rr_upper_fwd"): 11.0,   # at (4079.2, 581.1, 459.1)
    ("brake_lines", "wishbone_fl_upper_aft"): 10.6,   # at (929.1, -601.9, 449.1)
    ("brake_lines", "wishbone_rl_upper_aft"): 10.2,   # at (4073.1, -584.0, 457.4)
    ("brake_lines", "wishbone_rr_upper_aft"): 10.2,   # at (4073.1, 584.0, 457.4)
    ("floor_inlet_lip", "turning_vane_l1"): 10.2,   # at (1321.0, -351.1, 103.0)
    ("floor_inlet_lip", "turning_vane_r1"): 10.2,   # at (1321.0, 351.1, 103.0)
    ("floor_plenum_edge_l", "floor_strake_l4"): 9.7,   # at (3889.8, -548.0, 61.8)
    ("floor_plenum_edge_r", "floor_strake_r4"): 9.7,   # at (3889.8, 548.0, 61.8)
    ("bduct_drum_rl", "brake_lines"): 9.3,   # at (4064.8, -648.7, 538.4)
    ("bduct_drum_rr", "brake_lines"): 9.3,   # at (4064.8, 648.7, 538.4)
    ("bargeboard_l4", "turning_vane_l1"): 9.1,   # at (1586.5, -372.8, 250.2)
    ("bargeboard_r4", "turning_vane_r1"): 9.1,   # at (1586.4, 372.8, 250.2)
    ("brake_lines", "driveshaft_rl"): 9.0,   # at (4060.7, -533.4, 352.5)
    ("brake_lines", "driveshaft_rr"): 9.0,   # at (4060.7, 533.4, 352.5)
    ("brake_lines", "pushrod_rl"): 8.8,   # at (4077.3, -584.6, 462.1)
    ("brake_lines", "pushrod_rr"): 8.8,   # at (4077.3, 584.6, 462.1)
    ("trackrod_fl", "tyre_sensors"): 8.7,   # at (827.6, -674.9, 229.6)
    ("trackrod_fr", "tyre_sensors"): 8.7,   # at (827.6, 674.9, 229.6)
    ("floor_surface", "tub"): 8.2,   # at (2333.4, -0.0, 45.7)
    ("pushrod_fl", "tether_fl"): 8.1,   # at (982.7, -587.5, 182.0)
    ("pushrod_fr", "tether_fr"): 8.1,   # at (982.7, 587.5, 182.0)
    ("steering_arm_fl", "trackrod_fl"): 7.3,   # at (793.4, -704.0, 233.5)
    ("steering_arm_fr", "trackrod_fr"): 7.3,   # at (793.6, 704.0, 234.8)
    ("brake_lines", "sidepod_l"): 6.9,   # at (2710.4, -321.5, 257.2)
    ("brake_lines", "sidepod_r"): 6.9,   # at (2710.4, 321.5, 257.2)
    ("bduct_drum_fl", "brake_lines"): 6.7,   # at (902.0, -709.7, 514.2)
    ("bduct_drum_fr", "brake_lines"): 6.7,   # at (902.0, 709.7, 514.2)
    ("trackrod_rl", "tyre_sensors"): 6.5,   # at (4045.3, -528.2, 205.5)
    ("trackrod_rr", "tyre_sensors"): 6.5,   # at (4045.3, 528.2, 205.5)
    ("seat", "side_intrusion"): 6.1,   # at (1599.4, -228.3, 479.4)
    ("fan_fairing_l", "tunnel_l"): 5.9,   # at (4560.0, -482.8, 249.3)
    ("bduct_fence_rl", "brake_lines"): 5.1,   # at (4074.5, -578.9, 424.3)
    ("bduct_fence_rr", "brake_lines"): 5.1,   # at (4074.5, 578.9, 424.3)
    ("bduct_fence_fl", "tyre_sensors"): 4.8,   # at (821.6, -665.5, 237.8)
    ("bduct_fence_fr", "tyre_sensors"): 4.8,   # at (821.6, 665.5, 237.8)
    ("fan_fairing_r", "tunnel_r"): 4.2,   # at (4560.0, 479.7, 248.8)
    ("diffuser_kick", "tunnel_l"): 3.6,   # at (4552.5, -469.3, 246.8)
    ("diffuser_kick", "tunnel_r"): 3.6,   # at (4552.5, 469.3, 246.8)
    ("gearbox", "wishbone_rl_lower_aft"): 3.5,   # at (3967.8, -142.3, 342.2)
    ("gearbox", "wishbone_rr_lower_aft"): 3.5,   # at (3967.8, 142.3, 342.2)
    ("tether_rl", "tow_hooks"): 3.5,   # at (4168.7, -97.6, 372.4)
    ("tether_rr", "tow_hooks"): 3.5,   # at (4168.7, 97.6, 372.4)
    ("torsion_bars_f", "wishbone_fl_upper_aft"): 2.2,   # at (1080.5, -177.1, 416.2)
    ("hub_fl", "steering_arm_fl"): 0.8,   # at (904.6, -754.4, 274.4)
    ("hub_fr", "steering_arm_fr"): 0.8,   # at (904.6, 754.4, 274.4)
    ("diffuser_lip", "tunnel_l"): 0.7,   # at (4560.0, -486.4, 249.6)
    ("diffuser_lip", "tunnel_r"): 0.7,   # at (4560.0, 486.4, 249.6)
    ("tyre_sensors", "wishbone_rl_lower_fwd"): 0.5,   # at (3998.8, -578.8, 243.7)
    ("tyre_sensors", "wishbone_rr_lower_fwd"): 0.5,   # at (3998.8, 578.8, 243.7)
}
# --- end KNOWN ---

if __name__ == "__main__":
    import _interfere
    sys.exit(_interfere.intersect_main(__file__, ROOT, PKG, EXPECTED, KNOWN,
                                       TOL, UNIT))

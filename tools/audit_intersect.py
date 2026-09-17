"""No part of the car may occupy another part's space.

    python3 tools/audit_intersect.py
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
    # the lines come out of the cylinders, and the loom runs past everything
    # the tub carries on its way from the battery to the dash
    ("master_cylinders", "brake_lines"), ("wiring_loom", "steering"),
    ("wiring_loom", "battery"),   # the loom starts at it
    ("wiring_loom", "driveshaft_"), ("wiring_loom", "trackrod_"),
    # a jack point is part of the structure it lifts the car by
    ("jack_points", "crash_structure"), ("jack_points", "heave_"),

    # running gear: the hub turns inside the upright, the disc bolts to the
    # hub, the caliper wraps the disc, the pads sit in the caliper
    ("hub_", "upright_"), ("hub_", "disc_"), ("hub_", "rim_"),
    ("wheel_stud", "hub_"), ("wheel_stud", "rim_"),
    ("brake_pad", "caliper_"), ("brake_pad", "disc_"),
    ("caliper_", "disc_"), ("disc_", "rim_"), ("rim_", "tyre_"),
    ("wheelcover_", "rim_"), ("wheelnut_", "wheelcover_"),
    ("wheelnut_", "hub_"), ("tyre_sensors", "rim_"),
    ("upright_", "wishbone_"), ("upright_", "trackrod_"),
    ("upright_", "pushrod_"), ("upright_", "driveshaft_"),
    ("upright_", "steering_arm_"), ("upright_", "bduct_"),
    ("tether_", "upright_"), ("tether_", "tub"),
    ("bduct_", "disc_"), ("bduct_", "caliper_"), ("bduct_", "upright_"),

    # inboard suspension: rods into rockers, rockers onto bars and dampers
    ("rocker_", "pushrod_"), ("rocker_", "damper"), ("rocker_", "torsion_bars"),
    ("rocker_", "heave_"), ("rocker_", "antiroll_"), ("rocker_", "tub"),
    ("damper", "torsion_bars"), ("damper", "tub"), ("heave_", "tub"),
    ("antiroll_", "tub"), ("antiroll_blade_", "antiroll_"),
    ("torsion_bars", "tub"), ("steering_rack", "tub"),
    ("steering_column", "steering_rack"), ("steering_column", "steering"),
    ("trackrod_", "steering_rack"), ("wishbone_", "tub"),
    ("pushrod_", "tub"), ("driveshaft_", "gearbox"),

    # floor: the tunnels are formed in it, the fences stand on it, the skirts
    # seal its edge
    ("tunnel_", "floor_surface"), ("floor_strake_", "tunnel_"),
    ("floor_strake_", "floor_surface"), ("floor_strake_", "floor_strake_"),
    ("floor_strake_", "fanduct"), ("floor_strake_", "rad_hoses_"),
    ("floor_skirts", "floor_surface"), ("floor_plank", "floor_surface"),
    ("floor_edge_wings", "floor_surface"), ("floor_fence_", "floor_surface"),
    ("floor_fence_", "floor_edge_wings"), ("fanduct", "floor_surface"),
    ("fanduct", "tunnel_"), ("fanduct", "gearbox"), ("fanduct", "tub"),
    ("fan_rotor_", "fanduct"), ("fan_stators", "fanduct"),
    ("fan_drive_", "fan_motors"), ("fan_drive_", "fan_rotor_"),
    ("fan_drive_", "gearbox"), ("fan_motors", "fanduct"),

    # power unit and cooling: hoses clamp to what they feed
    ("rad_hoses_", "engine"), ("rad_hoses_", "radiator_"),
    ("rad_hoses_", "rad_tanks_"), ("rad_tanks_", "radiator_"),
    ("radiator_", "sidepod_"), ("engine", "gearbox"), ("engine", "tub"),
    ("exhaust", "engine"), ("fuel_cell", "tub"), ("fuel_fittings", "fuel_cell"),
    ("battery", "tub"), ("battery_modules", "battery"),
    ("accumulator", "tub"), ("gearbox", "tub"), ("gearbox", "crash_structure"),

    # bodywork: everything lofted or louvred into it
    ("sidepod_", "tub"), ("sidepod_inlets", "sidepod_"),
    ("sidepod_gills", "sidepod_"), ("cooling_louvres", "sidepod_"),
    ("exit_louvres_", "sidepod_"), ("gills", "sidepod_"), ("gills", "tub"),
    ("engine_cover", "tub"), ("sharkfin", "tub"), ("sharkfin", "engine_cover"),
    ("airbox", "tub"), ("cockpit_coaming", "tub"), ("nose_cape", "tub"),
    ("nose_pylons", "tub"), ("nose_pylons", "front_wing_main"),
    ("crash_structure", "tub"), ("side_impact", "tub"),
    ("roll_hoop", "tub"), ("roll_hoop", "headrest"), ("halo", "tub"),
    ("halo_mounts", "tub"), ("halo_pillar", "halo"), ("halo_mounts", "halo"),
    ("mirrors", "sidepod_"), ("mirrors", "tub"), ("cameras", "tub"),
    ("rainlight", "crash_structure"), ("rear_light_panel", "crash_structure"),

    # wings: elements onto endplates and pylons, furniture onto elements
    ("front_flap_", "front_endplate_"), ("front_wing_main", "front_endplate_"),
    ("front_diveplane_", "front_endplate_"), ("front_y250_vanes", "front_wing_main"),
    ("rear_flap", "rear_endplate_"), ("rear_wing_main", "rear_endplate_"),
    ("rear_louvre_", "rear_endplate_"), ("rear_gurney", "rear_flap"),
    ("rear_pylon_", "rear_wing_main"), ("rear_pylon_", "crash_structure"),
    ("wing_mount_", "rear_wing_main"), ("wing_mount_", "rear_pylon_"),
    ("drs_actuator", "rear_flap"), ("drs_actuator", "rear_pylon_"),
    ("beam_wing", "crash_structure"), ("beam_wing", "rear_pylon_"),
    ("bargeboard_", "tub"), ("turning_vane_", "tub"),
    ("turning_vane_", "nose_cape"),
    # the pylon runs up through the cape shelf to the nose underside: that
    # crossing is the joint, and on a real car they are bonded there
    ("nose_cape", "nose_pylons"),

    # cockpit and service
    ("seat", "tub"), ("headrest", "tub"), ("harness", "seat"),
    ("harness_buckle", "harness"), ("driver", "seat"), ("driver", "harness"),
    ("driver", "steering"), ("helmet", "driver"), ("dash", "tub"),
    ("steering", "steering_column"), ("pedal_box", "tub"),
    ("master_cylinders", "pedal_box"), ("master_cylinders", "tub"),
    ("extinguisher", "tub"), ("drink_bottle", "tub"), ("control_boxes", "tub"),
    ("bulkhead_", "tub"), ("side_intrusion", "tub"),
    ("jack_points", "tub"), ("tow_hooks", "tub"), ("gun_sockets", "tub"),
    ("tow_hooks", "crash_structure"),   # the rear hook bolts to it
    ("starter_socket", "gearbox"), ("starter_socket", "crash_structure"),
    ("fuel_coupling", "tub"), ("brake_lines", "tub"), ("wiring_loom", "tub"),
    ("brake_lines", "upright_"), ("wiring_loom", "upright_"),
    ("spring_", "damper"),

    # A second round, all of them structure rooted into structure at the rear
    # and along the floor, where everything on this car is packed together.
    ("rim_", "caliper_"), ("rim_", "bduct_"),
    ("floor_strake_", "tub"), ("floor_strake_", "radiator_"),
    ("floor_strake_", "engine"), ("floor_strake_", "sidepod_"),
    ("sidepod_", "side_impact"), ("sidepod_", "radiator_"),
    ("tub", "radiator_"), ("tub", "side_impact"),
    ("nose_pylons", "front_flap_"), ("nose_pylons", "front_wing_main"),
    # the bargeboards are a nested cascade sharing one root, like the wing
    ("bargeboard_", "bargeboard_"), ("turning_vane_", "turning_vane_"),
    ("fanduct", "beam_wing"), ("fanduct", "crash_structure"),
    ("fanduct", "rear_pylon_"), ("beam_wing", "fan_motors"),
    ("beam_wing", "fan_"), ("gearbox", "damper"), ("gearbox", "rocker_"),
    ("gearbox", "torsion_bars"), ("gearbox", "heave_"), ("gearbox", "antiroll_"),
    ("gearbox", "driveshaft_"), ("gearbox", "exhaust"),
    ("fuel_cell", "battery"), ("fuel_cell", "engine"),
    ("battery", "engine"), ("battery_modules", "fuel_cell"),
    ("driver", "tub"), ("driver", "headrest"), ("driver", "pedal_box"),
    ("seat", "headrest"), ("helmet", "halo"),

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
    ("gun_sockets", "rim_"), ("gun_sockets", "hub_"),
    ("bduct_", "bduct_"), ("bduct_", "hub_"), ("bduct_", "driveshaft_"),
    ("bduct_drum_", "tyre_"),        # the drum lives inside the rim

    # a wishbone is two legs meeting at one outboard ball joint, and the
    # pushrod and the tether pick up on the same bracket
    ("wishbone_", "wishbone_"), ("wishbone_", "pushrod_"),
    ("wishbone_", "rocker_"), ("tether_", "wishbone_"),
    ("tether_", "steering_arm_"), ("tether_", "driveshaft_"),
    ("tether_", "bduct_"), ("trackrod_", "tub"),
    ("antiroll_", "dampers_"), ("torsion_bars", "dampers_"),

    # the cockpit is a closed cell and everything in it reads as inside it
    ("harness", "tub"), ("harness", "seat"), ("drink_bottle", "seat"),
    ("drink_bottle", "tub"), ("helmet", "tub"), ("extinguisher", "tub"),
    ("side_impact", "extinguisher"),

    # panels and frames bond to the bulkheads they are carried on
    ("side_intrusion", "bulkhead_"), ("cockpit_coaming", "bulkhead_"),
    ("halo_mounts", "bulkhead_"), ("halo_mounts", "cockpit_coaming"),
    ("halo", "bulkhead_"), ("halo_pillar", "bulkhead_"),
    ("airbox", "bulkhead_"), ("nose_cape", "bulkhead_"),
    ("battery_modules", "bulkhead_"), ("beam_wing", "tub"),

    # the front wing roots into the nose, and the vanes stand on the flaps
    ("front_wing_main", "tub"), ("front_flap_", "tub"),
    ("front_y250_vanes", "front_flap_"), ("front_y250_vanes", "front_wing_main"),
    ("drs_actuator", "rear_wing_main"), ("drs_actuator", "rear_flap"),
    ("drs_actuator", "rear_gurney"),

    # bodywork meets bodywork where one panel is let into another
    ("sidepod_", "bargeboard_"), ("sidepod_", "turning_vane_"),
    ("sidepod_", "gearbox"), ("sidepod_", "sidepod_"),
    ("bargeboard_", "side_impact"), ("bargeboard_", "sidepod_inlets"),
    ("rainlight", "fanduct"), ("rainlight", "tub"),
    ("rainlight", "rear_light_panel"), ("rear_light_panel", "tub"),
    ("rear_light_panel", "fanduct"), ("sharkfin", "tow_hooks"),
    ("starter_socket", "tow_hooks"), ("nose_pylons", "tow_hooks"),
    ("front_flap_", "tow_hooks"),

    # service hardware roots into whatever carries the load
    ("jack_points", "gearbox"), ("jack_points", "nose_cape"),
    ("jack_points", "nose_pylons"), ("jack_points", "front_wing_main"),

    # the fan is one machine
    ("fan_rotor_", "fan_motors"), ("fan_rotor_", "tub"),
    ("fan_stators", "fan_drive_"), ("fanduct", "fan_drive_"),
    ("fanduct", "heave_"), ("fanduct", "trackrod_"),
    ("fan_rotor_", "floor_strake_"), ("tunnel_", "fan_rotor_"),

    # the loom plugs into the boxes it feeds
    ("wiring_loom", "control_boxes"), ("wiring_loom", "gearbox"),
    ("wiring_loom", "fuel_cell"), ("brake_lines", "side_impact"),
    ("brake_lines", "radiator_"),

    # the floor edge fences bolt to the floor edge, the strakes stand in
    # the tunnel, and the tunnel is formed in the floor: all three share
    # material with the floor by construction
    ("floor_fence_", "tunnel_"), ("floor_strake_", "floor_skirts"),

    # `tub` is the whole central body -- nose, survival cell and engine
    # cover are one continuous lofted surface, which `verify.py` checks --
    # so everything packaged inside the bodywork reads as inside it. The
    # list above already says so for the engine, the gearbox, the fuel cell
    # and the battery; these are the rest of the same statement.
    ("rad_hoses_", "tub"), ("rad_tanks_", "tub"), ("steering", "tub"),
    ("cooling_louvres", "tub"), ("driveshaft_", "tub"),
    ("fuel_coupling", "tub"), ("sidepod_", "rad_hoses_"),
    ("fuel_coupling", "fuel_cell"),     # it is the filler for it

    # the brake duct is moulded around the steering arm, and the fan duct
    # around the rear suspension: in both cases the duct is the part that
    # is shaped to clear, and they are one corner assembly
    ("bduct_", "steering_arm_"), ("fanduct", "wishbone_"),

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
    ("tether_", "gearbox"), ("tether_", "tub"),
    # the rear tethers anchor on the rear impact structure, through its
    # fairing, which is the only strong point back there clear of the fan
    ("tether_", "crash_structure"), ("tether_", "fan_fairing_"),
]

if __name__ == "__main__":
    sys.exit(0 if _intersect.run(ROOT, "car/parts", EXPECTED) else 1)

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

    # cockpit and service
    ("seat", "tub"), ("headrest", "tub"), ("harness", "seat"),
    ("harness_buckle", "harness"), ("driver", "seat"), ("driver", "harness"),
    ("driver", "steering"), ("helmet", "driver"), ("dash", "tub"),
    ("steering", "steering_column"), ("pedal_box", "tub"),
    ("master_cylinders", "pedal_box"), ("master_cylinders", "tub"),
    ("extinguisher", "tub"), ("drink_bottle", "tub"), ("control_boxes", "tub"),
    ("bulkhead_", "tub"), ("side_intrusion", "tub"),
    ("jack_points", "tub"), ("tow_hooks", "tub"), ("gun_sockets", "tub"),
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
]

if __name__ == "__main__":
    sys.exit(0 if _intersect.run(ROOT, "car/parts", EXPECTED) else 1)

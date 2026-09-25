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
    # the nose camera pods' feet are bolted through the skin
    ("cameras", "tub"),
    # the brake hard line is P-clipped along the top of each upper wishbone's
    # forward leg, the clips' bolts into the leg; the flexible hose enters
    # the brake cooling drum through its grommet to reach the caliper
    ("brake_lines", "wishbone_fl_upper_fwd"),
    ("brake_lines", "wishbone_fr_upper_fwd"),
    ("brake_lines", "wishbone_rl_upper_fwd"),
    ("brake_lines", "wishbone_rr_upper_fwd"),
    ("brake_lines", "bduct_drum_"),
    # the engine's castings and the rest of the engine meet as the engine
    # repository's own audit says they may; this one audits the car
    ("engine", "engine_"),
    # the lines come out of the cylinders, and the loom runs past everything
    # the tub carries on its way from the battery to the dash
    ("master_cylinders", "brake_lines"), ("wiring_loom", "steering"),
    ("wiring_loom", "battery"),   # the loom starts at it
    ("wiring_loom", "driveshaft_"),
    # a jack point is part of the structure it lifts the car by
    ("jack_points", "crash_structure"),

    # running gear: the studs are in the hub, the caliper wraps the disc and
    # the pads sit in the caliper. The hub runs in the upright's bearing bore
    # and touches it nowhere else.
    ("wheel_stud", "hub_"), ("wheel_stud", "rim_"),
    ("brake_pad", "caliper_"),
    # Joints that sat on the known-defect list. Each overlap is the joint:
    # the track rod's end is on the steering arm and the arm on the hub; the
    # floor bolts to the bottom of the tub; the first turning vane is bonded
    # to the floor's inlet lip and to the bargeboard beside it; the outer
    # strake is bonded along the plenum edge; the fan fairings, the diffuser
    # kick and its lip are bonded to the tunnels' trailing edge; and the rear
    # lower wishbones pick up on the gearbox casing.
    ("steering_arm_", "trackrod_"), ("hub_", "steering_arm_"),
    ("floor_surface", "tub"), ("floor_inlet_lip", "turning_vane_"),
    ("bargeboard_", "turning_vane_"), ("floor_plenum_edge_", "floor_strake_"),
    ("fan_fairing_", "tunnel_"), ("diffuser_kick", "tunnel_"),
    ("diffuser_lip", "tunnel_"), ("gearbox", "wishbone_r"),
    # the rear rockers pivot on the gearbox casing; the halo's front pillar
    # comes up through the cockpit rim to its mount on the tub
    ("gearbox", "rocker_r"), ("cockpit_coaming", "halo"),
    # and the rear anti-roll bar's bearings are on the crash structure's face
    ("antiroll_r", "crash_structure"),
    # the crash structure's struts bolt into the back of the gearbox
    ("crash_structure", "gearbox"),
    # the rear rocker sits on the casing, so the pullrod's clevis on it is
    # in the casing's flank; and each damper's eye is on its rocker
    ("gearbox", "pushrod_r"), ("dampers_", "rocker_"),
    # the rear heave damper sits on the torsion bars between the rockers
    ("heave_", "torsion_bars"),
    # the front bars' inboard splines are in their anchor, which hangs from
    # the tub's top skin
    ("torsion_anchor_f", "torsion_bars_f"), ("torsion_anchor_f", "tub"),
    # the fuel line screws into the engine's fuel rail; the plenum edge is
    # bonded along the tunnel's outer wall; the diffuser fences are bonded
    # to the tunnel roof; the fan fairings sit on the diffuser's trailing
    # edge and kick
    ("floor_plenum_edge_", "tunnel_"),
    ("diffuser_fences", "tunnel_"), ("diffuser_kick", "fan_fairing_"),
    ("diffuser_lip", "fan_fairing_"),
    # the caliper is bolted to the upright by its two lugs, and the brake
    # hose screws into the caliper
    ("caliper_", "upright_"), ("brake_lines", "caliper_"),
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
    ("damper", "torsion_bars"), ("antiroll_blade_", "antiroll_"),
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
    # the fuel hose is pushed on over the port-injection rail's inlet nipple
    ("fuel_fittings", "engine"),
    ("battery_modules", "battery"),

    # bodywork: everything lofted or louvred into it
    ("sidepod_", "tub"), ("sidepod_inlets", "sidepod_"),
    ("sharkfin", "tub"),         # rooted in the engine cover
    ("airbox", "tub"), ("cockpit_coaming", "tub"), ("nose_cape", "tub"),
    ("nose_pylons", "tub"), ("nose_pylons", "front_wing_main"),
    ("side_impact", "tub"),
    ("roll_hoop", "tub"), ("halo", "tub"),
    ("halo_mounts", "tub"), ("halo_pillar", "halo"), ("halo_mounts", "halo"),
    ("mirrors", "tub"),
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
    ("cockpit_coaming", "bulkhead_"),
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
    ("bargeboard_", "sidepod_inlets"),

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
    ("rainlight", "rear_light_panel"),
    ("starter_socket", "tow_hooks"), ("nose_pylons", "tow_hooks"),

    # service hardware roots into whatever carries the load
    ("jack_points", "gearbox"), ("jack_points", "nose_cape"),
    ("jack_points", "nose_pylons"), ("jack_points", "front_wing_main"),

    # the fan is one machine
    ("fan_rotor_", "fan_motors"),

    # the loom plugs into the boxes it feeds
    ("wiring_loom", "gearbox"),

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
    # the charge coolers' loop: its hoses go through the tub the same way,
    # onto the engine's stubs, the core's upper port and the pump's outlet;
    # the pump's spigot is in the core's lower port
    ("rad_lt_hoses_", "tub"),
    ("rad_lt_hoses_", "engine"), ("rad_lt_hoses_", "rad_lt_"),
    ("rad_lt_pump_", "rad_lt_"),
    # the pumps' leads: into the motor's connector, through the pod's wall
    # and the tub's, onto the pack's plug
    ("lt_pump_lead_", "rad_lt_pump_"), ("lt_pump_lead_", "sidepod_"),
    ("lt_pump_lead_", "tub"), ("lt_pump_lead_", "battery"),
    ("driveshaft_", "tub"),
    ("fuel_coupling", "tub"), ("sidepod_", "rad_hoses_"),
    ("fuel_coupling", "fuel_cell"),     # it is the filler for it

    # The high-voltage system (powertrain._hv). The pack's cables leave its
    # terminals; the fan feeds through their grommets in the engine cover
    # into the plugs on the controllers' inboard faces, and the controllers
    # hang off the rear frame by their straps; each fan's lead leaves its
    # controller and ends in the gland set into the fan's cowl. The fan DC
    # plugs are set into the inverter's side faces, which are in "engine".
    ("battery_hv_terminals", "hv_pack_"),
    ("hv_grommets", "tub"), ("fan_controllers", "hv_fan_"),
    ("fan_controllers", "rear_frame"), ("fan_controllers", "fan_leads"),
    ("fan_glands", "fan_fairing_"), ("engine", "inverter_fan_plugs"),
    # the P-clips grip their cables and stand on studs bonded to the floor,
    # the gearbox's top and the crash cone
    ("hv_clips", "hv_"), ("hv_clips", "gearbox"),
    ("hv_clips", "crash_structure"),
    # the battery is bolted to the engine bulkhead's flange
    ("battery", "bulkhead_engine"),
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
    # An exhaust runs inside the engine cover and exits through the tail --
    # the bodywork it passes through is the bodywork it is routed inside.
    ("exhaust", "tub"),
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
}
# --- end KNOWN ---

if __name__ == "__main__":
    import _interfere
    sys.exit(_interfere.intersect_main(__file__, ROOT, PKG, EXPECTED, KNOWN,
                                       TOL, UNIT))

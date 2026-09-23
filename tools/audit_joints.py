"""Does the car hold together, and does every load path close?

    python3 tools/audit_joints.py

Every other audit here is one-sided. `audit_intersect` lists parts sharing
material and `audit_fit` lists parts that got too close -- both are looking for
things that touch when they should not. A pushrod that stops 40 mm short of the rocker it drives passes both, because not
touching is exactly what they want to see.

That is the defect this catches, and it is the commonest one in a model built
a part at a time: something moves, the thing that lands on it does not, and
the only witness is a render from the one angle where the joint is not hidden
behind something else.

`audit_intersect.EXPECTED` is nearly this list already -- naming two parts
there says they are meant to be one assembly -- but it is a permission, not a
requirement. Nothing there fails when one of them drifts away; the entry just
stops applying. The circuits below are the same knowledge stated as an
obligation.

Three checks:

  ASSEMBLY   every part is attached to the machine, however indirectly
  CIRCUITS   each declared run of material is continuous, link by link
  MODULES    no two modules build a part under the same name, and no cutter
             is aimed at a part its own module does not build

CONTACT is 3 mm. Parts that are bolted, welded or bonded together in
this model interpenetrate, so anything further apart than that is not a joint.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import _joints  # noqa: E402

CONTACT_MM = 3.0
ROOT_PART = 'tub'
PKG = 'car/parts'
UNIT = 'mm'

CIRCUITS = [
    ('front left suspension carries wheel load into the tub',
     ['tyre_fl', 'rim_fl', 'wheel_stud_fl', 'hub_fl', 'upright_fl',
      'wishbone_fl_lower_fwd', 'tub']),
    ('front left upper wishbone',
     ['upright_fl', 'wishbone_fl_upper_fwd', 'tub']),
    ('front left pushrod to the heave spring',
     ['upright_fl', 'pushrod_fl', 'rocker_fl', 'torsion_bars_f', 'dampers_f']),
    ('front anti-roll',
     ['rocker_fl', 'antiroll_f', 'antiroll_blade_f']),
    ('rear left suspension carries wheel load into the gearbox',
     ['tyre_rl', 'rim_rl', 'wheel_stud_rl', 'hub_rl', 'upright_rl',
      'wishbone_rl_lower_fwd', 'gearbox']),
    ('rear left pushrod to the dampers',
     ['upright_rl', 'pushrod_rl', 'rocker_rl', 'torsion_bars_r', 'dampers_r']),
    ('steering: wheel to rack to upright',
     ['steering', 'steering_column', 'steering_rack', 'trackrod_fl',
      'steering_arm_fl', 'upright_fl']),
    ('wheel retention',
     ['rim_fl', 'wheelnut_fl', 'hub_fl']),
    ('wheel tether',
     ['upright_fl', 'tether_fl', 'tub']),
    ('front left brake: pedal to caliper',
     ['pedal_box', 'master_cylinders', 'brake_lines', 'caliper_fl']),
    ('front left brake: pad on disc, caliper on upright',
     ['disc_fl', 'brake_pad_fl', 'caliper_fl', 'upright_fl']),
    ('front left brake duct',
     ['bduct_inlet_fl', 'bduct_pipe_fl', 'bduct_drum_fl', 'upright_fl']),
    ('drive: engine to gearbox to the rear wheel',
     ['engine', 'gearbox', 'driveshaft_rl', 'hub_rl']),
    ('the pack and cell are carried on the engine bulkhead',
     ['tub', 'bulkhead_engine', 'fuel_cell', 'battery']),
    ('fuel: cell to fittings to engine',
     ['fuel_cell', 'fuel_fittings', 'engine']),
    ('fuel filler',
     ['fuel_cell', 'fuel_coupling']),
    ('exhaust leaves the engine',
     ['engine', 'exhaust']),
    ('cooling, left: inlet to core to tanks to engine',
     ['sidepod_inlets', 'sidepod_l', 'radiator_l', 'rad_tanks_l', 'rad_hoses_l', 'engine']),
    ('hot air leaves the left sidepod',
     ['sidepod_l', 'exit_louvres_l']),
    ('high voltage: the pack is one assembly',
     ['battery', 'battery_modules']),
    ('fan, left: floor intake to shroud to nozzle',
     ['floor_fan_throat_l', 'fanduct', 'fan_nozzle_l']),
    ('fan, right',
     ['floor_fan_throat_r', 'fanduct', 'fan_nozzle_r']),
    ('the fans are driven: rotor on the motor, motor on the stators',
     ['fan_rotor_l', 'fan_motors', 'fan_stators', 'fanduct']),
    ('the fan pods are carried on the rear frame, on the crash structure',
     ['fanduct', 'fan_fairing_l', 'rear_frame', 'crash_structure']),
    ('the fans breathe from the floor, not from outside it',
     ['floor_surface', 'floor_fan_throat_l']),
    ('underbody, left: inlet to tunnel to diffuser',
     ['floor_inlet_lip', 'tunnel_l', 'diffuser_kick', 'diffuser_lip']),
    ('the plank and the skirts are on the floor',
     ['floor_surface', 'floor_plank']),
    ('the skirts seal the floor',
     ['floor_surface', 'floor_skirts']),
    ('the front wing is carried off the nose',
     ['front_wing_main', 'nose_pylons', 'tub']),
    ('every front wing element is carried by the endplate',
     ['front_wing_main', 'front_endplate_l', 'front_flap_1']),
    ('the rear wing is carried off its pylons',
     ['rear_wing_main', 'wing_mount_l', 'rear_pylon_l', 'rear_frame',
      'crash_structure']),
    ('rear flap, endplate and gurney belong to the rear wing',
     ['rear_wing_main', 'rear_endplate_l', 'rear_flap', 'rear_gurney']),
    ('DRS drives the rear flap',
     ['drs_actuator', 'rear_flap']),
    ('beam wing',
     ['beam_wing', 'rear_pylon_l']),
    ('the rear crash structure is on the car',
     ['tub', 'crash_structure']),
    ('halo into the tub',
     ['halo', 'halo_pillar', 'halo_mounts', 'tub']),
    ('roll hoop into the tub',
     ['roll_hoop', 'tub']),
    ('the driver is in the seat and belted to the tub',
     ['tub', 'seat', 'driver', 'helmet']),
    ('the harness anchors to the tub',
     ['tub', 'seat', 'harness', 'harness_buckle']),
    ('side impact structure',
     ['tub', 'side_impact', 'side_intrusion']),
    ('the airbox feeds the engine',
     ['airbox', 'engine']),
]


def main():
    parts, collisions, cut_owner, built_by, failures = _joints.load(ROOT, PKG)
    bad = []

    print(f"\n{len(parts)} parts from {len(set(built_by.values()))} modules")

    print("\nMODULES")
    for name, why in failures:
        print(f"  x   {name:26s} did not build: {why}")
        bad.append(f"{name} did not build")
    for key, first, second in collisions:
        print(f"  x   {key:26s} built by both {first} and {second}")
        bad.append(f"{key} is built twice")
    for target, owners in sorted(cut_owner.items()):
        for owner in owners:
            if target not in built_by:
                print(f"  x   {target:26s} cut declared by {owner}, and"
                      f" nothing builds it -- the cutter has no target")
                bad.append(f"{target} cutter from {owner} has no target")
    if not bad:
        print("  ok  every part name is built once, by one module, and every"
              " cutter reaches its target")

    print(f"\nASSEMBLY  (contact within {CONTACT_MM:g} {UNIT})")
    graph = _joints.contact_graph(parts, CONTACT_MM)
    groups = _joints.components(graph)
    main_group = next((g for g in groups if ROOT_PART in g), set())
    loose = [g for g in groups if g is not main_group]
    if not loose:
        print(f"  ok  all {len(main_group)} parts hang together off {ROOT_PART}")
    for g in loose:
        names = ", ".join(sorted(g))
        print(f"  x   detached: {names}")
        bad.append(f"detached: {names}")

    print("\nCIRCUITS")
    for label, chain in CIRCUITS:
        breaks = _joints.broken_links(parts, graph, chain)
        if not breaks:
            print(f"  ok  {label}")
            continue
        for (_i, a, b, why) in breaks:
            extra = ""
            if why == "no contact":
                A, B = _joints.match(parts, a), _joints.match(parts, b)
                d = min(_joints.gap(parts[x], parts[y]) for x in A for y in B)
                extra = f" ({d:.0f} {UNIT} apart)"
            print(f"  x   {label}: {a} -> {b}, {why}{extra}")
            bad.append(f"{label}: {a} -> {b} {why}")

    print()
    if not bad:
        print("PASS  it is one assembly and every circuit is joined")
        return 0
    print(f"FAIL  {len(bad)} joints are not made")
    return 1


if __name__ == "__main__":
    sys.exit(main())

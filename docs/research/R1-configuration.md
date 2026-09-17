# R1 — configuration decision memo

## Decision boundary

The rules in `car/spec.py:990–1017` allow four wheels, combustion or hybrid propulsion, and an unaided single flying lap on the track. There is no regulatory reason to retain today's mass, tyre width, fixed aero or fan sizing. This is a configuration comparison, not a validated lap prediction.

`ANCHORS.md` fixes the tyre load-sensitivity exponent at a central **k = 0.18**, with **0.15–0.25** sensitivity, and the driver ceiling at **6–7 g**. Its example tyre's absolute friction coefficient is not a calibration for a bespoke racing slick. The T.50 numbers describe speed-dependent aero, not sealed-plenum fan suction; they cannot validate this car's claimed static download.

For the supplied 5.5 m² sealed area, 650 kg-equivalent download requires `650 × 9.81 / 5.5 = 1,159 Pa`. With air density assumed at 1.20 kg/m³, 23.6 kg/s means 19.67 m³/s; delivering that flow at that depression uses 38.0 kW shaft power at 60% efficiency. Thus the supplied 62 kW, flow and download are not a closed operating point: losses, leakage and the fan pressure–flow map must be measured before claiming an actual optimum.


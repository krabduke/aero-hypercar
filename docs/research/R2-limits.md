# R2 — What actually limits this car?

## Decision frame

The driver is a likely performance ceiling, but tyre qualification and fan-loss stability are prior safety gates. The stated 7 g is a design assumption, not demonstrated sustained human capability. This memo separates calculated capability from validated capability.

The baseline is 700 kg, ClA = 5.90 m², and 650 kg-equivalent fan downforce. The repository uses tyre load-sensitivity exponent k = 0.12; ANCHORS.md instead supports k = 0.15–0.25, centred on 0.18. All decision calculations below must distinguish those assumptions. A lap-time claim without a specified circuit, speed trace, and acceleration/braking model is not a verified lap prediction.

## Computed state

From `car/spec.py`: 935 kW, RHO = 1.225, ClA = 5.90 (wings 2.55 + floor 3.35), C dA = 1.62, fan 650 kg, TYRE_MU = 1.80, TYRE_LOAD_SENS = 0.12, DRIVER_G_LIMIT = 7.0.

| k | steady 5 g | steady 6 g | steady 7 g |
|---|---|---|---|
| 0.12 | 176 | 222 | 260 |
| 0.18 | 195 | 244 | 286 |
| 0.25 | 221 | 274 | 321 |

Steady-state speeds (km/h) at which lateral g equals a driver cap, from `g = mu0·(N/W)^0.82` with N = W + 650g + ½ρV²·5.90, W = 700·9.81. Below those speeds the car cannot reach the cap; above them the cap, not the tyre, sets corner speed. F1 faces the same cap at 6 g — this is a human, not a machine, difference.

Per tyre at 300 km/h: front ≈ 8.5 kN vertical, rear ≈ 10.6 kN. This is roughly double an F1 tyre's ~5 kN reference load. Lateral force per tyre at 6 g ≈ 10.3 kN against 9.6 kN vertical. Contact-patch pressure ~100–110 kPa vs cold inflation 175–230 kPa: the patch is not failing, it is simply over-capacity.

## What limits this car first

1. **Driver ceiling (7 g).** Binds above ~260–321 km/h depending on k. Above that, extra ClA buys nothing; below it, downforce still pays. This is a performance ceiling, not a safety gate.
2. **Tyre qualification.** At k = 0.12 and 7 g, required N ≈ 29.8 kN — 4.4× static, ~2× F1-corner load. Published data (Milliken via ANCHORS.md; Goodyear F1 front in Sharp 2003) tops out around 8.7 kN. This car needs a tyre qualified to ~3× any published data point. It is a gap, not a graceful mu rolloff. No F1 supplier will sign off without a test program.
3. **Fan-loss stability.** Instant loss of 650 kg-equivalent downforce at 6 g drops tyre lateral capacity to ~4.9 g-equivalent (−18% grip), a 9% speed margin — tight but not catastrophic for an alert driver. However, the car is in a 6 g corner at ~250 km/h with ~40% yaw margin consumed. This is a certification and recovery-procedure question, not an optimisation one.
4. **Structure.** Floor + fan loads ≈ 20.6 kN at 300 km/h; wings ≈ 10.8 kN; total ≈ 38.3 kN = 5.6× weight. Front upright sees ~8.5 kN, rear ~10.6 kN. These are high but within motorsport-standard carbon practice; verify.py does not yet test any of this.


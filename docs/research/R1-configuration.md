# Is this the right car?

> **Superseded in part by [R2](R2-limits.md).** R1's recommendation — take
> wing off — is correct and has been acted on. Its *reason* was not: R1
> attributed the optimum to the driver's 7 g limit, and R2 shows that removing
> that limit entirely is worth 0.04 s because the tyre saturates in the same
> place. The optimum is set by tyre load sensitivity, not by the driver, and it
> holds for every driver limit from 6 g up.

Every number here comes out of `aero/config_study.py`, which drives the same
solver as `aero/laptime.py`. Nothing in this document can disagree with the
headline lap time by construction. Load sensitivity is held at k = 0.20, the
middle of the band `ANCHORS.md` sources from Milliken.

Baseline: 700 kg, ClA 5.90, CdA 1.62, a 650 kg fan on 62 kW, 935 kW at the
crank. Lap 80.34 s against a Formula 1 reference at 91 s.

## The finding

**The car carries more downforce than it can use, and pays for it in drag.**

Reducing ClA from 5.90 to 4.72 makes it **a second a lap faster**:

| ClA | lap | vs baseline |
|---|---|---|
| 3.54 | 79.48 s | −0.86 |
| **4.72** | **79.33 s** | **−1.01** |
| 5.90 (today) | 80.34 s | — |
| 7.08 | 82.39 s | +2.05 |
| 8.26 | 84.72 s | +4.38 |

The optimum is near ClA 4.7, twenty per cent below what the car has. Past that
the drag costs more on the straights than the grip returns in the corners.

The reason is the driver. **62 % of the car's cornering time is spent at the
7 g limit with the tyres able to give more.** Downforce beyond the point where
the driver saturates buys no lateral acceleration at all, so its only effect
is drag. This is not a modelling artefact; it is the central consequence of
building a car with no minimum weight, no aero restriction and a human in it.

## The levers, ranked

| change | worth | notes |
|---|---|---|
| power 935 → 1300 kW | **−6.15 s** | no fuel-flow or energy limit in the ruleset |
| mass 700 → 550 kg | **−2.27 s** | no minimum weight either |
| wider tyres, mu 1.75 → 2.20 | **−2.23 s** | no tyre regulations at all |
| ClA 5.90 → 4.72 | **−1.01 s** | the car is over-winged |
| fan 650 kg | 0.00 s | already at its optimum |

Taken together those are worth roughly eleven seconds more, on top of the ten
already held over the reference car.

## The fan is right, and that is worth stating

| fan download | fan power | lap | vs baseline |
|---|---|---|---|
| none | 0 kW | 83.98 s | +3.64 |
| 325 kg | 26 kW | 81.35 s | +1.01 |
| **650 kg** | **62 kW** | **80.34 s** | — |
| 975 kg | 110 kW | 80.32 s | −0.03 |
| 1300 kg | 172 kW | 81.16 s | +0.82 |

The curve is flat from 650 to 975 kg and turns over after. The fan as
specified is at its optimum and deleting it costs 3.64 s a lap. Note that this
is the one downforce source *not* subject to the argument above: it is
speed-independent, so it does its work in the slow corners where the car is
furthest from the driver's limit, which is exactly where aerodynamic downforce
has least to give.

## Recommendation

Take the wing off it. Specifically: reduce ClA toward 4.7 by unloading the
wings rather than the floor, since the floor's contribution is cheaper in drag
and works lower down the speed range. Spend the recovered drag and the 150 kg
on power and tyre width, both of which the ruleset leaves entirely open and
both of which are still climbing at the edge of the range tested.

## What would change this

- **A different driver limit.** At 5 g the car is over-winged by more; at 9 g
  the current ClA is closer to right. `spec.DRIVER_G_LIMIT` is 7.0 and the
  whole recommendation hangs on it. It is the single number most worth
  getting from a real source rather than an assumption.
- **Load sensitivity.** At k = 0.15 the tyre punishes extra load less and the
  optimum ClA rises; at k = 0.25 it falls further. The band is sourced but
  wide.
- **The drag model for downforce.** ClA is traded against CdA here as
  `CdA ∝ ClA^1.5` on the wing share only. A real polar for these surfaces
  would sharpen the optimum but is unlikely to move it much, because the
  driver limit sets it, not the drag.

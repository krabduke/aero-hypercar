# What limits this car

All figures from `aero/limits_study.py`, driving the same solver as
`aero/laptime.py`. Load sensitivity held at k = 0.20, the middle of the band
`ANCHORS.md` sources from Milliken.

## This corrects R1

R1 concluded the car is over-winged **because the driver is the limit** — it
sits at the 7 g cap for 62 per cent of its cornering time, so downforce past
that point cannot be used. The conclusion was right. The reason was wrong.

| driver g limit | lap | vs 7 g | fastest ClA |
|---|---|---|---|
| 5.0 | 82.44 s | +2.10 | 3.54 |
| 6.0 | 81.02 s | +0.68 | 4.13 |
| **7.0** | **80.34 s** | — | **4.13** |
| 8.0 | 80.30 s | −0.04 | 4.13 |
| 9.0 | 80.30 s | −0.04 | 4.13 |
| none at all | 80.30 s | −0.04 | 4.13 |

**Removing the driver limit entirely is worth 0.04 s.** The car sits at the cap
constantly, but lifting it gains almost nothing, because the tyre saturates in
the same place — the driver and the rubber run out together. Raising one
without the other buys nothing.

What actually sets the optimum is **load sensitivity**. Past roughly ClA 4.5
the extra vertical load buys so little extra grip that the drag needed to
generate it is a straight loss. That holds at ClA 4.13 for every driver limit
from 6 g upward, so the recommendation to take wing off is far more robust
than R1's argument for it. Below 6 g the cap does bite: at 5 g the optimum
falls to 3.54 and the lap costs 2.1 s.

**Acted on.** `cla_wings` 2.55 → 1.20, `cda` 1.62 → 1.28. The car's advantage
over the reference went from 10.61 s to **11.77 s a lap** by removing
downforce.

## The tyre — least trustworthy thing in the project

| | load per tyre | × static |
|---|---|---|
| slowest corner, 118 km/h | 4,275 N | 2.5 |
| top speed, 333 km/h | 11,039 N | 6.4 |

Milliken's published table covers 900–1800 lbf, which is 4,000–8,000 N. This
car reaches **11,039 N per tyre, 1.4× the top of the measured range.** Every
coefficient at those loads is a power law extrapolated past its data, and a
real tyre at 6.4× its static load may fail rather than lose grip smoothly.

The lap time should be read as an upper bound for that reason alone, and no
amount of care in the solver fixes it. This is the single biggest hole in the
claim.

## The structure

| speed | downforce | × car weight | front axle |
|---|---|---|---|
| 150 km/h | 12,648 N | 1.8 | 5,628 N |
| 250 km/h | 23,802 N | 3.5 | 10,592 N |
| 330 km/h | 36,740 N | 5.4 | 16,349 N |

The floor's suction at 330 km/h is about 3.1 kPa over 5.5 m², roughly 3 % of
an atmosphere — ordinary for the class. The concern is not the floor but the
suspension: it carries around three times a Formula 1 car's load through
uprights of similar size, and that needs a stress check this study cannot do.

## Losing the fan

In the slowest corner at 118 km/h:

- with the fan: **3.63 g** available
- fan stopped: **2.50 g** available
- **31 % of the grip, gone in the time a fan spins down**

A car cornering at 3.63 g that loses 31 % of its grip does not understeer, it
leaves. This is a single point of failure at maximum load. The car has two
fans on separate drives, which only helps if **either one alone is enough** —
that needs checking, and if it is not, the honest answer is to size them so
that it is.

## Ranked

1. **The driver** — binds constantly but costs only 0.04 s, because the tyre
   binds with it. Worth sourcing only to know whether we are above or below 6 g.
2. **The tyre** — 1.4× past the top of published data. The real limit.
3. **The fan** — single point of failure at maximum load.
4. **The structure** — large loads, ordinary for the class.

Least confident in the tyre, by a wide margin.

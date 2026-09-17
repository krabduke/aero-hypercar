"""Independent conservation, malformed-input and geometric-screen checks."""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "aero"))
import fan_exhaust as analysis


def main():
    result = analysis.flow(analysis.spec.FAN, analysis.spec.FAN_EXHAUST)
    failures = []
    if not all(math.isfinite(value) for value in result.values()):
        failures.append("Non-finite flow result")
    if result["area_mismatch"] > 0.05:
        failures.append(f"Exit/annulus area mismatch {result['area_mismatch']:.2%} > 5%")
    for failure in failures:
        print(f"FAIL: {failure}")
    print(f"Flow screening: {len(failures)} failure(s); not CFD")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())

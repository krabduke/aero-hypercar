"""Does the 2D panel method give the answers that are already known?

A cylinder, where potential flow has a closed form. A thin aerofoil, where it
has another. And a section in ground effect, where the trend is known even if
the number is not. Nothing about the car is believed until these pass.
"""
import math
import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel2d import Section2D                              # noqa: E402


def cylinder(n=200):
    th = np.linspace(0, -2 * math.pi, n + 1)
    return np.cos(th), np.sin(th)


def naca(code="0012", n=160, alpha_camber=True):
    t = int(code[2:]) / 100.0
    m, p = int(code[0]) / 100.0, int(code[1]) / 10.0
    b = np.linspace(0, math.pi, n // 2 + 1)
    xc = 0.5 * (1 - np.cos(b))
    yt = 5 * t * (0.2969 * np.sqrt(xc) - 0.1260 * xc - 0.3516 * xc**2
                  + 0.2843 * xc**3 - 0.1036 * xc**4)
    if m > 0 and p > 0 and alpha_camber:
        yc = np.where(xc < p, m / p**2 * (2 * p * xc - xc**2),
                      m / (1 - p)**2 * ((1 - 2*p) + 2*p*xc - xc**2))
    else:
        yc = np.zeros_like(xc)
    xl, yl = xc, yc - yt                     # lower, LE -> TE
    xu, yu = xc, yc + yt                     # upper, LE -> TE
    # clockwise from the trailing edge: TE -> LE along the lower, LE -> TE
    # along the upper
    x = np.concatenate([xl[::-1], xu[1:]])
    y = np.concatenate([yl[::-1], yu[1:]])
    return x, y


ok = True
def fail(m):
    global ok
    ok = False
    print("   x  " + m)


print("\n2D PANEL METHOD VALIDATION")

print("\n  CYLINDER -- exact Cp = 1 - 4 sin^2(theta)")
print("    panels    Cp rms     Cp worst")
prev = None
for n in (100, 200, 400):
    x, y = cylinder(n)
    s = Section2D(x, y).solve(0.0, 1.0)
    th = np.arctan2(s.cy, s.cx)
    exact = 1 - 4 * np.sin(th) ** 2
    e = np.abs(s.cp - exact)
    rms = float(np.sqrt((e**2).mean()))
    print(f"    {n:6d}    {rms:.3e}  {e.max():.3e}")
    if prev is not None and rms > prev * 3:
        fail("the cylinder got worse with more panels")
    prev = rms
if prev > 1e-6:
    fail(f"cylinder Cp rms {prev:.4f}")

print("\n  NACA 0012 -- thin-aerofoil theory says dCl/dalpha = 2.pi = 6.283")
x, y = naca("0012", 200)
s0 = Section2D(x, y).solve(0.0, 1.0)
s4 = Section2D(x, y).solve(4.0, 1.0)
slope = (s4.cl - s0.cl) / math.radians(4)
print(f"    Cl at 0 deg   {s0.cl:+.5f}   (a symmetric section: must be zero)")
print(f"    Cl at 4 deg   {s4.cl:+.5f}")
print(f"    dCl/dalpha    {slope:.3f}   ({100*(slope/(2*math.pi)-1):+.1f} % of 2.pi;")
print( "                   a thick section is a little above it, which is right)")
if abs(s0.cl) > 1e-6:
    fail(f"a symmetric section makes {s0.cl:.2e} of lift at zero incidence")
if not (6.1 < slope < 7.1):
    fail(f"lift slope {slope:.3f} is not 2.pi")

print("\n  GROUND EFFECT -- an inverted section closing on the road")
print("    (with ground=True, which the first version of this test forgot,")
print("     and so measured a section in free air five times over)")
print("    ride height/chord    Cl        suction under it")
x, y = naca("4412", 200)
y = -y                                      # inverted: a car's wing
x = x[::-1]; y = y[::-1]                    # keep the clockwise ordering
prevcl = None
for h in (1.00, 0.50, 0.25, 0.12, 0.06):
    s = Section2D(x, y + h + 0.1, ground=True).solve(0.0, 1.0)
    lower = s.cp[s.cy < (h + 0.1)]
    print(f"    {h:6.2f}            {s.cl:+.4f}     {lower.min():+.3f}")
    if prevcl is not None and s.cl > prevcl + 1e-9:
        fail("downforce fell as the section approached the road")
    prevcl = s.cl
print("    (more negative Cl is more downforce: it must grow as the gap closes,")
print("     which is the whole of ground effect)")

print("\n" + "=" * 62)
print("PASS  the 2D solver reproduces the cases with known answers" if ok
      else "FAIL")
sys.exit(0 if ok else 1)

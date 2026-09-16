"""A two-dimensional panel method, with a road under it.

WHY TWO DIMENSIONS

The three-dimensional solve cannot answer about this car and the reason is
measured: the floor runs 10 mm off the ground with panels 200 to 500 mm
across, so every floor panel faces its own image in the road at 0.035 of its
own width and the influence matrix is near-singular exactly there. To put a
floor panel one width from its image it would have to be 20 mm across, and the
floor is 5.5 square metres -- about 14,000 panels before the wings, which a
dense O(N^3) solve will not do.

In TWO dimensions that argument evaporates. A section through the floor needs
a few hundred panels, not fourteen thousand, and a few hundred panels can be
40 micrometres long if that is what the gap wants. The underfloor is a duct
and a duct's section is the thing that decides its pressure, so this is not a
consolation prize: it is the right tool for the part of the car that matters
most, and the part whose entire contribution is currently a number somebody
typed into a spec file.

WHAT IT IS

Hess and Smith's classic arrangement: constant-strength source panels with one
constant vortex shared across the whole body, N+1 unknowns against N
tangency conditions and a Kutta condition at the trailing edge. The road is an
image system -- every panel mirrored in y = 0 with the source sign kept and
the vortex sign flipped, which is what makes the road a streamline.

Nothing here is trusted until check_panel2d.py has run it against a case with
a known answer.
"""

import math

import numpy as np


def panel_geometry(x, y):
    """Panel mid-points, lengths and unit vectors for a closed section given
    clockwise from the trailing edge (the usual panel-method ordering)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    dx, dy = x[1:] - x[:-1], y[1:] - y[:-1]
    ell = np.hypot(dx, dy)
    sin, cos = dy / ell, dx / ell
    return (0.5 * (x[:-1] + x[1:]), 0.5 * (y[:-1] + y[1:]), ell, sin, cos)


def influence(px, py, x, y, ell, sin, cos):
    """Velocity at (px, py) from unit source and unit vortex on each panel.

    Returns (us, vs, uv, vv), each (len(px), N). The source and the vortex on
    one panel are related -- the vortex's velocity is the source's rotated a
    quarter turn -- which is why both come out of one pass.
    """
    n = len(ell)
    px = np.asarray(px, float)[:, None]
    py = np.asarray(py, float)[:, None]
    x1, y1 = x[:-1][None, :], y[:-1][None, :]
    x2, y2 = x[1:][None, :], y[1:][None, :]
    # into each panel's own frame
    dxp, dyp = px - x1, py - y1
    xp = dxp * cos + dyp * sin
    yp = -dxp * sin + dyp * cos
    # A point on a panel's own line is approached from OUTSIDE.
    #
    # The angle a panel subtends at a point in its own plane is +pi from one
    # side and -pi from the other, and atan2 picks between them on the SIGN
    # OF FLOATING-POINT ZERO. Every collocation point is the midpoint of its
    # own panel, where that offset is exactly zero, so half the diagonal of
    # the influence matrix came out at -0.5 instead of +0.5 -- half the body
    # was solved with its boundary condition inverted. The cylinder's
    # pressure was wrong by 1.7 rms and the lift slope came out at a quarter
    # of 2.pi.
    #
    # Outside is the +y side of a panel, because the outward normal is
    # (-sin, cos). So an exact zero is nudged to +0.
    yp = np.where(np.abs(yp) < 1e-12, 1e-12, yp)
    r1 = np.hypot(xp, yp)
    r2 = np.hypot(xp - ell, yp)
    # the angle the panel subtends, continuous across the sheet
    th = np.arctan2(yp, xp - ell) - np.arctan2(yp, xp)
    ln = np.log(np.maximum(r1, 1e-300) / np.maximum(r2, 1e-300))
    # source: u along the panel from the log, v across it from the angle
    us_l, vs_l = ln / (2 * math.pi), th / (2 * math.pi)
    # vortex: the same pair rotated
    uv_l, vv_l = vs_l, -us_l
    # back to global
    us = us_l * cos - vs_l * sin
    vs = us_l * sin + vs_l * cos
    uv = uv_l * cos - vv_l * sin
    vv = uv_l * sin + vv_l * cos
    return us, vs, uv, vv


class Section2D:
    """One closed section in a uniform stream, optionally over a road at y=0.

    `x, y` run clockwise from the trailing edge and close on themselves.
    """

    def __init__(self, x, y, ground=False):
        self.x = np.asarray(x, float)
        self.y = np.asarray(y, float)
        self.ground = ground
        self.cx, self.cy, self.ell, self.sin, self.cos = panel_geometry(
            self.x, self.y)
        self.n = len(self.ell)

    def _blocks(self, px, py):
        """Source and vortex influence at (px, py), road included."""
        us, vs, uv, vv = influence(px, py, self.x, self.y, self.ell,
                                   self.sin, self.cos)
        if self.ground:
            # the image body: reflected in y = 0, traversed the other way so
            # its normals still point out of it
            xi, yi = self.x, -self.y
            cxi, cyi, elli, sini, cosi = panel_geometry(xi, yi)
            ius, ivs, iuv, ivv = influence(px, py, xi, yi, elli, sini, cosi)
            # a source's image is a source of the SAME sign; a vortex's image
            # is a vortex of the OPPOSITE sign. Together they make y = 0 a
            # streamline, which is what a road is.
            us, vs = us + ius, vs + ivs
            uv, vv = uv - iuv, vv - ivv
        return us, vs, uv, vv

    def solve(self, alpha_deg=0.0, v=1.0):
        a = math.radians(alpha_deg)
        ux, uy = v * math.cos(a), v * math.sin(a)
        n = self.n
        us, vs, uv, vv = self._blocks(self.cx, self.cy)
        nx, ny = -self.sin, self.cos          # outward normal of each panel
        tx, ty = self.cos, self.sin
        A = np.zeros((n + 1, n + 1))
        b = np.zeros(n + 1)
        # flow tangency at every mid-point
        A[:n, :n] = us * nx[:, None] + vs * ny[:, None]
        A[:n, n] = (uv * nx[:, None] + vv * ny[:, None]).sum(axis=1)
        b[:n] = -(ux * nx + uy * ny)
        # Kutta: equal tangential speed on the two panels at the trailing edge
        k = np.array([0, n - 1])
        A[n, :n] = (us[k] * tx[k, None] + vs[k] * ty[k, None]).sum(axis=0)
        A[n, n] = (uv[k] * tx[k, None] + vv[k] * ty[k, None]).sum()
        b[n] = -((ux * tx[k] + uy * ty[k]).sum())
        sol = np.linalg.solve(A, b)
        self.sigma, self.gamma = sol[:n], sol[n]
        # surface speed and pressure
        vt = (ux * tx + uy * ty
              + (us * tx[:, None] + vs * ty[:, None]) @ self.sigma
              + (uv * tx[:, None] + vv * ty[:, None]).sum(axis=1) * self.gamma)
        self.vt = vt
        self.cp = 1.0 - (vt / v) ** 2
        # circulation and lift, by Kutta-Joukowski
        self.circulation = self.gamma * self.ell.sum()
        chord = self.x.max() - self.x.min()
        self.cl = 2.0 * self.circulation / (v * chord)
        return self

    def velocity(self, px, py, alpha_deg=0.0, v=1.0):
        a = math.radians(alpha_deg)
        us, vs, uv, vv = self._blocks(px, py)
        u = v * math.cos(a) + us @ self.sigma + uv.sum(axis=1) * self.gamma
        w = v * math.sin(a) + vs @ self.sigma + vv.sum(axis=1) * self.gamma
        return u, w

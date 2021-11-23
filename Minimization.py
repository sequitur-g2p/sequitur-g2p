from __future__ import division
from __future__ import print_function

__author__ = "Maximilian Bisani"
__version__ = "$LastChangedRevision: 1691 $"
__date__ = "$LastChangedDate: 2011-08-03 15:38:08 +0200 (Wed, 03 Aug 2011) $"
__copyright__ = "Copyright (c) 2004-2005  RWTH Aachen University"
__license__ = """
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License Version 2 (June
1991) as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, you will find it at
http://www.gnu.org/licenses/gpl.html, or write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110,
USA.

Should a provision of no. 9 and 10 of the GNU General Public License
be invalid or become invalid, a valid provision is deemed to have been
agreed upon which comes closest to what the parties intended
commercially. In any case guarantee/warranty shall be limited to gross
negligent actions or intended actions or fraudulent concealment.
"""

from math import *
from numpy import *


gold = (1 + sqrt(5)) / 2
cGold = (3 - sqrt(5)) / 2


def bracketMinimum(f, xa, xb):
    """
    Given a unary function f and initial point xa and xb, search in
    downhill direction and returns new points xa, xb, xc which bracket
    a minimum of f.
    adapted from: W. H. Press et. al., "Numerical Recipes", section 10.1
    """
    fa = f(xa)
    fb = f(xb)
    if fb > fa:
        xa, xb = xb, xa
        fa, fb = fb, fa
    xc = xb + gold * (xb - xa)
    fc = f(xc)
    while fb >= fc:
        xuLimit = xb + 100.0 * (xc - xb)
        r = (xb - xa) * (fb - fc)
        q = (xb - xc) * (fb - fa)
        xu = xb - (xb - xc) * q - (xb - xa) * r
        if q != r:
            xu /= 2 * (q - r)
        else:
            xu = xuLimit
        if (xb - xu) * (xu - xc) > 0.0:
            # xu is between xb and xc
            fu = f(xu)
            if fu < fc:
                xa, xb = xb, xu
                fa, fb = fb, fu
                break
            elif fu > fb:
                xc = xu
                fc = fu
                break
            xu = xc + gold * (xc - xb)
            fu = f(xu)
        elif (xc - xu) * (xu - xuLimit) > 0.0:
            # xu is between xc and xuLimit
            fu = f(xu)
            if fu < fc:
                xb, xc = xc, xu
                fb, fc = fc, fu
                xu = xc + gold * (xc - xb)
                fu = f(xu)
        elif (xu - xuLimit) * (xuLimit - xc) >= 0.0:
            xu = xuLimit
            fu = f(xu)
        else:
            xu = xc + gold * (xc - xb)
            fu = f(xu)
        xa, xb, xc = xb, xc, xu
        fa, fb, fc = fb, fc, fu
    assert (xa < xb and xb < xc) or (xa > xb and xb > xc)
    assert fb <= fa and fb <= fc
    return xa, xb, xc, fa, fb, fc


maxIterations = 100
zEpsilon = 1.0e-18


def linearMinimization(
    f, x=None, lower=None, upper=None, tolerance=1.0e-10, maxIterations=maxIterations
):
    """
    Given a function f and staring point x, this function determines
    the minimum of x using Brent's method of parabolic interpolation.
    Alternatively lower and upper bounds can be given instead of x.
    adapted from: W. H. Press et. al., "Numerical Recipes", section 10.2
    """

    if x is not None:
        xa, xb, xc, fa, fb, fc = bracketMinimum(f, x, x + 1.0)
        if xa < xc:
            a, b = xa, xc
        else:
            a, b = xc, xa
        x, fx = xb, fb
    elif lower is not None and upper is not None:
        a, b = lower, upper
        x = a + cGold * (b - a)
        fx = f(x)
    else:
        raise ValueError("Either x or lower and upper must be given.")

    d = 0.0
    e = 0.0
    v, fv = x, fx
    w, fw = x, fx

    for iteration in range(maxIterations):
        xm = (a + b) / 2
        tol = tolerance * fabs(x) + zEpsilon
        if fabs(x - xm) <= (2.0 * tol - (b - a) / 2):
            break
        if fabs(e) > tol:
            r = (x - w) * (fx - fv)
            q = (x - v) * (fx - fw)
            p = (x - v) * q - (x - w) * r
            q = 2.0 * (q - r)
            if q > 0.0:
                p = -p
            q = fabs(q)
            etemp, e = e, d
            if fabs(p) >= fabs(0.5 * q * etemp) or p <= q * (a - x) or p >= q * (b - x):
                if x >= xm:
                    e = a - x
                else:
                    e = b - x
                d = cGold * e
            else:
                d = p / q
                u = x + d
                if u - a < 2.0 * tol or b - u < 2.0 * tol:
                    if xm >= x:
                        d = tol
                    else:
                        d = -tol
        else:
            if x >= xm:
                e = a - x
            else:
                e = b - x
            d = cGold * e
        if fabs(d) > tol:
            u = x + d
        elif d > 0.0:
            u = x + tol
        else:
            u = x - tol

        fu = f(u)

        if fu <= fx:
            if u >= x:
                a = x
            else:
                b = x
            v, w, x = w, x, u
            fv, fw, fx = fw, fx, fu
        else:
            if u < x:
                a = u
            else:
                b = u
            if fu < fw or w == x:
                v, w = w, u
                fv, fw = fw, fu
            elif fu <= fv or v == x or v == w:
                v = u
                fv = fu
    else:
        raise "failed to converge"
    return x, fx


def hasConverged(fCurrent, fOld, tolerance):
    return 2 * (fOld - fCurrent) <= tolerance * (fabs(fOld) + fabs(fCurrent) + zEpsilon)


def directionSetMinimization(
    f, initialPoint, directions=None, tolerance=1.0e-10, maxIterations=maxIterations
):
    """
    Powell's method of multi-dimension minimization.
    inspired from: W. H. Press et. al., "Numerical Recipes", section 10.5
    """
    if directions is None:
        directions = identity(len(initialPoint), type=Float64)
    current = initialPoint
    fCurrent = f(current)
    for iteration in range(maxIterations):
        old = current
        fOld = fCurrent
        largestDecrease = 0.0
        directionOfLargestDecrease = None
        for dir, dirVector in enumerate(directions):
            xMin, fMin = linearMinimization(
                lambda x: f(current + x * dirVector), 0, tolerance=tolerance
            )
            decrease = fCurrent - fMin
            if decrease > largestDecrease:
                largestDecrease = decrease
                directionOfLargestDecrease = dir
            current = current + xMin * dirVector
            fCurrent = fMin
            if fabs(xMin) > zEpsilon:
                dirVector *= xMin

        if hasConverged(fCurrent, fOld, tolerance):
            break

        averageDirection = current - old
        extrapolated = current + averageDirection
        fExtrapolated = f(extrapolated)
        if fExtrapolated < fCurrent:
            if (
                2
                * (fOld - 2 * fCurrent + fExtrapolated)
                * (fOld - fCurrent - largestDecrease) ** 2
                < (fOld - fExtrapolated) ** 2 * largestDecrease
            ):
                directions[directionOfLargestDecrease] = directions[0]
                directions[0] = averageDirection
    else:
        raise "failed to converge"
    return current, fCurrent


def hasSignificantDecrease(series):
    """
    Determines the slope of a series of values and its standard error.
    Returns True if the hypothesis [slope >= 0] can be rejected with
    99% confidence.
    """

    N = len(series)
    x = arange((1 - N) / 2, N / 2)
    y = array(series)
    assert len(x) == N
    assert sum(x) == 0
    xx = (N - 1) * N * (N + 1) / 12
    assert xx == sum(x * x)

    mean = sum(y) / N
    slope = sum(x * y) / xx

    delta = y - mean - slope * x
    if not fabs(sum(delta)) < fabs(mean) * 1e-14:
        print("Minimization.py:223:", sum(delta), mean)

    sigma = sqrt(sum(delta ** 2) / (N * (N - 1)))
    sigmaSlope = sigma / sqrt(xx)

    print("b=%f   sigma=%f   sigma_b=%f" % (slope, sigma, sigmaSlope))
    return slope < -2.326348 * sigmaSlope

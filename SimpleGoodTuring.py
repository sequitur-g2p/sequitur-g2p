#!/usr/bin/env python

"""
Simple Good-Turing Frequency Estimator

Based on the C  implementation "SGT.c" by
Geoffrey Sampson, with help from Miles Dennis
School of Cognitive and Computing Sciences
University of Sussex, England
http://www.grs.u-net.com/
Revised release: 24 July 2000

Ported to Python by Maximilian Bisani
(bisani@informatik.rwth-aachen.de) on 23 July 2003
"""

from __future__ import division

__author__    = 'Maximilian Bisani'
__version__   = '$LastChangedRevision: 1668 $'
__date__      = '$LastChangedDate: 2007-06-02 18:14:47 +0200 (Sat, 02 Jun 2007) $'
__copyright__ = 'Copyright (c) 2004-2005  RWTH Aachen University'
__license__   = """
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
Foundation, Inc., 51 Franlin Street, Fifth Floor, Boston, MA 02110,
USA.
 
Should a provision of no. 9 and 10 of the GNU General Public License
be invalid or become invalid, a valid provision is deemed to have been
agreed upon which comes closest to what the parties intended
commercially. In any case guarantee/warranty shall be limited to gross
negligent actions or intended actions or fraudulent concealment.
"""

__all__ = [ 'simpleGoodTuring' ]


import math, operator, sys


def sum(l):
    return reduce(operator.add, l)


def findBestFit(data):
    meanX = sum([ x for x, y in data ]) / len(data)
    meanY = sum([ y for x, y in data ]) / len(data)
    XYs      = sum([ (x - meanX) * (y - meanY) for x, y in data ])
    Xsquares = sum([ (x - meanX) * (x - meanX) for x, y in data ])
    slope = XYs / Xsquares
    intercept = meanY - slope * meanX
    return slope, intercept


def zipfFit(data):
    """
    Takes a list of (count, count-of-count) pairs, and performs a
    linear least-squares fit in the log-log domain.  This meaningful
    under the assumtion that the rank-frequency relation follows a
    power law (known as Zipf's law).
    """
    data.sort()
    loglog = [ ]
    for j in range(len(data)):
	r, n = data[j]
	if j == 0:
	    r1 = 0
	else:
	    r1 = data[j - 1][0]
	if j == len(data) - 1:
	    r2 = (2 * r - r1)
	else:
	    r2 = data[j + 1][0]
	assert r1 < r2
	Z = 2.0 * n / (r2 - r1)
	loglog.append((math.log(r), math.log(Z)))

    slope, intercept = findBestFit(loglog)

    nSmoothed = lambda r: math.exp(intercept + slope * math.log(r))
    setattr(nSmoothed, 'alpha', slope)
    return nSmoothed


def simpleGoodTuring(data):
    """

    Takes a list of (count, count-count) pairs, and applies the
    "Simple Good-Turing" technique for estimating the probabilities
    corresponding to the observed frequencies, and P.0, the total
    probability of all unobserved species.  No checks are made for
    linearity; the program simply assumes that the requirements for
    using the SGT estimator are met.

    The result is a series of triples ( r, p(e|r), p(r) ), i.e. the
    observed frequency r (count), the estimated probability of any
    event with frequency r, and the estimated total probability of all
    events with frequency r.  In particular the first triple is (0,
    None, P.0).

    The "Simple Good-Turing" technique was devised by William A. Gale
    of AT&T Bell Labs, and described in Gale & Sampson, "Good-Turing
    Frequency Estimation Without Tears" (JOURNAL OF QUANTITATIVE
    LINGUISTICS, vol. 2, pp. 217-37 -- reprinted in Geoffrey Sampson,
    EMPIRICAL LINGUISTICS, Continuum, 2001).
    """

    data.sort()
    nr = dict(data)
    N = sum([ r * n for r, n in data ])
    PZero = nr[1] / N
    nSmoothed = zipfFit(data)

    rStar = []
    indiffValsSeen = False
    for r, n in data:
	y = (r + 1) * nSmoothed(r + 1) / nSmoothed(r)
	if not indiffValsSeen:
	    if (r + 1) in nr:
		next_n = nr[r + 1]
		x = (r + 1) * next_n / n
		if abs(x - y) <= 1.96 * math.sqrt(
		    (r + 1.0) * (r + 1.0)
		    * next_n / (n*n)
		    * (1.0 + next_n / n)):
		    indiffValsSeen = True
	    else:
		indiffValsSeen = True
	if indiffValsSeen:
	    rStar.append(y)
	else:
	    rStar.append(x)

    Nprime = sum([ n * rs for (r, n), rs in zip(data, rStar) ])

    result = [ (0, None, PZero, None) ]
    for (r, n), rs in zip(data, rStar):
	p = (1.0 - PZero) * rs / Nprime
	result.append( (r, p, p * n, rs) )

    return result


def main(args):
    data = sys.stdin
    data = [ line.split() for line in data ]
    data = [ tuple(fields) for fields in data if len(fields) == 2 ]
    data = [ (int(r), int(n)) for r, n in data ]
    sgt = simpleGoodTuring(data)
    for r, p, np, rStar in sgt:
	print r, p, np, rStar


if __name__ == '__main__':
    main(sys.argv[1:])

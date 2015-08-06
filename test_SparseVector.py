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

import unittest
from SparseVector import sparse, sumSparse
from misc import sorted
TestCase = unittest.TestCase


class SparseVectorTestCase(TestCase):
    def testEmpty(self):
	sv = sparse([])
	self.failUnlessEqual(sv.size, 0)
	for i in range(10):
	    self.failUnlessEqual(sv[i], 0)

    example = [
	( 7,  2.1),
	( 9,  2.7),
	( 1,  0.3),
	( 4,  1.0),
	( 0,  1.0),
	(12,  3.6),
	( 2,  0.7) ]

    def testSeven(self):
	sv = sparse(self.example)

	self.failUnlessEqual(sv.size, len(self.example))

	d = dict(self.example)
	for k in range(20):
	    self.failUnlessEqual(sv[k], d.get(k, 0))

    def testBadTypes(self):
	self.failUnlessRaises(TypeError, sparse, 'xxx')
	self.failUnlessRaises(TypeError, sparse, ['xxx'])
	self.failUnlessRaises(TypeError, sparse, [('xxx', 1.0)])
	self.failUnlessRaises(TypeError, sparse, [(1, 'xxx')])

    def testBadList(self):
	self.failUnlessRaises(ValueError, sparse, [(1, 0.1), (1, 0.2)])
	self.failUnlessRaises(ValueError, sparse, 2 * self.example)

    def testBool(self):
	self.failUnlessEqual(bool(sparse([])), False)
	self.failUnlessEqual(bool(sparse(self.example)), True)

    def testIter(self):
	sv = sparse(self.example)
	ref = sorted(self.example)
	for i, item in enumerate(sv):
	    self.failUnlessEqual(item, ref[i])

	sl = list(sv)
	self.failUnlessEqual(sl, ref)

    def testContains(self):
	sv = sparse(self.example)
	d = dict(self.example)
	for k in range(20):
	    self.failUnlessEqual(k in sv, k in d)

    def testDouble(self):
	sv1 = sparse(self.example)
	sv2 = sparse(self.example)
	sv = sv1 + sv2
	d = dict(self.example)
	for k in range(20):
	    self.failUnlessEqual(sv[k], 2 * d.get(k, 0))

    def dictAdd(self, a, b):
	result = dict(a)
	for k, v in b:
	    result[k] = result.get(k, 0) + v
	return sorted(result.items())

    def testAdd(self):
	sv = sparse(self.example)
	for x in [ [ (-100, 42) ], [], [(100, 42)], [(-100, 42), (100, 42)], [(0, 32)] ]:
	    self.failUnlessEqual(list(sv + sparse(x)), self.dictAdd(self.example, x))
	    self.failUnlessEqual(list(sparse(x) + sv), self.dictAdd(self.example, x))

    def testMul(self):
	sv = sparse(self.example)
	sv3 = sv * 3.0
	ref = sparse([ (k, v * 3) for k, v in self.example ])
	self.failUnlessEqual(sv3, ref)

    def testDiv(self):
	sv = sparse(self.example)
	sv3 = sv / 3.0
	ref = sparse([ (k, v / 3) for k, v in self.example ])
	self.failUnlessEqual(sv3, ref)

    def testSum(self):
	sv = sparse(self.example)
	self.failUnlessEqual(sv.sum(), sum(dict(self.example).values()))

    def testCopyByConstructor(self):
	sv1 = sparse(self.example)
	sv2 = sparse(sv1)
	self.failUnlessEqual(sv1, sv2)

    def testCopyByCopy(self):
	from copy import copy
	sv1 = sparse(self.example)
	sv2 = copy(sv1)
	self.failUnlessEqual(sv1, sv2)

    def testSumSparse(self):
	for m in range(5):
	    sv = sparse(self.example)
	    sv = sumSparse(m*[sv])
	    d = dict(self.example)
	    for k in range(20):
		self.failUnlessEqual(sv[k], m * d.get(k, 0))

    def testSumSparseTypeError(self):
	for obj in [ 5, None, () ]:
	    for nn in [2, 3, 4]:
		arg = nn * [obj]
		self.failUnlessRaises(TypeError, sumSparse, arg)

    def testThreshold(self):
	for t in [0.5, 1.0, 1.5, 2.0, 2.5]:
	    sv = sparse(self.example).threshold(t)
	    self.failUnlessEqual(list(sv), sorted(filter(lambda x: x[1]>=t, self.example)))


if __name__ == '__main__':
    unittest.main()

from __future__ import print_function
__author__    = 'Maximilian Bisani'
__version__   = '$LastChangedRevision: 1667 $'
__date__      = '$LastChangedDate: 2007-06-02 16:32:35 +0200 (Sat, 02 Jun 2007) $'
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
from SequenceModel import *


class SequenceModelEstimatorTestCase(unittest.TestCase):
    estimator = SequenceModelEstimator()

    def failUnlessNormalized(self, model, hists = ['A', 'B', 'C'], preds = ['X', 'Y', 'Z']):
        for u in hists:
            for v in hists:
                sum = 0.0
                for w in preds:
                    p = model((u, v), w)
#                   print u, v, w, p
                    sum += p
#               print u, v, sum
#               print
                self.failUnlessAlmostEqual(sum, 1.0)

    def testEmpty(self):
        evidence = []
        model = self.estimator.make(3, evidence, [0.0])
#       self.show(model)
#       self.failUnlessEqual(model, [])

    def testOne(self):
        evidence = [((), 'X', 1.0)]
        model = self.estimator.make(3, evidence, [0.1, 0.0])
#       self.show(model)

    def testTwo(self):
        evidence = [(('A', 'B'), 'X', 3.0),
                    (('C', 'B'), 'Y', 3.0)]
        model = self.estimator.make(3, evidence, [0.8, 1.0, 0.0])
#       self.show(model)
        self.failUnlessNormalized(model)
#       print model.perplexity(evidence)

    def show(sslf, model):
        for (history, predicted), probability in model:
            print(history, predicted, probability)


if __name__ == '__main__':
    unittest.main()

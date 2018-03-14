from __future__ import print_function
__author__    = 'Maximilian Bisani'
__version__   = '$LastChangedRevision: 1691 $'
__date__      = '$LastChangedDate: 2011-08-03 15:38:08 +0200 (Wed, 03 Aug 2011) $'
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
import math
from sequitur import *


class SequenceModelTestCase(unittest.TestCase):
    def testEmpty(self):
        sm = SequenceModel.SequenceModel()
        h = sm.initial()
        for t in range(10):
            self.failUnlessEqual(sm.advanced(h, t), h)
            self.failUnlessEqual(sm.probability(t, h), 0.0)

    def testZerogram(self):
        p = 0.1
        data = [((), None, - math.log(p))]
        sm = SequenceModel.SequenceModel()
        sm.setInitAndTerm(0, 0)
        sm.set(data)
        h = sm.initial()
        for t in range(10):
            self.failUnlessEqual(sm.advanced(h, t), h)
            self.failUnlessAlmostEqual(sm.probability(t, h), p)

    def testUnigram(self):
        probs = [ 0.2, 0.3, 0.5 ]
        data = [((), t+1, - math.log(p)) for t, p in enumerate(probs) ]
        sm = SequenceModel.SequenceModel()
        sm.setInitAndTerm(0, 0)
        sm.set(data)
        h = sm.initial()
        for t in range(1, 4):
            self.failUnlessEqual(sm.advanced(h, t), h)
            self.failUnlessAlmostEqual(sm.probability(t, h), probs[t-1])

    def testBigram(self):
        probs = [ 0.2, 0.3, 0.5 ]
        data = [((), t+1, - math.log(p)) for t, p in enumerate(probs) ]
        probs2 = [ 0.4, 0.1, 0.5 ]
        data += [((2,), t+1, - math.log(p)) for t, p in enumerate(probs2) ]
        sm = SequenceModel.SequenceModel()
        sm.setInitAndTerm(0, 0)
        sm.set(data)
        h = sm.initial()
        h2 = sm.advanced(h, 2)
        for t in range(1, 4):
            if t == 2:
                self.failUnlessEqual(sm.advanced(h, t), h2)
                self.failUnlessEqual(sm.advanced(h2, t), h2)
            else:
                self.failUnlessEqual(sm.advanced(h, t), h)
                self.failUnlessEqual(sm.advanced(h2, t), h)
            self.failUnlessAlmostEqual(sm.probability(t, h), probs[t-1])
            self.failUnlessAlmostEqual(sm.probability(t, h2), probs2[t-1])


class EstimatorTestCase(unittest.TestCase):
    def setUp(self):
        self.sequitur = Sequitur()

    def tearDown(self):
        del self.sequitur

    def obliviousModel(self, Q):
        result = SequenceModel.SequenceModel()
        result.setInitAndTerm(self.sequitur.term, self.sequitur.term)
        result.setZerogram(Q);
        return result

    def testNoData(self):
        sizeTemplates = [(1,1), (1,0), (0,1)]
        model = self.obliviousModel(1)
        sample = Sample(self.sequitur, sizeTemplates, EstimationGraphBuilder.emergeNewMultigrams, [], model)
        evidence, logLik = sample.evidence(model, useMaximumApproximation=False)
        evidence = evidence.asList()
        self.failUnlessEqual(evidence, [])

    def testMonograms(self):
        sizeTemplates = [(1,1), (1,0), (0,1)]
        model = self.obliviousModel(3)
        sample = [ ((c,), (c,)) for c in list('abc') ]
        sample = self.sequitur.compileSample(sample)
        sample = Sample(self.sequitur, sizeTemplates, EstimationGraphBuilder.emergeNewMultigrams, sample, model)
        evidence, logLik = sample.evidence(model, useMaximumApproximation=False)
        evidence = evidence.asList()
        for hist, seg, p in evidence:
            l, r = self.sequitur.symbol(seg)
            self.failUnless(len(l) in range(2))
            self.failUnless(len(r) in range(2))
            if l == ('__term__',) and r == ('__term__',):
                self.failUnlessAlmostEqual(p, 3.0)
            elif len(l) == 1 and len(r) == 1:
                self.failUnlessAlmostEqual(p, 0.6)
            else:
                self.failUnlessAlmostEqual(p, 0.4)

    def testAbcMonoGrams(self):
        return

        estm = self.makeEstimator(1.0/16.0)
        estm.setLengthConstraints(0, 1, 0, 1)
        estm.addSample(['a', 'b', 'c'], ['A', 'B', 'C'])
        evidence = estm.estimate()
        self.failUnlessEqual(len(evidence), (1+3)**2)
        for hist, (l, r), p in evidence:
            self.failUnless(len(l) in range(2))
            self.failUnless(len(r) in range(2))

    def testAbcDiGrams(self):
        return

        estm = self.makeEstimator(1.0/36.0)
        estm.setLengthConstraints(0, 2, 0, 2)
        estm.addSample(['a', 'b', 'c'], ['A', 'B', 'C'])
        evidence = estm.estimate()
        self.failUnlessEqual(len(evidence), (1+3+2)**2)
        for hist, (l, r), p in evidence:
            self.failUnless(len(l) in range(3))
            self.failUnless(len(r) in range(3))

    def testAbcTriGrams(self):
        return

        estm = self.makeEstimator(1.0/49.0)
        estm.setLengthConstraints(0, 3, 0, 3)
        estm.addSample(['a', 'b', 'c'], ['A', 'B', 'C'])
        for i in range(5):
            print('\n', i)
            evidence = estm.estimate()
            self.failUnlessEqual(len(evidence), (1+3+2+1)**2)
            evidence.sort(lambda a, b: cmp(a[-1], b[-1]))
            for hist, (l, r), p in evidence:
                self.failUnless(len(l) in range(4))
                self.failUnless(len(r) in range(4))
                print(l, r, p)
            estm.reestimate()


if __name__ == '__main__':
    unittest.main()

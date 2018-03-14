__author__    = 'Maximilian Bisani'
__version__   = '$LastChangedRevision: 11 $'
__date__      = '$LastChangedDate: 2005-04-06 11:15:33 +0200 (Wed, 06 Apr 2005) $'
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
import sys
import unittest
from mGramCounts import *
TestCase = unittest.TestCase

if sys.version_info[:2] >= (3, 0):
    xrange = range

class MGramsTestCase(TestCase):
    def templateTestX(self, mGramsFromX, events, order):
        iMgram = 0
        for mgram in mGramsFromX(events, order):
            self.failUnless(type(mgram) is tuple)
            self.failUnless(len(mgram) == 2)
            history, predicted = mgram
            self.failUnlessEqual(predicted, events[iMgram])
            self.failUnless(type(history) is tuple)
            self.failUnless((order is None) or (len(history) <= order))
            iMgram += 1
        self.failUnlessEqual(iMgram, len(events))

    def templateTest(self, length, order):
        self.templateTestX(mGramsFromIter,    xrange(length), order)
        self.templateTestX(mGramsFromSequence, range(length), order)

    def runTest(self):
        for length in range(20):
            for order in range(6):
                self.templateTest(length, order)
            self.templateTest(length, None)


if __name__ == '__main__':
    unittest.main()

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
from LanguageModel import *
from mGramCounts import *
TestCase = unittest.TestCase
import difflib, itertools, misc, StringIO


class EqualFile(StringIO.StringIO):
    def __init__(self, fname):
	StringIO.StringIO.__init__(self)
	self.reference = gOpenIn(fname).read()
	self.data = None

    def close(self):
	self.data = self.getvalue()
	StringIO.StringIO.close(self)

    def __nonzero__(self):
	if self.data is None:
	    self.data = self.getvalue()
	if self.data == self.reference:
	    return True
	else:
	    self.diff()
	    return False

    def diff(self):
	if self.data is None:
	    self.data = self.getvalue()
	diff = difflib.unified_diff(
	    self.reference.split('\n'),
	    self.data.split('\n'))
	for line in diff:
	    print >> sys.stderr, line


class MGramCountTestCase(TestCase):
    """
    regenerate reference data:
    mGramCounts.py --text tests/nab-mini-corpus.txt.gz
		   --write tests/nab-mini-corpus.raw-counts.gz
		   --counts-of-counts tests/nab-mini-corpus.raw-coc

    mGramCounts.py --text tests/nab-mini-corpus.txt.gz
		   --vocab tests/nab-5k-vocabulary.txt.gz
		   --write tests/nab-mini-corpus.mapped-counts.gz
    """

    def testLoadVocabulary(self):
	vocabulary = loadVocabulary('tests/nab-5k-vocabulary.txt.gz')
	self.failUnlessEqual(vocabulary.size(), 4990)

    order = 2

    def templateTestRawCounts(self, StorageClass):
	text = misc.gOpenIn('tests/nab-mini-corpus.txt.gz')
	sentences = itertools.imap(str.split, text)
	grams = mGramsChainCount(sentences, self.order)
	counts = StorageClass()
	counts.addIter(grams)

	f = EqualFile('tests/nab-mini-corpus.raw-counts.gz')
	TextStorage.write(f, counts)
	self.failUnless(f)

    def templateTestMappedCounts(self, StorageClass):
	vocabulary = loadVocabulary('tests/nab-5k-vocabulary.txt.gz')
	text = misc.gOpenIn('tests/nab-mini-corpus.txt.gz')
	sentences = itertools.imap(str.split, text)
	sentences = itertools.imap(lambda s: map(vocabulary.map, s), sentences)
	grams = mGramsChainCount(sentences, self.order)
	counts = StorageClass()
	counts.addIter(grams)

	f = EqualFile('tests/nab-mini-corpus.mapped-counts.gz')
	TextStorage.write(f, counts)
	self.failUnless(f)

    def testCoutsOfCounts(self):
	counts = TextStorage('tests/nab-mini-corpus.raw-counts.gz')
	coc = [ mGramCounts.countsOfCounts(mGramReduceToOrder(counts, order))
		for order in range(self.order) ]
	reference = eval(open('tests/nab-mini-corpus.raw-coc').read())
	for order in range(self.order):
	    self.failUnlessEqual(coc[order], reference[order])

for StorageClass in [DictStorage, ListStorage, SimpleMultifileStorage, BiHeapMultifileStorage]:
    def testRawCounts(self, StorageClass=StorageClass):
	return self.templateTestRawCounts(StorageClass)
    def testMappedCounts(self, StorageClass=StorageClass):
	return self.templateTestMappedCounts(StorageClass)
    setattr(MGramCountTestCase, 'testRawCountsWith'    + StorageClass.__name__, testRawCounts)
    setattr(MGramCountTestCase, 'testMappedCountsWith' + StorageClass.__name__, testMappedCounts)


class LanguageModelTestCase(TestCase):
    """
    regenerate reference data:
    LanguageModel.py --read tests/nab-mini-corpus.mapped-counts.gz
		     --vocab tests/nab-5k-vocabulary.txt.gz
		     --counts-of-counts tests/nab-mini-corpus.raw-coc
		     --order 1
		     --lm tests/nab-mini-corpus.unigram.lm.gz

    LanguageModel.py --read tests/nab-mini-corpus.mapped-counts.gz
		     --vocabulary tests/nab-5k-vocabulary.txt.gz
		     --counts-of-counts tests/nab-mini-corpus.raw-coc
		     --order 3
		     --lm tests/nab-mini-corpus.trigram.lm.gz
    """

    order = 3
    def setUp(self):
	self.vocabulary = loadVocabulary('tests/nab-5k-vocabulary.txt.gz')
	self.counts = loadCounts('tests/nab-mini-corpus.mapped-counts.gz', self.vocabulary)
	self.coc = eval(open('tests/nab-mini-corpus.raw-coc').read())
	self.builder = LanguageModelBuilder()
	self.builder.setVocabulary(self.vocabulary)

    def testUnigram(self):
	self.builder.setHighestOrder(0)
	self.builder.estimateDiscounts(self.coc)
	f = EqualFile('tests/nab-mini-corpus.unigram.lm.gz')
	lm = LmArpaWriter(f, 0)
	self.builder.build(self.counts, lm)
	self.failUnless(f)

    def testTrigram(self):
	self.builder.setHighestOrder(2)
	self.builder.estimateDiscounts(self.coc)
	f = EqualFile('tests/nab-mini-corpus.trigram.lm.gz')
	lm = LmArpaWriter(f, 2)
	self.builder.build(self.counts, lm)
	self.failUnless(f)


if __name__ == '__main__':
    unittest.main()

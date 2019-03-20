#!/usr/bin/env python

"""
Monotonous Machine Translation
"""

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
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110,
USA.
 
Should a provision of no. 9 and 10 of the GNU General Public License
be invalid or become invalid, a valid provision is deemed to have been
agreed upon which comes closest to what the parties intended
commercially. In any case guarantee/warranty shall be limited to gross
negligent actions or intended actions or fraudulent concealment.
"""

from sets import Set
from misc import gopen
from sequitur import Translator
import sys, SequiturTool

# ===========================================================================
def loadSample(compfname):
    fnames = compfname.split(':')
    assert len(fnames) == 2
    left  = gopen(fnames[0])
    right = gopen(fnames[1])
    sample = []
    for a, b in zip(left, right):
	sample.append((a.split(), b.split()))
    return sample


def addUnknowns(model, words):
    knownWords = Set(model.sequitur.leftInventory.list)
    unknownWords = words - knownWords
    for word in unknownWords:
	i = model.sequitur.index((word,), (word,))
    print >> sys.stderr, '%d unknown words added to model' % len(unknownWords)

# ===========================================================================
def main(options, args):
    model = SequiturTool.procureModel(options, loadSample)
    if options.applySample:
	lines = gopen(options.applySample).readlines()
	words = Set([ word for line in lines for word in line.split() ])
	addUnknowns(model, words)
	translator = Translator(model)
	for line in lines:
	    left = tuple(line.split())
	    try:
		result = translator(left)
		print ' '.join(result)
	    except translator.TranslationFailure:
		print '<translation-failed/>'

# ===========================================================================
if __name__ == '__main__':
    import optparse, tool
    optparser = optparse.OptionParser(
	usage   = '%prog [OPTION]... FILE...\n' + __doc__,
	version = '%prog ' + __version__)
    SequiturTool.addOptions(optparser)
    tool.addTrainOptions(optparser)
    optparser.add_option(
	'-a', '--apply', dest='applySample',
	help='apply translation to sentences read from FILE', metavar='FILE')
    options, args = optparser.parse_args()

    tool.run(main, options, args)

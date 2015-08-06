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

import marshal, os
from mGramCounts import AbstractFileStorage

class StoredCounts(AbstractFileStorage):
    def write(self, seq):
	file = os.popen('gzip -fc >%s' % self.fname, 'wb')
	for history, values in seq:
	    marshal.dump(history, file)
	    SparseVector.dump(values, file)
	file.close()

    def __iter__(self):
	file = os.popen('gzip -dc %s' % self.fname, 'rb')
	while True:
	    try:
		history = marshal.load(file)
		values = SparseVector.load(file)
		yield (history, values)
	    except EOFError:
		break
	file.close()

def store(seq, big=False, filename=None):
    if big:
	s = StoredCounts(filename)
	s.write(seq)
	return s
    else:
	return list(seq)


from misc import restartable
import SparseVector
Counts = SparseVector.sparse
sumCounts = SparseVector.sumSparse

class NonMonotonousHistoriesError(RuntimeError):
    pass

def contract(seq):
    it = iter(seq)
    (history, predicted), value = it.next()
    values = [(predicted, value)]
    for (h, p), v in it:
	if h != history:
	    if h < history:
		raise NonMonotonousHistoriesError(history, h)
	    yield history, Counts(values)
	    history = h
	    values = []
	values.append((p, v))
    yield history, Counts(values)
contract = restartable(contract)

class CountsAccumulator(object):
    def __init__(self):
	self.terms = [ [], [], [] ]

    def set(self, initial = None):
	self.terms = [ [initial], [], [] ]

    def shrink(self):
	for i in range(3):
	    if len(self.terms[i]) < 64:
		break
	    s = sumCounts(self.terms[i])
	    try:
		self.terms[i+1].append(s)
		self.terms[i] = []
	    except IndexError:
		self.terms[i] = [s]

    def __iadd__(self, counts):
	self.terms[0].append(counts)
	if len(self.terms[0]) > 64:
	    self.shrink()
	return self

    def sum(self):
	return sumCounts([ t for ts in self.terms for t in ts ])

def sumLotsOfCounts(counts):
    accu = CountsAccumulator()
    for c in counts:
	accu += c
    return accu.sum()

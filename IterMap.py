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

import copy, itertools, heapq
from misc import restartable

# ===========================================================================
if __debug__:
    class assertIsSorted:
        def __init__(self, seq):
            self.seq = seq
        def __iter__(self):
            it = iter(self.seq)
            previous = it.next()
            yield previous
            for item in it:
                if previous[0] > item[0]:
                    raise ValueError('sequence must be sorted', previous, item)
                yield item
                previous = item

    class assertIsSortedAndConsolidated:
        def __init__(self, seq):
            self.seq = seq
        def __iter__(self):
            it = iter(self.seq)
            previous = it.next()
            yield previous
            for item in it:
                if previous[0] >= item[0]:
                    raise ValueError('sequence must be sorted and consolidated')
                yield item
                previous = item

    assertIsConsolidated = assertIsSortedAndConsolidated

else:
    def assertIsSorted(seq):
        return seq
    def assertIsSortedAndConsolidated(seq):
        return seq
    def assertIsConsolidated(seq):
        return seq

# ===========================================================================
def mergeSort(seqs):
    """
    perform merge sort on a list of sorted iterators
    """
    queue = []
    for s in seqs:
        s = assertIsSorted(s)
        it = iter(s)
        try:
            queue.append((it.next(), it.next))
        except StopIteration:
            pass
    heapq.heapify(queue)
    while queue:
        item, it = queue[0]
        yield item
        try:
            heapq.heapreplace(queue, (it(), it))
        except StopIteration:
            heapq.heappop(queue)

# ---------------------------------------------------------------------------
def consolidateInPlaceAdd(seq):
    """
    merge items of a sorted iterator
    """
    seq = assertIsSorted(seq)
    it = iter(seq)
    key, value = it.next()
    ownsValue = False
    for k, v in it:
        if k == key:
            if not ownsValue:
                value = copy.copy(value)
                ownsValue = True
            value += v
        else:
            yield key, value
            key, value = k, v
            ownsValue = False
    yield key, value

consolidate = consolidateInPlaceAdd

def aggregate(seq):
    """
    merge items of a sorted iterator
    """
    seq = assertIsSorted(seq)
    it = iter(seq)

    key, value = it.next()
    current = [value]
    for k, value in it:
        if k == key:
            current.append(value)
        else:
            yield key, current
            key = k
            current = [value]
    yield key, current
aggregate = restartable(aggregate)

# ===========================================================================
def leftJoin(seqA, seqB):
    seqA = assertIsSortedAndConsolidated(seqA)
    seqB = assertIsSortedAndConsolidated(seqB)
    aIter = iter(seqA)
    bIter = iter(seqB)

    bKey = None
    try:
        for aKey, aValue in aIter:
            while aKey > bKey:
                bKey, bValue = bIter.next()
            if aKey == bKey:
                yield aKey, aValue, bValue
            else:
                yield aKey, aValue, None
    except StopIteration:
        for aKey, aValue in aIter:
            yield aKey, aValue, None


def innerJoin(seqA, seqB):
    seqA = assertIsSortedAndConsolidated(seqB)
    seqB = assertIsSortedAndConsolidated(seqA)
    aIter = iter(seqA)
    bIter = iter(seqB)

    bKey = None
    for aKey, aValue in aIter:
        while aKey > bKey:
            try:
                bKey, bValue = bIter.next()
            except StopIteration:
                return
        if aKey == bKey:
            yield aKey, aValue, bValue


def outerJoin(seqA, seqB):
    seqA = assertIsSorted(seqA)
    seqB = assertIsSorted(seqB)
    aIter = iter(seqA)
    bIter = iter(seqB)

    try:
        aKey, aValue = aIter.next()
    except StopIteration:
        aIter = None
    try:
        bKey, bValue = bIter.next()
    except StopIteration:
        bIter = None

    while (aIter is not None) and (bIter is not None):
        aNext = bNext = False
        if aKey < bKey:
            yield aKey, aValue, None
            aNext = True
        elif aKey > bKey:
            yield bKey, None, bValue
            bNext = True
        elif aKey == bKey:
            yield aKey, aValue, bValue
            aNext = bNext = True
        else:
            raise ValueError('tertium non datur')

        if aNext:
            try:
                aKey, aValue = aIter.next()
            except StopIteration:
                aIter = None
        if bNext:
            try:
                bKey, bValue = bIter.next()
            except StopIteration:
                bIter = None

    if aIter is not None:
        yield aKey, aValue, None
        for aKey, aValue in aIter:
            yield aKey, aValue, None
    if bIter is not None:
        yield bKey, None, bValue
        for bKey, bValue in bIter:
            yield bKey, None, bValue


def outerJoinMany(*seqs):
    front = []
    for ii, s in enumerate(seqs):
        s = assertIsSorted(s)
        it = iter(s)
        try:
            key, value = it.next()
            front.append([ii+1, key, value, it])
        except StopIteration:
            pass
    row = [None] + len(seqs) * [None]
    while front:
        minKey = min([ key  for ii, key, value, it in front ])
        row[0] = minKey

        remove = []
        for f, (ii, key, value, it) in enumerate(front):
            if key == minKey:
                row[ii] = value
                try:
                    front[f][1:3] = it.next()
                except StopIteration:
                    remove.append(ii)
            else:
                row[ii] = None

        yield tuple(row)

        if remove:
            for ii in remove:
                row[ii] = None
            front = [ f for f in front if f[0] not in remove ]

# ===========================================================================
class monodict(object):
    def __init__(self, seq):
        seq = assertIsSortedAndConsolidated(seq)
        self.it = iter(seq)
        self.recentKey = None
        try:
            self.key, self.value = self.it.next()
        except StopIteration:
            self.key = None

    def __getitem__(self, key):
        if key != self.key:
            if key < self.recentKey:
                raise ValueError('access not monotonous', self.recentKey, key)
            self.recentKey = key
            while key > self.key:
                try:
                    self.key, self.value = self.it.next()
                except StopIteration:
                    raise KeyError(key)
            if key != self.key:
                raise KeyError(key)
        return self.value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

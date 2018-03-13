#!/usr/bin/env python

"""
example usage:
  python -O mGramCounts.py
  --text /u/corpora/language/wsj/NAB-training-corpus.gz
  --order 4 --sort
  --write /work/bisani/NAB-4gram.counts.gz
  --memory-limit 5000000 --tempdir /var/tmp/

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

import itertools
import sys
from misc import set, sorted

if sys.version_info[:2] >= (3, 0):
    xrange = range

# ===========================================================================
from IterMap import mergeSort, aggregate, consolidate, assertIsConsolidated, \
                    assertIsSortedAndConsolidated

class Storage(object):
    """
    hasRandomAccess - supports __getitem__()
    isMutable       - supports add()
    isConsolidated  - obtaining an consolidated iterator is cheap
    """

    def size(self):
        "Total number of items."
        raise NotImplementedError

    def add(self, key, value):
        raise NotImplementedError

    def addIter(self, it):
        for item in it:
            self.add(*item)

    def iter(self, sorted, consolidated):
        raise NotImplementedError

    def __iter__(self):
        return self.iter()

    def __getitem__(self, key):
        raise NotImplementedError

    def set(self, other):
        "Copy contents of other storage."
        raise NotImplementedError


class DictStorage(Storage):
    hasRandomAccess = True
    isMutable       = True
    isConsolidated  = True

    def __init__(self):
        self.items = {}

    def set(self, other):
        self.items = dict(other.iter(consolidated=True))

    def size(self):
        return len(self.items)

    def add(self, key, value):
        self.items[key] = self.items.get(key, 0) + value

    def iter(self, sorted=False, consolidated=True):
        if sorted:
            items = self.items.items()
            items.sort()
            return iter(items)
        else:
            return self.items.iteritems()

    def __getitem__(self, key):
        return self.items.get(key)


class ListStorage(Storage):
    hasRandomAccess = False
    isMutable       = True

    def __init__(self):
        self.items = []
        self.isSorted = True
        self.isConsolidated = True

    def set(self, other):
        self.items = list(other.iter())
        self.isSorted = False
        self.isConsolidated = False

    def size(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def add(self, key, value):
        self.items.append((key, value))
        self.isSorted = False
        self.isConsolidated = False

    def sort(self):
        if not self.isSorted:
            self.items.sort()
        self.isSorted = True

    def consolidate(self):
        if not self.isConsolidated:
            self.sort()
            self.items = consolidate(self.items)
        self.isConsolidated = True

    def iter(self, sorted=False, consolidated=False):
        if sorted: self.sort()
        if consolidated: self.consolidate()
        return iter(self.items)

# ===========================================================================
import marshal, os, tempfile

class FileWriter(object):
    def __init__(self, fname):
        self.fname = fname
        self.f = os.popen('gzip -fc >%s' % self.fname, 'wb')
        self.n = 0

    def write(self, item):
        marshal.dump(item, self.f)
        self.n += 1

    def close(self):
        self.f.close()
        self.f = None

    def __del__(self):
        assert self.f is None

def writeToFile(fname, items):
    w = FileWriter(fname)
    for item in items:
        w.write(item)
    w.close()
    return w.n


class FileReader(object):
    def __init__(self, fname):
        self.fname = fname

    def __iter__(self):
        f = os.popen('gzip -dc %s' % self.fname, 'rb')
        while True:
            try:
                yield marshal.load(f)
            except EOFError:
                break
        f.close()


class AbstractFileStorage(object):
    def __init__(self, fname = None):
        self.isTemporary = fname is None
        if self.isTemporary:
            self.fname = tempfile.mkstemp('counts')[1]
        else:
            self.fname = fname

    def __del__(self):
        if self.isTemporary:
            os.unlink(self.fname)

# ===========================================================================
class FileStorage(Storage, AbstractFileStorage):
    hasRandomAccess = False
    isMutable       = False
    isConsolidated  = True

    def set(self, other):
        writeToFile(self.fname, other.iter(sorted=True, consolidated=True))

    def iter(self, sorted=True, consolidated=True):
        return iter(FileReader(self.fname))


class AbstractMultifileStorage(Storage):
    hasRandomAccess = False
    isMutable       = True
    isConsolidated  = False

    inMemoryLimit = 10 ** 6

    def __init__(self, dir=None):
        self.dir = tempfile.mkdtemp(dir=dir)
        self.files = []
        self.nStoredItems = 0

    def setMemoryLimit(self, limit):
        self.inMemoryLimit = limit

    def clearFiles(self):
        for fname in self.files:
            os.unlink(fname)
        self.files = []
        self.nStoredItems = 0

    def __del__(self):
        for fname in self.files:
            os.unlink(fname)
        os.rmdir(self.dir)

    def newFile(self):
        fname = os.path.join(self.dir, str(len(self.files)).zfill(8))
        self.files.append(fname)
        return fname

    def flush(self):
        raise NotImplementedError

    def iter(self, sorted=False, consolidated=False):
        self.flush()
        iters = [ FileReader(fname) for fname in self.files ]
        if sorted or consolidated:
            return consolidate(mergeSort(iters))
        else:
            return itertools.chain(*iters)


class SimpleMultifileStorage(AbstractMultifileStorage):
    def __init__(self, dir=None):
        super(SimpleMultifileStorage, self).__init__(dir)
        self.current = []

    def clear(self):
        self.clearFiles()
        self.current = []

    def size(self):
        return self.nStoredItems + len(self.current)

    def store(self, iter):
        n = writeToFile(self.newFile(), iter)
        self.nStoredItems += n

    def set(self, other):
        self.clear()
        self.store(other.iter(sorted=True, consolidated=True))

    def flush(self):
        if len(self.current) == 0: return
        self.current.sort()
        self.store(consolidate(self.current))
        self.current = []

    def add(self, key, value):
        self.current.append((key, value))
        if len(self.current) > self.inMemoryLimit:
            self.flush()


from heapq import heappush, heappop, heapreplace

class BiHeapMultifileStorage(AbstractMultifileStorage):
    def __init__(self, dir=None):
        super(BiHeapMultifileStorage, self).__init__(dir)
        self.primary   = []
        self.secondary = []
        self.currentFile = None
        self.isUnderfull = True

    def __del__(self):
        if self.currentFile:
            self.currentFile.close()

    def setMemoryLimit(self, limit):
        self.inMemoryLimit = limit

    def clear(self):
        self.clearFiles()
        self.primary   = []
        self.secondary = []
        self.currentFile = None
        self.isUnderfull = True

    def size(self):
        return self.nStoredItems + len(self.primary) + len(self.secondary)

    def add(self, key, value):
        if self.isUnderfull:
            if len(self.primary) < self.inMemoryLimit:
                heappush(self.primary, (key, value))
                return
            else:
                self.isUnderfull = False
                assert self.currentFile is None
                self.currentFile = FileWriter(self.newFile())

        if key < self.primary[0][0]:
            heappush(self.secondary, (key, value))
            key, value = heappop(self.primary)
        else:
            key, value = heapreplace(self.primary, (key, value))

        while self.primary and self.primary[0][0] == key:
            value += heappop(self.primary)[1]
        self.currentFile.write((key, value))
        self.nStoredItems += 1

        if not self.primary:
            self.primary = self.secondary
            self.secondary = []
            self.currentFile.close()
            self.currentFile = None
            self.isUnderfull = True

    def flush(self):
        if self.primary:
            if self.currentFile is None:
                self.currentFile = FileWriter(self.newFile())
            self.primary.sort()
            for item in consolidate(self.primary):
                self.currentFile.write(item)
                self.nStoredItems += 1
        if self.currentFile:
            self.currentFile.close()
            self.currentFile = None
        self.primary = []

        if self.secondary:
            self.secondary.sort()
            self.nStoredItems += writeToFile(self.newFile(), consolidate(self.secondary))
        self.secondary = []

        self.isUnderfull = True

# ---------------------------------------------------------------------------
from misc import gOpenIn, gOpenOut

class TextStorage(Storage, AbstractFileStorage):
    """
    Write counts as plain text file.  Each line contains an n-gram and
    its count.  The n-grams are represented in *natural* order,
    i.e. words are read from left to right, the predicted event being
    in final position.  The n-grams are listed in *canonical* order,
    i.e. they are sorted first by history, then by predicted token,
    and histories are ordered lexicographically recent-most first.
    """

    hasRandomAccess = False
    isMutable       = False
    isConsolidated  = True

    def __init__(self, fname = None, inputConversion = None, outputConversion = None):
        super(TextStorage, self).__init__(fname)
        self.inputConversion = inputConversion
        self.outputConversion = outputConversion
        self.value = int

    def write(cls, file, counts, conv=None):
        it = counts.iter(consolidated = True, sorted = True)
        for (history, predicted), value in it:
            mGram = map(conv, (predicted,) + history)
            mGram.reverse()
            print >> file, '%s\t%s' % (' '.join(mGram), value)
    write = classmethod(write)

    def set(self, other):
        file = gOpenOut(self.fname)
        self.write(file, othe, self.outputConversion)
        file.close()

    def iter(self, sorted=True, consolidated=True):
        for line in gOpenIn(self.fname):
            fields = line.split()
            mGram = map(self.inputConversion, fields[:-1])
            mGram.reverse()
            item = (tuple(mGram[1:]), mGram[0])
            value = self.value(fields[-1])
            yield item, value

# ===========================================================================
def mGramsFromIter(sequence, order):
    """
    For a sequence w_1 ... w_n return a sequence of pairs:
    ((),         w_1),
    ((w_1,),     w_2),
    ((w_2, w_1), w_3), ...
       ... ((w_{i-1}, ..., w_{i-order}), w_i) ...
       ... ((w_{n-1}, ..., w_{n-order}), w_n)
    Notes:
    * The number of tuples returned equals the length of the sequences
    * The first element  of the pair (history) is a tuple of length <order> (or less)
    * The second element of the pair (predicted) is the "recent-most" item of sequence.
    * The history tuple is in "recent-most first" order
    * When order is None, history contains all previous events (potentially infinite order)
    """
    history = ()
    for predicted in sequence:
        yield history, predicted
        history = ((predicted,) + history)[:order]

def mGramsFromSequence(sequence, order):
    if order is None:
        order = len(sequence)
    for i in xrange(len(sequence)):
        history = list(sequence[max(0, i - order) : i])
        history.reverse()
        history = tuple(history)
        yield history, sequence[i]

def countsFromSequence(sequence, order, value=1):
    counts = DictStorage()
    for gv in mGramsFromSequence(sequence, order):
        counts.add(gv, value)
    return counts

def mGramsChainCount(sequences, order, value=1):
    for sequence in sequences:
        for gv in mGramsFromIter(sequence, order):
            yield gv, value

def countsFromSequences(sequences, order, storageClass = DictStorage):
    grams = mGramsChainCount(sequences, order)
    counts = storageClass()
    counts.addIter(grams)
    return counts

def countsFromSequencesWithCounts(sequences, order, storageClass = DictStorage):
    def grams():
        for sequence, count in sequences:
            for gv in mGramsFromIter(sequence, order):
                yield gv, count
    counts = storageClass()
    counts.addIter(grams())
    return counts

# ---------------------------------------------------------------------------
class MapUnknownsFilter(object):
    def __init__(self, counts, knowns, unknown):
        self.counts = counts
        self.knowns = dict([(w, w) for w in knowns])
        self.unknown = unknown
        self.store = None

    def rawIter(self):
        for (history, predicted), value in self.counts:
            predicted = self.knowns.get(predicted, self.unknown)
            history = tuple([self.knowns.get(w, self.unknown) for w in history])
            yield (history, predicted), value

    def __iter__(self):
        if self.store is None:
            self.store = MGramCounts(DictStorage)
            self.store.addIter(self.rawIter())
        return self.store.iter(sorted=True, consolidated=True)

def mapUnknowns(counts, knowns, unknown='[UNKNOWN]'):
    return MapUnknownsFilter(counts, knowns, unknown)

# ---------------------------------------------------------------------------
class MGramReduceToOrderFilter(object):
    def __init__(self, counts, order):
        self.counts = counts
        self.order = order

    def rawIter(self):
        for (history, predicted), value in self.counts:
            if len(history) >= self.order:
                yield (history[:self.order], predicted), value

    def __iter__(self):
        it = iter(self.rawIter())
        (history, predicted), value = it.next()
        values = { predicted: value }
        for (h, p), v in it:
            if h == history:
                values[p] = values.get(p, 0) + v
            elif h > history:
                for predicted, value in sorted(values.iteritems()):
                    yield (history, predicted), value
                history = h
                values = { p: v }
            else:
                raise ValueError('sequence not ordered', history, h)
        for predicted, value in sorted(values.iteritems()):
            yield (history, predicted), value

def mGramReduceToOrder(counts, order):
    return MGramReduceToOrderFilter(counts, order)

# ---------------------------------------------------------------------------
def countsOfCounts(counts, group = None):
    histogram = {}
    counts = assertIsConsolidated(counts)
    for gram, count in counts:
        cat = group and group(count) or count
        try:
            histogram[cat] += 1
        except KeyError:
            histogram[cat] = 1
    result = sorted(histogram.items())
    return result

# ===========================================================================
class Vocabulary(object):
    noneIndex = 0

    def symbol(self, ind):
        return self.list[ind]

    def map(self, sym):
        return self.symbol(self.index(sym))

    def size(self):
        return len(self.list)

    def __iter__(self):
        return iter(self.list)

    def indices(self):
        return xrange(len(self.list))


class OpenVocabulary(Vocabulary):
    def __init__(self):
        self.list = [None]
        self.dir  = {None: self.noneIndex}

    def index(self, sym):
        try:
            return self.dir[sym]
        except KeyError:
            result = self.dir[sym] = len(self.list)
            self.list.append(sym)
            return result

class ClosedVocablary(Vocabulary):
    noneIndex = 0
    unknownIndex = 1
    unknownSymbol = '[UNKNOWN]'

    def __init__(self):
        self.list = [None, self.unknownSymbol]
        self.dir  = {None:               self.noneIndex,
                     self.unknownSymbol: self.unknownIndex}

    def index(self, sym):
        try:
            return self.dir[sym]
        except KeyError:
            return self.unknownIndex

    def addSym(self, sym, soft=False):
        if soft and sym in self.dir: return
        assert sym not in self.dir
        self.dir[sym] = len(self.list)
        self.list.append(sym)

    def add(self, syms, soft=False):
        for s in syms: self.addSym(s, soft)

    def sort(self):
        self.list.sort()
        self.dir = dict([(s, i) for i, s in enumerate(self.list)])
        self.noneIndex = self.dir[None]
        self.unknownIndex = self.dir[self.unknownSymbol]


def loadVocabulary(fname):
    vocabulary = ClosedVocablary()
    vocabulary.add(['<s>', '</s>'])
    vocabulary.add([ line.strip() for line in gOpenIn(fname) ], soft=True)
    vocabulary.sort()
    return vocabulary

# ===========================================================================
import sys, misc

def createStorage(options):
    storageClass = {
        'list': ListStorage,
        'dict': DictStorage,
        'smf' : SimpleMultifileStorage,
        'bhmf': BiHeapMultifileStorage }[options.storage_class]
    counts = storageClass()
    if options.memory_limit:
        counts.setMemoryLimit(options.memory_limit)
    return counts

def main(options, args):
    if options.vocabulary:
        vocabulary = loadVocabulary(options.vocabulary)
    else:
        vocabulary = OpenVocabulary()

    if options.text:
        text = misc.gOpenIn(options.text)
        sentences = itertools.imap(str.split, text)
        sentences = itertools.imap(lambda s: map(vocabulary.map, s), sentences)
        grams = mGramsChainCount(sentences, options.order - 1)
        counts = createStorage(options)
        counts.addIter(grams)
    elif options.read:
        if len(options.read) > 1:
            counts = createStorage(options)
            counts.addIter(consolidate(mergeSort(
                [ TextStorage(fname) for fname in options.read ])))
        else:
            counts = TextStorage(options.read[0])
    else:
        print >> sys.stderr, 'no counts'
        return

    if options.map_oov:
        if not options.vocabulary:
            print >> sys.stderr, 'you need to specify a vocabulary'
        filt = MapUnknownsFilter(counts, vocabulary.list, vocabulary.unknownSymbol)
        mappedCounts = createStorage(options)
        mappedCounts.addIter(filt.rawIter())
        counts = mappedCounts

    if options.write:
        countFile = misc.gOpenOut(options.write)
        TextStorage.write(countFile, counts)

    if options.counts_of_counts:
        coc = [ countsOfCounts(mGramReduceToOrder(counts, order))
                for order in range(options.order) ]
        import pprint
        pprint.pprint(coc, misc.gOpenOut(options.counts_of_counts))


if __name__ == '__main__':
    import optparse, tool
    options = optparse.OptionParser()
    tool.addOptions(options)
    options.add_option('-t', '--text')
    options.add_option('-r', '--read', action='append')
    options.add_option('-v', '--vocabulary')
    options.add_option('-M', '--order', type='int', default=3)
    options.add_option('-w', '--write')
    options.add_option('--map-oov', action='store_true')
    options.add_option('-C', '--counts-of-counts')

    options.add_option('--storage-class', default='smf')
    options.add_option('--memory-limit', type='int')

    options, args = options.parse_args()
    tool.run(main, options, args)

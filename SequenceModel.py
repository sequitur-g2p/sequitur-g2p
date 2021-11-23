from __future__ import division
from __future__ import print_function

__author__ = "Maximilian Bisani"
__version__ = "$LastChangedRevision: 1668 $"
__date__ = "$LastChangedDate: 2007-06-02 18:14:47 +0200 (Sat, 02 Jun 2007) $"
__copyright__ = "Copyright (c) 2004-2005  RWTH Aachen University"
__license__ = """
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

import copy, math
from misc import set
import sequitur_


class AccuDict(dict):
    def __getitem__(self, key):
        return self.get(key, 0)


class EvidenceList:
    def __init__(self, evidence=None):
        if evidence is None:
            self.evidence = []
        else:
            self.evidence = evidence

    def __repr__(self):
        return repr(self.evidence)

    def __iter__(self):
        return self.evidence.__iter__()

    def add(self, history, predicted, value):
        if value > 0.0:
            self.evidence.append((history, predicted, value))
        elif value != 0.0:
            raise AssertionError(history, predicted, value)

    def addList(self, other):
        self.evidence += other.evidence
        self.consolidate()

    def consolidate(self):
        self.evidence.sort()
        out = 0
        for i in range(1, len(self.evidence)):
            if self.evidence[i][:2] == self.evidence[out][:2]:
                history, predicted, value = self.evidence[out]
                value += self.evidence[i][2]
                self.evidence[out] = history, predicted, value
            else:
                out += 1
                self.evidence[out] = self.evidence[i]
        del self.evidence[out + 1 :]

    def discount(self, discount):
        discounted = EvidenceList()
        backOff = EvidenceList()
        for history, predicted, value in self.evidence:
            if history:
                shorterHistory = history[1:]
                if value > discount:
                    discounted.add(history, predicted, value - discount)
                    backOff.add(shorterHistory, predicted, discount)
                else:
                    backOff.add(shorterHistory, predicted, value)
            else:
                if value > discount:
                    discounted.add(history, predicted, value - discount)
                    backOff.add(None, None, discount)
                else:
                    backOff.add(None, None, value)
        discounted.consolidate()
        backOff.consolidate()
        return discounted, backOff

    def grouped(self):
        result = {}
        for history, predicted, value in self.evidence:
            if history in result:
                result[history].append((predicted, value))
            else:
                result[history] = [(predicted, value)]
        return result

    def groupedSums(self):
        result = AccuDict()
        for history, predicted, value in self.evidence:
            result[history] += value
        return result


class BackOffModel:
    def __init__(self):
        self.prob = {}
        self.compiled = None

    def __getstate__(self):
        self.compiled = None
        return self.__dict__

    def size(self):
        return len(self.prob)

    def __call__(self, history, predicted):
        backOffWeight = 1.0
        while True:
            if (history, predicted) in self.prob:
                return backOffWeight * self.prob[(history, predicted)]
            backOffWeight *= self.prob.get((history, None), 1.0)
            if history:
                history = history[1:]
            else:
                break
        return backOffWeight

    def __setitem__(self, key, value):
        assert not self.compiled
        self.prob[key] = value

    def __iter__(self):
        return self.prob.iteritems()

    def perplexity(self, evidence):
        total = 0.0
        totalEvidence = 0.0
        for history, predicted, value in evidence:
            total += value * math.log(self(history, predicted))
            totalEvidence += value
        return math.exp(-total / totalEvidence)

    def compile(self, term, inventory=None):
        if not self.compiled:
            self.inventory = inventory
            data = []
            if inventory is None:
                for (history, predicted), probability in self.prob.iteritems():
                    try:
                        data.append((history, predicted, -math.log(probability)))
                    except (ValueError, OverflowError):
                        if (history, predicted) != ((), None):
                            print(
                                "SequenceModel.py:116: cannot take logarithm of zero probability",
                                history,
                                predicted,
                                probability,
                            )
            else:
                for (history, predicted), probability in self.prob.iteritems():
                    history = tuple(map(inventory.index, history))
                    if predicted is not None:
                        predicted = inventory.index(predicted)
                    data.append((history, predicted, -math.log(probability)))
            self.compiled = SequenceModel()
            self.compiled.setInitAndTerm(term, term)
            self.compiled.set(data)
        else:
            assert self.inventory == inventory
        return self.compiled

    def showMostProbable(self, f, inventory, limit=None):
        sample = [
            (probability, inventory(predicted), map(inventory, history))
            for (history, predicted), probability in self.prob.iteritems()
            if predicted is not None
        ]
        sample.sort()
        sample.reverse()
        if limit and 1.5 * limit < len(sample):
            for probability, predicted, history in sample[:limit]:
                print(predicted, history, probability, file=f)
            print("...", file=f)
            for probability, predicted, history in sample[-int(limit / 2) :]:
                print(predicted, history, probability, file=f)
        else:
            for probability, predicted, history in sample:
                print(predicted, history, probability, file=f)
        print("n-grams", len(sample), file=f)
        print(
            "uni-gram total",
            sum(
                [
                    probability
                    for probability, predicted, history in sample
                    if len(history) == 0
                ]
            ),
            file=f,
        )

    def rampUp(self):
        newHistories = set()
        for (history, predicted), probability in self.prob.iteritems():
            if predicted is None:
                continue
            newHistory = history + (predicted,)
            if (newHistory, None) not in self.prob:
                newHistories.add(newHistory)
        for newHistory in newHistories:
            self.prob[(newHistory, None)] = 1.0
        self.compiled = None


class SequenceModelEstimator:
    def groupEvidences(self, evidence):
        grouped = {}
        for history, predicted, value in evidence:
            g = len(history)
            if g not in grouped:
                grouped[g] = []
            grouped[g].append((history, predicted, value))
        if grouped:
            return [
                EvidenceList(grouped.get(g)) for g in range(max(grouped.keys()) + 1)
            ]
        else:
            return []

    def makeKneserNeyDiscounting(self, evidences, discount):
        levels = list(range(len(evidences)))
        levels.reverse()
        result = []
        evidence = EvidenceList()
        for level in levels:
            evidence.addList(evidences[level])
            total = evidence.groupedSums()
            discounted, backOff = evidence.discount(discount[level])
            result.append((discounted, total))
            evidence = backOff
        result.reverse()
        return result

    def makeProbabilities(self, vocabularySize, evidences):
        result = BackOffModel()
        zeroGramProbability = 1 / vocabularySize
        result[((), None)] = zeroGramProbability
        for evidence, totals in evidences:
            evidence = evidence.grouped()
            for history in evidence:
                denominator = totals[history]
                backOffWeight = (
                    1.0 - sum([v for w, v in evidence[history]]) / denominator
                )
                backOffWeight = max(0.0, backOffWeight)
                if history:
                    shorterHistory = history[1:]
                else:
                    shorterHistory = None
                    backOffWeight *= zeroGramProbability
                result[(history, None)] = backOffWeight
                for predicted, value in evidence[history]:
                    p = value / denominator
                    if shorterHistory is not None:
                        p += backOffWeight * result(shorterHistory, predicted)
                    else:
                        p += backOffWeight
                    if p > 0.0:
                        result[(history, predicted)] = p
        return result

    def make(self, vocabularySize, evidence, discount=None):
        evidences = self.groupEvidences(evidence)
        if discount is not None:
            evidences = self.makeKneserNeyDiscounting(evidences, discount)
        else:
            evidences = [(ev, ev.groupedSums()) for ev in evidences]
        result = self.makeProbabilities(vocabularySize, evidences)
        return result


class SequenceModel(sequitur_.SequenceModel):
    def __getstate__(self):
        dct = copy.copy(self.__dict__)
        del dct["this"]
        return (self.init(), self.term(), self.get(), dct)

    def __setstate__(self, data):
        super(SequenceModel, self).__init__()
        init, term, data, dct = data
        self.setInitAndTerm(init, term)
        self.set(data)
        self.__dict__.update(dct)

    def size(self):
        return len(self.get())

    def showMostProbable(self, f, inventory, limit=None):
        sample = [
            (math.exp(-score), inventory(predicted), map(inventory, history))
            for history, predicted, score in self.get()
            if predicted is not None
        ]
        sample.sort()
        sample.reverse()
        if limit and 1.5 * limit < len(sample):
            for probability, predicted, history in sample[:limit]:
                print(predicted, history, probability, file=f)
            print("...", file=f)
            for probability, predicted, history in sample[-int(limit / 2) :]:
                print(predicted, history, probability, file=f)
        else:
            for probability, predicted, history in sample:
                print(predicted, history, probability, file=f)
        print("n-grams", len(sample), file=f)
        print(
            "uni-gram total",
            sum(
                [
                    probability
                    for probability, predicted, history in sample
                    if len(history) == 0
                ]
            ),
            file=f,
        )

    def rampUp(self):
        data = self.get()
        histories = set([history for history, predicted, score in data])
        newHistories = set()
        for history, predicted, score in data:
            if predicted is None:
                continue
            newHistory = history + (predicted,)
            if newHistory not in histories:
                newHistories.add(newHistory)
        for newHistory in newHistories:
            data.append((newHistory, None, 0.0))
        self.set(data)

    def wipeOut(self, vocabularySize):
        histories = set()
        for history, predicted, score in self.get():
            histories.add(history)
        histories.remove(())
        data = [((), None, math.log(vocabularySize))]
        for history in histories:
            data.append((history, None, 0.0))
        self.set(data)

    def setZerogram(self, vocabularySize):
        data = [((), None, math.log(vocabularySize))]
        self.set(data)


def evidenceFromSequence(sequence, order):
    result = []
    for j, predicted in enumerate(sequence):
        history = tuple(sequence[max(0, j - order) : j])
        result.append((history, predicted, 1))
    return result


def evidenceFromSequences(sequences, order):
    result = []
    for sequence in sequences:
        result += evidenceFromSequence(sequence, order)
    result = EvidenceList(result)
    result.consolidate()
    return result

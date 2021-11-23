from __future__ import division
from __future__ import print_function

__author__ = "Maximilian Bisani"
__version__ = "$LastChangedRevision: 1691 $"
__date__ = "$LastChangedDate: 2011-08-03 15:38:08 +0200 (Wed, 03 Aug 2011) $"
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

import itertools, math, sys
import numpy as num
import sequitur_, SequenceModel, Minimization, misc
from symbols import SymbolInventory
from misc import reversed, sorted, set


class MultigramInventory(sequitur_.MultigramInventory):
    def __getstate__(self):
        return [self.symbol(i) for i in range(1, self.size() + 1)]

    def __setstate__(self, data):
        super(MultigramInventory, self).__init__()
        for i, lr in enumerate(data):
            j = self.index(lr)
            assert j == i + 1

    def sizeTemplates(self):
        result = set()
        for i in range(1, self.size() + 1):
            left, right = self.symbol(i)
            result.add((len(left), len(right)))
        return sorted(result)


class Sequitur:
    """
    Multigram / sequence model tokens / indices: 0 (zero) indicates
    VOID, and is only used internally as a sentinel. term is the index
    of the (term,term) multigram which is the end-of-string token.
    (Also used as begin-of-string token.)
    """

    def __init__(self, leftInventory=None, rightInventory=None):
        self.leftInventory = leftInventory
        self.rightInventory = rightInventory
        if not self.leftInventory:
            self.leftInventory = SymbolInventory()
        if not self.rightInventory:
            self.rightInventory = SymbolInventory()
        self.inventory = MultigramInventory()
        self.term = self.inventory.index(
            ((self.leftInventory.term,), (self.rightInventory.term,))
        )

    def compileSample(self, sample):
        return [
            (self.leftInventory.parse(left), self.rightInventory.parse(right))
            for left, right in sample
        ]

    def symbol(self, i):
        "multigramFromTokenIndex"
        l, r = self.inventory.symbol(i)
        l = self.leftInventory.format(l)
        r = self.rightInventory.format(r)
        return (l, r)

    def symbols(self):
        return [self.symbol(i) for i in range(1, self.inventory.size() + 1)]

    def index(self, left, right):
        "tokenIndexFromMultigram"
        left = self.leftInventory.parse(left)
        right = self.rightInventory.parse(right)
        return self.inventory.index((left, right))

    def makeStringInventory(self):
        result = []
        for i in range(1, self.inventory.size() + 1):
            result.append("%s:%s" % self.symbol(i))
        return sequitur_.StringInventory(result)


class Model(object):
    discount = None
    sequenceModel = None

    def __init__(self, sequitur=None):
        self.sequitur = sequitur

    def strip(self):
        oldSequitur = self.sequitur
        self.sequitur = Sequitur(
            self.sequitur.leftInventory, self.sequitur.rightInventory
        )
        data = []
        for history, predicted, score in self.sequenceModel.get():
            history = map(oldSequitur.inventory.symbol, history)
            history = tuple(map(self.sequitur.inventory.index, history))
            if predicted is not None:
                predicted = oldSequitur.inventory.symbol(predicted)
                predicted = self.sequitur.inventory.index(predicted)
            data.append((history, predicted, score))
        self.sequenceModel = SequenceModel.SequenceModel()
        self.sequenceModel.set(data)
        self.sequenceModel.setInitAndTerm(self.sequitur.term, self.sequitur.term)

        return oldSequitur.inventory.size(), self.sequitur.inventory.size()

    def transpose(self):
        oldInventory = self.sequitur.inventory
        self.sequitur = Sequitur(
            self.sequitur.rightInventory, self.sequitur.leftInventory
        )
        for i in range(1, oldInventory.size() + 1):
            left, right = oldInventory.symbol(i)
            j = self.sequitur.inventory.index((right, left))
            assert i == j  # hope

    def rampUp(self):
        self.sequenceModel.rampUp()

    def wipeOut(self, inventorySize):
        self.sequenceModel.wipeOut(inventorySize)


class MixtureModel(Model):
    "for side-ways compatibility with branch mixture-model"

    def __setstate__(self, data):
        Model.__init__(self, data["sequitur"])
        if len(data["components"]) > 1:
            raise NotImplementedError("mixture models not supported")
        component = data["components"][0]
        self.sequenceModel = component.sequenceModel
        self.discount = component.discount


class MixtureModelComponent(object):
    "for side-ways compatibility with branch micture-model"
    pass


class EstimationGraphBuilder(sequitur_.EstimationGraphBuilder):
    def setSizeTemplates(self, templates):
        self.clearSizeTemplates()
        for left, right in templates:
            self.addSizeTemplate(left, right)


class Sample(object):
    def __init__(self, sequitur, sizeTemplates, emergenceMode, sample, model):
        self.sequitur = sequitur
        self.sizeTemplates = sizeTemplates
        self.emergenceMode = emergenceMode
        self.builder = EstimationGraphBuilder()
        self.builder.setSizeTemplates(self.sizeTemplates)
        self.builder.setEmergenceMode(self.emergenceMode)
        self.sample = sample

        self.masterModel = model
        self.currentModel = None
        self.storedGraphs = None

    def __getstate__(self):
        state = {
            "sequitur": self.sequitur,
            "sizeTemplates": self.sizeTemplates,
            "emergenceMode": self.emergenceMode,
            "sample": self.sample,
            "masterModel": self.masterModel,
        }
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.builder = EstimationGraphBuilder()
        self.builder.setSizeTemplates(self.sizeTemplates)
        self.builder.setEmergenceMode(self.emergenceMode)
        self.currentModel = None
        self.storedGraphs = None

    def size(self):
        return len(self.sample)

    def makeGraphs(self):
        for left, right in self.sample:
            self.builder.setSequenceModel(self.sequitur.inventory, self.masterModel)
            try:
                eg = self.builder.create(left, right)
            except RuntimeError:
                error = sys.exc_info()[1]
                if str(error) != "final node not reachable":
                    raise
                print(
                    "warning: dropping one sample that has no segmentation",
                    repr((left, right)),
                )
                continue
            eg.thisown = True
            if self.currentModel is not self.masterModel:
                self.builder.setSequenceModel(
                    self.sequitur.inventory, self.currentModel
                )
                self.builder.update(eg)
            yield eg

    class GraphsOnDemand:
        def __init__(self, master, model):
            self.master = master
            self.model = model

        def __iter__(self):
            assert self.model is self.master.currentModel
            return self.master.makeGraphs()

    maxStoredGraphs = 5000

    def graphs(self, model):
        if len(self.sample) > self.maxStoredGraphs:
            self.currentModel = model
            return self.GraphsOnDemand(self, model)
        else:
            if self.storedGraphs is None:
                self.builder.setSequenceModel(self.sequitur.inventory, self.masterModel)
                graphs = []
                for left, right in self.sample:
                    try:
                        eg = self.builder.create(left, right)
                    except RuntimeError:
                        error = sys.exc_info()[1]
                        if str(error) != "final node not reachable":
                            raise
                        print(
                            "warning: dropping one sample that has no segmentation",
                            repr((left, right)),
                        )
                        continue
                    eg.thisown = True
                    graphs.append(eg)
                self.storedGraphs = graphs
                self.currentModel = self.masterModel
            if model is not self.currentModel:
                self.builder.setSequenceModel(self.sequitur.inventory, model)
                for eg in self.storedGraphs:
                    self.builder.update(eg)
                self.currentModel = model
            return self.storedGraphs

    def evidence(self, model, useMaximumApproximation):
        evidences = sequitur_.EvidenceStore()
        evidences.setSequenceModel(model)
        if useMaximumApproximation:
            accumulator = sequitur_.ViterbiAccumulator()
        else:
            accumulator = sequitur_.Accumulator()
        accumulator.setTarget(evidences)
        logLik = 0.0
        for eg in self.graphs(model):
            logLik += accumulator.accumulate(eg, 1.0)
        misc.reportMemoryUsage()
        return evidences, logLik

    def logLik(self, model, useMaximumApproximation):
        if useMaximumApproximation:
            accumulator = sequitur_.ViterbiAccumulator()
        else:
            accumulator = sequitur_.Accumulator()
        logLik = 0.0
        for eg in self.graphs(model):
            logLik += accumulator.logLik(eg)
        return logLik

    def overlappingOccurenceCounts(self, model):
        counts = sequitur_.EvidenceStore()
        counts.setSequenceModel(model)
        accumulator = sequitur_.OneForAllAccumulator()
        accumulator.setTarget(counts)
        for eg in self.graphs(model):
            accumulator.accumulate(eg, 1.0)
        return counts


class TrainingContext:
    def __init__(self):
        self.iteration = 0
        self.order = None
        self.logLikTrain = []
        self.logLikDevel = []
        self.bestModel = None
        self.bestLogLik = None
        self.log = sys.stdout

    def registerNewModel(self, newModel, logLik):
        if self.bestModel is None or logLik >= self.bestLogLik:
            print("new best model found", file=self.log)
            self.bestModel = newModel
            self.bestLogLik = logLik


class StaticDiscounts:
    """
    Dummy discount adjuster, that just keeps the current discounts.
    """

    def __init__(self, modelFactory, develSample, discount, useMaximumApproximation):
        self.discount = discount
        if self.discount is None:
            self.discount = [0.0]
        self.discount = num.array(self.discount, dtype=num.float64)

    def adjust(self, context, evidence, order):
        if len(self.discount) < order + 1:
            oldSize = len(self.discount)
            highestOrderDiscount = self.discount[-1]
            self.discount.resize(order + 1)
            self.discount[oldSize:] = highestOrderDiscount
        print("keep discount: %s" % self.discount, file=context.log)
        return self.discount


class FixedDiscounts:
    """
    Dummy discount adjuster, that just returns a fixed value.
    """

    def __init__(self, discount):
        self.discount = num.array(discount, dtype=num.float64)

    def __call__(self, modelFactory, develSample, discount, useMaximumApproximation):
        return self

    def adjust(self, context, evidence, order):
        if len(self.discount) < order + 1:
            oldSize = len(self.discount)
            highestOrderDiscount = self.discount[-1]
            self.discount.resize(order + 1)
            self.discount[oldSize:] = highestOrderDiscount
        print("fixed discount: %s" % self.discount, file=context.log)
        return self.discount


class DefaultDiscountAdjuster:
    """
    Optimize discounts at constant evidence by optimizing
    log-likelihood of the development set.
    """

    maximumReasonableDiscount = 10.0

    def __init__(self, modelFactory, develSample, discount, useMaximumApproximation):
        self.modelFactory = modelFactory
        self.develSample = develSample
        if discount is not None:
            discount = num.asarray(discount, dtype=num.float64)
        self.discounts = [None, discount]
        self.shallUseMaximumApproximation = useMaximumApproximation

    def adjustOrderZero(self, evidence, maximumDiscount):
        def criterion(discount):
            sm = self.modelFactory.sequenceModel(evidence, [max(0.0, discount)])
            ll = self.develSample.logLik(sm, self.shallUseMaximumApproximation)
            crit = -ll - min(discount, 0) + max(discount - maximumDiscount, 0)
            print(discount, ll, crit)  # TESTING
            return crit

        initialGuess = self.discounts[-1]
        previous = self.discounts[-2]
        if initialGuess is None:
            initialGuess = 0.1
        else:
            initialGuess = initialGuess[0]

        discount, ll = Minimization.linearMinimization(
            criterion, initialGuess, tolerance=1e-4
        )
        discount = max(0.0, discount)
        discount = num.array([discount])
        return discount, -ll

    def adjustHigherOrder(self, evidence, order, maximumDiscount):
        def criterion(discount):
            disc = tuple(num.maximum(0.0, discount))
            sm = self.modelFactory.sequenceModel(evidence, disc)
            ll = self.develSample.logLik(sm, self.shallUseMaximumApproximation)
            crit = (
                -ll
                - sum(num.minimum(discount, 0))
                + sum(num.maximum(discount - maximumDiscount, 0))
            )
            print(discount, ll, crit)  # TESTING
            return crit

        initialGuess = self.discounts[-1]
        firstDirection = None
        if initialGuess is None:
            initialGuess = 0.1 * num.arange(1, order + 2, dtype=num.float64)
        elif len(initialGuess) < order + 1:
            oldGuess = initialGuess
            oldSize = len(initialGuess)
            initialGuess = num.zeros(order + 1, dtype=num.float64)
            initialGuess[:oldSize] = oldGuess
            initialGuess[oldSize:] = oldGuess[-1]
        elif len(initialGuess) > order + 1:
            initialGuess = initialGuess[: order + 1]
        else:
            previous = self.discounts[-2]
            if previous is not None and len(previous) == order + 1:
                firstDirection = initialGuess - previous
                if not num.sometrue(num.abs(firstDirection) > 1e-4):
                    firstDirection = None

        directions = num.identity(order + 1, dtype=num.float64)
        directions = directions[::-1]
        if firstDirection is not None:
            directions = num.concatenate((firstDirection[num.newaxis, :], directions))
        directions *= 0.1
        print(directions)  # TESTING

        discount, ll = Minimization.directionSetMinimization(
            criterion, initialGuess, directions, tolerance=1e-4
        )

        discount = num.maximum(0.0, discount)
        return discount, -ll

    def adjust(self, context, evidence, order):
        if self.shouldAdjustDiscount(context, evidence):
            print("adjusting discount ...", file=context.log)
            maximumDiscount = min(evidence.maximum(), self.maximumReasonableDiscount)
            evidence = evidence.makeSequenceModelEstimator()
            evidence.thisown = True
            if order == 0:
                discount, logLik = self.adjustOrderZero(evidence, maximumDiscount)
            else:
                discount, logLik = self.adjustHigherOrder(
                    evidence, order, maximumDiscount
                )
            self.discounts.append(discount)
            print("optimal discount: %s" % discount, file=context.log)
            print("max. rel. change: %s" % self.maxRelChange(), file=context.log)
        else:
            discount = self.discounts[-1]
            print("keep discount: %s" % discount, file=context.log)
        return discount

    def shouldAdjustDiscount(self, context, evidence):
        if len(context.logLikDevel) < 1:
            return True
        tentativeModel = self.modelFactory.sequenceModel(evidence, self.discounts[-1])
        logLikDevel = context.develSample.logLik(
            tentativeModel, self.shallUseMaximumApproximation
        )
        return logLikDevel <= context.logLikDevel[-1]

    def maxRelChange(self):
        if self.discounts[-2] is None:
            maxRelChange = 1.0
        elif len(self.discounts[-1]) != len(self.discounts[-2]):
            maxRelChange = 1.0
        else:
            maxRelChange = max(
                abs(
                    (self.discounts[-1] - self.discounts[-2])
                    / (self.discounts[-2] + 1e-10)
                )
            )
        return maxRelChange


class EagerDiscountAdjuster(DefaultDiscountAdjuster):
    def shouldAdjustDiscount(self, context, evidence):
        return True


class ModelTemplate:
    sizeTemplates = [(1, 1), (1, 0), (0, 1)]

    def __init__(self, sequitur):
        self.sequitur = sequitur
        self.observers = []
        self.shallUseMaximumApproximation = False
        self.emergenceMode = EstimationGraphBuilder.emergeNewMultigrams

    def useMaximumApproximation(self, viterbi):
        self.shallUseMaximumApproximation = viterbi

    def allowEmergenceOfNewMultigrams(self, allow):
        self.emergenceMode = {
            True: EstimationGraphBuilder.emergeNewMultigrams,
            False: EstimationGraphBuilder.suppressNewMultigrams,
        }[allow]

    def setLengthConstraints(
        self, minLeftLength, maxLeftLength, minRightLength, maxRightLength
    ):
        assert 0 <= minLeftLength and minLeftLength <= maxLeftLength
        assert 0 <= minRightLength and minRightLength <= maxRightLength
        self.sizeTemplates = [
            (left, right)
            for left in range(minLeftLength, maxLeftLength + 1)
            for right in range(minRightLength, maxRightLength + 1)
            if left > 0 or right > 0
        ]

    def setSizeTemplates(self, templates):
        self.sizeTemplates = templates

    def nPossibleMultigrams(self):
        nLeftSymbols = self.sequitur.leftInventory.size() - 1  # for __term__
        nRightSymbols = self.sequitur.rightInventory.size() - 1  # for __term__
        result = 0
        for left, right in self.sizeTemplates:
            result += (nLeftSymbols ** left) * (nRightSymbols ** right)
        result += 1  # for __term__
        return result

    # =======================================================================
    def obliviousSequenceModel(self):
        result = SequenceModel.SequenceModel()
        result.setInitAndTerm(self.sequitur.term, self.sequitur.term)
        result.setZerogram(self.nPossibleMultigrams())
        return result

    def sequenceModel(self, evidence, discount):
        result = SequenceModel.SequenceModel()
        if type(evidence) is not sequitur_.SequenceModelEstimator:
            evidence = evidence.makeSequenceModelEstimator()
            evidence.thisown = True
        evidence.makeSequenceModel(result, self.nPossibleMultigrams(), discount)
        return result

    # =======================================================================
    def showMostEvident(self, f, evidence, limit):
        sample = evidence.asList()
        sample = [(value, predicted, history) for history, predicted, value in sample]
        sample.sort()
        sample.reverse()

        def asString(index):
            left, right = self.sequitur.symbol(index)
            return "".join(left) + ":" + "_".join(right)

        def show(value, predicted, history):
            print(
                "    ",
                value,
                "      ",
                asString(predicted),
                "      ",
                " ".join(map(asString, history)),
                file=f,
            )

        if limit and 1.5 * limit < len(sample):
            for vph in sample[:limit]:
                show(*vph)
            print("    ...", file=f)
            for vph in sample[-limit // 2 :]:
                show(*vph)
        else:
            for vph in sample:
                show(*vph)
        print(len(sample), "evidences total", file=f)
        print(self.sequitur.inventory.size(), "multigrams ever seen", file=f)

    # =======================================================================
    def masterSequenceModel(self, model):
        allHistories = set()
        for history, predicted, score in model.sequenceModel.get():
            allHistories.add(history)
        result = SequenceModel.SequenceModel()
        result.setInitAndTerm(self.sequitur.term, self.sequitur.term)
        result.set([(history, None, 0.0) for history in allHistories])
        return result

    def obliviousModel(self):
        result = Model(self.sequitur)
        result.sequenceModel = self.obliviousSequenceModel()
        result.discount = None
        return result

    def initializeWithOverlappingCounts(self, context):
        counts = context.trainSample.overlappingOccurenceCounts(
            context.model.sequenceModel
        )

        print("  count types: %s" % counts.size(), file=context.log)
        print(
            "  count total / max: %s / %s" % (counts.total(), counts.maximum()),
            file=context.log,
        )

        self.showMostEvident(context.log, counts, 10)  ### TESTING

        context.model = Model(self.sequitur)
        context.model.discount = num.zeros(counts.maximumHistoryLength() + 1)
        context.model.sequenceModel = self.sequenceModel(counts, context.model.discount)

        print("  model size: %s" % context.model.sequenceModel.size(), file=context.log)
        print("", file=context.log)

        context.log.flush()

    def iterate(self, context):
        evidence, logLikTrain = context.trainSample.evidence(
            context.model.sequenceModel, self.shallUseMaximumApproximation
        )

        print(("LL train: %s (before)" % logLikTrain), file=context.log)
        context.logLikTrain.append(logLikTrain)

        if (not context.develSample) and (context.iteration > self.minIterations):
            context.registerNewModel(context.model, logLikTrain)

        order = evidence.maximumHistoryLength()
        print("  evidence order: %s" % order, file=context.log)
        if context.order is not None and order != context.order:
            print(
                "  warning: evidence order changed from %d to %d!"
                % (context.order, order),
                file=context.log,
            )
        context.order = order

        print("  evidence types: %s" % evidence.size(), file=context.log)
        print(
            "  evidence total / max: %s / %s" % (evidence.total(), evidence.maximum()),
            file=context.log,
        )
        self.showMostEvident(context.log, evidence, 10)  ### TESTING

        newModel = Model(self.sequitur)
        newModel.discount = context.discountAdjuster.adjust(context, evidence, order)
        newModel.sequenceModel = self.sequenceModel(evidence, newModel.discount)
        print("  model size: %s" % newModel.sequenceModel.size(), file=context.log)

        if context.develSample:
            logLikDevel = context.develSample.logLik(
                newModel.sequenceModel, self.shallUseMaximumApproximation
            )
            print("LL devel: %s" % logLikDevel, file=context.log)
            context.logLikDevel.append(logLikDevel)

        for observer in self.observers:
            observer(context.log, context, newModel)

        if (context.develSample) and (context.iteration >= self.minIterations):
            context.registerNewModel(newModel, logLikDevel)

        shouldStop = False
        if context.bestModel:
            if context.develSample:
                crit = context.logLikDevel
            else:
                crit = context.logLikTrain
            crit = [-ll for ll in crit[-self.convergenceWindow :]]
            if not Minimization.hasSignificantDecrease(crit):
                print("iteration converged.", file=context.log)
                shouldStop = True

        context.model = newModel
        return shouldStop

    maxIterations = 100
    minIterations = 20
    convergenceWindow = 10
    DiscountAdjustmentStrategy = DefaultDiscountAdjuster
    checkpointInterval = None  # or CPU time in seconds
    checkpointFile = None  # filename template must contain '%d'

    def makeContext(self, trainSample, develSample, initialModel=None):
        context = TrainingContext()
        if initialModel:
            context.model = initialModel
        else:
            context.model = self.obliviousModel()
        masterModel = self.masterSequenceModel(context.model)
        context.trainSample = Sample(
            self.sequitur,
            self.sizeTemplates,
            self.emergenceMode,
            trainSample,
            masterModel,
        )
        if develSample:
            context.develSample = Sample(
                self.sequitur,
                self.sizeTemplates,
                EstimationGraphBuilder.anonymizeNewMultigrams,
                develSample,
                masterModel,
            )
        else:
            context.develSample = None
        context.discountAdjuster = self.DiscountAdjustmentStrategy(
            self,
            context.develSample,
            context.model.discount,
            self.shallUseMaximumApproximation,
        )
        context.iteration = 0
        return context

    def run(self, context):
        lastCheckpoint = misc.cputime()
        shouldStop = False
        while not shouldStop:
            if context.iteration >= self.maxIterations:
                print("maximum number of iterations reached.", file=context.log)
                break
            print("iteration: %s" % context.iteration, file=context.log)
            try:
                shouldStop = self.iterate(context)
            except:
                import traceback

                traceback.print_exc()
                print("iteration failed.", file=context.log)
                break
            if (self.checkpointInterval) and (
                misc.cputime() > lastCheckpoint + self.checkpointInterval
            ):
                self.checkpoint(context)
                lastCheckpoint = misc.cputime()
            context.iteration += 1
            misc.reportMemoryUsage()
            print("", file=context.log)
            context.log.flush()

    def resume(cls, filename):
        from six.moves import cPickle as pickle

        if sys.version_info[:2] >= (3, 0):
            self, context = pickle.load(open(filename), encoding="latin1")
        else:
            try:
                self, context = pickle.load(open(filename))
            except ValueError:
                print(
                    "This error most likely occurred because the loaded model was created in python3.\n",
                    file=sys.stderr,
                )
                raise
        self.run(context)
        return context.bestModel

    resume = classmethod(resume)

    def checkpoint(self, context):
        print("checkpointing", file=context.log)
        import cPickle as pickle

        fname = self.checkpointFile % context.iteration
        f = open(fname, "wb")
        pickle.dump((self, context), f, pickle.HIGHEST_PROTOCOL)
        f.close()


# ===========================================================================
class Translator:
    def __init__(self, model):
        self.setModel(model)

    def setModel(self, model):
        self.model = model
        self.sequitur = self.model.sequitur
        self.translator = sequitur_.Translator()
        self.translator.setMultigramInventory(self.sequitur.inventory)
        self.translator.setSequenceModel(self.model.sequenceModel)

    def setStackLimit(self, n):
        self.translator.setStackLimit(n)

    class TranslationFailure(RuntimeError):
        pass

    def unpackJoint(self, joint):
        assert joint[0] == self.sequitur.term
        assert joint[-1] == self.sequitur.term
        return [self.sequitur.inventory.symbol(q) for q in joint[1:-1]]

    def translateFirstBest(self, left):
        left = self.sequitur.leftInventory.parse(left)
        try:
            logLik, joint = self.translator(left)
        except RuntimeError:
            exc = sys.exc_info()[1]
            raise self.TranslationFailure(*exc.args)
        return logLik, self.unpackJoint(joint)

    def firstBestJoint(self, left):
        logLik, joint = self.translateFirstBest(left)
        joint = [
            (
                self.sequitur.leftInventory.format(left),
                self.sequitur.rightInventory.format(right),
            )
            for left, right in joint
        ]
        return logLik, joint

    def jointToLeftRight(self, joint):
        left = [l for ll, rr in joint for l in ll]
        left = self.sequitur.leftInventory.format(left)
        right = [r for ll, rr in joint for r in rr]
        right = self.sequitur.rightInventory.format(right)
        return left, right

    def firstBest(self, left):
        logLik, joint = self.translateFirstBest(left)
        left2, right = self.jointToLeftRight(joint)
        assert tuple(left) == left2
        return logLik, right

    def __call__(self, left):
        logLik, right = self.firstBest(left)
        return right

    def nBestInit(self, left):
        left = self.sequitur.leftInventory.parse(left)
        try:
            result = self.translator.nBestInit(left)
        except RuntimeError:
            exc = sys.exc_info()[1]
            raise self.TranslationFailure(*exc.args)
        result.thisown = True
        result.logLikBest = self.translator.nBestBestLogLik(result)
        result.logLikTotal = self.translator.nBestTotalLogLik(result)
        return result

    def nBestNext(self, nBestContext):
        try:
            logLik, joint = self.translator.nBestNext(nBestContext)
        except RuntimeError:
            exc = sys.exc_info()[1]
            if exc.args[0] == "no further translations":
                raise StopIteration
            else:
                raise self.TranslationFailure(*exc.args)
        joint = self.unpackJoint(joint)
        left, right = self.jointToLeftRight(joint)
        return logLik, right

    def reportStats(self, f):
        print("stack usage: ", self.translator.stackUsage(), file=f)


class Segmenter:
    def __init__(self, model):
        self.model = model
        self.sequitur = model.sequitur
        self.builder = EstimationGraphBuilder()
        self.builder.setSizeTemplates(self.sequitur.inventory.sizeTemplates())
        #       self.builder.setEmergenceMode(EstimationGraphBuilder.anonymizeNewMultigrams)
        self.builder.setEmergenceMode(EstimationGraphBuilder.suppressNewMultigrams)
        self.builder.setSequenceModel(self.sequitur.inventory, self.model.sequenceModel)
        self.viterbi = sequitur_.ViterbiAccumulator()

    class SegmentationFailure(RuntimeError):
        pass

    def firstBestJoint(self, left, right):
        try:
            eg = self.builder.create(
                self.sequitur.leftInventory.parse(left),
                self.sequitur.rightInventory.parse(right),
            )
            logLik, joint = self.viterbi.segment(eg)
        except RuntimeError:
            exc = sys.exc_info()[1]
            raise self.SegmentationFailure(*exc.args)
        assert joint[-1] == self.sequitur.term
        joint = map(self.sequitur.inventory.symbol, joint[:-1])
        joint = [
            (
                self.sequitur.leftInventory.format(left),
                self.sequitur.rightInventory.format(right),
            )
            for left, right in joint
        ]
        return logLik, joint

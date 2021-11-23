from __future__ import division, print_function

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

from collections import defaultdict
import os.path
from six.moves import cPickle as pickle
import operator
import numpy as num
from sequitur import (
    Sequitur,
    ModelTemplate,
    DefaultDiscountAdjuster,
    StaticDiscounts,
    FixedDiscounts,
    EagerDiscountAdjuster,
)
from sequitur import Translator
from Evaluation import Evaluator
from tool import UsageError
import sys


class OnlineTester(object):
    def __init__(self, name, sample):
        self.name = name
        self.evaluator = Evaluator()
        self.evaluator.setSample(sample)

    def __call__(self, log, context, model):
        translator = Translator(model)
        result = self.evaluator.evaluate(translator)
        print(
            "ER %s: string errors %s    symbol errors %s"
            % (self.name, result.stringError, result.symbolError),
            file=log,
        )


def transposeSample(sample):
    return [(right, left) for left, right in sample]


def partition_sample(sample, portion=0.1):
    train_sample = []
    devel_sample = []
    j = 0
    for i, s in enumerate(group_by_orth(sample)):
        if j / (i + 1) < portion:
            for value in s[1]:
                devel_sample.append((s[0], value))
            j += 1
        else:
            for value in s[1]:
                train_sample.append((s[0], value))
    return train_sample, devel_sample


def group_by_orth(sample):
    import random

    source_values = set()
    mapping = defaultdict(list)
    for s in sample:
        source_values.add(s[0])
        mapping[s[0]].append(s[1])
    source_values = list(source_values)
    random.shuffle(source_values)
    for s in source_values:
        yield s, mapping[s]


class Tool:
    def __init__(self, options, loadSample, log=sys.stdout):
        self.options = options
        self.loadSample = loadSample
        self.log = log

    def loadSamples(self):
        self.trainSample = self.loadSample(self.options.trainSample)
        if not self.options.develSample:
            self.develSample = []
        elif self.options.develSample.endswith("%"):
            portion = float(self.options.develSample.rstrip("% ")) / 100.0
            self.trainSample, self.develSample = partition_sample(
                self.trainSample, portion
            )
        else:
            self.develSample = self.loadSample(self.options.develSample)
        print(
            "training sample: %d + %d devel"
            % (len(self.trainSample), len(self.develSample)),
            file=self.log,
        )

    def trainModel(self, initialModel):
        self.loadSamples()
        compiledTrainSample = self.sequitur.compileSample(self.trainSample)
        compiledDevelSample = self.sequitur.compileSample(self.develSample)
        del self.trainSample

        if self.options.fixed_discount:
            discount = eval(self.options.fixed_discount)
            if not operator.isSequenceType(discount):
                discount = [discount]
            discount = num.array(discount)
        else:
            discount = None

        template = ModelTemplate(self.sequitur)
        if self.options.fixed_discount:
            template.DiscountAdjustmentStrategy = FixedDiscounts(discount)
        elif self.develSample:
            if self.options.eager_discount_adjustment:
                template.DiscountAdjustmentStrategy = EagerDiscountAdjuster
            else:
                template.DiscountAdjustmentStrategy = DefaultDiscountAdjuster
        else:
            template.DiscountAdjustmentStrategy = StaticDiscounts

        if self.options.lengthConstraints:
            spec = self.options.lengthConstraints.strip()
            if spec.startswith("["):
                assert spec.endswith("]")
                st = spec[1:-1].split(",")
                st = [t.split(":") for t in st]
                st = [(int(l), int(r)) for l, r in st]
                template.setSizeTemplates(st)
            else:
                lc = tuple(map(int, spec.split(",")))
                template.setLengthConstraints(*lc)
        template.allowEmergenceOfNewMultigrams(
            not bool(self.options.shouldSuppressNewMultigrams)
        )
        template.useMaximumApproximation(bool(self.options.viterbi))

        if self.options.minIterations > self.options.maxIterations:
            print(
                "invalid limits on number of iterations %d > %d"
                % (self.options.minIterations, self.options.maxIterations),
                file=self.log,
            )
            return
        template.minIterations = self.options.minIterations
        template.maxIterations = self.options.maxIterations
        if self.options.checkpoint and self.options.newModelFile:
            template.checkpointInterval = 8 * 60 * 60
            base, ext = os.path.splitext(self.options.newModelFile)
            template.checkpointFile = base + "-cp%d" + ext

        if self.options.shouldWipeModel:
            initialModel.wipeOut(template.nPossibleMultigrams())

        if self.options.shouldTestContinuously:
            if self.develSample:
                template.observers.append(OnlineTester("devel", self.develSample))
            if self.options.testSample:
                template.observers.append(
                    OnlineTester("test", self.loadSample(self.options.testSample))
                )

        estimationContext = template.makeContext(
            compiledTrainSample, compiledDevelSample, initialModel
        )
        del initialModel

        estimationContext.log = self.log
        if self.options.shouldInitializeWithCounts:
            template.initializeWithOverlappingCounts(estimationContext)
        template.run(estimationContext)
        return estimationContext.bestModel

    def procureModel(self):
        if self.options.resume_from_checkpoint:
            model = ModelTemplate.resume(self.options.resume_from_checkpoint)
            self.sequitur = model.sequitur
        elif self.options.modelFile:
            if sys.version_info[:2] >= (3, 0):
                model = pickle.load(
                    open(self.options.modelFile, "rb"), encoding="latin1"
                )
            else:
                try:
                    model = pickle.load(open(self.options.modelFile, "rb"))
                except ValueError:
                    print(
                        "This error most likely occurred because the loaded model was created in python3.\n",
                        file=sys.stderr,
                    )
                    raise

            self.sequitur = model.sequitur
        else:
            self.sequitur = Sequitur()
            model = None

        if self.options.shouldRampUp:
            model.rampUp()

        if self.options.trainSample:
            model = self.trainModel(model)
            if not model:
                print("failed to estimate or load model", file=self.log)
                return

        if not model:
            raise UsageError

        #       model.sequenceModel.showMostProbable(sys.stdout, model.sequitur.symbol, limit=250)

        if self.options.shouldTranspose:
            model.transpose()

        if self.options.newModelFile:
            oldSize, newSize = model.strip()
            print(
                "stripped number of multigrams from %d to %d" % (oldSize, newSize),
                file=self.log,
            )
            f = open(self.options.newModelFile, "wb")
            pickle.dump(model, f, pickle.HIGHEST_PROTOCOL)
            f.close()
            del f

        if self.options.shouldSelfTest:
            print(
                "warning: --self-test does not treat pronunciation variants correctly",
                file=self.log,
            )
            if not self.develSample:
                print(
                    "error: cannot do --self-test without --devel sample", file=self.log
                )
            else:
                translator = Translator(model)
                evaluator = Evaluator()
                evaluator.setSample(self.develSample)
                evaluator.verboseLog = self.log
                result = evaluator.evaluate(translator)
                print(result, file=self.log)

        return model


def procureModel(options, loadSample, log=sys.stdout):
    tool = Tool(options, loadSample, log)
    return tool.procureModel()


def addTrainOptions(optparser):
    optparser.add_option(
        "-t",
        "--train",
        dest="trainSample",
        help="read training sample from FILE",
        metavar="FILE",
    )
    optparser.add_option(
        "-d",
        "--devel",
        dest="develSample",
        help="read held-out training sample from FILE or use N% of the training data",
        metavar="FILE / N%",
    )
    optparser.add_option(
        "-x",
        "--test",
        dest="testSample",
        help="read test sample from FILE",
        metavar="FILE",
    )
    optparser.add_option(
        "--checkpoint",
        action="store_true",
        help="save state of training in regular time intervals"
        ". The name of the checkpoint file is derived from --write-model.",
    )
    optparser.add_option(
        "--resume-from-checkpoint",
        help="load checkpoint FILE and continue training",
        metavar="FILE",
    )
    optparser.add_option(
        "-T",
        "--transpose",
        dest="shouldTranspose",
        action="store_true",
        help="Transpose model, i.e. do phoneme-to-grapheme conversion",
    )
    optparser.add_option(
        "-m", "--model", dest="modelFile", help="read model from FILE", metavar="FILE"
    )
    optparser.add_option(
        "-n",
        "--write-model",
        dest="newModelFile",
        help="write model to FILE",
        metavar="FILE",
    )
    optparser.add_option(
        "--continuous-test",
        dest="shouldTestContinuously",
        action="store_true",
        help="report error rates on development and test set in each iteration",
    )
    optparser.add_option(
        "-S",
        "--self-test",
        dest="shouldSelfTest",
        action="store_true",
        help="apply model to development set and report error rates",
    )
    optparser.add_option(
        "-s",
        "--size-constraints",
        dest="lengthConstraints",
        help="""multigrams must have l1 ... l2 left-symbols and r1 ... r2 right-symbols""",
        metavar="l1,l2,r1,r2",
    )
    optparser.add_option(
        "-E",
        "--no-emergence",
        dest="shouldSuppressNewMultigrams",
        action="store_true",
        help="do not allow new joint-multigrams to be added to the model",
    )
    optparser.add_option(
        "--viterbi",
        action="store_true",
        help="estimate model using maximum approximation rather than true EM",
    )
    optparser.add_option(
        "-r",
        "--ramp-up",
        dest="shouldRampUp",
        action="store_true",
        help="ramp up the model",
    )
    optparser.add_option(
        "-W",
        "--wipe-out",
        dest="shouldWipeModel",
        action="store_true",
        help="wipe out probabilities, retain only model structure",
    )
    optparser.add_option(
        "-C",
        "--initialize-with-counts",
        dest="shouldInitializeWithCounts",
        action="store_true",
        help="estimate probabilities from overlapping occurence counts in first iteration",
    )
    optparser.add_option(
        "-i",
        "--min-iterations",
        dest="minIterations",
        type="int",
        default=ModelTemplate.minIterations,
        help="minimum number of EM iterations during training",
    )
    optparser.add_option(
        "-I",
        "--max-iterations",
        dest="maxIterations",
        type="int",
        default=ModelTemplate.maxIterations,
        help="maximum number of EM iterations during training",
    )
    optparser.add_option(
        "--eager-discount-adjustment",
        action="store_true",
        help="re-adjust discounts in each iteration",
    )
    optparser.add_option(
        "--fixed-discount", help="set discount to D and keep it fixed", metavar="D"
    )

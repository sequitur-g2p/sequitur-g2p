from __future__ import division, print_function

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

from sequitur_ import align

try:
    unicode
except NameError:
    # In Python 3:
    unicode = str


class Result:
    def __init__(self, name=None, tableFile=None, print_header=False):
        self.name = name
        self.tableFile = tableFile
        self.nStringsTranslated = 0
        self.nStringsFailed = 0
        self.nSymbolsTranslated = 0
        self.nSymbolsFailed = 0
        self.nInsertions = 0
        self.nDeletions = 0
        self.nSubstitutions = 0
        self.nStringErrors = 0
        if self.tableFile and print_header:
            print(self.build_row(True), file=self.tableFile)

    def build_row(
        self,
        header,
        source=tuple(),
        weight=None,
        nSymbols=None,
        nInsertions=None,
        nDeletions=None,
        nSubstitutions=None,
        nStringErrors=None,
    ):
        tableFormat = [
            ("entry", "".join(source)),
            ("weight", weight),
            ("symbols", nSymbols),
            ("ins", nInsertions),
            ("del", nDeletions),
            ("sub", nSubstitutions),
            ("err", nStringErrors),
        ]
        if header:
            row = [unicode(column) for column, var in tableFormat]
        else:
            row = [unicode(var) for column, var in tableFormat]
        return u"\t".join(row)

    def accu(self, source, reference, candidate, alignment, errors, weight=1):
        self.nStringsTranslated += weight
        if errors > 0:
            self.nStringErrors += weight
            nStringErrors = weight
        else:
            nStringErrors = 0
        nSymbols = len(reference) * weight
        self.nSymbolsTranslated += nSymbols

        nInsertions = 0
        nDeletions = 0
        nSubstitutions = 0
        for ss, rr in alignment:
            if ss is None:
                assert rr is not None
                nInsertions += weight
            elif rr is None:
                assert ss is not None
                nDeletions += weight
            elif ss == rr:
                pass
            else:
                nSubstitutions += weight
        self.nInsertions += nInsertions
        self.nDeletions += nDeletions
        self.nSubstitutions += nSubstitutions

        if self.tableFile:
            row = self.build_row(
                False,
                source=source,
                weight=weight,
                nSymbols=nSymbols,
                nInsertions=nInsertions,
                nDeletions=nDeletions,
                nSubstitutions=nSubstitutions,
                nStringErrors=nStringErrors,
            )
            print(row, file=self.tableFile)

    def accuFailure(self, reference, weight=1):
        self.nStringsFailed += weight
        self.nSymbolsFailed += len(reference) * weight

    def relativeCount(self, n, total):
        if total:
            return "%d (%1.2f%%)" % (n, 100.0 * float(n) / float(total))
        else:
            return "%d (n/a)" % n

    stringError = property(
        lambda self: self.relativeCount(self.nStringsIncorrect, self.nStrings)
    )
    symbolError = property(
        lambda self: self.relativeCount(self.nSymbolsIncorrect, self.nSymbols)
    )

    def __getattr__(self, attr):
        if attr.startswith("rc:"):
            n, m = attr[3:].split("/")
            return self.relativeCount(getattr(self, n), getattr(self, m))
        elif attr == "nStrings":
            return self.nStringsTranslated + self.nStringsFailed
        elif attr == "nStringsIncorrect":
            return self.nStringErrors + self.nStringsFailed
        elif attr == "nSymbols":
            return self.nSymbolsTranslated + self.nSymbolsFailed
        elif attr == "nSymbolErrors":
            return self.nInsertions + self.nDeletions + self.nSubstitutions
        elif attr == "nSymbolsIncorrect":
            return self.nSymbolErrors + self.nSymbolsFailed
        else:
            raise AttributeError(attr)

    def __getitem__(self, key):
        return getattr(self, key)

    template = """%(name)s
    total: %(nStrings)d strings, %(nSymbols)d symbols
    successfully translated: %(rc:nStringsTranslated/nStrings)s strings, %(rc:nSymbolsTranslated/nSymbols)s symbols
        string errors:       %(rc:nStringErrors/nStringsTranslated)s
        symbol errors:       %(rc:nSymbolErrors/nSymbolsTranslated)s
            insertions:      %(rc:nInsertions/nSymbolsTranslated)s
            deletions:       %(rc:nDeletions/nSymbolsTranslated)s
            substitutions:   %(rc:nSubstitutions/nSymbolsTranslated)s
    translation failed:      %(rc:nStringsFailed/nStrings)s strings, %(rc:nSymbolsFailed/nSymbols)s symbols
    total string errors:     %(rc:nStringsIncorrect/nStrings)s
    total symbol errors:     %(rc:nSymbolsIncorrect/nSymbols)s
    """

    def __str__(self):
        return self.template % self


def showAlignedResult(source, alignment, errors, out):
    vis = []
    for ss, rr in alignment:
        if ss is None:
            vis.append("\033[0;32m%s\033[0m" % rr)
        elif rr is None:
            vis.append("\033[0;31m[%s]\033[0m" % ss)
        elif ss == rr:
            vis.append("%s" % rr)
        else:
            vis.append("\033[0;31m%s/%s\033[0m" % (rr, ss))
    print(u"%s\t%s\t(%d errors)" % ("".join(source), " ".join(vis), errors), file=out)


def collateSample(sample):
    sources = []
    references = {}
    for source, reference in sample:
        if source in references:
            references[source].append(reference)
        else:
            sources.append(source)
            references[source] = [reference]
    return sources, references


class Evaluator(object):
    resultFile = None
    compareFilter = None
    verboseLog = None

    def setSample(self, sample):
        self.sources, self.references = collateSample(sample)

    def evaluate(self, translator):
        result = Result(tableFile=self.resultFile)
        for source in self.sources:
            references = self.references[source]
            if self.compareFilter:
                references = map(self.compareFilter, references)

            try:
                candidate = translator(source)
            except translator.TranslationFailure:
                result.accuFailure(references[0])
                continue

            if self.compareFilter:
                candidate = self.compareFilter(candidate)

            eval = []
            for reference in references:
                alignment, errors = align(reference, candidate)
                eval.append((errors, reference, alignment))
            eval.sort()
            errors, reference, alignment = eval[0]

            result.accu(source, reference, candidate, alignment, errors)
            if self.verboseLog:
                showAlignedResult(source, alignment, errors, self.verboseLog)

        return result

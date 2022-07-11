"""
Convert sequitur model to FSA.
"""

__author__ = "Maximilian Bisani"
__version__ = "$Revision: 1667 $"
__date__ = "$Date: 2007-06-02 16:32:35 +0200 (Sat, 02 Jun 2007) $"
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

import pickle
import sys
from xmlwriter import XmlWriter


def writeAsFsa(model, xml, shouldMakeClosure=True):
    sq = model.sequitur
    sm = model.sequenceModel

    xml.open("fsa", initial=0, type="transducer", semiring="tropical")

    def makeAlphabet(inv):
        for index, symbol in enumerate(inv.list):
            xml.element("symbol", symbol, index=index)

    xml.open("input-alphabet")
    makeAlphabet(sq.leftInventory)
    xml.close("input-alphabet")

    xml.open("output-alphabet")
    for disambi in range(sq.inventory.size()):
        sq.rightInventory.index("__%d__" % (disambi + 1))
    makeAlphabet(sq.rightInventory)
    xml.close("output-alphabet")

    initial = (None, None, sm.initial())
    idMap = {initial: 0}
    open = [initial]

    def makeArc(left, right, target, weight=None):
        inp = out = None
        if left:
            inp = left[0]
            left = left[1:]
        if not left:
            left = None

        if right:
            out = right[0]
            right = right[1:]
        if not right:
            right = None

        target = (left, right, target)
        try:
            targetId = idMap[target]
        except KeyError:
            targetId = idMap[target] = len(idMap)
            open.append(target)

        xml.open("arc", target=targetId)
        if inp or out:
            xml.comment((inp or "") + ":" + (out or ""))
        if inp:
            xml.element("in", sq.leftInventory.index(inp))
        if out:
            xml.element("out", sq.rightInventory.index(out))
        if weight:
            xml.element("weight", weight)
        xml.close("arc")

    while open:
        current = open.pop()
        currentId = idMap[current]
        left, right, current = current

        currentDesc = map(sq.symbol, sm.historyAsTuple(current))
        currentDesc = ["".join(ll) + ":" + "_".join(rr) for ll, rr in currentDesc]
        if left or right:
            currentDesc += ["/", "".join(left or ()) + ":" + "_".join(right or ())]
        currentDesc = " ".join(currentDesc)

        xml.open("state", id=currentId)
        xml.comment(currentDesc)
        if left or right:
            makeArc(left, right, current)
        else:
            for predicted, score in sm.getNode(current):
                if predicted == sq.term:
                    xml.element("final")
                    xml.element("weight", score)
                if predicted is None:
                    target = sm.shortened(current)
                    if target:
                        makeArc(None, None, target, score)
                elif predicted != sq.term or shouldMakeClosure:
                    target = sm.advanced(current, predicted)
                    left, right = sq.symbol(predicted)
                    right = right + ("__%d__" % predicted,)
                    makeArc(left, right, target, score)
        xml.close("state")
    xml.close("fsa")


def main(options, args):
    model = pickle.load(open(options.modelFile, "rb"),encoding=options.encoding)
    with open(options.fsaFile, "wb") as out:
        writeAsFsa(model, XmlWriter(out, "UTF-8"))


# ===========================================================================
if __name__ == "__main__":
    import optparse
    import tool

    optparser = optparse.OptionParser(
        usage="%prog [OPTION]... FILE...\n" + __doc__, version="%prog " + __version__
    )
    tool.addOptions(optparser)
    optparser.add_option(
        "-e", "--encoding", default="UTF-8",help="read model in given ENCODING", metavar="ENC"
    )
    optparser.add_option(
        "-m", "--model", dest="modelFile", help="read model from FILE", metavar="FILE"
    )
    optparser.add_option(
        "-o", "--fsa", dest="fsaFile", help="write fsa to FILE", metavar="FILE"
    )
    options, args = optparser.parse_args()
    tool.run(main, options, args)

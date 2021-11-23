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


class SymbolInventory:
    """
    0 (zero) is __void__ which is used internally as a terminator to
    indicate end of a multigram

    1 (one) is __term__, the end-of-string symbol (similar to the
    end-of-sentence word in language modeling).

    """

    term = 1

    def __init__(self):
        self.list = ["__void__", "__term__"]
        self.dir = {"__term__": self.term}

    def size(self):
        "The number of symbols, including __term__, but not counting __void__."
        return len(self.list) - 1

    def index(self, sym):
        try:
            return self.dir[sym]
        except KeyError:
            result = self.dir[sym] = len(self.list)
            self.list.append(sym)
            return result

    def parse(self, seq):
        return tuple(map(self.index, list(seq)))

    def symbol(self, ind):
        return self.list[ind]

    def format(self, seq):
        return tuple(map(self.symbol, seq))

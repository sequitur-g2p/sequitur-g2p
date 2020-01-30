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
import codecs


class XmlWriter:
    def __init__(self, file, encoding='UTF-8'):
        self.path = []
        self.encoding = encoding
        encoder, decoder, streamReader, streamWriter = codecs.lookup(encoding)
        self.file = streamWriter(file)
        self.margin = 78

    def write(self, data):
        self.file.write(data)

    def begin(self):
        self.write('<?xml version="1.0" encoding="%s"?>\n' %
                   self.encoding)

    def end(self):
        assert len(self.path) == 0
        pass

    def indent_str(self):
        return '  ' * len(self.path)

    def escapeSpecialCharacters(self, w):
        w = w.replace('&', '&amp;')
        w = w.replace('<', '&lt;')
        w = w.replace('>', '&gt;')
        return w

    def formTag(self, element, attr=[]):
        result = " ".join([element] + ['%s="%s"' % kv for kv in attr])
        return self.escapeSpecialCharacters(result)

    def open(self, element, **args):
        attr = [k_v1 for k_v1 in list(args.items()) if k_v1[1] is not None]
        self.write(self.indent_str() +
                   '<' + self.formTag(element, attr) + '>\n')
        self.path.append(element)

    def empty(self, element, **args):
        attr = [k_v2 for k_v2 in list(args.items()) if k_v2[1] is not None]
        self.write(self.indent_str() +
                   '<' + self.formTag(element, attr) + '/>\n')

    def close(self, element):
        assert element == self.path[-1]
        del self.path[-1]
        self.write(self.indent_str() + '</' + element + '>\n')

    def openComment(self):
        self.write('<!--\n')
        self.path.append('<!--')

    def closeComment(self):
        assert self.path[-1] == '<!--'
        del self.path[-1]
        self.write('-->\n')

    formatRaw = 0
    formatIndent = 1
    formatBreakLines = 2
    formatFill = 3

    def fillParagraph(self, w):
        indent_str = self.indent_str()
        ll = []
        fragment = []
        n = len(indent_str)
        for a in w.split():
            if n + len(a) < self.margin:
                n = n + len(a) + 1
                fragment.append(a)
            else:
                ll.append(indent_str + " ".join(fragment))
                fragment = [a]
                n = len(indent_str) + len(a)
        if len(fragment) > 0:
            ll.append(indent_str + " ".join(fragment))
        return ll

    def cdata(self, w, format=formatFill):
        if 'u<!--' in self.path:
            # comment must not contain double-hyphens
            w = w.replace('--', '=')
        if format == self.formatRaw:
            out = [w]
        elif format == self.formatIndent:
            indentStr = self.indent_str()
            out = [indentStr + line for line in w.split('\n')]
        elif format == self.formatBreakLines:
            out = [self.fillParagraph(line) for line in w.split('\n')]
            out = ''.join(out)
        elif format == self.formatFill:
            out = self.fillParagraph(w)
        self.write("\n".join(out) + '\n')

    def formatted_cdata(self, s):
        for w in s.split('\\n'):
            self.cdata(w, self.formatFill)

    def comment(self, comment):
        # comment must not contain double-hyphens
        comment = comment.replace('--', '=')
        self.cdata('<!-- ' + comment + ' -->')

    def element(self, element, cdata=None, **args):
        if cdata is None:
            self.empty(*(element,), **args)
        else:
            attr = [k_v for k_v in list(args.items()) if k_v[1] is not None]
            s = self.indent_str() \
                + '<' + self.formTag(element, attr) + '>' \
                + self.escapeSpecialCharacters(str(cdata)) \
                + '</' + element + '>'
            if len(s) <= self.margin:
                self.write(s + '\n')
            else:
                # apply(self.open, (element,), args)
                self.open(*(element,), **args)
                self.cdata(cdata)
                self.close(element)

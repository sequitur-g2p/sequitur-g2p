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

import codecs, string, types

class XmlWriter:
    def __init__(self, file, encoding='ISO-8859-1'):
	self.path = []
	self.encoding = encoding
	encoder, decoder, streamReader, streamWriter = codecs.lookup(encoding)
	self.file = streamWriter(file)
	self.margin = 78

    def write(self, data):
	self.file.write(data)

    def begin(self):
	self.write(u'<?xml version="1.0" encoding="%s"?>\n' %
		   self.encoding)

    def end(self):
	assert len(self.path) == 0
	pass

    def indent_str(self):
	return u'  ' * len(self.path)

    def escapeSpecialCharacters(self, w):
	w = string.replace(w, '&', '&amp;')
	w = string.replace(w, '<', '&lt;')
	w = string.replace(w, '>', '&gt;')
	return w

    def formTag(self, element, attr=[]):
	result = string.join([element] + [ u'%s="%s"' % kv for kv in attr ])
	return self.escapeSpecialCharacters(result)

    def open(self, element, **args):
	attr = filter(lambda (k, v): v is not None, args.items())
	self.write(self.indent_str() + u'<' + self.formTag(element, attr) + u'>\n')
	self.path.append(element)

    def empty(self, element, **args):
	attr = filter(lambda (k, v): v is not None, args.items())
	self.write(self.indent_str() + u'<' + self.formTag(element, attr) + u'/>\n')

    def close(self, element):
	assert element == self.path[-1]
	del self.path[-1]
	self.write(self.indent_str() + u'</' + element + u'>\n')

    def openComment(self):
	self.write(u'<!--\n')
	self.path.append('u<!--')

    def closeComment(self):
	assert self.path[-1] == 'u<!--'
	del self.path[-1]
	self.write(u'-->\n')

    formatRaw = 0
    formatIndent = 1
    formatBreakLines = 2
    formatFill = 3

    def fillParagraph(self, w):
	indent_str = self.indent_str()
	ll = []
	l = [] ; n = len(indent_str)
	for a in w.split():
	    if n + len(a) < self.margin:
		n = n + len(a) + 1
		l.append(a)
	    else:
		ll.append(indent_str + string.join(l))
		l = [a] ; n = len(indent_str) + len(a)
	if len(l) > 0:
	    ll.append(indent_str + string.join(l))
	return ll

    def cdata(self, w, format = formatFill):
	if 'u<!--' in self.path:
	    w = w.replace(u'--', u'=') # comment must not contain double-hyphens
	if format == self.formatRaw:
	    out = [ w ]
	elif format == self.formatIndent:
	    indentStr = self.indent_str()
	    out = [ indentStr + line for line in w.split(u'\n') ]
	elif format == self.formatBreakLines:
	    out = [ self.fillParagraph(line) for line in w.split(u'\n') ]
	    out = reduce(operator.add, out)
	elif format == self.formatFill:
	    out = self.fillParagraph(w)
	self.write(string.join(out, u'\n') + u'\n')

    def formatted_cdata(self, s):
	for w in string.split(s, u'\\n'):
	    self.cdata(w, self.formatFill)

    def comment(self, comment):
	comment = string.replace(comment, u'--', u'=') # comment must not contain double-hyphens
	self.cdata(u'<!-- ' + comment + u' -->')

    def element(self, element, cdata=None, **args):
	if cdata is None:
	    apply(self.empty, (element,), args)
	else:
	    attr = filter(lambda (k, v): v is not None, args.items())
	    s = self.indent_str() \
		+ u'<' + self.formTag(element, attr) + u'>' \
		+ unicode(cdata) \
		+ u'</' + element + u'>'
	    if len(s) <= self.margin:
		self.write(s + u'\n')
	    else:
		apply(self.open, (element,), args)
		self.cdata(cdata)
		self.close(element)

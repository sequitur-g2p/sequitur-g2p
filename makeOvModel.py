#!/usr/bin/env python

"""
Create an open-vocabulary speech recognition model
(comprising a lexicon and a language model)

currently implements:
- flat hybrid model

state of each word
- used for g2p training
- as "true" word in recognition vocabulary
- treated as "OOV" in hybrid LM
  (i.e. converted to fragments with unsupervised G2P)
- treated as "known OOV" in building hybrid LM:  yes/no
  (i.e. converted to fragments with supervised segmentation)


procedure:
1. load reference lexicon
2. load models for fragmentizing unknown words (Sequitur G2P model)
3. add fragements to lexicon and store augmented lexicon
4. determine set of LM tokens
5. create modified LM training corpus counts
6. count LM events
7. (optional) dump list of fragmentized OOV words
8. (optional) dump modified LM training corpus
"""

__author__    = 'Maxilian Bisani'
__version__   = '$Revision: 1.14 $'
__date__      = '$Date: 2005/04/21 14:00:58 $'
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

import sys
import codecs
import cPickle as pickle
from elementtree.ElementTree import ElementTree, Element, Comment, SubElement
from itertools import ifilter, starmap
import mGramCounts
from sequitur import Segmenter, Translator
from g2p import loadBlissLexicon
from misc import gOpenIn, gOpenOut, set, reversed

# ===========================================================================
nonLmTokens = set("""
"QUOTE
"UNQUOTE
"BEGIN-QUOTE
"END-QUOTE
%PERCENT
.POINT
/SLASH
""".split())

def isLmToken(word):
    return word not in nonLmTokens

# ===========================================================================
def lmToken(letters, phonemes):
    return '*' + ''.join(letters) + ':' + '_'.join(phonemes) + '*'

def addGraphonesToLexicon(xml, graphones):
    lexicon = xml.getroot()
    for letters, phonemes in graphones:
	lemma = SubElement(lexicon, 'lemma')
	lemma.text = '\n  '
	orth = SubElement(lemma, 'orth')
	orth.text = '_' + ''.join(letters) + '_'
	orth.tail = '\n  '
	phon = SubElement(lemma, 'phon')
	phon.text = ' '.join(phonemes)
	phon.tail = '\n  '
	synt = SubElement(lemma, 'synt')
	SubElement(synt, 'tok').text = lmToken(letters, phonemes)
	synt.tail = '\n'
#       synt.tail = '\n  '
#       eval = SubElement(lemma, 'eval')
#       SubElement(eval, 'tok').text = '[UNKNOWN]'
#       eval.tail = '\n'
	lemma.tail = '\n'

def changeSyntaticToPhonetic(xml):
    lexicon = xml.getroot()
    for lemma in lexicon.getiterator('lemma'):
	if lemma.get('special'): continue
	phon = lemma.find('phon')
	if phon is not None:
	    phon = phon.text.split()
	    phon.append('#1')
	synt = lemma.find('synt')
	if synt is None:
	    synt = SubElement(lemma, 'synt')
	else:
	    synt.clear()
	synt.tail = '\n  '
	if phon:
	    for ph in phon:
		SubElement(synt, 'tok').text = ph

# ===========================================================================
class Fragmentizer:
    def __init__(self, model):
	self.model = model
	self.translator = Translator(self.model)
	self.memory = dict()

    def addSupervised(self, lexicon=None):
	"""
	Caveat: supervised splitting might come up with graphones that
	are NOT present in the model g2p, because they were trimmed!
	Therefore this function may modify the sequitur inventory.
	"""
	segmenter = Segmenter(self.model)
	fragments = set()
	for orth, phon in lexicon:
	    logLik, joint = segmenter.firstBestJoint(orth, phon)
	    for fragment in joint:
		fragments.add(fragment)
	    joint = [ lmToken(gra, pho) for gra, pho in joint ]
	    if orth not in self.memory: self.memory[orth] = []
	    self.memory[orth].append(joint)

	oldSize, newSize = self.model.strip()
	print 'stripped number of multigrams from %d to %d' % (oldSize, newSize)

	sequitur = self.model.sequitur
	for gra, pho in fragments:
	    fragment = ( sequitur.leftInventory.parse(gra),
			 sequitur.rightInventory.parse(pho) )
	    sequitur.inventory.index(fragment)
	self.translator.setModel(self.model)

    def __call__(self, word):
	translations = []
	if word in self.memory:
	    translations = self.memory[word]
	else:
	    try:
		logLik, joint = self.translator.firstBestJoint(word)
		joint = [ lmToken(gra, pho) for gra, pho in joint ]
		translations.append(joint)
	    except Translator.TranslationFailure:
		print 'failed to represent "%s" using graphones' % word
		translations.append([word+'[UNKNOWN]'])
	return translations


class RotatingDict:
    def __init__(self, items=[]):
	self.store = dict(items)

    def __contains__(self, key):
	return key in self.store

    def __getitem__(self, key):
	variants = self.store[key]
	result = variants[0]
	if len(variants) > 1:
	    self.store[key] = variants[1:] + variants[:1]
	return result

    def __setitem__(self, key, values):
	self.store[key] = tuple(values)

    def add(self, key, value):
	self.store[key] = self.store.get(key, ()) + (value,)


class EventGenerator:
    specialEvents = set([
	'<s>', '</s>' ])

    def __init__(self, knownWords, fragmentizer, order):
	self.knownWords = set(knownWords)
	self.fragmentizer = fragmentizer
	self.order = order
	self.rotor = RotatingDict()

    def fragmentize(self, word):
	if word not in self.rotor:
	    self.rotor[word] = tuple(self.fragmentizer(word))
	return self.rotor[word]

    def frobnicate(self, rawWords):
	raise NotImplementedError

    def __call__(self, source):
	for line in source:
	    words = line.split()
	    if words[0] != '<s>':
		assert words[-1] != '</s>'
		words = ['<s>'] + words + ['</s>']
	    for event in self.frobnicate(words):
		yield event, 1

class HybridEventGenerator(EventGenerator):
    def frobnicateWord(self, w):
	if w in self.knownWords or w in self.specialEvents:
	    return (w,)
	else:
	    return self.fragmentize(w)

    def frobnicateWithFragmentRange(self, rawWords):
	return mGramCounts.mGramsFromSequence(
	    [  f
	       for w in rawWords
	       for f in self.frobnicateWord(w) ],
	    self.order)

    def frobnicateWithTrueWordRange(self, rawWords):
	for i in xrange(len(rawWords)):
	    history = [ f
			for w in rawWords[max(0, i - self.order) : i]
			for f in self.frobnicateWord(w) ]
	    for f in self.frobnicateWord(rawWords[i]):
		yield tuple(reversed(history)), f
		history.append(f)

    def setTrueWordRange(self):
	self.frobnicate = self.frobnicateWithTrueWordRange

    def setFragmentRange(self):
	self.frobnicate = self.frobnicateWithFragmentRange


class OovEventGenerator(EventGenerator):
    def frobnicate(self, rawWords):
	mGrams = []
	for w in rawWords:
	    if w in self.knownWords: continue
	    if w in self.specialEvents: continue
	    fragments = self.fragmentize(w)
	    fragments = ['<s>'] + fragments + ['</s>']
	    mGrams += mGramCounts.mGramsFromSequence(fragments, self.order)
	return mGrams


class PhonemeEventGenerator(EventGenerator):
    def __init__(self, lexicon, order):
	self.lexicon = RotatingDict()
	for orth, phon in lexicon:
	    self.lexicon.add(orth, phon)
	self.order = order

    def frobnicate(self, rawWords):
	phon = []
	for w in rawWords:
	    if w in self.specialEvents:
		phon.append(w)
	    elif w in self.lexicon:
		phon += self.lexicon[w]
		phon += ['#1']
	    else:
#               phon += ['mul', '#1']
		pass
	return mGramCounts.mGramsFromSequence(phon, self.order)

class OovFragmentGenerator:
    specialEvents = set([
        '<s>', '</s>' ])
    
    def __init__(self, knownWords, fragmentizer):
        self.knownWords = set(knownWords)
        self.fragmentizer = fragmentizer
        self.rotor = RotatingDict()
        self.fragmentDict = {}

    def fragmentize(self, word):
        if word not in self.rotor:
            self.rotor[word] = tuple(self.fragmentizer(word))
        return self.rotor[word]

    def __call__(self, source):
        for line in source:
            words = line.split()
            self.frobnicate(words)
        return self.fragmentDict
    
    def frobnicate(self, rawWords):
        for w in rawWords:
            if w in self.knownWords: continue
            if w in self.specialEvents: continue
            if w in self.fragmentDict.keys(): continue
            fragments = self.fragmentize(w)
            self.fragmentDict[w]=fragments

    def modifyLmText(self, rawWords):
        modWords=[]
        for w in rawWords:
            if w in self.knownWords:
                modWords.append(w)
            elif w in self.specialEvents:
                modWords.append(w)
            else:
                fragments=self.fragmentize(w)
                modWords.append(' '.join(fragments))
        return modWords


# ===========================================================================
def main(options, args):
    # 1. load reference lexicon
    print 'loading reference lexicon ...'
    lexicon = loadBlissLexicon(options.lexicon)
    knownWords = set([ orth for orth, phon in lexicon ])

    # 2. load model for fragmentizing unknown words
    if options.subliminal_lexicon:
	print 'loading subliminal lexicon ...'
	subliminalLexicon = loadBlissLexicon(options.subliminal_lexicon)
    else:
	subliminalLexicon = None

    if options.subliminal_g2p:
	print 'loading subliminal g2p model ...'
	subliminalG2p = pickle.load(open(options.subliminal_g2p))
    else:
	subliminalG2p = None

    if options.g2pModel:
	print 'loading g2p model ...'
	model = pickle.load(open(options.g2pModel))
	oldSize, newSize = model.strip()
	print 'stripped number of multigrams from %d to %d' % (oldSize, newSize)

	fragmentizer = Fragmentizer(model)
	if subliminalLexicon:
	    fragmentizer.addSupervised(subliminalLexicon)
	if subliminalG2p:
	    fragmentizer.addSupervised(subliminalG2p)
	graphones = model.sequitur.symbols()
	graphones.remove(model.sequitur.symbol(model.sequitur.term))
    else:
	model = fragmentizer = graphones = None

    # 3. add fragments to lexicon
    if options.write_lexicon:
	print 'creating extended lexicon ...'
	xmlLexicon = ElementTree(file = options.lexicon)
	if options.model_type == 'phonemes':
	    changeSyntaticToPhonetic(xmlLexicon)
	else:
	    addGraphonesToLexicon(xmlLexicon, graphones)
	xmlLexicon.write(gOpenOut(options.write_lexicon), defaultEncoding)

    # 4. determine set of LM tokens
    vocabulary = mGramCounts.ClosedVocablary()
    vocabulary.add(['<s>', '</s>'])
    if options.model_type == 'flat-hybrid':
	vocabulary.add(ifilter(isLmToken, knownWords), soft=True)
    if graphones:
	vocabulary.add(starmap(lmToken, graphones))
    vocabulary.sort()
    if options.write_tokens:
	f = gOpenOut(options.write_tokens, defaultEncoding)
	if options.model_type == 'phonemes':
	    phonemes = set(p for orth, phon in lexicon for p in phon)
	    phonemes.add('#1')
	    if 'si' in phonemes: phonemes.remove('si')
	    for p in sorted(phonemes):
		print >> f, p
	else:
	    for w in vocabulary:
		if w is not None:
		    print >> f, w

    # 5./6. set-up LM event generator
    if options.write_counts or options.write_events:
	order = options.order - 1
	if options.model_type == 'flat-hybrid':
	    events = HybridEventGenerator(knownWords, fragmentizer, order)
	    if options.range_type == 'fragments':
		events.setFragmentRange()
	    elif options.range_type == 'words':
		events.setTrueWordRange()
	    else:
		assert ValueError(options.range_type)
	elif options.model_type == 'fragments':
	    events = OovEventGenerator(knownWords, fragmentizer, order)
	elif options.model_type == 'phonemes':
	    events = PhonemeEventGenerator(lexicon, order)

    # 5. create modified LM training corpus counts
    if options.write_events:
	print 'creating sequence model events ...'
	f = gOpenOut(options.write_events, defaultEncoding)
	for event, count in events(gOpenIn(options.text, defaultEncoding)):
	    print >> f, repr(event), '\t', count

    # 6. count LM events
    if options.write_counts:
	print 'creating sequence model counts ...'
	counts = mGramCounts.SimpleMultifileStorage()
	counts.addIter(events(gOpenIn(options.text, defaultEncoding)))
	mGramCounts.TextStorage.write(gOpenOut(options.write_counts, defaultEncoding), counts)

    # 7. dump list of OOV words and their corresponding fragmentation
    if options.write_fragments:
        print 'dumping fragments ...'
        f = gOpenOut(options.write_fragments, defaultEncoding)
        events = OovFragmentGenerator(knownWords, fragmentizer)
        fragments =  events(gOpenIn(options.text, defaultEncoding))
        for event in fragments.keys():
            print >> f, event, '\t', ' '.join(fragments[event])

    # 8. dump modified LM training text
    if options.write_lm_text:
        print 'dumping modified LM training text ...'
        f = gOpenOut(options.write_lm_text, defaultEncoding)
        events = OovFragmentGenerator(knownWords, fragmentizer)
        for line in gOpenIn(options.text, defaultEncoding):
            words = line.split()
            modWords =  events.modifyLmText(words)
            print >> f, " ".join(modWords)
        


# ===========================================================================
if __name__ == '__main__':
    import optparse
    optparser = optparse.OptionParser(
	usage   = '%prog [OPTION]... FILE...\n' + __doc__,
	version = '%prog ' + __version__)
    optparser.add_option(
	'-e', '--encoding', default='UTF-8',
	help='use character set encoding ENC', metavar='ENC')
    optparser.add_option(
	'-t', '--text',
	help="read original LM training data from FILE", metavar="FILE")
    optparser.add_option(
	'-l', '--lexicon',
	help="""use FILE as baseline lexicon""", metavar='FILE')
    optparser.add_option(
	'--subliminal-lexicon',
	help="""use FILE as subliminal lexicon ("known unknown" words)""", metavar='FILE')
    optparser.add_option(
	'--subliminal-g2p',
	help="""use Sequitur model FILE as a subliminal grapheme-to-phoneme model""", metavar='FILE')
    optparser.add_option(
	'-g', '--g2p', dest='g2pModel',
	help="""use Sequitur grapheme-to-phoneme model FILE to fragmentize unknown words""", metavar='FILE')

    optparser.add_option(
	'--write-lexicon',
	help="""write new lexicon to FILE""", metavar='FILE')
    optparser.add_option(
	'--write-fragments',
	help="""write OOV words and their fragmentation to FILE""", metavar='FILE')
    optparser.add_option(
	'--write-lm-text',
	help="""write new LM text to FILE""", metavar='FILE')
    optparser.add_option(
	'--write-tokens',
	help="write list of sequence model tokens to FILE", metavar='FILE')
    optparser.add_option(
	'--model-type',
	help="type of model: flat-hybrid, fragments, phonemes")
    optparser.add_option(
	'--range-type', default='fragments',
	help="--order refers to words/fragments", metavar="words/fragments")
    optparser.add_option(
	'-M', '--order', type='int', default=3,
	help="generate/count events of order M ", metavar='M')
    optparser.add_option(
	'--write-events',
	help="write new LM events to FILE (mainly for testing)", metavar='FILE')
    optparser.add_option(
	'--write-counts',
	help="write new LM counts to FILE", metavar='FILE')
    options, args = optparser.parse_args()

    global defaultEncoding
    defaultEncoding = options.encoding
    import g2p
    g2p.defaultEncoding = defaultEncoding
    sys.stdout = codecs.getwriter(defaultEncoding)(sys.stdout)

    main(options, args)

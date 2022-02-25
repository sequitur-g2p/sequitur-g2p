[![Build Status](https://travis-ci.com/sequitur-g2p/sequitur-g2p.svg?branch=master)](https://travis-ci.com/sequitur-g2p/sequitur-g2p)
Sequitur G2P
============

A trainable Grapheme-to-Phoneme converter.

Introduction
------------

Sequitur G2P is a data-driven grapheme-to-phoneme converter written at
RWTH Aachen University by Maximilian Bisani.

The method used in this software is described in

```
   M. Bisani and H. Ney: "Joint-Sequence Models for Grapheme-to-Phoneme
   Conversion". Speech Communication, Volume 50, Issue 5, May 2008,
   Pages 434-451

   (available online at http://dx.doi.org/10.1016/j.specom.2008.01.002)
```

This software is made available to you under terms of the GNU Public
License. It can be used for experimentation and as part of other free
software projects. For details see the licensing terms below.

If you publish about work that involves the use of this software,
please cite the above paper. (You should feel obliged to do so by
rules of good scientific conduct.)

The original README contains also these lines:
*You may contact the author with any questions or comments via e-mail:
maximilian.bisani@rwth-aachen.de. For questions regarding current
releases of Sequitur G2P contact Pavel Golik (golik@cs.rwth-aachen.de).*
but we are not sure how active they are. If needed, feel free to create
an issue on https://github.com/sequitur-g2p/sequitur-g2p. We will try to help.


License
-------

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


Installing
----------

To build and use this software you need to have the following part installed:
- Python (http://www.python.org)
  tested with 2.5, 2.7 and 3.6
- SWIG (http://www.swig.org)
  tested with 1.3.31
- NumPy (http://numpy.scipy.org)
  tested with 1.0.4
- a C++ compiler that's recognized by Python's distutils.
  tested with GCC 4.1, 4.2 and 4.3

To install change to the source directory and type:
    ```python setup.py install --prefix /usr/local```
You may substitute /usr/local with some other directory.  If you do so
make sure that `some-other-directory/lib/python2.5/site-packages/` is in
your PYTHONPATH, e.g. by typing
    ```export PYTHONPATH=some-other-directory/lib/python2.7/site-packages```

You can also install via `pip` by pointing it at this repository. You still
need SWIG and a C++ compiler.
```
pip install numpy
pip install git+https://github.com/sequitur-g2p/sequitur-g2p@master
```

Note, when installing on MacOS, you might run into issues due to the default
libc being clang's one. If that is the case, try installing it with:
```
CPPFLAGS="-stdlib=libstdc++" pip install git+https://github.com/sequitur-g2p/sequitur-g2p@master
```


Using
-----

Sequitur G2P is a data-driven grapheme-to-phoneme converter.
Actually, it can be applied to any monotonous sequence translation
problem, provided the source and target alphabets are small (less than
255 symbols).  Data-driven means that you need to train it with
example pronunciations.  It has no built-in linguistic knowledge
whatsoever, which means that it should work for any alphabetic
language.  Training takes a pronunciation dictionary and creates a
model file.  The model file can then be used to transcribe words that
where not in the dictionary.

Here is step-by-step guide to get you started:

1. Obtain a pronunciation dictionary for training.
   The format is one word per line.  Each line contains the
   orthographic form of the word followed by the corresponding
   phonemic transcription.  The word and all phonemes need to be
   separated by white space.  The word and phoneme symbols may thus
   not contain blanks.  We'll assume your training lexicon is called
   train.lex, and that you set aside some portion for testing purposes
   as test.lex, which is disjoint from train.lex.

2. Train a model.
   To create a first model type:

   ```g2p.py --train train.lex --devel 5% --write-model model-1```

   This first model will be rather poor because it is only a unigram.
   To create higher order models you need to run g2p.py again:

   ```g2p.py --model model-1 --ramp-up --train train.lex --devel 5% --write-model model-2```

   Repeat this a couple of times

   ```
   g2p.py --model model-2 --ramp-up --train train.lex --devel 5% --write-model model-3
   g2p.py --model model-3 --ramp-up --train train.lex --devel 5% --write-model model-4
   ...
   ```



3. Evaluate the model.
   To find out how accurately your model can transcribe unseen words type:

   ```g2p.py --model model-6 --test test.lex```

4. Transcribe new words.
   Prepare a list of words you want to transcribe as a simple text
   file words.txt with one word per line (and no phonemic
   transcription), then type:

   ```g2p.py --model model-3 --apply words.txt```


Random comments:
- You cannot open models created in a `python3` environment inside a
  python2 environment. The opposite works.
- Whenever a file name is required, you can specify `"-"` to mean
  standard in, or standard out.
- If a file name ends in `".gz"`, it is assumed that the file is (or
  should be) compressed using gzip.
- For the  time being you need to type `g2p.py --help`  and/or read the
  source to find out the other things `g2p.py` can do.  Sorry about that.

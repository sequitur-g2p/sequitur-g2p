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

import os
import numpy

from setuptools import setup, Extension
from setuptools.command.build_py import build_py as _build_py

VERSION = "1.0.1668.30"

with open("requirements.txt") as fp:
    required = fp.read().splitlines()


with open("README.md", "r") as fh:
    long_description = fh.read()


class build_py(_build_py):
    """Build SWIG extension before Python modules."""

    def run(self):
        self.run_command("build_ext")
        return _build_py.run(self)


sequiturExtension = Extension(
    "_sequitur_",
    language="c++",
    define_macros=[("MULTIGRAM_SIZE", "4")],
    sources=[
        "sequitur.i",
        "Assertions.cc",
        "Types.cc",
        "Utility.cc",
        "Graph.cc",
        "Multigram.cc",
    ],
    depends=[
        "Assertions.hh",
        "Graph.hh",
        "Multigram.hh",
        "MultigramGraph.hh",
        "Multigram.hh",
        "Obstack.hh",
        "PriorityQueue.hh",
        "Probability.hh",
        "Python.hh",
        "SequenceModel.hh",
        "Types.hh",
        "Utility.hh",
        "EditDistance.cc",
        "Estimation.cc",
        "SequenceModel.cc",
        "Translation.cc",
    ],
    include_dirs=[numpy.get_include()],
    extra_compile_args=[
        "-std=c++11",
        "-DNPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION",
        "-pedantic",
    ],
)

sequiturModules = [
    "Evaluation",
    "Minimization",
    "SequenceModel",
    "SequiturTool",
    "g2p",
    "misc",
    "sequitur",
    "sequitur_",
    "symbols",
    "tool",
]

sequiturScripts = ["g2p.py"]


# os.system("cython -3  SparseVector.pyx")
# sparseExtension = Extension("SparseVector", language="c", sources=["SparseVector.c"])
# os.system('pyrexc IntTuple.pyx')
# intTupleExtension = Extension('IntTuple', ['IntTuple.c'])

lmModules = [
    "IterMap",
    "mGramCounts",
    "groupedCounts",
    "SimpleGoodTuring",
    "LanguageModel",
    "makeOvModel",
]
lmScripts = ["makeOvModel.py"]


setup(
    name="sequitur-g2p",
    version=VERSION,
    license="gpl-2.0",
    description="sequence and joint-sequence modelling tool for g2p",
    keywords="g2p grapheme-to-phoneme sequitur grapheme phoneme",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Maximilian Bisani",
    author_email="unknown@example.com",
    maintainer="Jan 'Yenda' Trmal",
    maintainer_email="jtrmal@gmail.com",
    url="https://github.com/sequitur-g2p/sequitur-g2p",
    project_urls={
        "Original site": "https://www-i6.informatik.rwth-aachen.de/web/Software/g2p.html",
        "Bug Tracker": "https://github.com/sequitur-g2p/sequitur-g2p/issues",
    },
    cmdclass={"build_py": build_py},
    install_requires=required,
    py_modules=sequiturModules,
    ext_modules=[sequiturExtension],
    scripts=sequiturScripts,
    classifiers=[
        "Development Status :: 6 - Mature",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9.0",
)

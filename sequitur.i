/*
 * $Id: sequitur.ii,v 1.26 2005/01/27 14:05:32 bisani Exp $
 *
 * Copyright (c) 2004-2005  RWTH Aachen University
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License Version 2 (June
 * 1991) as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, you will find it at
 * http://www.gnu.org/licenses/gpl.html, or write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110,
 * USA.
 *
 * Should a provision of no. 9 and 10 of the GNU General Public License
 * be invalid or become invalid, a valid provision is deemed to have been
 * agreed upon which comes closest to what the parties intended
 * commercially. In any case guarantee/warranty shall be limited to gross
 * negligent actions or intended actions or fraudulent concealment.
 */

%module sequitur_

%{
#include "Python.hh"
%}

%{
#include <iostream>
namespace AssertionsPrivate {
    void stackTrace(std::ostream&, int cutoff);
}
%}

%exception {
    try {
        $function
    } catch (ExistingPythonException) {
        return NULL;
    } catch (PythonException &e) {
        PyErr_SetString(e.type_, e.message_);
        return NULL;
    } catch (const std::exception &e) {
        AssertionsPrivate::stackTrace(std::cerr, 0);
        PyErr_SetString(PyExc_RuntimeError, const_cast<char*>(e.what()));
        return NULL;
    } catch (...) {
        PyErr_SetString(PyExc_RuntimeError, "unspecified exception");
        return NULL;
    }
}

#ifdef SWIGPYTHON
%typemap(in) FILE* {
    if (!PyFile_Check($input)) {
        PyErr_SetString(PyExc_TypeError,"not a file");
        SWIG_fail;
    }
    $1 = PyFile_AsFile($input);
}
%typemap(in) std::string {
    if (!PyString_Check($input)) {
        PyErr_SetString(PyExc_TypeError,"not a string");
        SWIG_fail;
    }
    $1 = std::string(PyString_AsString($input));
}
#endif  // SWIGPYTHON

%{
#include "numpy/ndarrayobject.h"
#include "numpy/arrayobject.h"
    typedef PyArrayObject* DoubleVector;
%}
%init %{
    import_array()
%}
#ifdef SWIGPYTHON
%typemap(in) DoubleVector {
    $1 = (PyArrayObject*) PyArray_ContiguousFromObject($input, NPY_DOUBLE, 1, 1);
    if ($1 == NULL) SWIG_fail;
}
%typemap(freearg) DoubleVector {
    Py_DECREF($1);
}
#endif  // SWIGPYTHON

// ===========================================================================
%{
#include "EditDistance.cc"
%}

%native(align) python_align;

// ===========================================================================
%{
#include "Multigram.hh"
%}

#ifdef SWIGPYTHON
%typemap(in) Sequence {
    PyObject *seq = PySequence_Fast($input, "not a sequence");
    if (!seq) SWIG_fail;
    int length = PySequence_Fast_GET_SIZE(seq);
    $1.reserve(length);
    for (int i = 0; i < length; ++i) {
        PyObject *sym = PySequence_Fast_GET_ITEM(seq, i);
        if (!PyInt_Check(sym)) {
            Py_DECREF(seq);
            PyErr_Format(PyExc_TypeError, "element %d not an integer", i);
            SWIG_fail;
        }
        long ind = PyInt_AsLong(sym);
        if (ind < 0 || ind > Core::Type<Symbol>::max) {
            Py_DECREF(seq);
            PyErr_Format(PyExc_ValueError, "symbol out of range: %ld", ind);
            SWIG_fail;
        }
        $1.push_back(ind);
    }
    Py_DECREF(seq);
}

%typemap(in) Multigram {
    $1 = Multigram($input);
}

%typemap(in) JointMultigram {
    PyObject *left, *right;
    if (!PyArg_ParseTuple($input, "OO", &left, &right)) {
        PyErr_SetString(PyExc_TypeError,"not a tuple of size 2");
        SWIG_fail;
    }
    $1.left  = Multigram(left);
    $1.right = Multigram(right);
}
%typemap(out) JointMultigram {
    $result = Py_BuildValue(
        "(NN)",
        $1.left.asPyObject(), $1.right.asPyObject());
}
#endif  // SWIGPYTHON

class MultigramInventory {
public:
    int size();
    int index(JointMultigram);
    JointMultigram symbol(int);
    int memoryUsed();
};

// ===========================================================================
%{
#include "SequenceModel.cc"
%}

#ifdef SWIGPYTHON
%typemap(out) Probability {
    $result = Py_BuildValue("f", $1.probability());
}
%typemap(out) LogProbability {
    $result = Py_BuildValue("f", - $1.score());
}
%typemap(in) Probability {
    PyObject *pp = PyNumber_Float($input);
    if (pp == NULL) SWIG_fail;
    $1 = Probability(PyFloat_AsDouble($input));
    Py_DECREF(pp);
}

%typemap(out) SequenceModel::History {
    $result = PyLong_FromVoidPtr(const_cast<void *>(static_cast<const void *>($1)));
}
%typemap(in) SequenceModel::History {
    void *ptr = PyLong_AsVoidPtr($input);
    if (ptr == NULL) SWIG_fail;
    $1 = reinterpret_cast<SequenceModel::History>(ptr);
}
#endif  // SWIGPYTHON

class SequenceModel {
public:
//  typedef size_t History;
    typedef unsigned int Token;

    SequenceModel();
    ~SequenceModel();
    void setInitAndTerm(int, int);
    void set(PyObject*);
    PyObject *get();
    PyObject *getNode(SequenceModel::History) const;

    Token init() const;
    Token term() const;
    SequenceModel::History initial() const;
    SequenceModel::History advanced(SequenceModel::History, Token) const;
    SequenceModel::History shortened(SequenceModel::History) const;

    PyObject *historyAsTuple(SequenceModel::History) const;
    Probability probability(Token, SequenceModel::History) const;

    int memoryUsed();
};

#if defined(INSTRUMENTATION)
class StringInventory {
public:
    StringInventory(PyObject*);
    ~StringInventory();
};
#endif  // INSTRUMENTATION

// ===========================================================================
%{
#include "Estimation.cc"
%}

class EstimationGraph {
public:
#if defined(INSTRUMENTATION)
    void draw(FILE*, const StringInventory*, const SequenceModel*) const;
#endif
    int memoryUsed();
};

class EstimationGraphBuilder {
public:
    void setSequenceModel(MultigramInventory*, SequenceModel*);
    void clearSizeTemplates();
    void addSizeTemplate(int left, int right);
    enum MultigramEmergenceMode {
        emergeNewMultigrams,
        suppressNewMultigrams,
        anonymizeNewMultigrams
    };
    void setEmergenceMode(MultigramEmergenceMode);
    EstimationGraph *create(Sequence left, Sequence right);
    void update(EstimationGraph*);
    int memoryUsed();
};

class SequenceModelEstimator {};

class EvidenceStore {
public:
    EvidenceStore();
    void setSequenceModel(SequenceModel*);
    PyObject *asList();
    size_t size();
    int maximumHistoryLength();
    Probability maximum();
    Probability total();

    SequenceModelEstimator *makeSequenceModelEstimator();

    int memoryUsed();
};
%extend SequenceModelEstimator {
    void makeSequenceModel(
        SequenceModel *target,
        double vocabularySize,
        DoubleVector discountArray)
    {
        std::vector<double> discounts(
            (double*) PyArray_DATA(discountArray),
            (double*) PyArray_DATA(discountArray) + PyArray_DIMS(discountArray)[0]);
        self->makeSequenceModel(target, vocabularySize, discounts);
    }
};


class Accumulator {
public:
    Accumulator();
    void setTarget(EvidenceStore*);
    LogProbability accumulate(EstimationGraph*, Probability weight);
    LogProbability logLik(EstimationGraph*);
};

class ViterbiAccumulator {
public:
    ViterbiAccumulator();
    void setTarget(EvidenceStore*);
    LogProbability accumulate(EstimationGraph*, Probability weight);
    LogProbability logLik(EstimationGraph*);
};
%extend ViterbiAccumulator {
    PyObject *segment(EstimationGraph *eg) {
        std::vector<MultigramIndex> mgs;
        LogProbability p = self->segment(eg, mgs);
        u32 len = mgs.size();
        PyObject *result = PyList_New(len);
        for (u32 i = 0; i < len; ++i)
            PyList_SET_ITEM(result, i, PyInt_FromLong(mgs[i]));
        return Py_BuildValue("(fN)", -p.score(), result);
    }
}

class OneForAllAccumulator {
public:
    OneForAllAccumulator();
    void setTarget(EvidenceStore*);
    void accumulate(EstimationGraph*, Probability weight);
};

// ===========================================================================
%{
#include "Translation.cc"
typedef Translator::NBestContext Translator_NBestContext;
%}

class Translator_NBestContext {
    Translator_NBestContext();
public:
    ~Translator_NBestContext();
#if defined(INSTRUMENTATION)
    void draw(FILE*, const StringInventory*) const;
#endif  // INSTRUMENTATION
};

class Translator {
public:
    Translator();
    void setMultigramInventory(MultigramInventory*);
    void setSequenceModel(SequenceModel*);
    int stackUsage();
    void setStackLimit(int);

    Translator_NBestContext *nBestInit(Sequence left);
    LogProbability nBestBestLogLik(Translator_NBestContext*);
    LogProbability nBestTotalLogLik(Translator_NBestContext*);
};
%extend Translator {
    PyObject *__call__(Sequence left) {
        std::vector<MultigramIndex> mgs;
        LogProbability p = self->translate(left, mgs);
        u32 len = mgs.size();
        PyObject *result = PyList_New(len);
        for (u32 i = 0; i < len; ++i)
            PyList_SET_ITEM(result, i, PyInt_FromLong(mgs[i]));
        return Py_BuildValue("(fN)", -p.score(), result);
    }
    PyObject *nBestNext(Translator_NBestContext *nbc) {
        std::vector<MultigramIndex> mgs;
        LogProbability p = self->nBestNext(nbc, mgs);
        u32 len = mgs.size();
        PyObject *result = PyList_New(len);
        for (u32 i = 0; i < len; ++i)
            PyList_SET_ITEM(result, i, PyInt_FromLong(mgs[i]));
        return Py_BuildValue("(fN)", -p.score(), result);
    }
};

/*
 * $Id: Multigram.cc 1667 2007-06-02 14:32:35Z max $
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

#include "Python.hh"

#include "Assertions.hh"
#include "Multigram.hh"

#if PY_MAJOR_VERSION >= 3
  #define PyInt_Check(x) PyLong_Check(x)
  #define PyInt_AsLong(x) PyLong_AsLong(x)
  #define PyInt_FromLong(x) PyLong_FromLong(x)
#endif

PyObject *Multigram::asPyObject() const {
  u32 len = length();
  PyObject *result = PyTuple_New(len);
  for (u32 i = 0; i < len; ++i)
    PyTuple_SET_ITEM(result, i, PyInt_FromLong(data_[i]));
  return result;
}

Multigram::Multigram(PyObject *obj) {
  memset(data_, 0, sizeof(data_));
  PyObject *seq = PySequence_Fast(obj, "need a sequence to create a multigram");
  if (!seq) throw ExistingPythonException();
  int len = PySequence_Fast_GET_SIZE(seq);
  if (len > (int)maximumLength) {
    Py_DECREF(seq);
    throw PythonException(PyExc_ValueError, "sequence too long");
  }
  for (int i = 0; i < len; ++i) {
    PyObject *item = PySequence_Fast_GET_ITEM(seq, i);
    if (!PyInt_Check(item)) {
      Py_DECREF(seq);
      throw PythonException(PyExc_TypeError, "not an integer");
    }
    long value = PyInt_AsLong(item);
    if (value < 0 || value > Core::Type<Symbol>::max) {
      Py_DECREF(seq);
      throw PythonException(PyExc_ValueError, "symbol out of range");
    }
    data_[i] = Symbol(value);
  }
  Py_DECREF(seq);
}

/*
 * $Id: EditDistance.cc 1667 2007-06-02 14:32:35Z max $
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

#include "Assertions.hh"
#include <vector>
#include <iostream>

struct Hyp {
    int cost;
    size_t pre_i, pre_j;
    Hyp() {};
    Hyp(int _cost, int _pre_i, int _pre_j) : cost(_cost), pre_i(_pre_i), pre_j(_pre_j) {}
};

PyObject *python_align(PyObject *self, PyObject *args) {
  struct SubstitutionCost {
    int operator() (PyObject *a, PyObject *b) {
      return (PyObject_RichCompareBool(a, b, Py_EQ)) == 1 ? 0 : 1; // can return -1
    }
  };
  SubstitutionCost sub_cost;

  PyObject *a = 0, *b = 0;
  if (!PyArg_ParseTuple(args, "OO", &a, &b)) return NULL;
  if (!PySequence_Check(a)) return NULL;
  if (!PySequence_Check(b)) return NULL;
  size_t len_a = PyObject_Length(a);
  size_t len_b = PyObject_Length(b);

  std::vector< std::vector<Hyp> > D(len_a + 1, std::vector<Hyp>(len_b + 1));
  int c;
  D[0][0] = Hyp(0, 0, 0);
  for (size_t j = 1 ; j <= len_b ; ++j) {
    c = D[0][j-1].cost;
    c += 1; // del_cost(b[j-1])
    D[0][j] = Hyp(c, 0, j-1);
  }

  for (size_t i = 1 ; i <= len_a ; ++i) {
    PyObject *ai = PySequence_GetItem(a, i-1);

    c = D[i-1][0].cost;
    c += 1; // ins_cost(ai);
    D[i][0] = Hyp(c, i-1, 0);

    for (size_t j = 1 ; j <= len_b ; ++j) {
      PyObject *bj = PySequence_GetItem(b, j-1);

      c = D[i][j-1].cost;
      c += 1; // del_cost(bj)
      D[i][j] = Hyp(c, i, j-1);

      c = D[i-1][j].cost;
      c += 1; // ins_cost(ai])
      if (c < D[i][j].cost)
        D[i][j] = Hyp(c, i-1, j);

      c = D[i-1][j-1].cost;
      c += sub_cost(ai, bj);
      if (c < D[i][j].cost)
        D[i][j] = Hyp(c, i-1, j-1);

      Py_DECREF(bj);
    }
    Py_DECREF(ai);
  }

  // traceback
  PyObject *alignment = PyList_New(0);
  size_t i = len_a;
  size_t j = len_b;
  while (i > 0 || j > 0) {
    Hyp &h(D[i][j]);
    //        alignment.append((a[pi:i], b[pj:j]))
    PyObject *p = 0;
    if (h.pre_i == i-1 && h.pre_j == j) {
      p = Py_BuildValue("(N,O)",
          PySequence_GetItem(a, h.pre_i),
          Py_None);
    } else if (h.pre_i == i && h.pre_j == j-1) {
      p = Py_BuildValue("(O,N)",
          Py_None,
          PySequence_GetItem(b, h.pre_j));
    } else if (h.pre_i == i-1 && h.pre_j == j-1) {
      p = Py_BuildValue("(N,N)",
          PySequence_GetItem(a, h.pre_i),
          PySequence_GetItem(b, h.pre_j));
    } else {
      defect();
      return NULL;
    }
    PyList_Append(alignment, p); Py_DECREF(p);
    i = h.pre_i;
    j = h.pre_j;
  }
  PyList_Reverse(alignment);

  PyObject *result = Py_BuildValue("Oi", alignment, D[len_a][len_b].cost);
  Py_DECREF(alignment);
  return result;
}


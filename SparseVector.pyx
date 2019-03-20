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

# ===========================================================================
ctypedef int size_t

cdef extern from "string.h":
    void *memcpy(void *dest, void *src, size_t n)
    int memcmp(void *s1, void *s2, size_t n)

cdef extern from "stdlib.h":
    void qsort(void *base, size_t nmemb, size_t size, int(*compar)(void*, void*))

cdef extern from "stdio.h":
    struct FILE
    size_t fread(void *ptr, size_t size, size_t nmemb, FILE *stream)
    size_t fwrite(void *ptr, size_t size, size_t nmemb, FILE *stream)

cdef extern from "Python.h":
    void *PyMem_Malloc(size_t n)
    void *PyMem_Realloc(void*, size_t)
    void PyMem_Free(void *p)
    int PyFile_Check(p)
    FILE* PyFile_AsFile(p)
    PyErr_SetFromErrno(p)

# ===========================================================================

cdef struct Item:
    int key
    double value

cdef int item_cmp(Item *a, Item *b):
    return a.key - b.key


cdef class SparseVector:
    cdef readonly int size
    cdef Item *data

    def __new__(self, int size):
        self.size = size
        if size > 0:
            self.data = <Item*> PyMem_Malloc(size * sizeof(Item))
        else:
            self.data = NULL
 
    def __dealloc__(self):
        PyMem_Free(self.data)

    def __copy__(self):
        cdef SparseVector result
        result = SparseVector(self.size)
        memcpy(result.data, self.data, self.size * sizeof(Item))
        return result

    def __cmp__(self, SparseVector othr):
        if self.size != othr.size:
            return self.size - othr.size
        else:
            return memcmp(self.data, othr.data, self.size * sizeof(Item))

    def __nonzero__(self):
        return self.size

    def __iter__(self):
        return SparseVectorIter(self)

    def __contains__(self, int key):
        return self.find(key) != NULL

    def __getitem__(self, int key):
        cdef Item *l
        l = self.find(key)
        if l == NULL:
            return 0.0
        return l.value
        
    cdef Item *find(self, int key):
        cdef Item *l, *r, *m
        l = self.data
        r = self.data + self.size
        while l < r:
            if l.key == key:
                return l
            if (r - l) < 8: # TUNE ME 
                l = l + 1
            else:
                m = l + (r - l) / 2
                if key < m.key:
                    r = m
                else:
                    l = m
        return NULL

    cdef sort(self):
        qsort(self.data, self.size, sizeof(Item),
              <int ((*)(void (*),void (*)))> item_cmp)

    cdef consolidate(self):
        if self.size == 0: return
        cdef i, j, oldSize
        j = 0
        oldSize = self.size
        for i from 1 <= i < oldSize:
            if self.data[i].key == self.data[j].key:
                self.data[j].value = self.data[j].value + self.data[i].value
            else:
                j = j + 1
                self.data[j] = self.data[i]
        self.size = j + 1
        if self.size < oldSize*2/3:
            self.data = <Item*> PyMem_Realloc(self.data, self.size * sizeof(Item))

    def __add__(SparseVector self, SparseVector othr not None):
        cdef Item *ai, *bi, *pi
        cdef SparseVector result
        result = SparseVector(self.size + othr.size)
        pi = result.data
        ai = self.data
        bi = othr.data
        while (ai - self.data < self.size) and (bi - othr.data < othr.size):
            if ai.key == bi.key:
                pi.key = ai.key
                pi.value = ai.value + bi.value
                ai = ai + 1
                bi = bi + 1
            elif ai.key < bi.key:
                pi[0] = ai[0]
                ai = ai + 1
            else:
                pi[0] = bi[0]
                bi = bi + 1
            pi = pi + 1
        while ai - self.data < self.size:
            pi[0] = ai[0]
            ai = ai + 1
            pi = pi + 1            
        while bi - othr.data < othr.size:
            pi[0] = bi[0]
            bi = bi + 1
            pi = pi + 1
        result.size = pi - result.data
        if result.size < (self.size + othr.size)*2/3:
            result.data = <Item*> PyMem_Realloc(result.data, result.size * sizeof(Item))
        return result

    def __mul__(SparseVector self, double den):
        cdef SparseVector result
        result = self.__copy__()
        cdef i
        for i from 0 <= i < result.size:
            result.data[i].value = result.data[i].value * den
        return result

    def __truediv__(SparseVector self, double den):
        cdef SparseVector result
        result = self.__copy__()
        cdef i
        for i from 0 <= i < result.size:
            result.data[i].value = result.data[i].value / den
        return result

    def sum(self):
        cdef double result
        cdef int i
        result = 0.0
        for i from 0 <= i < self.size:
            result = result + self.data[i].value
        return result

    def threshold(self, double minValue):
        cdef i, j
        j = 0
        for i from 0 <= i < self.size:
            if self.data[i].value >= minValue:
                j = j + 1
        cdef SparseVector result
        result = SparseVector(j)
        if j > 0:
            j = 0
            for i from 0 <= i < self.size:
                if self.data[i].value >= minValue:
                    result.data[j] = self.data[i]
                    j = j + 1
        return result


cdef class SparseVectorIter:
    cdef SparseVector sv
    cdef int current
    
    def __init__(self, SparseVector sv):
        self.sv = sv
        self.current = -1

    def __next__(self):
        self.current = self.current + 1
        if self.current >= self.sv.size:
            raise StopIteration
        cdef Item *item
        item = self.sv.data + self.current
        return item.key, item.value


def sparse(seq):
    if type(seq) is SparseVector:
        return seq
    lst = list(seq)
    cdef SparseVector sv
    sv = SparseVector(len(lst))
    cdef int i, k
    cdef double v
    for i from 0 <= i < len(lst):
        k, v = lst[i]
        sv.data[i].key   = k
        sv.data[i].value = v
    sv.sort()
    for i from 0 < i < sv.size:
        if sv.data[i-1].key == sv.data[i].key:
            raise ValueError('duplicate key encountered', sv.data[i].key)
    return sv


def sumSparse(svs):
    if len(svs) == 1:
        return svs[0]
    elif len(svs) == 0:
        return SparseVector(0)
    elif len(svs) == 2:
        return SparseVector.__add__(*svs)

    cdef int totalSize
    cdef SparseVector sv
    totalSize = 0
    for sv in svs:
        if sv is None: raise TypeError
        totalSize = totalSize + sv.size
    cdef SparseVector result
    result = SparseVector(totalSize)
    cdef Item *tail
    tail = result.data
    for sv in svs:
        memcpy(tail, sv.data, sv.size * sizeof(Item))
        tail = tail + sv.size
    result.sort()
    result.consolidate()
    return result


def leftJoinInterpolateAndAddOneSparse(SparseVector aa, double scale, SparseVector bb, int extraKey, double extraValue):
    cdef SparseVector result
    cdef Item *i, *l, *r, *m
    cdef int key
    
    result = SparseVector(aa.size + 1)
    result.data[0].key = extraKey
    result.data[0].value = extraValue
    memcpy(result.data + 1, aa.data, aa.size * sizeof(Item))

    l = bb.data
    i = result.data + 1
    while i < result.data + result.size:
        key = i.key
        r = l + 8
        while r < bb.data + bb.size and r.key <= key:
            r = l + 2*(r-l)
        if r > bb.data + bb.size:
            r = bb.data + bb.size
        assert (l == bb.data) or (l[-1].key < key)
        while l < r:
            if l.key == key:
                i.value = i.value + scale * l.value
                break
            if (r - l) < 8: # TUNE ME
                if l.key > key: break
                l = l + 1
            else:
                m = l + (r - l) / 2
                if key < m.key:
                    r = m
                else:
                    l = m
        i = i + 1

    return result


def dump(SparseVector sv not None, file):
    assert PyFile_Check(file)
    cdef FILE *f
    f = PyFile_AsFile(file)
    
    if fwrite(&sv.size, sizeof(int), 1, f) != 1:
        PyErr_SetFromErrno(IOError)        
    if fwrite(sv.data, sizeof(Item), sv.size, f) != sv.size:
        PyErr_SetFromErrno(IOError)        

def load(file):
    assert PyFile_Check(file)
    cdef FILE *f
    f = PyFile_AsFile(file)
    
    cdef int size
    if fread(&size, sizeof(int), 1, f) != 1:
        PyErr_SetFromErrno(IOError)
    cdef SparseVector sv
    sv = SparseVector(size)
    if fread(sv.data, sizeof(Item), size, f) != size:
        PyErr_SetFromErrno(IOError)
    return sv

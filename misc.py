#!/usr/bin/env python
from __future__ import division
from __future__ import print_function

import sys
import errno
import os
import io
import codecs
import gc
import gzip


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

# ===========================================================================

if sys.version_info[:2] < (2, 4):

    def sorted(l):
        lx = list(l)
        lx.sort()
        return lx

    def reversed(l):
        lx = list(l)
        lx.reverse()
        return lx

    from sets import Set

    set = Set

else:
    sorted = sorted
    reversed = reversed
    set = set

if sys.version_info[:2] >= (3, 0):
    unicode = None
    object_or_InstanceType = object

    def cmp(a, b):
        return (a > b) - (b > a)


else:
    import types

    object_or_InstanceType = types.InstanceType

# ===========================================================================
try:
    # Unix system
    import resource

    pageSize = resource.getpagesize()
except ImportError:
    # Windows system
    import mmap

    pageSize = mmap.PAGESIZE
megabyte = 1024 * 1024


def meminfo():
    pid = os.getpid()
    try:
        with open("/proc/%d/statm" % pid) as f:
            data = f.read()
    except:
        raise NotImplementedError
    data = map(int, data.split())
    size, resident, shared, trs, drs, lrs, dt = tuple(data)
    return size * pageSize, resident * pageSize


def reportMemoryUsage():
    try:
        size, resident = meminfo()
    except NotImplementedError:
        return
    print(
        "memory usage:  virtual %1.1f MB   resident %1.1f MB"
        % (size / megabyte, resident / megabyte)
    )


def cputime():
    user, system, childUser, childSystem, wall = os.times()
    return user


class MemoryProfiler:
    class Record(object):
        __slots__ = ["id", "object", "type", "path", "usage"]

        def __init__(self, object, path):
            self.id = id(object)
            self.object = object
            self.path = path
            self.usage = self.measureMemory(self.object)
            self.type = type(self.object)
            if self.type is object_or_InstanceType:
                self.type = self.object.__class__

        def measureMemory(self, object):
            """
            memory consumption for this object alone
            (not including children)
            """
            if hasattr(object, "memoryUsed"):
                try:
                    return object.memoryUsed()
                except:
                    return -1
            if type(object) in self.valuators:
                return self.pythonObjectHead + self.valuators[type(object)](object)
            return 0

        # Machine dependent: Trying to emulate AMD64 here.
        pythonObjectHead = 4 + 8
        valuators = {
            str: lambda s: len(s),
            unicode: lambda u: 2 * len(u),
            list: lambda l: 4 + 8 + 8 * len(l),
            tuple: lambda t: 4 + 8 * len(t),
            dict: lambda d: 16 * len(d),
            int: lambda i: 8,
            float: lambda f: 8,
        }

    def __init__(self):
        self.queue = list()
        self.records = dict()

    def add(self, record):
        if record.id not in self.records:
            self.queue.append(record)
            self.records[record.id] = record

    def search(self, root):
        self.add(self.Record(root, "/"))
        while self.queue:
            current = self.queue.pop(0)
            inspector = self.inspectors.get(type(current.object))
            if inspector:
                children = inspector(self, current)
            elif hasattr(current.object, "__dict__"):
                children = self.inspectInstance(current)
            else:
                self.inspectGeneral(current)
            for child in children:
                self.add(child)

    def inspectList(self, current):
        for index, item in enumerate(current.object):
            yield self.Record(item, "%s[%d]" % (current.path, index))

    def inspectDict(self, current):
        for key, value in current.object.iteritems():
            yield self.Record(value, "%s[%s]" % (current.path, repr(key)))

    def inspectInstance(self, current):
        for key, value in current.object.__dict__.iteritems():
            if type(key) is not str:
                continue
            yield self.Record(value, "%s.%s" % (current.path, key))

    def inspectGeneral(self, current):
        for ii, object in enumerate(gc.get_referents(current.object)):
            if type(object) is type:
                continue
            yield self.Record(object, "%s/%d" % (current.path, ii))

    inspectors = {
        list: inspectList,
        tuple: inspectList,
        dict: inspectDict,
        object_or_InstanceType: inspectInstance,  # old-style class
    }

    def report(self, out):
        records = self.records.values()
        records.sort(key=lambda rec: rec.path)
        sum = 0
        for record in records:
            what = repr(record.object)
            if len(what) > 50:
                what = what[:46] + " ..."
            fields = [record.path, str(record.usage), what]
            print("\t".join(fields), file=out)
            sum += record.usage
        print("total:", sum, file=out)

    def reportByType(self, out):
        recordsByType = {}
        for record in self.records.itervalues():
            if record.type not in recordsByType:
                recordsByType[record.type] = []
            recordsByType[record.type].append(record)

        typesAndClasses = recordsByType.keys()
        typesAndClasses.sort()
        for typeOrClass in typesAndClasses:
            records = recordsByType[typeOrClass]
            records.sort(lambda a, b: cmp(b.usage, a.usage))
            count = len(records)
            memoryUsed = sum([rec.usage for rec in records])
            print("%5d\t%-40s\t%d" % (count, typeOrClass, memoryUsed), file=out)
            for record in records[:5]:
                print("\t%-40s\t%d" % (record.path, record.usage), file=out)
            if len(records) > 5:
                print("\t...", file=out)


def reportMemoryProfile(root):
    profiler = MemoryProfiler()
    profiler.search(root)
    #   profiler.report(sys.stdout)
    profiler.reportByType(sys.stdout)


# ===========================================================================


def gOpenOut(fname, encoding=None):
    if fname == "-":
        if hasattr(sys.stdout, "buffer"):
            out = sys.stdout.buffer
        else:
            out = sys.stdout
    elif os.path.splitext(fname)[1] == ".gz":
        out = os.popen("gzip -fc >%s" % fname, "w")
    #       out = gzip.open(fname, 'w')
    else:
        out = io.open(fname, "w", encoding=encoding)
        return out

    if encoding:
        out = codecs.getwriter(encoding)(out)

    return out


def gOpenIn(fname, encoding=None):
    if fname == "-":
        if hasattr(sys.stdin, "buffer"):
            inp = sys.stdin.buffer
        else:
            inp = sys.stdin
    elif os.path.splitext(fname)[1] == ".gz":
        if not os.path.isfile(fname):
            raise IOError(errno.ENOENT, "No such file: '%s'" % fname)
        inp = gzip.open(fname, "rb")
    else:
        inp = io.open(fname, encoding=encoding)
        return inp

    if encoding:
        inp = codecs.getreader(encoding)(inp)
    return inp


# ===========================================================================


class RestartStub:
    def __init__(self, fun, args):
        self.fun = fun
        self.args = args

    def __iter__(self):
        return self.fun(*self.args)


def restartable(fun):
    def restartableFun(*args):
        return RestartStub(fun, args)

    return restartableFun


def once(fun):
    return fun()

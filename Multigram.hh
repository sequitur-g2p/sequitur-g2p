/*
 * $Id: Multigram.hh 1691 2011-08-03 13:38:08Z hahn $
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

#ifndef _MULTIGRAM_HH
#define _MULTIGRAM_HH
#include "Python.hh"

#include <vector>
#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__) || (_MSC_VER)
#include <unordered_map>
using std::unordered_map;
#else
#include <tr1/unordered_map>
using std::tr1::unordered_map;
#endif
#include "SequenceModel.hh"


#if !defined(MULTIGRAM_SIZE)
#error "You need to define MULTIGRAM_SIZE."
#endif

#if (MULTIGRAM_SIZE < 3)
typedef u8 Symbol;
#else
typedef u16 Symbol;
#endif

typedef std::vector<Symbol> Sequence;


class Multigram {
  public:
#if (MULTIGRAM_SIZE < 2)
    static const u32 maximumLength = 4;
#else
    static const u32 maximumLength = 8;
#endif
  private:
    Symbol data_[maximumLength];
  public:
    Multigram() {
      memset(data_, 0, sizeof(data_));
    }

    Multigram(const Symbol *begin, const Symbol *end) {
      require(begin <= end && begin + maximumLength >= end);
      memset(data_, 0, sizeof(data_));
      for (Symbol *d = data_; begin < end; *d++ = *begin++);
    }

    Multigram(PyObject*);

    Symbol operator[](u32 i) const {
      require_(i < maximumLength);
      return data_[i];
    }
    Symbol &operator[](u32 i) {
      require_(i < maximumLength);
      return data_[i];
    }

    u32 length() const {
      u32 result = 0;
      while (result < maximumLength && data_[result]) ++result;
      return result;
    }

    size_t hash() const {
      size_t result = 0;
      for (u32 i = 0; i < maximumLength && data_[i]; ++i)
        result = (result << 6) ^ size_t(data_[i]);
      return result;
    }
    struct Hash { size_t operator() (const Multigram &m) const { return m.hash(); } };

    friend bool operator== (const Multigram &lhs, const Multigram &rhs) {
      return memcmp(lhs.data_, rhs.data_, sizeof(lhs.data_)) == 0;
    }

    /** @return NewReference */
    PyObject *asPyObject() const;
};

class JointMultigram {
  public:
    Multigram left, right;

    JointMultigram() {};
    JointMultigram(const Multigram &l, const Multigram &r) : left(l), right(r) {}
    JointMultigram(const Symbol  *leftBegin, const Symbol  *leftEnd,
        const Symbol *rightBegin, const Symbol *rightEnd) :
      left(leftBegin, leftEnd), right(rightBegin, rightEnd) {}

    size_t hash() const {
      return left.hash() + right.hash();
    }
    struct Hash { size_t operator() (const JointMultigram &m) const { return m.hash(); } };

    friend bool operator== (const JointMultigram &lhs, const JointMultigram &rhs) {
      return (lhs.left  == rhs.left) && (lhs.right == rhs.right);
    }
};

class MultigramInventory {
  public:
    typedef u32 Index;

  private:
    typedef unordered_map<JointMultigram, Index, JointMultigram::Hash> Map;
    typedef std::vector<JointMultigram> List;
    Map map_;
    List list_;

  public:
    MultigramInventory() {
      list_.push_back(JointMultigram());
    }

    static Index voidIndex() {
      return 0;
    }

    /** Number of multigrams not including VOID */
    size_t size() const {
      return list_.size() - 1;
    }

    Index index(const JointMultigram &jmg) {
      Map::iterator i = map_.find(jmg);
      if (i == map_.end()) {
        i = map_.insert(std::make_pair(jmg, list_.size())).first;
        list_.push_back(jmg);
      }
      return i->second;
    }

    Index testIndex(const JointMultigram &jmg) {
      Map::iterator i = map_.find(jmg);
      return (i != map_.end()) ? i->second : voidIndex();
    }

    JointMultigram symbol(Index i) {
      require_(i > 0);
      require_(i < list_.size());
      return list_[i];
    }

    size_t memoryUsed() const {
#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__) || (_MSC_VER)
      struct MapNode { Map::value_type value; bool cond;};
#elif __GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 3)
      typedef std::tr1::__detail::_Hash_node<Map::value_type, false> MapNode;
#elif __GNUC__ == 4 && __GNUC_MINOR__ == 2
      typedef std::tr1::__detail::_Hash_node<Map::value_type, false> MapNode;
#elif __GNUC__ == 4 && __GNUC_MINOR__ <= 1
      typedef Internal::hash_node<Map::value_type, false> MapNode;
#endif
      return sizeof(MultigramInventory)
        + list_.capacity() * sizeof(List::value_type)
        + map_.size() * sizeof(MapNode)
        + map_.bucket_count() * sizeof(MapNode*);
    }
};

typedef MultigramInventory::Index MultigramIndex;

#endif // _MULTIGRAM_HH

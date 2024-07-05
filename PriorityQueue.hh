/*
 * $Id: PriorityQueue.hh 1691 2011-08-03 13:38:08Z hahn $
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

#ifndef _CORE_PRIORITY_QUEUE_HH
#define _CORE_PRIORITY_QUEUE_HH

#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__) || (_MSC_VER)
#include <unordered_map>
using std::unordered_map;
#define stdhash std::hash
#else
#include <tr1/unordered_map>
using std::tr1::unordered_map;
#define stdhash std::tr1::hash
#endif
#include <functional>
//#include <ext/functional>


#include "Assertions.hh"
#include "Types.hh"


namespace Core {

template< typename P >
struct select1st
{
   typename P::first_type const& operator()( P const& p ) const
   {
       return p.first;
   }
};

template< typename P >
struct select2nd
{
   typename P::second_type const& operator()( P const& p ) const
   {
       return p.second;
   }
};



  template <class T_Heap, class T_PriorityFunction>
    class PriorityQueueBase :
      public T_Heap
  {
    typedef T_Heap Precursor;
    public:
    typedef T_PriorityFunction PriorityFunction;
    typedef typename Precursor::Item Item;
    typedef typename Precursor::Index Index;
    protected:
    u32 maxSize_;
    PriorityFunction precedes_;
    void upHeap(Index);
    void downHeap(Index);
    bool invariant() const;
    public:
    PriorityQueueBase(u32 maxSize = Type<u32>::max) : maxSize_(maxSize) {}
    PriorityQueueBase(const PriorityFunction &precedes, u32 maxSize = Type<u32>::max) :
      maxSize_(maxSize), precedes_(precedes) {}

    /** Return reference to top-most item in the queue */
    const Item &top() const {
      require(!Precursor::empty());
      return Precursor::item(1);
    }

    /** Remove top-most item */
    void pop() {
      require(!Precursor::empty());
      this->move(1, Precursor::size());
      Precursor::deleteLast();
      if (Precursor::size() > 0) downHeap(1);
      verify_(invariant());
    }

    /**
     * Change top-most item.
     * Equivalent to pop(); insert(), but usually more efficient.
     */
    void changeTop(const Item &e) {
      put(1, e);
      downHeap(1);
      verify_(invariant());
    }

    /** Insert new item */
    void insert(const Item &e) {
      this->append(e);
      this->upHeap(Precursor::size()) ;
      verify_(invariant());
      //if (size() > maxSize_) deleteLast();
    }
  };

  template <class H, class PF>
    void PriorityQueueBase<H, PF>::downHeap(Index i) {
      require(1 <= i && i <= Precursor::size());
      Index j;
      Item e = this->item(i);
      while (i <= Precursor::size() / 2) {
        j = 2 * i;
        if (j < Precursor::size() && precedes_(this->item(j+1), this->item(j))) j = j + 1;
        if (!this->precedes_(this->item(j), e)) break;
        this->move(i, j);
        i = j;
      }
      this->put(i, e);
    }

  template <class H, class PF>
    void PriorityQueueBase<H, PF>::upHeap(Index i) {
      require(1 <= i && i <= Precursor::size());
      Item e = this->item(i);
      while (i > 1 && !precedes_(this->item(i/2), e)) {
        this->move(i, i/2);
        i /= 2;
      }
      this->put(i, e);
    }

  template <class H, class PF>
    bool PriorityQueueBase<H, PF>::invariant() const {
      if (!Precursor::invariant()) return false;
      for (Index i = 2 ; i < Precursor::size() ; ++i)
        if (precedes_(item(i), item(i/2)))
          return false;
      return true;
    }


  template <class T_Item>
    class UntracedHeap {
      public:
        typedef T_Item Item;
        typedef typename std::vector<Item>::size_type Index;
      protected:
        std::vector<Item> heap_;
        bool invariant() const { return true; }
      public:
        UntracedHeap() { heap_.push_back(Item()); } // pseudo-sentinel
        void clear() { heap_.resize(1); }
        Index size() const { return heap_.size() - 1; }
        bool empty() const { return heap_.size() == 1; }
      protected:
        const Item &item(Index i) const { return heap_[i]; }
        void put(Index i, const Item &e) { heap_[i] = e; }
        void move(Index to, Index from) { heap_[to] = heap_[from]; }
        void append(const Item &e) { heap_.push_back(e); }
        void deleteLast() { heap_.pop_back(); }
    };

  template <class T_Item, class T_Key,
           class T_KeyFunction, template <typename, typename, class> class T_Map,
           class T_Hash_Obj = typename stdhash<T_Key> >
             class TracedHeap : public UntracedHeap<T_Item> {
               typedef UntracedHeap<T_Item> Precursor;
               public:
               typedef T_Key Key;
               typedef T_KeyFunction KeyFunction;
               protected:
               typedef T_Map<Key, typename Precursor::Index, T_Hash_Obj> Map;
               Map map_;
               KeyFunction key_;
               bool invariant() const;
               public:
               TracedHeap() : Precursor() {}

               bool contains(const Key &k) const {
                 //  require(key_valid(k)) ;
                 typename Map::const_iterator it(map_.find(k));
                 if (it == map_.end()) return false;
                 typename Precursor::Index i = it->second;
                 return 0 < i && i < Precursor::heap_.size() && key_(Precursor::heap_[i]) == k;
               }

               const typename Precursor::Item& operator[] (const Key &k) const {
                 require(contains(k));
                 return Precursor::heap_[map_[k]];
               }
               protected:
               void put(typename Precursor::Index i, const typename Precursor::Item &e) {
                 Precursor::heap_[i] = e;
                 verify(key_(Precursor::heap_[i]) == key_(e));
                 map_[key_(e)] = i;
               }

               void move(typename Precursor::Index to,typename Precursor::Index from) {
                 Precursor::heap_[to] = Precursor::heap_[from];
                 map_[key_(Precursor::heap_[to])] = to;
               }

               void append(const typename Precursor::Item &e) {
                 Precursor::heap_.push_back(e);
                 map_[key_(Precursor::heap_.back())] = Precursor::size()-1;
               }
             };

  template <class T_Item, class T_Key, class T_KeyFunction,
           template <typename, typename,typename> class T_Map, class T_Hash_Obj>
             bool TracedHeap<T_Item, T_Key, T_KeyFunction, T_Map, T_Hash_Obj>::invariant() const {
               for (typename Precursor::Index i = 1 ; i < Precursor::size() ; ++i) {
                 typename Map::const_iterator it(map_.find(key_(item(i))));
                 if (it == map_.end()) return false;
                 if (it->second != i) return false;
               }
               return true;
             }


  /**
   * Simple heap-based priority queue template.
   */
  template <class T_Item, class T_PriorityFunction = std::less<T_Item> >
    class PriorityQueue :
      public PriorityQueueBase< UntracedHeap<T_Item>, T_PriorityFunction >
  {
    typedef PriorityQueueBase< UntracedHeap<T_Item>, T_PriorityFunction > Precursor;
    public:
    PriorityQueue() : Precursor() {}
    PriorityQueue(const T_PriorityFunction &precedes, u32 maxSize = Type<u32>::max) :
      Precursor(precedes, maxSize) {}
  };

  template <typename T_Key, typename T_Tp, class T_Hash>
    class default_unordered_map : public unordered_map<T_Key, T_Tp, T_Hash> {};

  /**
   * Heap-based priority queue class template with random access.
   */
  // the lambda version:
  template <class T_Item, class T_Key = typename T_Item::first_type,
           class T_KeyFunction = select1st<T_Item>,
           class T_PriorityFunction = std::less<void>,
           class T_Hash_Obj = stdhash<T_Key> >
             class TracedPriorityQueue :
               public PriorityQueueBase<
               TracedHeap<T_Item, T_Key, T_KeyFunction, default_unordered_map, T_Hash_Obj>,
               T_PriorityFunction>
  {
    typedef PriorityQueueBase<
      TracedHeap<T_Item, T_Key, T_KeyFunction, default_unordered_map, T_Hash_Obj>, T_PriorityFunction> Precursor;
    public:
    TracedPriorityQueue(u32 maxSize = Type<u32>::max) : Precursor(maxSize) {}
    TracedPriorityQueue(const T_PriorityFunction &precedes, u32 maxSize = Type<u32>::max) :
      Precursor(precedes, maxSize) {}

    void insert(const typename Precursor::Item &e) {
      require(!this->contains(this->key_(e)));
      Precursor::insert(e) ;
      ensure(this->contains(this->key_(e))) ;
    }

    void changeTop(const typename Precursor::Item &e) {
      require(!contains(key_(e)) || Precursor::map_[key_(e)] == 1);
      Precursor::changeTop(e);
    }

    size_t size() const {
      return Precursor::heap_.size();
    }

    const T_Item& operator[] (size_t i) const {
      return Precursor::heap_[i];
    }

    /** Change item with the key of @c e to @c e. */
    void update(const typename Precursor::Item &e) {
      require(contains(key_(e)));
      typename Precursor::Index i = Precursor::map_[key_(e)] ;
      if (precedes_(e, Precursor::heap_[i])) {
        Precursor::heap_[i] = e;
        upHeap(i);
      } else {
        Precursor::heap_[i] = e;
        downHeap(i);
      }
    }

    /**
     * Conditional update with higher priority.
     *
     * If the stack contains an element with the same key as @c e but
     * lower priority then this element is replaced by @c e.  If their
     * is no element with @c e's key, @c e is inserted.  Otherwise
     * nothing happens.
     *
     * This rather specific function is most useful for implementing
     * best-first search like Dijkstra's algorithm or A*.
     *
     * @return true if given item was inserted (by replacing an
     * existing one or by enlarging the stack).  False if the
     * given item dropped, and the stack is unchanged.
     */
    bool insertOrRelax(const typename Precursor::Item &e) {
      if (this->contains(this->key_(e))) {
        typename Precursor::Index i = Precursor::map_[this->key_(e)] ;
        if (this->precedes_(e, Precursor::heap_[i])) {
          Precursor::heap_[i] = e;
          this->upHeap(i);
          verify_(invariant());
        } else return false;
      } else insert(e);
      return true;
    }
  };

} // namespace Core

#endif // _CORE_PRIORITY_QUEUE_HH

/*
 * $Id: Translation.cc 1691 2011-08-03 13:38:08Z hahn $
 *
 * Copyright (c) 2004-2005  RWTH Aachen University
 * Copyright (c) 2024 Uniphore (Author: Kadri Hacioglu, Vishay Raina, Manickavela)
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

#include "Python.hh"  // Must be first to prevent some warnings

#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__) || (_MSC_VER)
#include <unordered_map>
using std::unordered_multimap;
using std::unordered_map;
#else
#include <tr1/unordered_map>
using std::tr1::unordered_multimap;
using std::tr1::unordered_map;
#endif

#include <memory>
#include <stdexcept>

#include "Assertions.hh"
#include "Graph.hh"
#include "Multigram.hh"
#include "MultigramGraph.hh"
#include "PriorityQueue.hh"
#include "Probability.hh"
#include "SequenceModel.hh"
#include "Utility.hh"

class Translator {
  private:
    MultigramInventory *inventory_;
    SequenceModel *sequenceModel_;

    u32 minLeftLen_,  maxLeftLen_;
    typedef unordered_multimap<Multigram, SequenceModel::Token, Multigram::Hash> LeftMap;
    LeftMap leftMap_;

    u32 stackLimit_;
    u32 stackUsage_;

  public:
    Translator() :
      inventory_(0), sequenceModel_(0),
      stackLimit_(2147483647), stackUsage_(0)
  {}

    void setMultigramInventory(MultigramInventory *mi) {
      require(mi);

      inventory_ = mi;

      leftMap_.clear();
      minLeftLen_ = Multigram::maximumLength;
      maxLeftLen_ = 0;
      for (MultigramIndex q = 1; q <= inventory_->size(); ++q) {
        JointMultigram jmg(inventory_->symbol(q));
        leftMap_.insert(std::make_pair(jmg.left, q));
        minLeftLen_ = std::min(minLeftLen_, jmg.left.length());
        maxLeftLen_ = std::max(maxLeftLen_, jmg.left.length());
      }
    }

    void setSequenceModel(SequenceModel *sm) {
      require(sm);
      sequenceModel_ = sm;
    }

    u32 stackUsage() {
      u32 result = stackUsage_;
      stackUsage_ = 0;
      return result;
    }
    void setStackLimit(u32 l) { stackLimit_ = l; }

    // ===========================================================================
    // single best translation
  private:
    struct TracebackItem {
      MultigramIndex q;
      LogProbability p;
      TracebackItem(MultigramIndex _q, LogProbability _p) : q(_q), p(_p) {}
    };

    struct Trace :
      public TracebackItem
  {
    std::shared_ptr<Trace> back;
    Trace(const std::shared_ptr<Trace> &_b, const MultigramIndex &_q, LogProbability _p) :
      TracebackItem(_q, _p), back(_b) {}
  };

    struct State {
      u32 pos; /**< covered source positions */
      SequenceModel::History history;

      bool operator== (const State &rhs) const {
        return (pos == rhs.pos) && (history == rhs.history);
      }

      struct Hash {
        size_t operator() (const State &s) const {
          return reinterpret_cast<size_t>(s.history) ^ size_t(s.pos);
        }
      };
    };

    struct HypBase {
      State state;
      LogProbability p;

      struct KeyFunction {
        const State &operator() (const HypBase &h) const { return h.state; }
      };

      struct PriorityFunction {
        bool operator() (const HypBase &lhs, const HypBase &rhs) const {
          return lhs.p > rhs.p;
        }
      };
    };

    struct Hyp : public HypBase {
      MultigramIndex q;
      std::shared_ptr<Trace> trace;
    };

    typedef Core::TracedPriorityQueue<
      Hyp, State,
      Hyp::KeyFunction, Hyp::PriorityFunction,
      State::Hash> Open;
    typedef unordered_map<State, LogProbability, State::Hash> Closed;

    Open open_;
    Closed closed_;

    inline bool insertOrRelax(const Hyp &nh) {
      Closed::const_iterator relaxTo = closed_.find(nh.state);
      if (relaxTo != closed_.end()) {
        verify(nh.p <= relaxTo->second);
        return false;
      } else {
        if (!open_.insertOrRelax(nh))
          return false;
      }
#if 0
      std::cerr << "->\t" << nh.p.score() // DEBUG
        << "\tl=" << nh.state.pos
        << "\th=" << sequenceModel_->formatHistory(nh.state.history, 0)
        << "\tq=" << nh.q << std::endl;
#endif
      return true;
    }

  public:
    LogProbability translate(
        const Sequence &left,
        std::vector<MultigramIndex> &result)
    {
      require(sequenceModel_);
      verify(open_.empty());
      verify(closed_.empty());
      u32 maxStackSize = 0;

      Hyp current, next;
      next.state.pos  = 0;
      next.state.history = sequenceModel_->initial();
      next.q = sequenceModel_->init();
      next.p = LogProbability::certain();
      open_.insert(next);

      while (!open_.empty()) {
        current = open_.top(); open_.pop();
#if 0
        std::cerr << current.p.score()
          << "\tl=" << current.state.pos
          << "\th=" << sequenceModel_->formatHistory(current.state.history, 0)
          << "\tq=" << current.q << std::endl; // DEBUG
#endif
        Closed::const_iterator relaxTo = closed_.find(current.state);
        verify(relaxTo == closed_.end()); // DEBUG BRAIN: really ???
        if (relaxTo != closed_.end()) {
          verify(current.p <= relaxTo->second);
          continue;
        } else {
          closed_[current.state] = current.p;
        }

        next.trace = std::make_shared<Trace>(current.trace, current.q, current.p);

        if (current.state.history == sequenceModel_->culDeSac() &&
            current.q == sequenceModel_->term()) {
          verify(current.state.pos == left.size());
          goto goalStateReached;
        }

        verify(current.state.pos <= left.size());
        int lb = current.state.pos;
        LeftMap::const_iterator mi, mi_end;
        for (int le = lb + (int)minLeftLen_;
                 le <= lb + (int)maxLeftLen_ && le <= (int)left.size(); ++le) {
          Multigram lmg(&left[lb], &left[le]);
          for (Core::tie(mi, mi_end) = leftMap_.equal_range(lmg); mi != mi_end; ++mi) {
            next.q = mi->second;
            next.state.pos = le;
            next.state.history = sequenceModel_->advanced(current.state.history, next.q);
            next.p = current.p * sequenceModel_->probability(next.q, current.state.history);
            insertOrRelax(next);
          }
        }
        if (current.state.pos == left.size()) { // end of string
          next.q = sequenceModel_->term();
          next.state.pos = left.size();
          next.state.history = sequenceModel_->culDeSac();
          next.p = current.p * sequenceModel_->probability(next.q, current.state.history);
          insertOrRelax(next);
        }

        if (maxStackSize < open_.size())
          maxStackSize = open_.size();
        if (open_.size() > stackLimit_) {
          open_.clear(); closed_.clear();
          throw std::runtime_error("stack size limit exceeded");
        }
      } // while (!open_.empty())

      closed_.clear();
      throw std::runtime_error("translation failed");

goalStateReached:
      if (stackUsage_ < maxStackSize)
        stackUsage_ = maxStackSize;

      open_.clear(); closed_.clear();

      result.clear();
      for (std::shared_ptr<Trace> trace = next.trace; trace; trace = trace->back)
        result.push_back(trace->q);
      std::reverse(result.begin(), result.end());
      return next.trace->p;
    } // translate()

    // ===========================================================================
    // N-best translation
  public:
    class NBestContext : public MultigramGraph {
      friend class Translator;
      private:
      u32 stackLimit_;

      NodeMap<LogProbability> forwardProbability_;

      typedef Translator::Trace Trace;
      struct Hyp {
        Graph::NodeId n;
        std::shared_ptr<Trace> trace;
        LogProbability p, Q;

        struct PriorityFunction {
          bool operator() (const Hyp &lhs, const Hyp &rhs) const {
            return lhs.Q > rhs.Q;
          }
        };
      };

      typedef Core::PriorityQueue<Hyp, Hyp::PriorityFunction> Open;
      Open open_;

      NBestContext(u32 stackLimit) :
        MultigramGraph(),
        stackLimit_(stackLimit),
        forwardProbability_(&graph_)
      {}

      void initStack() {
        open_.clear();
        Hyp init;
        init.n = final_;
        init.p = LogProbability::certain();
        init.Q = forwardProbability_[init.n];
        open_.insert(init);
      }

      std::shared_ptr<Trace> next() {
        Hyp current, next;
        while (!open_.empty()) {
          current = open_.top(); open_.pop();

          if (current.n == initial_)
            return current.trace;

          for (Graph::IncomingEdgeIterator e = graph_.incomingEdges(current.n); e; ++e) {
            next.n = graph_.source(*e);
            next.p = current.p * probability_[*e];
            next.trace = std::make_shared<Trace>(current.trace, token_[*e], next.p);
            next.Q = next.p * forwardProbability_[next.n];
            open_.insert(next);
          }

          if (open_.size() > stackLimit_) {
            open_.clear();
            throw std::runtime_error("stack size limit exceeded");
          }
        }
        return std::shared_ptr<Trace>();
      }
#if defined(INSTRUMENTATION)
      public:
      void draw(FILE *f, const StringInventory *si) const {
        fprintf(f,
            "digraph \"translation graph\" {\n"
            "ranksep = 1.0;\n"
            "rankdir = LR;\n");
        for (Graph::NodeId n = graph_.nodesBegin(); n != graph_.nodesEnd(); ++n) {
          fprintf(f, "n%d [label=\"%d\"]\n", n, n);
        }
        for (Graph::EdgeId e = graph_.edgesBegin(); e != graph_.edgesEnd(); ++e) {
          std::string label = (si) ? si->symbol(token_[e]) : std::string("?");
          fprintf(f, "n%d -> n%d [label=\"%s %f\"]\n",
              graph_.source(e), graph_.target(e),
              label.c_str(), probability_[e].probability());
        }
        fprintf(f, "}\n");
        fflush(f);
      }
#endif // INSTRUMENTATION
    }; // struct NBestContext

  private:
    typedef HypBase BuildHyp;
    typedef unordered_map<State, Graph::NodeId, State::Hash> StateNodeMap;
    typedef Core::TracedPriorityQueue<
      BuildHyp, State,
      BuildHyp::KeyFunction, BuildHyp::PriorityFunction,
      State::Hash> OpenNodes;
    StateNodeMap stateNodes_;
    OpenNodes openNodes_;

    bool buildAndInsertOrRelax(
        NBestContext *context,
        const BuildHyp &current, Graph::NodeId currentNode, const BuildHyp &next, SequenceModel::Token token)
    {
      Graph::NodeId nextNode = stateNodes_[next.state];
      if (!nextNode) {
        nextNode = stateNodes_[next.state] = context->graph_.newNode();
        context->forwardProbability_.set(nextNode, LogProbability::invalid());
      }
      Graph::EdgeId edge = context->graph_.newEdge(currentNode, nextNode);
      context->token_.set(edge, token);
      context->probability_.set(
          edge, sequenceModel_->probability(token, current.state.history));
      if (context->forwardProbability_[nextNode] == LogProbability::invalid()) {
        return openNodes_.insertOrRelax(next);
      } else {
        verify(next.p <= context->forwardProbability_[nextNode]);
      }
      return false;
    }

  public:
    NBestContext *nBestInit(const Sequence &left) {
      require(sequenceModel_);
      verify(openNodes_.empty());
      verify(stateNodes_.empty());
      u32 maxStackSize = 0;

      NBestContext *context = new NBestContext(stackLimit_);
      BuildHyp current, next;
      current.state.pos  = 0;
      current.state.history = sequenceModel_->initial();
      current.p = LogProbability::certain();
      context->initial_ = stateNodes_[current.state] = context->graph_.newNode();
      context->forwardProbability_.set(context->initial_, LogProbability::invalid());
      openNodes_.insert(current);

      while (!openNodes_.empty()) {
        current = openNodes_.top(); openNodes_.pop();

        Graph::NodeId currentNode = stateNodes_[current.state];
        verify(currentNode);
        verify(context->forwardProbability_[currentNode] == LogProbability::invalid());
        context->forwardProbability_[currentNode] = current.p;

        if (current.state.history == sequenceModel_->culDeSac()) {
          verify(current.state.pos == left.size());
          continue;
        }

        verify(current.state.pos <= left.size());
        int lb = current.state.pos;
        LeftMap::const_iterator mi, mi_end;
        for (int le = lb + (int)minLeftLen_;
                 le <= lb +(int) maxLeftLen_ && le <= (int)left.size(); ++le) {
          Multigram lmg(&left[lb], &left[le]);
          for (Core::tie(mi, mi_end) = leftMap_.equal_range(lmg); mi != mi_end; ++mi) {
            SequenceModel::Token q = mi->second;
            next.state.pos = le;
            next.state.history = sequenceModel_->advanced(current.state.history, q);
            next.p = current.p * sequenceModel_->probability(q, current.state.history);
            buildAndInsertOrRelax(context, current, currentNode, next, q);
          }
        }
        if (current.state.pos == left.size()) { // end of string
          next.state.pos = left.size();
          next.state.history = sequenceModel_->culDeSac();
          next.p = current.p * sequenceModel_->probability(sequenceModel_->term(), current.state.history);
          buildAndInsertOrRelax(context, current, currentNode, next, sequenceModel_->term());
        }

        if (maxStackSize < openNodes_.size())
          maxStackSize = openNodes_.size();
        if (openNodes_.size() > stackLimit_) {
          openNodes_.clear(); stateNodes_.clear();
          throw std::runtime_error("stack size limit exceeded");
        }
      } // while (!openNodes_.empty())

      current.state.pos = left.size();
      current.state.history = sequenceModel_->culDeSac();
      context->final_ = stateNodes_[current.state];

      verify(openNodes_.empty());
      stateNodes_.clear();
      if (stackUsage_ < maxStackSize)
        stackUsage_ = maxStackSize;

      if (!context->final_) throw std::runtime_error("translation failed");

      context->initStack();
      return context;
    }

    LogProbability nBestNext(
        NBestContext *context,
        std::vector<MultigramIndex> &result)
    {
      std::shared_ptr<Trace> next = context->next();
      result.clear();
      if (!next) throw std::runtime_error("no further translations");
      result.push_back(sequenceModel_->init());
      for (std::shared_ptr<Trace> trace = next; trace; trace = trace->back)
        result.push_back(trace->q);
      return next->p;
    }

    LogProbability nBestBestLogLik(NBestContext *context) const {
      return context->forwardProbability_[context->final_];
    }

    /* CAVEAT: The following function computes the total likelihood
     * correctly only if the graph does not contain cycles.  However,
     * for empty input multigrams cycles do occur.  Presently we just
     * ignore this problem, but we try to keep the error low, by
     * initializing the forward sum array with the forward maximum
     * values.  A proper solution would either involve search with
     * iterative update to convergence or singular value decomposition
     * of the adjacency matrix. */

    LogProbability nBestTotalLogLik(NBestContext *context) const {
      NBestContext::NodeList nodesInTopogolicalOrder;
      GraphSorter sorter;
      sorter.sort(context->graph_, context->initial_, nodesInTopogolicalOrder);

      NodeMap<LogProbability> forward(&context->graph_);
#if 1
      for (EstimationGraph::NodeList::const_iterator n = nodesInTopogolicalOrder.begin(); n != nodesInTopogolicalOrder.end(); ++n)
        forward[*n] = context->forwardProbability_[*n];
#else
      forward.fill(LogProbability::impossible());
      forward[context->initial_] = LogProbability::certain();
#endif
      ProbabilityAccumulator accu;
      for (EstimationGraph::NodeList::const_iterator n = nodesInTopogolicalOrder.begin()+1; n != nodesInTopogolicalOrder.end(); ++n) {
        verify_(*n != eg->initial_);
        accu.clear() ;
        for (Graph::IncomingEdgeIterator e = context->graph_.incomingEdges(*n); e; ++e)
          accu.add(forward[context->graph_.source(*e)] * context->probability_[*e]);
        forward[*n] = accu.sum();
      }
      return forward[context->final_];
    }

}; // class Translator

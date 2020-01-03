/*
 * $Id: Estimation.cc 1691 2011-08-03 13:38:08Z hahn $
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

#include "Python.hh"  // Must be first to prevent some warnings

#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__) || (_MSC_VER)
#include <unordered_map>
using std::unordered_map;
#else
#include <tr1/unordered_map>
using std::tr1::unordered_map;
#endif

#include <vector>
#include <stdexcept>
#include <memory>

#include "Multigram.hh"
#include "MultigramGraph.hh"
#include "Probability.hh"
#include "SequenceModel.hh"
#include "Utility.hh"

class SequenceModelEstimator;

class EstimationGraph : public MultigramGraph {
  friend class EstimationGraphBuilder;
  friend class Accumulator;
  friend class ViterbiAccumulator;
  friend class OneForAllAccumulator;

  NodeList nodesInTopologicalOrder_;
  NodeMap<SequenceModel::History> histories_;
  public:
  EstimationGraph() :
    MultigramGraph(),
    histories_(&graph_)
  {}

  void yield() {
    graph_.yield();
    token_.yield();
    histories_.yield();
    probability_.yield();
    NodeList tmp(nodesInTopologicalOrder_);
    nodesInTopologicalOrder_.swap(tmp);
  }

  void updateHistories(const SequenceModel*);
  void updateProbabilities(const SequenceModel*);
#ifdef OBSOLETE
  void draw(FILE*, const StringInventory*, const SequenceModel*) const;
#endif // OBSOLETE

  size_t memoryUsed() const {
    return MultigramGraph::memoryUsed()
      + nodesInTopologicalOrder_.capacity() * sizeof(NodeList::value_type)
      + histories_.memoryUsed();
  }
};

#ifdef OBSOLETE
void EstimationGraph::draw(FILE *f, const StringInventory *si, const SequenceModel *sm) const {
  fprintf(f,
      "digraph \"estimation graph\" {\n"
      "ranksep = 1.0;\n"
      "rankdir = LR;\n"
      "size = \"8.5,11\";\n"
      "center = 1;\n"
      "orientation = Landscape\n"
      "node [fontname=\"Helvetica\"]\n"
      "edge [fontname=\"Helvetica\"]\n");

  for (Graph::NodeId n = graph_.nodesBegin(); n != graph_.nodesEnd(); ++n) {
    std::string label = (sm)? sm->formatHistory(histories_[n], si) : std::string("?");
    fprintf(f, "n%d [label=\"%s\"] \n", n, label.c_str());
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
#endif // OBSOLETE

void EstimationGraph::updateHistories(const SequenceModel *sm) {
  histories_.sync();
  histories_.fill(0);
  histories_[initial_] = sm->initial();
  histories_[final_] = sm->culDeSac();
  for (NodeList::const_iterator n = nodesInTopologicalOrder_.begin(); n != nodesInTopologicalOrder_.end(); ++n) {
    SequenceModel::History oldHistory = histories_[*n];
    for (Graph::OutgoingEdgeIterator e = graph_.outgoingEdges(*n); e; ++e) {
      Graph::NodeId target = graph_.target(*e);
      if (target == final_) continue;
      SequenceModel::History newHistory = sm->advanced(oldHistory, token_[*e]);
      verify(!histories_[target] || histories_[target] == newHistory);
      histories_[target] = newHistory;
    }
  }
}

void EstimationGraph::updateProbabilities(const SequenceModel *sm) {
  probability_.sync();
  for (Graph::EdgeId e = graph_.edgesBegin(); e != graph_.edgesEnd(); ++e) {
    probability_[e] = sm->probability(token_[e], histories_[graph_.source(e)]);
  }
}

// ===========================================================================
class EvidenceStore {
  public:
    struct Event {
      SequenceModel::History history;
      SequenceModel::Token token;

      bool operator==(const Event &other) const {
        return (token   == other.token)
          && (history == other.history);
      }

      struct Hash {
        size_t operator() (const Event &e) const {
          size_t h = size_t(e.history);
          h = (h << 4) ^ size_t(e.token);
          return h;
        }
      };
    };

  private:
    typedef unordered_map<Event, Probability, Event::Hash> Store;
    Store evidence_;

    const SequenceModel *sequenceModel_;

  public:
    EvidenceStore() : sequenceModel_(0) {}

    void setSequenceModel(SequenceModel *sm) {
      sequenceModel_ = sm;
    }

    void accumulate(
        SequenceModel::History history,
        SequenceModel::Token token,
        LogProbability evidence)
    {
      require(token != MultigramInventory::voidIndex()); // don't accumulate with anonymized unknowns!
      Event ev;
      ev.history = history;
      ev.token   = token;
      evidence_[ev] += evidence;
    }

    PyObject *asList() const {
      PyObject *result = PyList_New(evidence_.size());
      u32 i = 0;
      for (Store::const_iterator ev = evidence_.begin(); ev != evidence_.end(); ++ev) {
        PyObject *hte = Py_BuildValue("(Nif)",
            sequenceModel_->historyAsTuple(ev->first.history),
            int(ev->first.token),
            ev->second.probability());
        PyList_SET_ITEM(result, i++, hte);
      }
      return result;
    }

    size_t size() const {
      return evidence_.size();
    }

    u32 maximumHistoryLength() const {
      u32 result = 0;
      for (Store::const_iterator ev = evidence_.begin(); ev != evidence_.end(); ++ev)
        result = std::max(result, sequenceModel_->historyLength(ev->first.history));
      return result;
    }

    Probability maximum() const {
      Probability result = Probability::impossible();
      for (Store::const_iterator ev = evidence_.begin(); ev != evidence_.end(); ++ev)
        result = std::max(result, ev->second);
      return result;
    }
    Probability total() const {
      Probability result = Probability::impossible();
      for (Store::const_iterator ev = evidence_.begin(); ev != evidence_.end(); ++ev)
        result += ev->second;
      return result;
    }

    SequenceModelEstimator *makeSequenceModelEstimator() const;

    size_t memoryUsed() const {
#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__) || (_MSC_VER)
      struct StoreNode { typename Store::value_type value; bool cond;};
#elif __GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 3)
      typedef std::tr1::__detail::_Hash_node<Store::value_type, false> StoreNode;
#elif __GNUC__ == 4 && __GNUC_MINOR__ == 2
      typedef std::tr1::__detail::_Hash_node<Store::value_type, false> StoreNode;
#elif __GNUC__ == 4 && __GNUC_MINOR__ <= 1
      typedef Internal::hash_node<Store::value_type, false> StoreNode;
#endif
      return sizeof(EvidenceStore)
        + evidence_.size() * sizeof(StoreNode)
        + evidence_.bucket_count() * sizeof(StoreNode*);
    };
};

class Accumulator {
  EvidenceStore *target_;

  ProbabilityAccumulator accu_;
  NodeMap<LogProbability> forw_, bckw_;

  void forward(EstimationGraph *eg) {
    forw_[eg->initial_] = LogProbability::certain();
    for (EstimationGraph::NodeList::const_iterator n = eg->nodesInTopologicalOrder_.begin()+1; n != eg->nodesInTopologicalOrder_.end(); ++n) {
      verify_(*n != eg->initial_);
      accu_.clear() ;
      for (Graph::IncomingEdgeIterator e = eg->graph_.incomingEdges(*n); e; ++e)
        accu_.add(forw_[eg->graph_.source(*e)] * eg->probability_[*e]);
      forw_[*n] = accu_.sum();
    }
  }

  void backward(EstimationGraph *eg) {
    bckw_[eg->final_] = LogProbability::certain();
    for (EstimationGraph::NodeList::reverse_iterator n = eg->nodesInTopologicalOrder_.rbegin()+1; n != eg->nodesInTopologicalOrder_.rend(); ++n) {
      verify_(*n != eg->final_);
      accu_.clear() ;
      for (Graph::OutgoingEdgeIterator e = eg->graph_.outgoingEdges(*n); e; ++e)
        accu_.add(bckw_[eg->graph_.target(*e)] * eg->probability_[*e]);
      bckw_[*n] = accu_.sum();
    }
  }

  public:
  Accumulator() : target_(0) {}

  void setTarget(EvidenceStore *es) {
    target_ = es;
  }

  LogProbability accumulate(EstimationGraph *eg, LogProbability weight) {
    forw_.sync(&eg->graph_); forward(eg);
    bckw_.sync(&eg->graph_); backward(eg);
#if 1 // DEBUG
    if (!isNearlyEqual(forw_[eg->final_].score(), bckw_[eg->initial_].score(), 100)) {
      std::cerr << __FILE__ << ":" << __LINE__ << "\t"
        << forw_[eg->final_].score() << "\t"
        << bckw_[eg->initial_].score() << std::endl;
    }
#endif
    LogProbability total = (forw_[eg->final_] * bckw_[eg->initial_]).pow(0.5);
    for (Graph::EdgeId e = eg->graph_.edgesBegin(); e != eg->graph_.edgesEnd(); ++e) {
      Graph::NodeId source = eg->graph_.source(e);
      LogProbability post
        = forw_[source]
        * eg->probability_[e]
        * bckw_[eg->graph_.target(e)]
        / total;
#if 1 // DEBUG
      if (post > LogProbability::certain() &&
          !isNearlyEqual(post.probability(), 1.0, 100)) {
        std::cerr << __FILE__ << ":" << __LINE__ << "\t"
          << forw_[eg->final_].score() << "\t"
          << bckw_[eg->initial_].score() << "\t"
          << total.score() << "\t"
          << forw_[source].score() << "\t"
          << eg->probability_[e].score() << "\t"
          << bckw_[eg->graph_.target(e)].score() << "\t"
          << post.score() << std::endl;
      }
#endif
      target_->accumulate(eg->histories_[source], eg->token_[e], weight * post);
    }
    return total;
  }

  LogProbability logLik(EstimationGraph *eg) {
    forw_.sync(&eg->graph_); forward(eg);
#if 1
    return forw_[eg->final_];
#else
    bckw_.sync(&eg->graph_); backward(eg);
    return (forw_[eg->final_] * bckw_[eg->initial_]).pow(0.5);
#endif
  }
};

class ViterbiAccumulator {
  EvidenceStore *target_;

  NodeMap<LogProbability> forw_;
  NodeMap<Graph::EdgeId> back_;

  void forward(EstimationGraph *eg) {
    forw_[eg->initial_] = LogProbability::certain();
    for (EstimationGraph::NodeList::const_iterator n = eg->nodesInTopologicalOrder_.begin()+1; n != eg->nodesInTopologicalOrder_.end(); ++n) {
      verify_(*n != eg->initial_);
      LogProbability bestProb = LogProbability::impossible();
      Graph::EdgeId bestBack = 0;
      for (Graph::IncomingEdgeIterator e = eg->graph_.incomingEdges(*n); e; ++e) {
        LogProbability f = forw_[eg->graph_.source(*e)] * eg->probability_[*e];
        if (bestProb < f) {
          bestProb = f;
          bestBack = *e;
        }
      }
      forw_[*n] = bestProb;
      back_[*n] = bestBack;
    }
  }

  public:
  ViterbiAccumulator() : target_(0) {}

  void setTarget(EvidenceStore *es) {
    target_ = es;
  }

  LogProbability accumulate(EstimationGraph *eg, LogProbability weight) {
    forw_.sync(&eg->graph_); back_.sync(&eg->graph_); forward(eg);

    for (Graph::NodeId n = eg->final_; n != eg->initial_;) {
      Graph::EdgeId e = back_[n];
      Graph::NodeId source = eg->graph_.source(e);
      target_->accumulate(eg->histories_[source], eg->token_[e], weight);
      n = source;
    }
    return forw_[eg->final_];
  }

  LogProbability logLik(EstimationGraph *eg) {
    forw_.sync(&eg->graph_); back_.sync(&eg->graph_); forward(eg);
    return forw_[eg->final_];
  }

  LogProbability segment(EstimationGraph *eg, std::vector<MultigramIndex> &result) {
    forw_.sync(&eg->graph_); back_.sync(&eg->graph_); forward(eg);
    result.clear();
    for (Graph::NodeId n = eg->final_; n != eg->initial_;) {
      Graph::EdgeId e = back_[n];
      result.push_back(eg->token_[e]);
      n = eg->graph_.source(e);
    }
    std::reverse(result.begin(), result.end());
    return forw_[eg->final_];
  }
};

class OneForAllAccumulator {
  EvidenceStore *target_;

  public:
  OneForAllAccumulator() : target_(0) {}

  void setTarget(EvidenceStore *es) {
    target_ = es;
  }

  void accumulate(EstimationGraph *eg, LogProbability weight) {
    for (Graph::EdgeId e = eg->graph_.edgesBegin(); e != eg->graph_.edgesEnd(); ++e) {
      target_->accumulate(eg->histories_[eg->graph_.source(e)], eg->token_[e], weight);
    }
  }
};

// ===========================================================================
class EstimationGraphBuilder :
  public GraphSorter
{
  public:
    enum MultigramEmergenceMode {
      emergeNewMultigrams,
      suppressNewMultigrams,
      anonymizeNewMultigrams
    };

  private:
    struct SizeTemplate {
      u32 left, right;
    };
    typedef std::vector<SizeTemplate> SizeTemplateList;
    SizeTemplateList sizeTemplates_;
    MultigramEmergenceMode multigramEmergence_;

  public:
    void clearSizeTemplates() {
      sizeTemplates_.clear();
    }
    void addSizeTemplate(int left, int right) {
      require(left >= 0);
      require(right >= 0);
      require(left > 0 || right > 0);
      require(left  <= static_cast<int>(Multigram::maximumLength));
      require(right <= static_cast<int>(Multigram::maximumLength));
      SizeTemplate st;
      st.left = left;
      st.right = right;
      sizeTemplates_.push_back(st);
    }

    void setEmergenceMode(MultigramEmergenceMode mode) {
      multigramEmergence_ = mode;
    }

  private:
    MultigramInventory *inventory_;
    SequenceModel *sequenceModel_;
  public:
    void setSequenceModel(MultigramInventory *mi, SequenceModel *sm) {
      inventory_ = mi;
      sequenceModel_ = sm;
    }

  private:
    Sequence left_, right_;
    EstimationGraph *target_;

    struct NodeDesc {
      struct {
        u32 left, right;
      } position;
      SequenceModel::History history;

      bool operator==(const NodeDesc &other) const {
        return (position.left  == other.position.left)
          && (position.right == other.position.right)
          && (history        == other.history);
      }

      struct Hash {
        size_t operator() (const NodeDesc &s) const {
          size_t h = size_t(s.history);
          h = (h << 0) ^ s.position.left;
          h = (h << 4) ^ s.position.right;
          return h;
        }
      };
    };

    static const Graph::NodeId newNode = 0;
    static const Graph::NodeId greyNode = 0xfffffff;
    static const Graph::NodeId deadNode = 0xffffffe;
    typedef unordered_map<NodeDesc, Graph::NodeId, NodeDesc::Hash> NodeStateMap;
    NodeStateMap nodeStates_;
    typedef std::pair<NodeDesc, SizeTemplateList::const_iterator> DfsStackItem;
    typedef std::vector<DfsStackItem> DfsStack;
    DfsStack stack_;

    bool expand(
        const NodeDesc &current,
        SizeTemplateList::const_iterator st,
        NodeDesc &next,
        SequenceModel::Token &token)
    {
      next.position.left = current.position.left + st->left;
      if (next.position.left > left_.size())
        return false;
      next.position.right = current.position.right + st->right;
      if (next.position.right > right_.size())
        return false;

      JointMultigram jmg(
          &left_ [current.position.left ], &left_ [next.position.left ],
          &right_[current.position.right], &right_[next.position.right]);

      switch (multigramEmergence_) {
        case emergeNewMultigrams:
          token = inventory_->index(jmg);
          break;
        case suppressNewMultigrams:
          token = inventory_->testIndex(jmg);
          if (token == MultigramInventory::voidIndex())
            return false;
          break;
        case anonymizeNewMultigrams:
          token = inventory_->testIndex(jmg);
          break;
        default: defect();
      }

      next.history = sequenceModel_->advanced(current.history, token);

      return true;
    }

    bool isFinal(const NodeDesc &current) {
      return (current.position.left  == left_ .size() &&
          current.position.right == right_.size());
    }

    void explore() {
      while (!stack_.empty()) {
        DfsStackItem &top(stack_.back());
        NodeDesc &current(top.first);
        SizeTemplateList::const_iterator &st(top.second);
        Graph::NodeId currentState = nodeStates_[current];
        verify(currentState != newNode);
        verify(currentState != deadNode);

        if (isFinal(current)) {
          verify(nodeStates_[current] == greyNode);
          if (!target_->final_) {
            target_->final_ = target_->graph_.newNode();
            target_->nodesInTopologicalOrder_.push_back(target_->final_);
          }
          Graph::NodeId currentState = nodeStates_[current] = target_->graph_.newNode();
          target_->nodesInTopologicalOrder_.push_back(currentState);
          Graph::EdgeId edge = target_->graph_.newEdge(currentState, target_->final_);
          target_->token_.set(edge, sequenceModel_->term());
          stack_.pop_back();
        } else if (st != sizeTemplates_.end()) {
          NodeDesc next;
          SequenceModel::Token token;
          if (expand(current, st++, next, token)) {
            Graph::NodeId nextState = nodeStates_[next];
            if (nextState == newNode) {
              --st;
              nodeStates_[next] = greyNode;
              stack_.push_back(DfsStackItem(next, sizeTemplates_.begin()));
            } else if (nextState == greyNode) {
              defect(); // cycle detected!
            } else if (nextState != deadNode) {
              if (currentState == greyNode) {
                currentState = nodeStates_[current] = target_->graph_.newNode();
              }
              Graph::EdgeId edge = target_->graph_.newEdge(currentState, nextState);
              target_->token_.set(edge, token);
            }
          }
        } else {
          if (currentState == greyNode)
            nodeStates_[current] = deadNode;
          else
            target_->nodesInTopologicalOrder_.push_back(currentState);
          stack_.pop_back();
        }
      }
    }

  public:
    EstimationGraphBuilder() :
      multigramEmergence_(emergeNewMultigrams),
      inventory_(0),
      sequenceModel_(0),
      target_(0)
  {}

    void build(EstimationGraph *eg, const Sequence &left, const Sequence &right) {
      left_   = left;
      right_  = right;
      target_ = eg;

      target_->graph_.clear();
      target_->initial_ = target_->final_ = 0;
      NodeDesc initial;
      initial.position.left = initial.position.right = 0;
      initial.history = sequenceModel_->initial();
      nodeStates_[initial] = greyNode;
      stack_.push_back(DfsStackItem(initial, sizeTemplates_.begin()));
      target_->nodesInTopologicalOrder_.clear();
      explore();
      target_->initial_ = nodeStates_[initial];
      nodeStates_.clear();
      std::reverse(target_->nodesInTopologicalOrder_.begin(),
          target_->nodesInTopologicalOrder_.end());

      verify(target_->initial_ != greyNode);
      verify(target_->initial_ != newNode);
      if (target_->initial_ == deadNode)
        throw std::runtime_error("final node not reachable");

      verify(target_->nodesInTopologicalOrder_.size() == target_->graph_.nNodes() - 1);
      verify(target_->nodesInTopologicalOrder_.front() == target_->initial_);
      verify(target_->nodesInTopologicalOrder_.back() == target_->final_);

      target_->updateHistories(sequenceModel_);
      target_->updateProbabilities(sequenceModel_);
    }

    EstimationGraph *create(const Sequence &left, const Sequence &right) {
      EstimationGraph *result = new EstimationGraph;
      try {
        build(result, left, right);
      } catch (...) {
        delete result; result = 0;
        throw;
      }
      result->yield();
      return result;
    }

    void update(EstimationGraph *eg) {
      eg->updateHistories(sequenceModel_);
      eg->updateProbabilities(sequenceModel_);
    }

    size_t memoryUsed() const {
#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__) || (_MSC_VER)
      struct NodeStateMapNode { typename NodeStateMap::value_type value; bool cond;};
#elif __GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 3)
      typedef std::tr1::__detail::_Hash_node<NodeStateMap::value_type, false> NodeStateMapNode;
#elif __GNUC__ == 4 && __GNUC_MINOR__ == 2
      typedef std::tr1::__detail::_Hash_node<NodeStateMap::value_type, false> NodeStateMapNode;
#elif __GNUC__ == 4 && __GNUC_MINOR__ <= 1
      typedef Internal::hash_node<NodeStateMap::value_type, false> NodeStateMapNode;
#endif
      return sizeof(EstimationGraphBuilder)
        + GraphSorter::memoryUsed() - sizeof(GraphSorter)
        + sizeTemplates_.capacity() * sizeof(SizeTemplateList::value_type)
        + left_.capacity() * sizeof(Sequence::value_type)
        + right_.capacity() * sizeof(Sequence::value_type)
        + nodeStates_.size() * sizeof(NodeStateMapNode)
        + nodeStates_.bucket_count() * sizeof(NodeStateMapNode*)
        + stack_.capacity() * sizeof(DfsStack::value_type);
    }

};

// ===========================================================================
class SequenceModelEstimator {
  private:
    friend class EvidenceStore;

    struct Item : public EvidenceStore::Event {
      Probability evidence;
      Probability probability;

      struct Ordering {
        bool operator() (const Item &a, const Item &b) const {
          if (a.history != b.history) return a.history < b.history;
          return a.token < b.token;
        }
      };
      struct TokenOrdering {
        bool operator() (const Item &a, const Item &b) const {
          return a.token < b.token;
        }
      };
    };
    typedef std::vector<Item> ItemList;

    struct Group {
      struct { ItemList::iterator begin, end; } items;
      Probability total;
      Probability backOffWeight;
      Group() : total() {}
    };

    typedef unordered_map<SequenceModel::History, Group, Core::conversion<SequenceModel::History, size_t> > GroupStore;

    const SequenceModel *sequenceModel_;
    ItemList items;
    Item::Ordering itemOrdering;
    Item::TokenOrdering itemTokenOrdering;
    GroupStore groups;
    std::vector<std::vector<SequenceModel::History> > historiesByLength;

    void init(const SequenceModel*);
    void reset();
    void doKneserNeyDiscounting(const std::vector<double> &discounts);
    void computeProbabilities(double vocabularySize);
  public:
    void makeSequenceModel(
        SequenceModel *target,
        double vocabularySize,
        const std::vector<double> &discounts);
};

SequenceModelEstimator *EvidenceStore::makeSequenceModelEstimator() const {
  SequenceModelEstimator *sme = new SequenceModelEstimator();

  sme->items.clear();
  SequenceModelEstimator::Item item;
  unordered_map<Event, size_t, Event::Hash> pos;
  for (Store::const_iterator ev = evidence_.begin(); ev != evidence_.end(); ++ev) {
    item.history     = ev->first.history;
    item.token       = ev->first.token;
    item.evidence    = ev->second;
    pos[item] = sme->items.size();
    sme->items.push_back(item);
  }

  // ensure all events we are going to discount to are present
  for (size_t i = 0; i < sme->items.size(); ++i) {
    item = sme->items[i];
    item.evidence = Probability(0.0);
    item.history = sequenceModel_->shortened(item.history);
    if (item.history && pos.find(item) == pos.end()) {
      pos[item] = sme->items.size();
      sme->items.push_back(item);
    }
  }

  sme->init(sequenceModel_);
  return sme;
}

void SequenceModelEstimator::makeSequenceModel(
    SequenceModel *target,
    double vocabularySize,
    const std::vector<double> &discounts)
{
  reset();
  doKneserNeyDiscounting(discounts);
  computeProbabilities(vocabularySize);

#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__) || (_MSC_VER)
  std::shared_ptr<SequenceModel::InitData> data(new SequenceModel::InitData);
  //std::unique_ptr<SequenceModel::InitData> data;
  //data = std::move(new SequenceModel::InitData);
#else
  std::auto_ptr<SequenceModel::InitData> data(new SequenceModel::InitData);
#endif
  std::vector<SequenceModel::Token> history;
  for (GroupStore::const_iterator g = groups.begin(); g != groups.end(); ++g) {
    sequenceModel_->historyAsVector(g->first, history);
    std::reverse(history.begin(), history.end());
    data.get()->setHistory(&*history.begin(), &*history.end());

    if (g->second.backOffWeight != Probability(1.0))
      data->addBackOffWeight(g->second.backOffWeight);
    for (ItemList::const_iterator i = g->second.items.begin; i != g->second.items.end; ++i) {
      if (i->probability > Probability(0.0))
        data->addProbability(i->token, i->probability);
    }
  }
  target->setInitAndTerm(sequenceModel_->init(), sequenceModel_->term());
  target->set(&*data);
}

void SequenceModelEstimator::init(const SequenceModel *sm) {
  require(items.size() > 0);

  sequenceModel_ = sm;

  std::sort(items.begin(), items.end(), itemOrdering);

  groups.clear();
  historiesByLength.clear();
  Group ng;
  ItemList::iterator &i(ng.items.begin);
  i = items.begin();
  GroupStore::iterator g = groups.insert(std::make_pair(i->history, ng)).first;
  for (++i; i != items.end(); ++i) {
    if (i->history != g->first) {
      g->second.items.end = i;
      g = groups.insert(std::make_pair(i->history, ng)).first;
    }
  }
  g->second.items.end = items.end();

  for (GroupStore::const_iterator g = groups.begin(); g != groups.end(); ++g) {
    u32 hl = sequenceModel_->historyLength(g->first);
    if (hl >= historiesByLength.size()) historiesByLength.resize(hl+1);
    historiesByLength[hl].push_back(g->first);
  }
}

void SequenceModelEstimator::reset() {
  for (ItemList::iterator i = items.begin(); i != items.end(); ++i)
    i->probability = i->evidence;
}

void SequenceModelEstimator::doKneserNeyDiscounting(const std::vector<double> &discounts) {
  require(historiesByLength.size() > 0);
  require(discounts.size() >= historiesByLength.size());
  for (u32 level = historiesByLength.size()-1; level > 0; --level) {
    Probability discount(discounts[level]);
    std::vector<SequenceModel::History>::const_iterator h, h_end = historiesByLength[level].end();
    for (h = historiesByLength[level].begin(); h != h_end; ++h) {
      SequenceModel::History history = *h;
      SequenceModel::History shorterHistory = sequenceModel_->shortened(history);
      Group &g(groups[history]);
      verify_(groups.find(shorterHistory) != groups.end());
      Group &sg(groups[shorterHistory]);
      Probability sum;
      ItemList::iterator si = sg.items.begin;
      for (ItemList::iterator i = g.items.begin; i != g.items.end; ++i) {
#if 0 // DEBUG
        std::cout << __FILE__ << ":" << __LINE__ << "\t"
          << i - items.begin() << "\t"
          << "(" << sequenceModel_->formatHistory(i->history) << ")\t"
          << i->token << "\t"
          << i->probability.probability() << std::endl;
#endif
        Item sItem = *i;
        sum += i->probability;
        if (i->probability > discount) {
          i->probability -= discount;
          sItem.probability = discount;
        } else {
          i->probability = Probability(0.0);
        }
        verify_(si != sg.items.end); while (itemTokenOrdering(*si, sItem)) {
          ++si;
#if 0 // DEBUG
          std::cout << __FILE__ << ":" << __LINE__ << "\t"
            << si - items.begin() << "\t"
            << "(" << sequenceModel_->formatHistory(si->history) << ")\t"
            << si->token << "\t"
            << si->probability.probability() << std::endl;
#endif
          verify_(si != sg.items.end);
        }
        verify(si->token == sItem.token);
        si->probability += sItem.probability;
      }
      g.total = sum;
    }
  }
  u32 level = 0;
  Probability discount(discounts[level]);
  std::vector<SequenceModel::History>::const_iterator h, h_end = historiesByLength[level].end();
  for (h = historiesByLength[level].begin(); h != h_end; ++h) {
    SequenceModel::History history = *h;
    Group &g(groups[history]);
    Probability sum;
    for (ItemList::iterator i = g.items.begin; i != g.items.end; ++i) {
      sum += i->probability;
      if (i->probability > discount) {
        i->probability -= discount;
      } else {
        i->probability = Probability(0.0);
      }
    }
    g.total = sum;
  }
}

void SequenceModelEstimator::computeProbabilities(double vocabularySize) {
  // compute probabilities with interpolation
  Probability zeroGramProbability(1.0 / vocabularySize);

  for (u32 level = 0; level < historiesByLength.size(); ++level) {
    std::vector<SequenceModel::History>::const_iterator h, h_end = historiesByLength[level].end();
    for (h = historiesByLength[level].begin(); h != h_end; ++h) {
      SequenceModel::History history = *h;
      Group &g(groups[history]);

      Probability sum(0.0);
      for (ItemList::const_iterator i = g.items.begin; i != g.items.end; ++i)
        sum += i->probability;
      if (sum > g.total) {
        g.backOffWeight = Probability(0.0);
      } else if (sum <= Probability(0.0)) {
        g.backOffWeight = Probability(1.0);
      } else {
        g.backOffWeight = (sum / g.total).complement();
      }

      SequenceModel::History shorterHistory = sequenceModel_->shortened(history);
      if (shorterHistory == 0) {
        g.backOffWeight *= zeroGramProbability;
        for (ItemList::iterator i = g.items.begin; i != g.items.end; ++i) {
          if (i->probability == Probability(0.0)) continue;
          i->probability = i->probability / g.total + g.backOffWeight;
        }
      } else {
        const Group &sg(groups[shorterHistory]);
        ItemList::const_iterator si = sg.items.begin;
        for (ItemList::iterator i = g.items.begin; i != g.items.end; ++i) {
          if (i->probability == Probability(0.0)) continue;
          Probability pLowerOrder;
          verify_(si != sg.items.end); while (itemTokenOrdering(*si, *i)) { ++si; verify_(si != sg.items.end); }
          verify_(si->token == i->token);
          if (si->probability > Probability(0.0)) {
            pLowerOrder = si->probability;
          } else {
            pLowerOrder = sg.backOffWeight;
            for (SequenceModel::History boh = sequenceModel_->shortened(shorterHistory); boh; boh = sequenceModel_->shortened(boh)) {
              Group &bog(groups[boh]);
              ItemList::const_iterator boi = std::lower_bound(bog.items.begin, bog.items.end, *i, itemTokenOrdering);
              verify_(boi != bog.items.end && boi->token == i->token);
              if (boi->probability > Probability(0.0)) {
                pLowerOrder *= boi->probability;
                break;
              }
              pLowerOrder *= bog.backOffWeight;
            }
          }

          i->probability = i->probability / g.total + g.backOffWeight * pLowerOrder;
        }
      }
    } // for (h)
  } // for (level)
}

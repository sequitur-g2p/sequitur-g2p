/*
 * $Id: SequenceModel.cc 1691 2011-08-03 13:38:08Z hahn $
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

#include <memory>
#include <stdexcept>

#include "SequenceModel.hh"
#include "Types.hh"
#include "Utility.hh"


#if defined(INSTRUMENTATION)
// ===========================================================================
// StringInventory

StringInventory::StringInventory() {
  list_.push_back(0);
}

StringInventory::StringInventory(PyObject *strings) {
  if (!PySequence_Check(strings))
    throw PythonException(PyExc_TypeError, "not a sequence");

  u32 len = PySequence_Length(strings);
  list_.resize(len+1);
  list_[0] = 0;
  for (u32 i = 0; i < len; ++i) {
    PyObject *item = PySequence_GetItem(strings, i);
    if (!PyString_Check(item))
      throw PythonException(PyExc_TypeError, "not a string");
    const char *str = strdup(PyString_AsString(item));
    Py_DECREF(item);
    list_[i+1] = str;
    map_[str] = i+1;
  }
}

StringInventory::~StringInventory() {
  for (List::iterator i = list_.begin(); i != list_.end(); ++i)
    free((void*) *i);
}
#endif // INSTRUMENTATION

// ===========================================================================
// internal data structures

namespace SequenceModelPrivate {
  typedef SequenceModel::Token Token;

  template <class Node>
    const Node *binarySearch(const Node *l, const Node *r, Token t) {
      while (l <= r) {
        const Node *m = l + (r - l) / 2;
        if (t < m->token()) {
          r = m - 1;
        } else if (t > m->token()) {
          l = m + 1;
        } else /* t == m->token() */ {
          return m;
        }
      }
      return 0;
    }
}

using namespace SequenceModelPrivate;

class SequenceModel::Node {
  public:
    typedef std::vector<Node>::size_type Index;
    static const Index invalidIndex = 2000000000;
    typedef u16 Depth;

  private: // internal data
    friend class Internal;
    friend class SequenceModel;

    Token token_;  /**< least recent word in history */
    LogProbability backOffWeight_;
    Depth depth_;  /**< number of words in history */

    union parent_t {
      Node *finalized;
      Index init;
    } parent_;

    union node_struct_t {
      struct finalized_t {
        Node *firstChild_;
        WordProbability *firstWordProbability_;
      } finalized;
      struct done_t {
        Index firstChild_;
        size_t firstWordProbability_;
      } done;
      struct  init_t {
        InitItem *begin, *end;
      } init;
    } node_struct ;

  public:
    Token token() const { return token_; }
    LogProbability backOffWeight() const { return backOffWeight_; }
    Depth depth() const { return depth_; }

    const Node *parent() const { return parent_.finalized; }

    const Node *childrenBegin() const { return           node_struct.finalized.firstChild_; }
    const Node *childrenEnd()   const { return (this+1)->node_struct.finalized.firstChild_; }

    const WordProbability *probabilitiesBegin() const { return           node_struct.finalized.firstWordProbability_; }
    const WordProbability *probabilitiesEnd()   const { return (this+1)->node_struct.finalized.firstWordProbability_; }

    const Node *findChild(Token) const;
    const WordProbability *findWordProbability(Token) const;
};

const SequenceModel::Node *SequenceModel::Node::findChild(Token t) const {
  return binarySearch(childrenBegin(), childrenEnd() - 1, t);
}

const SequenceModel::WordProbability *SequenceModel::Node::findWordProbability(Token t) const {
  return binarySearch(probabilitiesBegin(), probabilitiesEnd() - 1, t);
}


class SequenceModel::Internal {
  private:
    friend class SequenceModel;

    typedef std::vector<Node> Nodes;
    Nodes nodes;

    typedef std::vector<WordProbability> WordProbabilities;
    WordProbabilities wordProbabilities;

    struct InitItemOrdering {
      bool operator() (const InitItem &a, const InitItem &b) const {
        if (a.history[0])
          return a.history[0] < b.history[0];
        else
          return (b.history[0]) || (a.token < b.token);
      }
    };

    void buildNode(Node::Index);

  public:
    Internal(Node::Index nNodes, Node::Index nWordProbabilities);
    ~Internal();
#ifdef OBSOLETE
    void dump(std::ostream&, const StringInventory*) const;
#endif
    const Node *build(InitItem*, InitItem*);

    static const Node *extendHistory(const Node *root, const Node *old, Token w);
    static LogProbability probability(const Node*, Token);
};

SequenceModel::Internal::Internal(Node::Index nNodes, Node::Index nWordProbabilities) {
  nodes.reserve(nNodes+1);
  wordProbabilities.reserve(nWordProbabilities);
}

SequenceModel::Internal::~Internal() {}

const SequenceModel::Node *SequenceModel::Internal::build(InitItem *begin, InitItem *end) {
  Node root;
  root.token_        = 0;
  root.backOffWeight_ = LogProbability::impossible();
  root.depth_        = 0;
  root.parent_.init  = Node::invalidIndex;
  root.node_struct.init.begin    = begin;
  root.node_struct.init.end      = end;
  nodes.push_back(root);

  for (Node::Index n = 0; n < nodes.size(); ++n)
    buildNode(n);

  Node sentinel;
  sentinel.node_struct.done.firstChild_     = nodes.size();
  sentinel.node_struct.done.firstWordProbability_ = wordProbabilities.size();
  sentinel.token_        = 0;   // phony
  sentinel.backOffWeight_ = LogProbability::certain(); // phony
  sentinel.depth_        = 0;   // phony
  sentinel.parent_.init  = nodes.size(); // phony
  nodes.push_back(sentinel);
  WordProbability sentinel2;
  wordProbabilities.push_back(sentinel2);

  for (Nodes::iterator n = nodes.begin(); n != nodes.end(); ++n) {
    Node::Index parent         = n->parent_.init;
    n->parent_.finalized       = (parent != Node::invalidIndex) ? &nodes[parent] : 0;
    Node::Index firstChild     = n->node_struct.done.firstChild_;
    Node::Index firstWordProbability = n->node_struct.done.firstWordProbability_;
    n->node_struct.finalized.firstChild_     = &nodes[firstChild];
    n->node_struct.finalized.firstWordProbability_ = &wordProbabilities[firstWordProbability];
  }
  nodes[0].parent_.finalized = 0;

  return &nodes[0];
}

void SequenceModel::Internal::buildNode(Node::Index ni) {
  Node &n(nodes[ni]);
  InitItem *i = n.node_struct.init.begin, *end = n.node_struct.init.end;

  std::sort(i, end, InitItemOrdering());

  n.node_struct.done.firstWordProbability_ = wordProbabilities.size();
  for (; i < end && i->history[0] == 0; ++i) {
    if (i->token) {
      WordProbability ws;
      ws.token_ = i->token;
      ws.probability_ = i->probability;
      wordProbabilities.push_back(ws);
    } else {
      n.backOffWeight_ = i->probability;
    }
  }

  n.node_struct.done.firstChild_ = nodes.size();
  Node::Depth d = n.depth_ + 1;
  for (; i < end ;) {
    verify(i->history[0]);
    Node nn;
    nn.parent_.init    = ni;
    nn.depth_          = d;
    nn.token_          = *i->history++;
    nn.backOffWeight_   = LogProbability::certain();
    nn.node_struct.init.begin      = i++;
    while (i < end && *i->history == nn.token_) { i->history++; ++i; }
    nn.node_struct.init.end        = i;
    nodes.push_back(nn); // CAVEAT: invalidates n
  }
}

SequenceModel::SequenceModel() {
  internal_ = 0;
  root_ = 0;
  initialize(0, 0);
  sentenceBegin_ = sentenceEnd_ = 0;
}

void SequenceModel::initialize(InitItem *begin, InitItem *end) {
  delete internal_;

  u32 nNodes = 0, nWordProbabilities = 0;
  for (const InitItem *i = begin; i != end; ++i) {
    if (i->token)
      ++nWordProbabilities;
    else
      ++nNodes;
  }
  nNodes += 2; // nNodes is just an educated guess, not a constraint

  internal_ = new Internal(nNodes, nWordProbabilities);
  root_ = internal_->build(begin, end);
}

size_t SequenceModel::memoryUsed() const {
  return sizeof(SequenceModel)
    + sizeof(Internal)
    + internal_->nodes.capacity() * sizeof(Internal::Nodes::value_type)
    + internal_->wordProbabilities.capacity() * sizeof(Internal::WordProbabilities::value_type);
}

// ===========================================================================
// sequence model interface

SequenceModel::~SequenceModel() {
  delete internal_;
}

SequenceModel::History SequenceModel::initial() const {
  const Node *n = root_->findChild(sentenceBegin_);
  if (!n) n = root_;
  ensure(n);
  return n;
}

SequenceModel::History SequenceModel::advanced(const Node *old, Token w) const {
  require_(old);
  Token *hist = new Token[old->depth() + 1];

  for (const Node *n = old; n; n = n->parent())
    hist[n->depth()] = n->token();
  verify(!hist[0]);
  hist[0] = w;

  const Node *result = root_;
  for (Node::Depth d = 0; d <= old->depth(); ++d) {
    const Node *n = result->findChild(hist[d]);
    if (!n) break;
    result = n;
  }
  ensure(result);

  delete[] hist;
  return result;
}

u32 SequenceModel::historyLength(const Node *h) const {
  require_(h);
  return h->depth();
}

SequenceModel::History SequenceModel::shortened(const Node *h) const {
  require_(h);
  return h->parent();
}

#ifdef OBSOLETE
std::string SequenceModel::formatHistory(const Node *h, const StringInventory *si) const {
  std::string result;
  if (!h) return "(void)";
  for (; h; h = h->parent()) {
    if (h->token()) {
      if (si)
        result = si->symbol(h->token()) + " " + result;
      else {
        std::ostringstream os;
        os << h->token() << " " << result;
        result = os.str();
      }
    }
  }
  return result;
}
#endif // OBSOLETE

PyObject *SequenceModel::historyAsTuple(const Node *h) const {
  require_(h);
  u32 length = h->depth();
  PyObject *result = PyTuple_New(length);
  for (; h; h = h->parent()) {
    if (h->token())
      PyTuple_SET_ITEM(result, length - h->depth(), PyInt_FromLong(h->token()));
  }
  return result;
}

void SequenceModel::historyAsVector(const Node *h, std::vector<Token> &out) const {
  u32 length = h->depth();
  out.resize(length);
  for (; h; h = h->parent()) {
    if (h->token())
      out[length - h->depth()] = h->token();
  }
}

LogProbability SequenceModel::probability(Token w, const Node *h) const {
  require_(h);
  LogProbability probability = LogProbability::certain();
  for (const Node *n = h; n;  n = n->parent()) {
    const WordProbability *ws = n->findWordProbability(w);
    if (ws) {
      probability *= ws->probability();
      break;
    }
    probability *= n->backOffWeight();
  }
  return probability;
}

LogProbability SequenceModel::probability(Token w, const std::vector<Token> &history) const {
  const Node *hn = root_;
  for (unsigned int i = history.size(); i;) {
    const Node *n = hn->findChild(history[--i]);
    if (!n) break;
    hn = n;
  }
  return probability(w, hn);
}

// ===========================================================================
SequenceModel::InitData::InitData() {
  ii.history = histories.add(0);
  ii.token = 0;
}

void SequenceModel::InitData::setHistory(const Token *newest, const Token *oldest) {
  const Token *h, *t;
  for (h = ii.history, t = newest; t != oldest && (*h == *t); ++h, ++t);
  if (*h == 0 && t == oldest) return;
  ii.history = histories.add0(newest, oldest);
}

void SequenceModel::InitData::addProbability(Token predicted, LogProbability probability) {
  ii.token = predicted;
  ii.probability = probability;
  items.push_back(ii);
}
void SequenceModel::InitData::addBackOffWeight(LogProbability probability) {
  ii.token = 0;
  ii.probability = probability;
  items.push_back(ii);
}


#ifdef OBSOLETE

void SequenceModel::Internal::dump(std::ostream &os, const StringInventory *strings) const {
  for (Nodes::iterator n = nodes.begin(); n+1 != nodes.end(); ++n) {
    for (const WordProbability *ws = n->finalized.firstWordProbability_; ws != (n+1)->finalized.firstWordProbability_; ++ws) {
      os << ws->probability_.probability() << '\t';
      for (const Node *pn = &*n; pn; pn = pn->parent())
        os << strings->symbol(pn->token()) << '\t';
      os << strings->symbol(ws->token_) << std::endl;
    }
    os << "BACKOFF\t";
    for (const Node *pn = &*n; pn; pn = pn->parent())
      os << strings->symbol(pn->token()) << '\t';
    os << n->backOffWeight().probability() << std::endl;
  }
}

void SequenceModel::dump(
    const std::string &filename,
    const StringInventory *strings) const
{
  std::ofstream os(filename.c_str());
  internal_->dump(os, strings);
}

#endif // OBSOLETE


void SequenceModel::set(InitData *data) {
  initialize(&*data->items.begin(), &*data->items.end());
}


/**
 * Expects a sequence of tuples (history, token, score)
 * history is a tuple of preceding tokens
 * score is *negative* *natural* logarithm of probability
 * token may be None to set the back-off weight
 */

void SequenceModel::set(PyObject *obj) {
  if (!PySequence_Check(obj))
    throw PythonException(PyExc_TypeError, "not a sequence");

#if defined(__GXX_EXPERIMENTAL_CXX0X__) || (__cplusplus >= 201103L) || (__APPLE__)
  std::shared_ptr<InitData> data(new InitData);
#else
  std::auto_ptr<InitData> data(new InitData);
#endif

  std::vector<Token> history;
  int len = PySequence_Length(obj);
  for (int i = 0; i < len; ++i) {
    PyObject *item = PySequence_GetItem(obj, i);
    PyObject *tuple = NULL, *predicted = NULL;
    double score;
    if (!PyArg_ParseTuple(item, "OOd", &tuple, &predicted, &score))
      throw ExistingPythonException();
    if (!PyTuple_Check(tuple))
      throw PythonException(PyExc_TypeError, "not a tuple");
    int tupleSize = PyTuple_GET_SIZE(tuple);
    for (int j = 0; j < tupleSize; ++j) {
      PyObject *tok = PyTuple_GET_ITEM(tuple, j);
      if (!PyInt_Check(tok))
        throw PythonException(PyExc_TypeError, "not an integer");
      history.push_back(PyInt_AsLong(tok));
    }
    std::reverse(history.begin(), history.end());
    if (predicted == Py_None) {
      data->setHistory(&*history.begin(), &*history.end());
      data->addBackOffWeight(LogProbability(score));
    } else {
      if (!PyInt_Check(predicted))
        throw PythonException(PyExc_TypeError, "not an integer");
      data->setHistory(&*history.begin(), &*history.end());
      data->addProbability(PyInt_AsLong(predicted), LogProbability(score));
    }
    history.clear();
    Py_DECREF(item);
  }

  initialize(&*data->items.begin(), &*data->items.end());
}

void SequenceModel::setInitAndTerm(u32 init, u32 term) {
  sentenceBegin_ = init;
  sentenceEnd_   = term;
}


PyObject *SequenceModel::get() const {
  PyObject *result = PyList_New(internal_->nodes.size() + internal_->wordProbabilities.size() - 2);
  int i = 0;
  for (Internal::Nodes::iterator n = internal_->nodes.begin(); n+1 != internal_->nodes.end(); ++n) {
    PyObject *history = historyAsTuple(&*n);
    for (const WordProbability *ws = n->probabilitiesBegin(); ws != n->probabilitiesEnd(); ++ws) {
      PyObject *hps = Py_BuildValue("(Oif)", history, ws->token_, ws->probability_.score());
      verify_(i < PyList_GET_SIZE(result));
      PyList_SET_ITEM(result, i++, hps);
    }
    PyObject *hps = Py_BuildValue("(OOf)", history, Py_None, n->backOffWeight_.score());
    verify_(i < PyList_GET_SIZE(result));
    PyList_SET_ITEM(result, i++, hps);
    Py_DECREF(history);
  }
  verify(i == PyList_GET_SIZE(result));
  return result;
}

PyObject *SequenceModel::getNode(const Node *nn) const {
  require(nn);
  PyObject *result = PyList_New(nn->probabilitiesEnd() - nn->probabilitiesBegin() + 1);
  int i = 0;
  PyList_SET_ITEM(result, i++, Py_BuildValue(
        "(Of)", Py_None, nn->backOffWeight_.score()));
  for (const WordProbability *wp = nn->probabilitiesBegin(); wp != nn->probabilitiesEnd(); ++wp)
    PyList_SET_ITEM(result, i++, Py_BuildValue(
          "(if)", wp->token_, wp->probability_.score()));
  verify(i == PyList_GET_SIZE(result));
  return result;
}

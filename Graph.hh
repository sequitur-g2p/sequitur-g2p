/*
 * $Id: Graph.hh 1667 2007-06-02 14:32:35Z max $
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

#ifndef _GRAPH_HH
#define _GRAPH_HH

#include "Assertions.hh"
#include "Types.hh"

/**
 * Simple abstract graph.
 * Nodes and Edges are feature-less and can be identified by their IDs.
 * There is always dummy node with ID zero, and a dummy Edge with ID zero.
 *
 * Guarantees:
 * Node and Edge IDs never change during their lifetime.
 * At any time nNodes() is strictly larger than any valid NodeId.
 * At any time nEdges() is strictly larger than any valid EdgeId.
 *
 * Memory complexity: O(V + E)
 *  V * 8 bytes  +  E * 16 bytes
 *
 * Time complexity:
 *  addNode       O(1)
 *  addEdge       O(1)
 */

class Graph {
public:
    typedef u32 NodeId;
    typedef u32 EdgeId;

private:
    struct Node {
        EdgeId outgoing, incoming;
        Node() : outgoing(0), incoming(0) {}
    };

    struct Edge {
        NodeId source, target;
        EdgeId linkOutgoing, linkIncoming;
    };

    std::vector<Node> nodes_;
    std::vector<Edge> edges_;

    void linkEdgeToTarget(EdgeId e, NodeId n) {
        require_(!edges_[e].target);
        edges_[e].target = n;
        edges_[e].linkIncoming = nodes_[n].incoming;
        nodes_[n].incoming = e;
    }

    void linkEdgeToSource(EdgeId e, NodeId n) {
        require(!edges_[e].source);
        edges_[e].source = n ;
        edges_[e].linkOutgoing = nodes_[n].outgoing;
        nodes_[n].outgoing = e;
    }

public:
    Graph();
    ~Graph();

    void clear();
    void yield();

    size_t memoryUsed() const {
        return sizeof(Graph)
            + nodes_.capacity() * sizeof(Node)
            + edges_.capacity() * sizeof(Edge);
    }

    NodeId newNode() {
        NodeId n = nodes_.size();
        nodes_.push_back(Node());
        return n;
    }
    NodeId nodesBegin() const { return 1; }
    NodeId nodesEnd()   const { return nodes_.size(); }

    EdgeId newEdge(NodeId from, NodeId to) {
        EdgeId e = edges_.size();
        edges_.push_back(Edge());
        linkEdgeToSource(e, from);
        linkEdgeToTarget(e, to);
        return e;
    }

    u32 nNodes() const {
        return nodes_.size();
    }

    u32 nEdges() const {
        return edges_.size();
    }
    EdgeId edgesBegin() const { return 1; }
    EdgeId edgesEnd()   const { return edges_.size(); }

    class EdgeIterator {
    protected:
        const Graph *graph_;
        EdgeId edge_;
        EdgeIterator(const Graph *g, EdgeId e) :
            graph_(g), edge_(e) {}
    public:
        operator bool() const {
            return (edge_ != 0);
        }

        EdgeId operator*() const {
            return edge_;
        }
    };

    struct OutgoingEdgeIterator : public EdgeIterator {
    private:
        friend class Graph;
        OutgoingEdgeIterator(const Graph *g, EdgeId e) : EdgeIterator(g, e) {}
    public:
        OutgoingEdgeIterator& operator++() {
            edge_ = graph_->edges_[edge_].linkOutgoing;
            return *this ;
        }
    };

    OutgoingEdgeIterator outgoingEdges(NodeId n) const {
        return OutgoingEdgeIterator(this, nodes_[n].outgoing);
    }

    struct IncomingEdgeIterator : public EdgeIterator {
    private:
        friend class Graph;
        IncomingEdgeIterator(const Graph *g, EdgeId e) : EdgeIterator(g, e) {}
    public:
        IncomingEdgeIterator& operator++() {
            edge_ = graph_->edges_[edge_].linkIncoming;
            return *this ;
        }
    };

    IncomingEdgeIterator incomingEdges(NodeId n) const {
        return IncomingEdgeIterator(this, nodes_[n].incoming);
    }

    NodeId source(EdgeId e) const {
        return edges_[e].source;
    }

    NodeId target(EdgeId e) const {
        return edges_[e].target;
    }
};

template <typename T>
class NodeMap {
    typedef T Value;
private:
    const Graph *graph_;
    typedef std::vector<Value> Values;
    Values values_;
public:
    NodeMap() : graph_(0) {}
    NodeMap(const Graph *g) : graph_(g), values_(graph_->nNodes()) {}
    void sync() {
        values_.resize(graph_->nNodes());
    }
    void sync(const Graph *g) {
        graph_ = g;
        values_.resize(graph_->nNodes());
    }
    void yield() {
        std::vector<Value> tmp(values_);
        values_.swap(tmp);
    }

    const Value &operator[](Graph::NodeId n) const {
        require_(n < values_.size());
        return values_[n];
    }
    Value &operator[](Graph::NodeId n) {
        require_(n < values_.size());
        return values_[n];
    }

    void set(Graph::NodeId n, const Value &value) {
        require_(n < graph_->nNodes());
        if (n == values_.size())
            values_.push_back(value);
        else {
            if (values_.size() < graph_->nNodes())
                values_.resize  (graph_->nNodes());
            values_[n] = value;
        }
    }

    void fill(const Value &v) {
        std::fill(values_.begin(), values_.end(), v);
    }

    size_t memoryUsed() const {
        return sizeof(NodeMap)
            + values_.capacity() * sizeof(typename Values::value_type);
    }
};

template <typename T>
class EdgeMap {
    typedef T Value;
private:
    const Graph *graph_;
    typedef std::vector<Value> Values;
    Values values_;
public:
    EdgeMap(const Graph *g) : graph_(g), values_(graph_->nEdges()) {}

    void sync() {
        values_.resize(graph_->nEdges());
    }
    void yield() {
        std::vector<Value> tmp(values_);
        values_.swap(tmp);
    }

    const Value &operator[](Graph::EdgeId n) const {
        require_(n < values_.size());
        return values_[n];
    }
    Value &operator[](Graph::EdgeId n) {
        require_(n < values_.size());
        return values_[n];
    }

    void set(Graph::EdgeId n, const Value &value) {
        require_(n < graph_->nEdges());
        if (n == values_.size())
            values_.push_back(value);
        else {
            if (values_.size() < graph_->nEdges())
                values_.resize  (graph_->nEdges());
            values_[n] = value;
        }
    }
    void fill(const Value &v) {
        std::fill(values_.begin(), values_.end(), v);
    }

    size_t memoryUsed() const {
        return sizeof(EdgeMap)
            + values_.capacity() * sizeof(typename Values::value_type);
    }
};

#endif // _GRAPH_HH

/*
 * $Id: MultigramGraph.hh 1667 2007-06-02 14:32:35Z max $
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

#ifndef _MULTIGRAM_GRAPH_HH
#define _MULTIGRAM_GRAPH_HH

#include "Graph.hh"
#include "Probability.hh"

class MultigramGraph {
protected:
    Graph graph_;
    Graph::NodeId initial_, final_;
    EdgeMap<SequenceModel::Token> token_;
    EdgeMap<LogProbability> probability_;

public:
    typedef std::vector<Graph::NodeId> NodeList;

    MultigramGraph() :
        initial_(0), final_(0),
        token_(&graph_),
        probability_(&graph_)
        {}

    size_t memoryUsed() const {
        return sizeof(this)
            + graph_.memoryUsed() - sizeof(Graph)
            + token_.memoryUsed() - sizeof(EdgeMap<SequenceModel::Token>)
            + probability_.memoryUsed() - sizeof(EdgeMap<LogProbability>);
    }
};


class GraphSorter {
private:
    enum DfsState { white, grey, black };
    NodeMap<DfsState> dfsState_;
    typedef std::pair<Graph::NodeId, Graph::OutgoingEdgeIterator> DfsStackItem;
    typedef std::vector<DfsStackItem> DfsStack;
    DfsStack dfsStack_;

public:
    /**
     * Sort nodes topologically.  Since this works from the initial
     * node forward, the result will contain only accessible nodes.
     *
     * CAVEAT: If we detect a cycle, we just pretend we didn't notice!
     */
    void sort(
        Graph &g,
        Graph::NodeId initial,
        MultigramGraph::NodeList &nodesInTopologicalOrder)
    {
        dfsState_.sync(&g);
        dfsState_.fill(white);
        dfsState_[initial] = grey;
        dfsStack_.push_back(DfsStackItem(initial, g.outgoingEdges(initial)));
        while (!dfsStack_.empty()) {
            DfsStackItem &current(dfsStack_.back());
            if (current.second) {
                Graph::NodeId next = g.target(*current.second);
                ++current.second;
             // verify(dfsState_[next] != grey); // cycle detected!
                if (dfsState_[next] == white) {
                    dfsState_[next] = grey;
                    dfsStack_.push_back(DfsStackItem(next, g.outgoingEdges(next)));
                }
            } else {
                dfsState_[current.first] = black;
                nodesInTopologicalOrder.push_back(current.first);
                dfsStack_.pop_back();
            }
        }
        verify(dfsState_[initial] == black);
        std::reverse(nodesInTopologicalOrder.begin(), nodesInTopologicalOrder.end());
    }

    size_t memoryUsed() const {
        return sizeof(GraphSorter)
            + dfsState_.memoryUsed() - sizeof(dfsState_)
            + dfsStack_.capacity() * sizeof(DfsStack::value_type);
    }
};

#endif // _MULTIGRAM_GRAPH_HH

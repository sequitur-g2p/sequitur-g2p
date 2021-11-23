/*
 * $Id: Graph.cc 1667 2007-06-02 14:32:35Z max $
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

#include "Graph.hh"

Graph::Graph() {
    clear();
}

Graph::~Graph() { }

void Graph::clear() {
    nodes_.clear();
    Node sentinelNode;
    sentinelNode.incoming = 0;
    sentinelNode.outgoing = 0;
    nodes_.push_back(sentinelNode);

    edges_.clear();
    Edge sentinelEdge;
    sentinelEdge.source = Core::Type<NodeId>::max;
    sentinelEdge.target = Core::Type<NodeId>::max;
    sentinelEdge.linkOutgoing = sentinelEdge.linkIncoming = 0;
    edges_.push_back(sentinelEdge);
}

void Graph::yield() {
    std::vector<Node> nTmp(nodes_);
    nodes_.swap(nTmp);
    std::vector<Edge> eTmp(edges_);
    edges_.swap(eTmp);
}

/*
 * $Id: SequenceModel.hh 1691 2011-08-03 13:38:08Z hahn $
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

#ifndef _SEQUENCEMODEL_HH
#define _SEQUENCEMODEL_HH

#include "Python.hh"

#include "Obstack.hh"
#include "Probability.hh"
#include "Types.hh"
#include <string>
#include <vector>

#if defined(INSTRUMENTATION)
#include <ext/hash_map>

struct StringHash {
    size_t operator() (const char *s) const {
        size_t result = 0;
        while (*s) result = 5 * result + size_t(*s++);
        return result;
    }
    size_t operator() (const std::string &s) const {
        return (*this)(s.c_str());
    }
};

struct StringEquality :
    std::binary_function<const char*, const char*, bool>
{
    bool operator() (const char *s, const char *t) const {
        return (s == t) || (strcmp(s, t) == 0);
    }
    bool operator() (const std::string &s, const std::string &t) const {
        return (s == t);
    }
};

class StringInventory {
    typedef std::vector<const char*> List;
    typedef std::hash_map<const char*, u32, StringHash, StringEquality> Map;
    List list_;
    Map map_;
public:
    static const u32 invalidIndex = 0;

    StringInventory();
    StringInventory(PyObject*);
    ~StringInventory();

    std::string symbol(u32 i) const {
        require(i < list_.size());
        const char *result = list_[i];
        return (result) ? result : "(void)";
    }

    u32 findOrAdd(const char *str) {
        Map::const_iterator wmi = map_.find(str);
        if (wmi == map_.end()) {
            u32 i = list_.size();
            const char *myStr = strdup(str);
            wmi = map_.insert(std::make_pair(myStr, i)).first;
            list_.push_back(myStr);
        }
        return wmi->second;
    }

    u32 index(const char *str) {
        Map::const_iterator wmi = map_.find(str);
        if (wmi == map_.end()) {
            return invalidIndex;
        } else
            return wmi->second;
    }
};
#endif // INSTRUMENTATION

class SequenceModel {
public:
    typedef unsigned int Token;
    struct InitItem; class InitData;
    struct WordProbability;

private:
    class Internal; Internal *internal_;
    class Node; const Node *root_;
    void initialize(InitItem *begin, InitItem *end);

    Token sentenceBegin_, sentenceEnd_;

public:
    typedef const Node *History;

    SequenceModel();
    ~SequenceModel();
#ifdef OBSOLETE
    void load(const std::string &filename, StringInventory*);
    void dump(const std::string &filename, const StringInventory*) const;
#endif // OBSOLETE
    void setInitAndTerm(u32 init, u32 term);
    void set(InitData*);
    void set(PyObject*);
    PyObject *get() const;
    PyObject *getNode(History) const;

    History initial() const;
    History culDeSac() const { return 0; }
    History advanced(History, Token) const;
    /** "forget" oldest word, i.e. back-off to lower order
     * @return zero if h was the empty history */
    History shortened(History h) const;
    u32 historyLength(History) const;
#ifdef OBSOLETE
    std::string formatHistory(History, const StringInventory *si = 0) const;
#endif // OBSOLETE
    void historyAsVector(History, std::vector<Token>&) const;
    PyObject *historyAsTuple(History) const;
    LogProbability probability(Token, const std::vector<Token> &history) const;
    LogProbability probability(Token, History) const;

    Token init() const { return sentenceBegin_; }
    Token term() const { return sentenceEnd_; }

    size_t memoryUsed() const;
};

struct SequenceModel::WordProbability {
    Token token_;
    LogProbability probability_;
public:
    Token token() const { return token_; }
    LogProbability probability() const { return probability_; }
};

struct SequenceModel::InitItem {
    Token *history; /**< zero-terminated string, recent-most first */
    Token token;    /**< predicted word, or zero iff back-off */
    LogProbability probability; /**< of p(token | history). */
    /* if (token == 0) probability is the back-off weight:
     * probability = p(token | history+) / p(token | history)
     */
};

class SequenceModel::InitData {
private:
    friend class SequenceModel;
    Core::Obstack<Token> histories;
    std::vector<InitItem> items;
    InitItem ii;

public:
    InitData();
    void setHistory(const Token *newest, const Token *oldest);
    void addProbability(Token predicted, LogProbability);
    void addBackOffWeight(LogProbability);
};

#endif // _SEQUENCEMODEL_HH

/*
 * $Id: Probability.hh 1667 2007-06-02 14:32:35Z max $
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

#ifndef _PROBABILITY_HH
#define _PROBABILITY_HH

#include "Assertions.hh"
#include <cmath>
#include <float.h>
#include <stdint.h>
#include <vector>


template<class T>
class StandardMaths {
public:
    typedef T BaseType;

    static BaseType logOnePlusExp(BaseType x) {
        return ::log1p(exp(x));
    }

    static BaseType logOneMinusExp(BaseType x) {
        return ::log1p(-exp(x));
    }

    static BaseType exp(BaseType x) {
        return ::exp(x);
    }

    static BaseType log(BaseType x) {
        return ::log(x);
    }

    static BaseType logOnePlus(BaseType x) {
        return ::log1p(x);
    }
};

class LogProbability;

class Probability {
public:
    typedef double BaseType;
protected:
    BaseType p;
public:
    Probability()                         { p = 0.0; }
    explicit Probability(BaseType _p)     { p = _p; }
    Probability(const Probability  &_p)   { p = _p.probability(); }
    Probability(const LogProbability &_s);

    BaseType probability() const {
        return p;
    }

    BaseType score() const {
        require_(std::isfinite(p));
        return (p > 0.0) ? (- ::log(p)) : (-1.0E8 * ::log(DBL_MIN));
    }

    static const Probability certain() {
        return Probability(1.0);
    }

    static const Probability impossible() {
        return Probability(0.0);
    }

    static const Probability epsilon() {
        return Probability(DBL_EPSILON);
    }

    static const Probability max() {
        return Probability(DBL_MAX);
    }

    static const Probability invalid() {
        return Probability(-1.0);
    }

    bool isValid() const {
        return std::isfinite(p) && p >= 0;
    }

    Probability operator+(const Probability &o) const {
        require_(isValid());
        require_(o.isValid());
        return Probability(probability() + o.probability());
    }

    Probability &operator+=(const Probability &o) {
        require_(isValid());
        require_(o.isValid());
        p += o.probability();
        return *this;
    }

    Probability operator-(const Probability &o) const {
        require_(isValid());
        require_(o.isValid());
        return Probability(probability() - o.probability());
    }

    Probability &operator-=(const Probability &o) {
        require_(isValid());
        require_(o.isValid());
        p -= o.probability();
        return *this;
    }

    Probability operator*(const Probability &o) const {
        require_(isValid());
        require_(o.isValid());
        return Probability(probability() * o.probability());
    }

    Probability &operator*=(const Probability &o) {
        require_(isValid());
        require_(o.isValid());
        p *= o.probability();
        return *this;
    }

    Probability operator/(const Probability &o) const {
        require_(isValid());
        require_(o.isValid());
        return Probability(probability() / o.probability());
    }

    Probability &operator/=(const Probability &o) {
        require_(isValid());
        require_(o.isValid());
        p /= o.probability();
        return *this;
    }

    Probability complement() const {
        require_(isValid());
        return Probability(1.0 - probability());
    }

    BaseType entropy() const {
        return probability() * score();
    }

    BaseType log() const {
        return StandardMaths<BaseType>::log(p);
    }

    Probability pow(double e) const {
        return Probability(::pow(probability(), e));
    }

};

class LogProbability {
public:
    typedef double BaseType;
protected:
    BaseType s;
public:
    LogProbability()                         { s = DBL_MAX; }
    explicit LogProbability(BaseType _s)     { s = _s; }
    LogProbability(const Probability &_p)    { s = _p.score(); }
    LogProbability(const LogProbability &_s) { s = _s.score(); }

    BaseType probability() const { return exp(-s); }
    BaseType score() const { return s; }

    static const LogProbability certain() {
        return LogProbability(0.0);
    }

    static const LogProbability impossible() {
        return LogProbability(-1.0E8*::log(DBL_MIN));  // ~ 70839600888
    }

    static const LogProbability epsilon() {
        return LogProbability(-::log(DBL_EPSILON));    // ~   36.04
    }

    static const LogProbability max() {
        return LogProbability(-::log(DBL_MAX));        // ~ -709.78
    }

    static const LogProbability invalid() {
        return LogProbability(-DBL_MAX);
    }

    bool isValid() const {
        return std::isfinite(s) && s > - DBL_MAX;
    }

    LogProbability &operator+=(const LogProbability &o);

    LogProbability operator*(const LogProbability &o) const {
        require_(isValid());
        require_(o.isValid());
        return LogProbability(score() + o.score());
    }

    LogProbability &operator*=(const LogProbability &o) {
        require_(isValid());
        require_(o.isValid());
        s += o.score();
        return *this;
    }

    LogProbability operator/(const LogProbability &o) const {
        require_(isValid());
        require_(o.isValid());
        return LogProbability(score() - o.score());
    }

    LogProbability &operator/=(const LogProbability &o) {
        require_(isValid());
        require_(o.isValid());
        s -= o.score();
        return *this;
    }

    LogProbability complement() const {
        require_(isValid());
        return LogProbability(- log1p( - probability()));
    }

    BaseType entropy() const {
        return probability() * score();
    }

    BaseType log() const {
        return -s;
    }

    LogProbability pow(double e) const {
        return LogProbability(score() * e);
    }
};

inline Probability::Probability(const LogProbability &_s) { p = _s.probability(); }


inline bool operator< (const Probability &lhs, const Probability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() < rhs.probability();
}

inline bool operator> (const Probability &lhs, const Probability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() > rhs.probability();
}

inline bool operator>= (const Probability &lhs, const Probability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() >= rhs.probability();
}

inline bool operator<= (const Probability &lhs, const Probability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() <= rhs.probability();
}

inline bool operator< (const LogProbability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.score() > rhs.score();
}

inline bool operator> (const LogProbability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.score() < rhs.score();
}

inline bool operator>= (const LogProbability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.score() <= rhs.score();
}

inline bool operator<= (const LogProbability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.score() >= rhs.score();
}

inline bool operator< (const Probability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() < rhs.probability();
}

inline bool operator> (const Probability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() > rhs.probability();
}

inline bool operator>= (const Probability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() >= rhs.probability();
}

inline bool operator<= (const Probability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() <= rhs.probability();
}

inline bool operator>= (const LogProbability &lhs, const Probability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() >= rhs.probability();
}

inline bool operator<= (const LogProbability &lhs, const Probability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() <= rhs.probability();
}

inline bool operator== (const Probability &lhs, const Probability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() == rhs.probability();
}
inline bool operator!= (const Probability &lhs, const Probability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.probability() != rhs.probability();
}

inline bool operator== (const LogProbability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.score() == rhs.score();
}
inline bool operator!= (const LogProbability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    return lhs.score() != rhs.score();
}

inline LogProbability &LogProbability::operator+=(const LogProbability &o) {
    require_(isValid());
    require_(o.isValid());
    if (score() > o.score()) {
        if (score() - o.score() < LogProbability::epsilon().score())
            s = o.score() - StandardMaths<BaseType>::logOnePlusExp(o.score() - score());
        else
            s = o.score();
    } else {
        if (o.score() - score() < LogProbability::epsilon().score())
            s = score() - StandardMaths<BaseType>::logOnePlusExp(score() - o.score());
    }
    return *this;
}

inline LogProbability operator+(const LogProbability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    if (lhs.score() > rhs.score()) {
        if (lhs.score() - rhs.score() < LogProbability::epsilon().score())
            return LogProbability(
                rhs.score() -
                StandardMaths<LogProbability::BaseType>::logOnePlusExp(
                    rhs.score() - lhs.score()));
        else
            return rhs;
    } else {
        if (rhs.score() - lhs.score() < LogProbability::epsilon().score())
            return LogProbability(
                lhs.score() -
                StandardMaths<LogProbability::BaseType>::logOnePlusExp(
                    lhs.score() - rhs.score()));
        else
            return lhs;
    }
}

inline LogProbability operator-(const LogProbability &lhs, const LogProbability &rhs) {
    require_(lhs.isValid());
    require_(rhs.isValid());
    require_(lhs.score() <= rhs.score());

    if (rhs.score() - lhs.score() > - log(1.0 - DBL_EPSILON))
        return LogProbability(
            lhs.score() -
            StandardMaths<LogProbability::BaseType>::logOneMinusExp(
                lhs.score() - rhs.score()));
    else
        return lhs;
}


class ProbabilityAccumulator {
public:
    typedef ProbabilityAccumulator Self;
    typedef LogProbability::BaseType BaseType;
private:
    BaseType  min;
    std::vector<BaseType> terms;
public:
    ProbabilityAccumulator() {
        min = LogProbability::impossible().score();
    }

    void add(LogProbability s) {
        require_(s.isValid());
        if (min > s.score()) {
            terms.push_back(min);
            min = s.score();
        } else {
            terms.push_back(s.score());
        }
    }

    Self &operator+=(LogProbability s) {
        add(s);
        return *this;
    }

    void clear() {
        terms.clear();
        min = LogProbability::impossible().score();
    }

    LogProbability sum() const {
        BaseType s = 0.0 ;
        for (std::vector<BaseType>::const_iterator t = terms.begin() ; t != terms.end() ; ++t)
            if (*t - min < LogProbability::epsilon().score())
                s += StandardMaths<BaseType>::exp(min - *t);
#if 1
        return LogProbability(min - StandardMaths<BaseType>::logOnePlus(s)) ;
#else
        min -= StandardMaths<BaseType>::logOnePlus(s);
        terms.clear();
        return LogProbability(min);
#endif
    }

    operator LogProbability() const {
        return sum();
    }
};

inline bool isNearlyEqual(float af, float bf, int tolerance) {
    union {
        int32_t i;
        float f;
    } a, b;
    a.f = af;
    b.f = bf;
    if (a.i < 0) a.i = 0x80000000 - a.i;
    if (b.i < 0) b.i = 0x80000000 - b.i;
    int32_t delta = (a.i < b.i) ? (b.i - a.i) : (a.i - b.i);
    return delta <= tolerance;
}

inline bool isNearlyEqual(double af, double bf, int tolerance) {
    union {
        int64_t i;
        double f;
    } a, b;
    a.f = af;
    b.f = bf;
    if (a.i < 0) a.i = (int64_t(1) << 63) - a.i;
    if (b.i < 0) b.i = (int64_t(1) << 63) - b.i;
    int64_t delta = (a.i < b.i) ? (b.i - a.i) : (a.i - b.i);
    return delta < tolerance;
}

#endif // _PROBABILITY_HH

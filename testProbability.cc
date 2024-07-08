/*
 * $Id:$
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

#include "Assertions.hh"
#include "Probability.hh"

int main(int argc, char *argv[]) {
    Probability  p, p1, p2;
    LogProbability s, s1, s2;

    // default constructor
    hope(p == Probability::impossible());
    hope(s == LogProbability::impossible());

    // certainty
    p = Probability::certain();
    hope(p == Probability::certain());
    hope(p.complement() == Probability::impossible());
    s = LogProbability::certain();
    hope(s == LogProbability::certain());
    hope(s.complement() == LogProbability::impossible());

    p = LogProbability::certain();
    s = Probability::certain();
    hope(p == Probability::certain());
    hope(s == LogProbability::certain());

    // impossibility
    p = Probability::impossible();
    s = p; p = s;
    hope(p == Probability::impossible());
    hope(s <= LogProbability::impossible());

    p1 = Probability::impossible();
    p2 = Probability(0.1);
    p = p1 * p2;
    hope(p == Probability::impossible());
    p = p1 / p2;
    hope(p == Probability::impossible());
    p = p2 + p1;
    hope(p == p2);
    p = p2 - p1;
    hope(p == p2);
    hope(p1.entropy() == 0.0);

    p1 = Probability::certain();
    p2 = Probability(0.1);
    p = p1 * p2;
    hope(p == p2);
    p = p2 / p1;
    hope(p == p2);
//  p = p2 + p1;
//  hope(p == p2);
    p = p1 - p2;
    hope(p == p2.complement());
    hope(p1.entropy() == 0.0);

    s1 = LogProbability::impossible();
    s2 = LogProbability(0.1);
    s = s1 * s2;
    hope(s <= LogProbability::impossible());
    s = s1 / s2;
    hope(s.probability() <= 0.0);
    s = s2 + s1;
    hope(s == s2);
    s = s2 - s1;
    hope(s == s2);
    hope(s1.entropy() == 0.0);

    s1 = LogProbability::certain();
    s2 = Probability(0.1);
    s = s1 * s2;
    hope(s == s2);
    s = s2 / s1;
    hope(s == s2);
    s = s2 + s1;
    hope(s >= s2);
    s = s1 - s2;
    hope(s == s2.complement());
    hope(s1.entropy() == 0.0);

    p1 = s1 = Probability(0.2);
    p2 = s2 = Probability(0.1);
    p = p1 + p2; s = s1 + s2;
    hope(p.probability() == s.probability());
    p = p1 - p2; s = s1 - s2;
    hope(equal_fpp(p.probability(), s.probability()));
    p = p1 * p2; s = s1 * s2;
    hope(equal_fpp(p.probability(), s.probability()));
    p = p1 / p2; s = s1 / s2;
    hope(equal_fpp(p.probability(), s.probability()));
}

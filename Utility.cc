/*
 * $Id: Utility.cc 1691 2011-08-03 13:38:08Z hahn $
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

#include "Utility.hh"
#include <algorithm>
#include <cstdlib>
#include <cstdio>
#include <iomanip>
#include <iostream>
#include <string>

using namespace Core;


int Core::getline(std::istream& is, std::string& str, std::string delim) {
    int token;
    std::string::size_type pos = std::string::npos;

    // check if end of stream is reached
    if (is.get() == EOF) return EOF;
    is.unget();

    // tokenize stream contents
    str = "";
    while (((token = is.get()) != EOF) &&
           ((pos = delim.find(token)) == std::string::npos)) {
        str += char(token);
    }

    if (pos == std::string::npos) return 0;

    return pos + 1;
}

std::string& Core::itoa(std::string &s, unsigned int val) {
    s = "";
    if (val < 10) { // small integers are very frequent
        s += ('0' + val);
    } else {
        do {
            s += ('0' + (val % 10));
            val /= 10;
        } while (val);
        std::reverse(s.begin(), s.end());
    }
    return s;
}

s32 Core::differenceUlp(f32 af, f32 bf) {
    union {
        s32 i;
        f32 f;
    } a, b;
    a.f = af;
    b.f = bf;
    if (a.i < 0) a.i = 0x80000000 - a.i;
    if (b.i < 0) b.i = 0x80000000 - b.i;
    return std::abs(a.i - b.i);
}

s64 Core::differenceUlp(f64 af, f64 bf) {
    union {
        s64 i;
        f64 f;
    } a, b;
    a.f = af;
    b.f = bf;
    if (a.i < 0) a.i = (s64(1) << 63) - a.i;
    if (b.i < 0) b.i = (s64(1) << 63) - b.i;
    return std::abs(a.i - b.i);
}

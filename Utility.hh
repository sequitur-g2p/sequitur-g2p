/*
 * $Id: Utility.hh 1691 2011-08-03 13:38:08Z hahn $
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

#ifndef _CORE_UTILITY_HH
#define _CORE_UTILITY_HH

#include <cmath>
#include <complex>
#include <iostream>
#include <sstream>
#include <string>
#include "Types.hh"
#include "Assertions.hh"

namespace Core {

    /**
     * reads from input stream until one of the specified delimiters
     * @param istream input stream to read from
     * @param string resulting string that has been read; will not include a trailing  delimiter
     * @param delim string of delimiters
     * @result returns EOF if nothing has been read, but the end of stream
     * has been reached, returns 0 at the end of the stream, but no delimiter
     * has been found, returns the position + 1 of the delimiter in delim
     * that the resulting string ends with
     **/
    int getline(std::istream&, std::string&, std::string delim = "\n");
    inline int wsgetline(std::istream &is, std::string &str, std::string delim = "\n") {
        is >> std::ws;
        return Core::getline(is, str, delim);
    }

    std::string& itoa(std::string &s, unsigned int val);
    inline std::string itoa(u32 i) {
        std::string s;
        return itoa(s, i);
    }

} // namespace Core

inline size_t __stl_hash_wstring(const wchar_t* __s) {
    unsigned long __h = 0;
    for ( ; *__s; ++__s)
        __h = 5*__h + *__s;

    return size_t(__h);
}

namespace Core {

    /** Generic unary functor for type conversion. */
    template <typename S, typename T>
    struct conversion
    {
        T operator() (S s) const {
            return T(s);
        }
    };

    /** A helper for conveniently assigning the two values from a pair
     * into separate variables. The idea for this comes from Jaakko
     * Jarvi's Binder/Lambda Library.  Code stolen from Boost, to
     * which it was contributed by Jeremy Siek */

    template <class A, class B>
    class tied {
    public:
        inline tied(A &a, B &b) : a_(a), b_(b) { }
        template <class U, class V>
        inline tied& operator=(const std::pair<U,V> &p) {
            a_ = p.first;
            b_ = p.second;
            return *this;
        }
    protected:
        A &a_;
        B &b_;
    };

    template <class A, class B>
    inline  tied<A,B> tie(A &a, B &b) { return tied<A,B>(a, b); }

    /** Core::round : wrapper for several round functions */
    inline float round(float v) { return ::roundf(v); }
    inline double round(double v) { return ::round(v); }
//  inline long double round(long double v) { return ::roundl(v); }

    /** Core::ceil : wrapper for several ceil functions */
    inline float ceil(float v) { return ::ceilf(v); }
    inline double ceil(double v) { return ::ceil(v); }
//  inline long double ceil(long double v) { return ::ceill(v); }

    /** Core::floor : wrapper for several floor functions */
    inline float floor(float v) { return ::floorf(v); }
    inline double floor(double v) { return ::floor(v); }
//  inline long double ceil(long double v) { return ::floorl(v); }

    /**
     * @return is true if [begin..end) interval does not contain any "inf", "nan" etc. value.
     */
    template<class InputIterator>
    bool isNormal(InputIterator begin, InputIterator end) {
        for(; begin != end; ++ begin)
            if (!std::isnormal(*begin)) return false;
        return true;
    }

    /**
     * @return is true if @param f is "inf" or "nan".
     */
    template<class F> bool isMalformed(F f) { return std::isinf(f) || std::isnan(f); }

    /**
     * Checks if @param x is infinite and clips it to the largest representable value.
     * @return is clipped value of @param x.
     */
    template<class T>
    T clip(T x)
    {
        require(!std::isnan(x));
        if (std::isinf(x))
            x = (x > 0) ? Type<T>::max : Type<T>::min;
        return x;
    }

    /**
     * @return is true if [begin..end) interval contains any malformed value (@see isMalformed(F f)).
     */
    template<class InputIterator>
    bool isMalformed(InputIterator begin, InputIterator end) {
        for(; begin != end; ++ begin)
            if (isMalformed(*begin)) return true;
        return false;
    }

    /** Functor for f(g(x), h(y)) */
    template <class F, class G, class H>
    class composedBinaryFunction
    {
    protected:
        F f_;
        G g_;
        H h_;
    public:
        composedBinaryFunction(const F &f, const G &g, const H &h) : f_(f), g_(g), h_(h) {}
        typename F::result_type
        operator()(const typename G::argument_type &x, const typename H::argument_type &y) const {
            return f_(g_(x), h_(y));
        }
    };

    template <class F, class G, class H>
    inline composedBinaryFunction<F, G, H> composeBinaryFunction(const F &f, const G &g, const H &h)
    {
        return composedBinaryFunction<F, G, H>(f, g, h);
    }

    /**
     * Test for near-equality of floating point numbers.
     * Due to finite precision, the bit-wise test (a == b) is almost
     * always false.  isAlmostEqual() compares the relative difference
     * of a and b to the machine precision (epsilon) times the given
     * tolerance factor.
     *
     * Deprecation warning: For new code you should prefer
     * isAlmostEqualUlp.
     *
     * Remark:
     *   -A similar idea can be found under the name "chordal metric":
     *    chord(a, b) = |a - b| / (sqrt(1+a^2) * sqrt(1 + b^2)).
     *   -sorry for repeating the same implementation for each
     *    floating point type, but specialization to complex numbers
     *    seems to be a hard nut with templates.
     */
    inline bool isAlmostEqual(f32 a, f32 b, f32 tolerance = (f32)1) {
        require_(tolerance > (f32)0);
        f32 d = std::abs(a - b);
        f32 e = (std::abs(a) + std::abs(b) + Type<f32>::delta) * Type<f32>::epsilon * tolerance;
        return (d < e);
    }
    inline bool isAlmostEqual(f64 a, f64 b, f64 tolerance = (f64)1) {
        require_(tolerance > (f64)0);
        f64 d = std::abs(a - b);
        f64 e = (std::abs(a) + std::abs(b) + Type<f64>::delta) * Type<f64>::epsilon * tolerance;
        return (d < e);
    }

    inline bool isAlmostEqual(const std::complex<f32> &a, const std::complex<f32> &b,
                              const std::complex<f32> tolerance = std::complex<f32>((f32)1, (f32)1)) {
        return (isAlmostEqual(a.real(), b.real(), tolerance.real())  &&
                isAlmostEqual(a.imag(), b.imag(), tolerance.imag()));
    }
    inline bool isAlmostEqual(const std::complex<f64> &a, const std::complex<f64> &b,
                              const std::complex<f64> tolerance = std::complex<f64>((f64)1, (f64)1)) {
        return (isAlmostEqual(a.real(), b.real(), tolerance.real())  &&
                isAlmostEqual(a.imag(), b.imag(), tolerance.imag()));
    }

    inline bool isSignificantlyGreater(f32 a, f32 b, f32 tolerance = (f32)1) {
        return a > b && !isAlmostEqual(a, b, tolerance);
    }
    inline bool isSignificantlyGreater(f64 a, f64 b, f64 tolerance = (f64)1) {
        return a > b && !isAlmostEqual(a, b, tolerance);
    }

    inline bool isSignificantlyLess(f32 a, f32 b, f32 tolerance = (f32)1) {
        return a < b && !isAlmostEqual(a, b, tolerance);
    }
    inline bool isSignificantlyLess(f64 a, f64 b, f64 tolerance = (f64)1) {
        return a < b && !isAlmostEqual(a, b, tolerance);
    }

    /**
     * Difference between two floating-point values in units of least
     * precision (ULP).
     *
     * @return The number of distinct floating-point values between @c
     * a and @c b.  I.e. If @c b is the smallest value greater than a,
     * the return value is 1.
     */
    s32 differenceUlp(f32 a, f32 b);
    s64 differenceUlp(f64 a, f64 b);

    /**
     * Test for near-equality of floating point numbers with tolerance
     * given in unit of least precision.  Due to finite precision, the
     * bit-wise test (a == b) should not be use for floating point
     * values.  This function was taken from "Comparing floating point
     * numbers" by Bruce Dawson
     * [http://www.cygnus-software.com/papers/comparingfloats/comparingfloats.htm].
     * You will probably not be able to make sense of this code
     * without reading the article.
     *
     * @param tolerance allowed difference between @c a and @c b
     * measured in units of least precision (Ulp).  This can be
     * thought of as the number of different normalized floating point
     * numbers between @c a and @c b.
     *
     * This method is preferable to the older isAlmostEqual(),
     * because it is faster and theoretically more sound.  So maybe
     * isAlmostEqual() should be removed some time.
     */
    inline bool isAlmostEqualUlp(f32 a, f32 b, s32 tolerance) {
        require_(tolerance > 0);
        require_(tolerance < 0x400000);
        return (differenceUlp(a, b) <= tolerance);
    }
    inline bool isAlmostEqualUlp(f64 a, f64 b, s64 tolerance) {
        require_(tolerance > 0);
        require_(tolerance < (s64(1) << 62));
        return (differenceUlp(a, b) <= tolerance);
    }
    inline bool isAlmostEqualUlp(f64 a, f64 b, s32 tolerance) {
        return isAlmostEqualUlp(a, b, s64(tolerance));
    }

    inline bool isSignificantlyLessUlp(f32 a, f32 b, s32 tolerance) {
        return a < b && !isAlmostEqualUlp(a, b, tolerance);
    }
    inline bool isSignificantlyLessUlp(f64 a, f64 b, s32 tolerance) {
        return a < b && !isAlmostEqualUlp(a, b, tolerance);
    }

} // namespace Core


#endif // _CORE_UTILITY_HH

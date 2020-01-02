/*
 * $Id: Types.hh 1667 2007-06-02 14:32:35Z max $
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

#ifndef _CORE_TYPES_HH
#define _CORE_TYPES_HH

#include <stdint.h>
#include <limits.h>
#include <string>
#include <vector>
#include <complex>

typedef int8_t      s8;
typedef uint8_t     u8;
typedef int16_t     s16;
typedef uint16_t    u16;
typedef int32_t     s32;
typedef uint32_t    u32;
typedef int64_t     s64;
typedef uint64_t    u64;

typedef float       f32;
typedef double      f64;

namespace Core {

  /** Static information about elementary types. */
  template<class T> struct Type {

    /** Name to be used to represent data type. */
    static const char *name;

    /** Largest representable value of data type. */
    static const T max;

    /**
     * Smallest representable value of data type.
     * Note that unlike std::numeric_limits<>::min this is the most negative
     * value also for floating point types.
     */
    static const T min;

    /**
     * The difference between the smallest value greater than one and one.
     */
    static const T epsilon;

    /**
     * Smallest representable value greater than zero.
     * For all integer types this is one.  For floating point
     * types this is the same as std::numeric_limits<>::min or
     * FLT_MIN / DBL_MIN.
     */
    static const T delta;

  };

  template<> struct Type<f32> {
    static const char *name;
    static const f32 max;
    static const f32 min;
    static const f32 epsilon;
    static const f32 delta;
  };

  template<> struct Type<f64> {
    static const char *name;
    static const f64 max;
    static const f64 min;
    static const f64 epsilon;
    static const f64 delta;
  };

#if defined(HAS_64BIT)
  template<> struct Type<s64> {
    static const char *name;
    static const s64 max;
    static const s64 min;
    static const s64 epsilon;
    static const s64 delta;
  };

  template<> struct Type<u64> {
    static const char *name;
    static const u64 max;
    static const u64 min;
    static const u64 epsilon;
    static const u64 delta;
  };
#endif

  template<> struct Type<s32> {
    static const char *name;
    static const s32 max;
    static const s32 min;
    static const s32 epsilon;
    static const s32 delta;
  };

  template<> struct Type<u32> {
    static const char *name;
    static const u32 max;
    static const u32 min;
    static const u32 epsilon;
    static const u32 delta;
  };

  template<> struct Type<s16> {
    static const char *name;
    static const s16 max;
    static const s16 min;
    static const s16 epsilon;
    static const s16 delta;
  };

  template<> struct Type<u16> {
    static const char *name;
    static const u16 max;
    static const u16 min;
    static const u16 epsilon;
    static const u16 delta;
  };

  template<> struct Type<s8> {
    static const char *name;
    static const s8 max;
    static const s8 min;
    static const s8 epsilon;
    static const s8 delta;
  };

  template<> struct Type<u8> {
    static const char *name;
    static const u8 max;
    static const u8 min;
    static const u8 epsilon;
    static const u8 delta;
  };

  /**
   *  Use this class for naming your basic classes.
   *  Creating new names: by specialization.
   *  @see example Matrix.hh
   */
  template <typename T>
  class NameHelper : public std::string {
    public:
      NameHelper() : std::string(Type<T>::name) {}
  };

  template <>
  class NameHelper<std::string> : public std::string {
    public:
      NameHelper() : std::string("string") {}
  };

  template <>
  class NameHelper<bool> : public std::string {
    public:
      NameHelper() : std::string("bool") {}
  };

  template <typename T>
  class NameHelper<std::complex<T> > : public std::string {
    public:
      NameHelper() : std::string(std::string("complex-") + NameHelper<T>()) {}
  };

  template <typename T>
  class NameHelper<std::vector<T> > : public std::string {
    public:
      NameHelper() : std::string(std::string("vector-") + NameHelper<T>()) {}
  };

} // namespace Core

#endif // _CORE_TYPES_HH

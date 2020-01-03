/*
 * $Id: Types.cc 1667 2007-06-02 14:32:35Z max $
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

#include "Types.hh"
#include <float.h>

namespace Core {
  const char *Type<u32>::name("u32");
  const u32 Type<u32>::max(4294967295U);
  const u32 Type<u32>::min(0U);
  const char *Type<s32>::name("s32");
  const s32 Type<s32>::max(2147483647);
  const s32 Type<s32>::min(-2147483647 - 1); // gcc warns about too large int when -2147483648
  const char *Type<u8>::name("u8");
  const u8  Type<u8 >::max(255U);
  const u8  Type<u8 >::min(0U);
  const char *Type<s8>::name("s8");
  const s8  Type<s8 >::max(127);
  const s8  Type<s8 >::min(-128);
  const char *Type<u16>::name("u16");
  const u16 Type<u16>::max(65535U);
  const u16 Type<u16>::min(0U);
  const char *Type<s16>::name("s16");
  const s16 Type<s16>::max(32767);
  const s16 Type<s16>::min(-32768);
#if 0
    template<> const char *Type<u8>::name("u8");
    template<> const u8  Type<u8 >::max(255U);
    template<> const u8  Type<u8 >::min(0U);
    template<> const char *Type<s8>::name("s8");
    template<> const s8  Type<s8 >::max(127);
    template<> const s8  Type<s8 >::min(-128);
    template<> const char *Type<u16>::name("u16");
    template<> const u16 Type<u16>::max(65535U);
    template<> const u16 Type<u16>::min(0U);
    template<> const char *Type<s16>::name("s16");
    template<> const s16 Type<s16>::max(32767);
    template<> const s16 Type<s16>::min(-32768);
    const char *Type<u32>::name("u32");
    const u32 Type<u32>::max(4294967295U);
    const u32 Type<u32>::min(0U);
    const char *Type<s32>::name("s32");
    const s32 Type<s32>::max(2147483647);
    const s32 Type<s32>::min(-2147483647 - 1); // gcc warns about too large int when -2147483648
#endif
#if defined(HAS_64BIT)
    const char *Type<u64>::name("u64");
    const u64 Type<u64>::max(18446744073709551615U);
    const u64 Type<u64>::min(0U);
    const char *Type<s64>::name("s64");
    const s64 Type<s64>::max(9223372036854775807LL);
    const s64 Type<s64>::min(-9223372036854775808LL);
#endif
    const char *Type<f32>::name("f32");
    const f32 Type<f32>::max(FLT_MAX);
    const f32 Type<f32>::min(-FLT_MAX);
    const f32 Type<f32>::epsilon(FLT_EPSILON);
    const f32 Type<f32>::delta(1.17549435e-38F);
    const char *Type<f64>::name("f64");
    const f64 Type<f64>::max(DBL_MAX);
    const f64 Type<f64>::min(-DBL_MAX);
    const f64 Type<f64>::epsilon(DBL_EPSILON);
    const f64 Type<f64>::delta(2.2250738585072014e-308);

    template <size_t size>
    void swapEndianess(void *buf, size_t count = 1) {
      char *b = (char*) buf ;
      for (size_t j = 0 ; j < size / 2 ; ++j)
        for (size_t i = 0 ; i < count ; ++i)
          std::swap(b[i * size + j], b[i * size + size - j - 1]) ;
    }

    template void swapEndianess<2>(void *buf, size_t count);
    template void swapEndianess<4>(void *buf, size_t count);
    template void swapEndianess<8>(void *buf, size_t count);

} // namespace Core

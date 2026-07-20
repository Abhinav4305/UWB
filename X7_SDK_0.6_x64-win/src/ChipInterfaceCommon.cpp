/**
 * @file ChipInterfaceCommon.cpp
 *
 * This file contains common utility functions for the chip interface.
 */

#include "ChipInterface.h"

#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>

namespace Novelda
{

uint32_t reverse_bits_per_byte(uint32_t n)
{
#if defined(__GNUC__) && defined(__ARM_ARCH) && (__ARM_ARCH > 6)
    uint32_t result;
#if __ARM_32BIT_STATE
    asm(
        "rbit %[result], %[input] \n"
        "rev  %[result], %[result]\n"
        : [result] "=r"(result) : [input] "r"(n));
#else
    asm(
        "rbit %w[result], %w[input] \n"
        "rev  %w[result], %w[result]\n"
        : [result] "=r"(result) : [input] "r"(n));
#endif // __ARM_32BIT_STATE
    return result;
#else
    n = ((n >> 1) & 0x55555555) | ((n << 1) & 0xaaaaaaaa);
    n = ((n >> 2) & 0x33333333) | ((n << 2) & 0xcccccccc);
    n = ((n >> 4) & 0x0f0f0f0f) | ((n << 4) & 0xf0f0f0f0);
    return n;
#endif // defined(__GNUC__) && defined(__ARM_ARCH) && (__ARM_ARCH > 6)
}

template<typename T>
void reverse_bits_per_byte(T *buf, size_t numElements)
{
    assert((numElements * sizeof(T)) % sizeof(uint32_t) == 0 && "Buffer length must be a multiple of 4 bytes");
    assert(reinterpret_cast<uintptr_t>(buf) % sizeof(uint32_t) == 0 && "Buffer must be 4-byte aligned");
    auto *begin = reinterpret_cast<uint32_t *>(buf);
    auto *end = begin + (numElements * sizeof(T)) / sizeof(uint32_t);
    std::transform(begin, end, begin, [](uint32_t word) {
        return reverse_bits_per_byte(word);
    });
}

template CHIPINTERFACE_SYMBOL_EXPORT void reverse_bits_per_byte<uint32_t>(uint32_t *, size_t);
template CHIPINTERFACE_SYMBOL_EXPORT void reverse_bits_per_byte<uint8_t>(uint8_t *, size_t);

} // namespace Novelda

#ifdef SIGNALFLOW_CHIPINTERFACE_USE_CAPI
extern "C" {

uint32_t reverse_bits_per_byte(uint32_t n)
{
    return Novelda::reverse_bits_per_byte(n);
}

void reverse_bits_per_byte_buffer_u32(uint32_t *buf, size_t numElements)
{
    Novelda::reverse_bits_per_byte(buf, numElements);
}

void reverse_bits_per_byte_buffer_u8(uint8_t *buf, size_t numElements)
{
    Novelda::reverse_bits_per_byte(buf, numElements);
}
} // extern "C"
#endif // SIGNALFLOW_CHIPINTERFACE_USE_CAPI
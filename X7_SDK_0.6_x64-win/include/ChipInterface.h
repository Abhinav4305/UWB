#pragma once

#include <chrono>
#include <cstdint>
#include <cstring>
#include <functional>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#if !defined(SIGNALFLOW_NO_EXCEPTIONS) || !SIGNALFLOW_NO_EXCEPTIONS
#include <stdexcept>
#endif // !defined(SIGNALFLOW_NO_EXCEPTIONS) || !SIGNALFLOW_NO_EXCEPTIONS

#if defined(__unix__) || defined(__unix)
#define LINUX
#endif

#ifdef BUILDING_CHIPINTERFACE
// When building a dynamic library
#ifdef _MSC_VER
#define CHIPINTERFACE_SYMBOL_EXPORT __declspec(dllexport)
#else // _MSC_VER
#define CHIPINTERFACE_SYMBOL_EXPORT __attribute__((visibility("default")))
#endif // _MSC_VER
#else
// When using a dynamic library
#ifdef _MSC_VER
#define CHIPINTERFACE_SYMBOL_EXPORT __declspec(dllimport)
#else // _MSC_VER
#define CHIPINTERFACE_SYMBOL_EXPORT
#endif // _MSC_VER
#endif

/**
 * @file
 *
 * C++ ChipInterface API for interfacing with Novelda radar sensors.
 */

namespace Novelda
{

/**
 * Abstract classes representing a communication interface to X4/X7 chips.
 */
class ChipInterface
{
public:
    /** Type of connection to the radar chip. */
    enum class ConnectionType : uint8_t
    {
        I2c, /**< I2C connection */
        I3c, /**< I3C connection */
        Spi /**< SPI connection */
    };

    /** Type of interface to the radar chip. */
    enum class InterfaceType : uint8_t
    {
        LinuxNative, /**< Linux native interface using libgpiod */
        Ft4222, /**< FTDI FT4222 interface */
        BareMetal /**< Bare metal interface using the C chip interface API */
    };

    /** State of the interrupt line. */
    enum class InterruptState : uint8_t
    {
        Asserted, /**< Interrupt line is asserted */
        Deasserted /**< Interrupt line is deasserted */
    };

    /**
     * Identifier (ID) for one ChipInterface.
     */
    class Identifier
    {
        // @cond
    public:
        Identifier() = default;
        explicit Identifier(std::string id)
            : id_(std::move(id)) { }
        [[nodiscard]] const std::string &value() const { return id_; }
        [[nodiscard]] std::string value_or(const std::string &default_value) const { return id_.empty() ? default_value : id_; }
        [[nodiscard]] bool empty() const { return id_.empty(); }
        void operator=(std::string id) { id_ = std::move(id); }
        void operator=(const char *id) { id_ = id; }
        operator const std::string &() const { return id_; }
        operator bool() const { return !id_.empty() && id_ != "0"; }

    private:
        std::string id_;
        // @endcond
    };

    /**
     * Constructor for the ChipInterface.
     */
    ChipInterface(ConnectionType connectionType, uint32_t frequencyHz)
        : clockFrequency_(frequencyHz), connectionType_(connectionType) { }

    ChipInterface(ChipInterface const &) = delete;
    ChipInterface &operator=(ChipInterface const &) = delete;

    virtual ~ChipInterface() = default;

    /**
     * Enable or disable the chip.
     *
     * @param enabled True to enable the chip, false to disable it.
     */
    virtual void SetChipEnabled(bool enabled) = 0;

    /**
     * Get the current time in microseconds.
     *
     * @param time_us Pointer to where the current time is written to.
     * @note Throws an exception on nullptr input.
     */
    virtual void GetTimeMicroseconds(std::chrono::microseconds *time_us) = 0;

    /**
     * Get the current state of the interrupt line.
     */
    virtual InterruptState GetInterruptState() = 0;

    /**
     * Wait for an interrupt.
     *
     * @param microseconds Maximum wait time in microseconds.
     *   0 means: infinite wait.
     *
     * @return True if an interrupt occurred, false if a timeout occurred.
     */
    virtual bool WaitForInterrupt(std::chrono::microseconds microseconds) = 0;

    /**
     * Wait for a specific number of microseconds.
     *
     * @param microseconds The number of microseconds to wait.
     */
    virtual void WaitMicroseconds(std::chrono::microseconds microseconds) = 0;

    /**
     * Set the clock frequency for the interface.
     *
     * @param newClock The new clock frequency in Hz.
     */
    void SetClockFrequency(uint32_t newClock)
    {
        clockFrequency_ = AdjustClockFrequency(newClock);
    }

    /**
     * Get the clock frequency for the interface.
     *
     * @return The clock frequency in Hz.
     */
    [[nodiscard]] uint32_t GetClockFrequency() const { return clockFrequency_; }

    /**
     * Transfer data to and from the chip.
     *
     * @param wdata Pointer to the buffer containing data to write.
     * @param wlength Number of bytes to write.
     * @param rdata Pointer to the buffer where incoming data should be stored.
     * @param rlength Number of bytes to read.
     */
    virtual void Transfer(const uint8_t *wdata, size_t wlength, uint8_t *rdata, size_t rlength) = 0;

    /**
     * Read data from the chip.
     *
     * @param rdata Pointer to the buffer where incoming data should be stored.
     * @param rlength Number of bytes to read.
     *
     * @note This is a convenience function that calls Transfer() with nullptr for wdata.
     */
    void Read(uint8_t *rdata, size_t rlength)
    {
        Transfer(nullptr, 0, rdata, rlength);
    }

    /**
     * Write data to the chip.
     *
     * @param wdata Pointer to the buffer containing data to write.
     * @param wlength Number of bytes to write.
     *
     * @note This is a convenience function that calls Transfer() with nullptr for rdata.
     */
    void Write(const uint8_t *wdata, size_t wlength)
    {
        Transfer(wdata, wlength, nullptr, 0);
    }

    /**
     * Get the type of connection to the radar chip.
     *
     * @return The connection type.
     */
    [[nodiscard]] ConnectionType GetConnectionType() const { return connectionType_; }

    /**
     * Get the interrupt callback function.
     *
     * @return The interrupt callback function.
     */
    [[nodiscard]] const std::function<void()> &GetInterruptCallback() const { return interruptCallback_; }

    /**
     * Set an interrupt callback function to be called when an interrupt occurs.
     *
     * @param callback The interrupt callback function.
     */
    void SetInterruptCallback(const std::function<void()> &callback) { interruptCallback_ = callback; }

protected:
    /**
     * Can be used to adjust the clock frequency to a value supported by the specific interface,
     * it also works as a way the interface can trigger other actions when the clock frequency is changed.
     *
     * Calling SetClockFrequency will call this function with the requested frequency, and the returned
     * value will be the actual frequency used.
     */
    virtual uint32_t AdjustClockFrequency(uint32_t requestedFrequency) { return requestedFrequency; }

private:
    uint32_t clockFrequency_;
    ConnectionType connectionType_;
    std::function<void()> interruptCallback_;
};

/**
 * Number of data lines for SPI.
 */
enum class SpiLineNumber
{
    Spi = 1,
    DSpi = 2,
    QSpi = 4,
};

/**
 * SPI Clock Polarity (CPOL).
 */
enum class ClockPolarity
{
    Low, /**< Clock which idles at the logical low voltage (CPOL=0) */
    High /**< Clock which idles at the logical high voltage (CPOL=1) */
};

/**
 * SPI Clock Phase (CPHA).
 *
 * Represents the phase of each data bit's transmission cycle relative to SCLK.
 */
enum class ClockPhase
{
    Leading, /**< The first data bit is output immediately when CS activates. (CPHA = 0) */
    Trailing /**< The first data bit is output on SCLK's first clock edge after CS activates. (CPHA = 1) */
};

/**
 * Bit order for SPI communication.
 */
enum class BitOrder
{
    MSB,
    LSB
};

/**
 * Represents the SPI settings for a device.
 */
struct SpiSettings
{
    ClockPolarity clockPolarity; /**< CPOL */
    ClockPhase clockPhase; /**< CPHA */
    BitOrder bitOrder; /**< Bit order */
    SpiLineNumber spiLineNumber; /**< Number of data lines */
};

/**
 * Represents a GPIO line on a device.
 *
 * A GPIO line is identified by a device and an offset.
 * Note the special value @ref GPIO_OFF for the offset which can be used to
 * indicate that the line is not used.
 */
class GpioLine
{
public:
    /** Special value for the offset to indicate that the line is not used. */
    constexpr static unsigned int GPIO_OFF { 255 };

    /**
     * GpioLine string constructor
     *
     * @param lineStr Accepts input on format "<device>:<offset>"
     */
    GpioLine(std::string lineStr)
    {
        const size_t colonPos = lineStr.find(':');
        if( colonPos != std::string::npos ) {
            device_ = lineStr.substr(0, colonPos);
            offset_ = std::stoi(lineStr.substr(colonPos + 1));
        } else {
#if !defined(SIGNALFLOW_NO_EXCEPTIONS) || !SIGNALFLOW_NO_EXCEPTIONS
            throw std::invalid_argument("Invalid GpioLine format '" + lineStr + "' Expected <device>:<offset>");
#else
            std::terminate();
#endif // !defined(SIGNALFLOW_NO_EXCEPTIONS) || !SIGNALFLOW_NO_EXCEPTIONS
        }
    }

    /**
     * GpioLine constructor
     *
     * @param device The gpio device for the specific line (e.g. "gpiochip0")
     * @param offset The line offset on the device
     */
    GpioLine(std::string device, unsigned int offset)
        : device_(device), offset_(offset) { }

    /**
     * GpioLine offset constructor
     *
     * @param offset The line offset on the device
     *
     * @note The device is assumed to be "gpiochip0", if this might not be true
     *       use the constructors taking both device and offset.
     */
    explicit GpioLine(unsigned int offset)
        : device_("gpiochip0"), offset_(offset) { }

    /**
     * Check if line is enabled
     *
     * @note Line is unused/off if offset is set to GPIO_OFF
     */
    bool enabled() const { return offset_ != GPIO_OFF; }

    /**
     * Get the device for the line.
     *
     * @return The device for the line.
     */
    [[nodiscard]] const std::string &device() const { return device_; }

    /**
     * Get the offset for the line.
     *
     * @return The offset for the line.
     */
    [[nodiscard]] unsigned int offset() const { return offset_; }

private:
    // The gpio device for the specific line (e.g. "gpiochip0")
    std::string device_;
    // The line offset on the device
    unsigned int offset_;
};

/**
 * Trigger edge for GPIO interrupts.
 */
enum class TriggerEdge
{
    Rising, /**< Listen for rising edge events. */
    Falling /**< Listen for falling edge events. */
};

/**
 * Trigger mode for GPIO interrupts.
 *
 * This is currently only used by the FT4222 chip interface where the
 * Continuous mode will use GPIO_TRIGGER_LEVEL_HIGH and GPIO_TRIGGER_LEVEL_LOW
 * instead of the GPIO_TRIGGER_RISING and GPIO_TRIGGER_FALLING.
 */
enum class TriggerMode : uint8_t
{
    Continuous,
    Trigger
};

/**
 * Represents the GPIO settings for a device.
 */
struct GpioSettings
{
    /** The trigger edge for the GPIO interrupt. See @ref TriggerEdge. */
    TriggerEdge triggerEdge { TriggerEdge::Rising };
    /** The trigger mode for the GPIO interrupt. See @ref TriggerMode. */
    TriggerMode triggerMode { TriggerMode::Trigger };
#if SIGNALFLOW_RATCHET
    GpioLine hostEnable { 1012 }; // sysfs pin numbering, HCT06 BA22 gpio 0 ?
    GpioLine hostIrq { 15 }; // ratchet pin numbering, HCT06 BA22 IO 11
    // unsigned hostIrq { 16 };   // ratchet pin numbering, HCT06 BA22 IO 6 (SDA, easier probing that IO 11)
#else
    /** The GPIO line for the host enable signal. */
    GpioLine hostEnable { 22 };
    /** The GPIO line for the host interrupt signal. */
    GpioLine hostIrq { 27 };
#endif // SIGNALFLOW_RATCHET
};

/**
 * Represents a SPI chip interface.
 *
 * The configuration consists of the @ref SpiSettings and the @ref GpioSettings
 * and the frequency in Hz.
 */
class SpiChipInterface : public ChipInterface
{
public:
    /**
     * Constructor for the SPI chip interface.
     *
     * @param spiSettings The SPI settings.
     * @param gpioSettings The GPIO settings.
     * @param frequencyHz The SPI clock frequency.
     */
    SpiChipInterface(SpiSettings spiSettings, GpioSettings gpioSettings, uint32_t frequencyHz)
        : ChipInterface(ConnectionType::Spi, frequencyHz), spiSettings_(std::move(spiSettings)), gpioSettings_(std::move(gpioSettings)) { }

    /**
     * Get the SPI settings for the chip interface.
     */
    const SpiSettings &GetSpiSettings() const { return spiSettings_; }

protected:
    /** SPI settings for the SPI interface. */
    SpiSettings spiSettings_;
    /** GPIO settings for the SPI interface. */
    const GpioSettings gpioSettings_;
};

/**
 * Represents an I2C chip interface.
 *
 * The configuration consists of the @ref GpioSettings and the frequency in Hz
 * and the slave address.
 */
class I2cChipInterface : public ChipInterface
{
public:
    /**
     * Constructor for the I2C chip interface.
     *
     * @param frequencyHz The I2C clock frequency.
     * @param slaveAddress The address of the X4/X7 chip.
     * @param gpioSettings The GPIO settings.
     */
    I2cChipInterface(uint32_t frequencyHz, uint8_t slaveAddress, GpioSettings gpioSettings)
        : ChipInterface(ConnectionType::I2c, frequencyHz),
          gpioSettings_(gpioSettings),
          slaveAddress_(slaveAddress) { }

protected:
    /** GPIO settings for the I2C interface. */
    const GpioSettings gpioSettings_;
    /** Slave address for the I2C interface. */
    uint8_t slaveAddress_;
};

/**
 * Create an I2C chip interface.
 *
 * @tparam type The type of the I2C chip interface.
 * @param frequencyHz The I2C clock frequency.
 * @param slaveAddress The address of the X4/X7 chip.
 * @param gpioSettings The GPIO settings.
 * @param identifier The identifier for the chip interface.
 * @return std::unique_ptr<I2cChipInterface>
 */
template<ChipInterface::InterfaceType type>
std::unique_ptr<I2cChipInterface> CreateI2cChipInterface(
    uint32_t frequencyHz,
    uint8_t slaveAddress,
    GpioSettings gpioSettings,
    ChipInterface::Identifier identifier = {});

/**
 * Create a SPI chip interface.
 *
 * @tparam type The type of the SPI chip interface.
 * @param spiSettings The SPI settings.
 * @param gpioSettings The GPIO settings.
 * @param frequencyHz The SPI clock frequency.
 * @param identifier The identifier for the chip interface.
 * @return std::unique_ptr<SpiChipInterface>
 */
template<ChipInterface::InterfaceType type>
std::unique_ptr<SpiChipInterface> CreateSpiChipInterface(
    SpiSettings spiSettings,
    GpioSettings gpioSettings,
    uint32_t frequencyHz,
    ChipInterface::Identifier identifier = {});

/**
 * Reverse the bits per byte.
 *
 * This function takes a 32-bit integer and reverses the bits in each byte.
 *
 * @param n The 32-bit integer whose bits are to be reversed.
 * @return The 32-bit integer with reversed bits per byte.
 *
 * @code
 * #include "ChipInterface.h"
 * #include <iostream>
 * #include <bitset>
 *
 * int main() {
 *     uint32_t original = 0b00000000'00000000'00000000'00000001;
 *     uint32_t reversed = reverse_bits_per_byte(original);
 *     // Output: 00000000000000000000000010000000
 *     std::cout << std::bitset<32>(reversed) << std::endl;
 *     return 0;
 * }
 * @endcode
 */
CHIPINTERFACE_SYMBOL_EXPORT uint32_t reverse_bits_per_byte(uint32_t n);

/**
 * Reverse the bits for each individual byte in a buffer of specified length.
 *
 * @param buf Pointer to the buffer.
 * @param numElements Number of elements of type T in the buffer.
 *
 * @note This is a wrapper around reverse_bits_per_byte(uint32_t n) which
 *       operates on a single 32-bit word at a time. Thus the buffer is assumed
 *       to have a length and alignment matching that of uint32_t.
 *       Supported types are uint32_t and uint8_t.
 */
template<typename T>
CHIPINTERFACE_SYMBOL_EXPORT void reverse_bits_per_byte(T *buf, size_t numElements);

/**
 * Wait for a specified number of microseconds.
 *
 * @param microseconds The number of microseconds to wait.
 */
inline void wait_us(std::chrono::microseconds microseconds)
{
    // On host system USB comm takes a variable amount of time, but possibly as
    // low as 14 µs, so we can't skip sleeping for any value.
    // std::chrono::sleep_for skips waiting at all if you set wait time to zero
    // (at least with GNU libstdc++), so we can't do a "yield" with sleep(0).

    if( microseconds < std::chrono::microseconds { 250 } ) {
        const auto start = std::chrono::high_resolution_clock::now();
        const auto end = start + microseconds;
        do
            std::this_thread::yield();
        while( std::chrono::high_resolution_clock::now() < end );
    } else {
        std::this_thread::sleep_for(microseconds);
    }
}

} // namespace Novelda

extern "C" {
/** Get a list of FT4222 host interface IDs */
CHIPINTERFACE_SYMBOL_EXPORT uint32_t *get_ft4222_host_interface_ids(int32_t *size);
/** Free the list of FT4222 host interface IDs */
CHIPINTERFACE_SYMBOL_EXPORT void free_ft4222_host_interface_ids(uint32_t *ptr);
}

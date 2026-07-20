#include "ChipInterface.h"

#include <ftd2xx.h>
// NOTE: Linux filename is lower case, Windows is mixed upper and lower.
// Intentionally kept lower for compatibility.
#include <libft4222.h>

#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cstring>
#include <iostream>
#include <mutex>
#include <string>
#include <set>
#include <sstream>
#include <thread>
#include <vector>
#include <cstring>
#include <memory>
#include <iostream>
#include <string_view>

#if defined(__unix__) || defined(__unix) || (defined(__APPLE__) && defined(__MACH__))
#define UNIXLIKE
#endif

#ifdef UNIXLIKE
#include <pthread.h>
#endif

#define FT_STATUS_LIST \
    X(FT_OK) \
    X(FT_INVALID_HANDLE) \
    X(FT_DEVICE_NOT_FOUND) \
    X(FT_DEVICE_NOT_OPENED) \
    X(FT_IO_ERROR) \
    X(FT_INSUFFICIENT_RESOURCES) \
    X(FT_INVALID_PARAMETER) \
    X(FT_INVALID_BAUD_RATE) \
    X(FT_DEVICE_NOT_OPENED_FOR_ERASE) \
    X(FT_DEVICE_NOT_OPENED_FOR_WRITE) \
    X(FT_FAILED_TO_WRITE_DEVICE) \
    X(FT_EEPROM_READ_FAILED) \
    X(FT_EEPROM_WRITE_FAILED) \
    X(FT_EEPROM_ERASE_FAILED) \
    X(FT_EEPROM_NOT_PRESENT) \
    X(FT_EEPROM_NOT_PROGRAMMED) \
    X(FT_INVALID_ARGS) \
    X(FT_NOT_SUPPORTED) \
    X(FT_OTHER_ERROR) \
    X(FT_DEVICE_LIST_NOT_READY)

#define FT4222_STATUS_LIST \
    X(FT4222_OK) \
    X(FT4222_INVALID_HANDLE) \
    X(FT4222_DEVICE_NOT_FOUND) \
    X(FT4222_DEVICE_NOT_OPENED) \
    X(FT4222_IO_ERROR) \
    X(FT4222_INSUFFICIENT_RESOURCES) \
    X(FT4222_INVALID_PARAMETER) \
    X(FT4222_INVALID_BAUD_RATE) \
    X(FT4222_DEVICE_NOT_OPENED_FOR_ERASE) \
    X(FT4222_DEVICE_NOT_OPENED_FOR_WRITE) \
    X(FT4222_FAILED_TO_WRITE_DEVICE) \
    X(FT4222_EEPROM_READ_FAILED) \
    X(FT4222_EEPROM_WRITE_FAILED) \
    X(FT4222_EEPROM_ERASE_FAILED) \
    X(FT4222_EEPROM_NOT_PRESENT) \
    X(FT4222_EEPROM_NOT_PROGRAMMED) \
    X(FT4222_INVALID_ARGS) \
    X(FT4222_NOT_SUPPORTED) \
    X(FT4222_OTHER_ERROR) \
    X(FT4222_DEVICE_LIST_NOT_READY) \
    X(FT4222_DEVICE_NOT_SUPPORTED) \
    X(FT4222_CLK_NOT_SUPPORTED) \
    X(FT4222_VENDER_CMD_NOT_SUPPORTED) \
    X(FT4222_IS_NOT_SPI_MODE) \
    X(FT4222_IS_NOT_I2C_MODE) \
    X(FT4222_IS_NOT_SPI_SINGLE_MODE) \
    X(FT4222_IS_NOT_SPI_MULTI_MODE) \
    X(FT4222_WRONG_I2C_ADDR) \
    X(FT4222_INVAILD_FUNCTION) \
    X(FT4222_INVALID_POINTER) \
    X(FT4222_EXCEEDED_MAX_TRANSFER_SIZE) \
    X(FT4222_FAILED_TO_READ_DEVICE) \
    X(FT4222_I2C_NOT_SUPPORTED_IN_THIS_MODE) \
    X(FT4222_GPIO_NOT_SUPPORTED_IN_THIS_MODE) \
    X(FT4222_GPIO_EXCEEDED_MAX_PORTNUM) \
    X(FT4222_GPIO_WRITE_NOT_SUPPORTED) \
    X(FT4222_GPIO_PULLUP_INVALID_IN_INPUTMODE) \
    X(FT4222_GPIO_PULLDOWN_INVALID_IN_INPUTMODE) \
    X(FT4222_GPIO_OPENDRAIN_INVALID_IN_OUTPUTMODE) \
    X(FT4222_INTERRUPT_NOT_SUPPORTED) \
    X(FT4222_GPIO_INPUT_NOT_SUPPORTED) \
    X(FT4222_EVENT_NOT_SUPPORTED) \
    X(FT4222_FUN_NOT_SUPPORT)

#define GPIO_X4_X7_ENABLE GPIO_PORT2

namespace Novelda {

using namespace std::chrono_literals;

using DeviceInfoList = std::vector<FT_DEVICE_LIST_INFO_NODE>;
using DevicesInfoList = std::vector<DeviceInfoList>;
constexpr size_t DeviceAIndex = 0;

// CHECK macros can be functions in C++20 with std::source_location
// The *_to_str macros could maybe be replaced by code in Common/Enums.h
// NOLINTBEGIN(cppcoreguidelines-macro-usage)

static const char *
ft_status_to_str(FT_STATUS stat)
{
    switch (stat) {
#define X(x) case x: return #x;
    FT_STATUS_LIST
    default:
        return "unknown";
#undef X
    }
}

static const char *
ft4222_status_to_str(FT4222_STATUS stat)
{
    switch (stat) {
#define X(x) case x: return #x;
    FT4222_STATUS_LIST
    default:
        return "unknown";
#undef X
    }
}

#define CHECK(fn) do { \
    FT_STATUS stat__##__LINE__ = fn; \
    if (stat__##__LINE__ != FT_OK) { \
        std::stringstream ss; \
        ss << "Failure: \"" \
           << #fn "\" = " << ft_status_to_str(stat__##__LINE__) \
           << "(" << (int)stat__##__LINE__ << ")"; \
        throw std::runtime_error(ss.str()); \
    } \
} while (0)

#define CHECK4(fn) do { \
    FT4222_STATUS stat__##__LINE__ = fn; \
    if (stat__##__LINE__  != FT4222_OK) { \
        std::stringstream ss; \
        ss << "Failure: \"" \
           << #fn << "\" = " << ft4222_status_to_str(stat__##__LINE__) \
           << "(" << (int)stat__##__LINE__ << ")"; \
        throw std::runtime_error(ss.str()); \
    } \
} while (0)

// NOLINTEND(cppcoreguidelines-macro-usage)

[[maybe_unused]]
std::ostream& operator<<( std::ostream& out, const FT_DEVICE_LIST_INFO_NODE &info )
{
    out << "  Flags:           0x" << std::hex << info.Flags << '\n'
        << "  ProductId:       0x" << std::hex << info.ID << '\n'
        << "  HostInterfaceId: "   << std::dec << info.LocId << '\n'
        << "  Serial:          "   << std::dec << info.SerialNumber << '\n'
        << "  Description:     "   << info.Description << '\n';
    return out;
}

// Store the index in the info struct. We won't use the handle.
static void set_device_number(FT_DEVICE_LIST_INFO_NODE &info, int number)
{
    std::memcpy(&info.ftHandle, &number, sizeof(number));
}

static int get_device_number(const FT_DEVICE_LIST_INFO_NODE &info)
{
    int index{};
    std::memcpy(&index, &info.ftHandle, sizeof(index));
    return index;
}

static void print_device_info_list(const DeviceInfoList infos) {
    for( size_t i = 0; i < infos.size(); ++i ) {
        // It's enough to output information about instance A because that is always
        // the one we specify if multiple devices are connected.
        if( std::string_view(infos[i].Description) == "FT4222 A" )
            std::cerr << "FT4222 " << i << '\n'
                      << infos[i];
    }
}

static DevicesInfoList list_ft_usb_devices(bool output)
{
    DWORD len_u32{};
    CHECK(FT_CreateDeviceInfoList(&len_u32));

    if( len_u32 == 0 )
        return {};

    // Get all FTxxx devices.
    DeviceInfoList infos { len_u32 };
    CHECK(FT_GetDeviceInfoList(infos.data(), &len_u32));

    // The index is needed to address the correct USB device in FT_Open().
    // But we will rearrange the list and thus need to remember it.
    for( size_t i = 0; i < infos.size(); ++i )
        set_device_number(infos[i], int(i));

    // We need only non-busy FT4222 devices in mode 0.
    // On Linux "Description" is empty if the device is busy.
    infos.erase(std::remove_if(infos.begin(), infos.end(), [](auto x) {
                    return std::string_view(x.Description).empty() || x.Type != FT_DEVICE_4222H_0;
                }),
                infos.cend());

    if( infos.empty() )
        return {};

    if( output )
        print_device_info_list(infos);

    // One FTDI device appears as multiple device instances in the info list. The
    // actual number depends on the configuration mode (DCNF0 and DCNF1 jumpers).
    // TODO: Find the source of the above statement and document it better.
    // Only the case when a device appears as two with descriptions "FT4222 A" and
    // "FT4222 B" is handled here.
    // The device instances may be mixed up and not reported completely if multiple
    // FTDI devices are connected.
    // Sort them by bus location id (LocId) and description (Description) to ensure
    // that adjacent entries belong to the same chip.
    const std::string chip_description_a = "FT4222 A";
    const std::string chip_description_b = "FT4222 B";
    std::sort(infos.begin(), infos.end(), [](auto a, auto b) { return a.LocId < b.LocId; });

    // Now correct entries should start with "FT4222 A" and the following
    // entry should be "FT4222 B" with sequential LocId. Check and remove invalid entries.
    for (auto it = infos.begin(); it != infos.end() - 1;) {
        if (it->Description == chip_description_a) {
            if (it == infos.end() - 1 || (it + 1)->Description != chip_description_b || it->LocId + 1 != (it + 1)->LocId)
                it = infos.erase(it);
            else
                ++it;
        } else if (it->Description == chip_description_b) {
            if (it == infos.begin() || (it - 1)->Description != chip_description_a || it->LocId - 1 != (it - 1)->LocId)
                it = infos.erase(it);
            else
                ++it;
        } else {
            throw std::runtime_error("Unexpected chip description for FT4222");
        }
    }

    if (infos.size() < 2 || infos.size() % 2 != 0) {
        throw std::runtime_error("FT4222 were found, but their device information "
                                 "does not match the expectation.");
    }

    DevicesInfoList devices(infos.size() / 2);
    for (size_t i = 0; i < infos.size(); ++i)
        devices[i / 2].push_back(infos[i]);

    return devices;
}

/* "Ping" X4 SPI by writing to debug register
int
spi_ping(struct spi_dev *dev)
{
       uint16_t written, read;
       uint8_t wbuf[] = { 0x84, 0x33 };
       uint8_t rwbuf[] = { 0x04 };
       uint8_t rbuf[1];

       CHECK4(FT4222_SPIMaster_SingleWrite(
               dev->spi_handle, rwbuf, 1, &written,
               false));
       assert(written == 1);
       CHECK4(FT4222_SPIMaster_SingleRead(
               dev->spi_handle, rbuf, 1, &read,
               true));

       printf("Pingsig pre: 0x%x\n", rbuf[0]);

       CHECK4(FT4222_SPIMaster_SingleWrite(
               dev->spi_handle, wbuf, 2, &written,
               true));
       assert(written == 2);


       CHECK4(FT4222_SPIMaster_SingleWrite(
               dev->spi_handle, rwbuf, 1, &written,
               false));
       assert(written == 1);

       CHECK4(FT4222_SPIMaster_SingleRead(
               dev->spi_handle, rbuf, 1, &read,
               true));

       printf("Pingsig post: 0x%x\n", rbuf[0]);

       return rbuf[0] == 0x33 ? 0 : 1;
} */


//
// The GPIO part (enable/interrupt) of the FTDI chip interface.
// This class is a singleton
//
class Ft4222GpioDriver
{
public:
    Ft4222GpioDriver(int device_number)
    {
        CHECK(FT_Open(device_number, &gpio_handle));

#ifdef UNIXLIKE
        pthread_mutex_init(&eh.eMutex, nullptr);
        pthread_cond_init(&eh.eCondVar, nullptr);
#else
        hEvent = CreateEvent(nullptr, false, false, "");
#endif
    }

    Ft4222GpioDriver(const Ft4222GpioDriver &other) = delete;
    Ft4222GpioDriver &operator=(const Ft4222GpioDriver &other) = delete;
    Ft4222GpioDriver(const Ft4222GpioDriver &&other) = delete;
    Ft4222GpioDriver &operator=(const Ft4222GpioDriver &&other) = delete;

    ~Ft4222GpioDriver()
    {
        // We don't throw in the destructor and we don't care about errors
#if ! defined(SIGNALFLOW_X7_BA22_NOT_RESET_ON_EXIT) || SIGNALFLOW_X7_BA22_NOT_RESET_ON_EXIT == 0
        FT4222_GPIO_Write(gpio_handle, GPIO_X4_X7_ENABLE, 0);
#endif
        FT4222_UnInitialize(gpio_handle);
        FT_Close(gpio_handle);
#ifndef UNIXLIKE
        if( hEvent != nullptr )
        {
            CloseHandle( hEvent );
            hEvent = nullptr;
        }
#endif
    }

    void RegisterInterruptListener(ChipInterface* listener)
    {
        std::lock_guard lock(int_mutex_);
        interfaces_.insert(listener);
    }

    void UnregisterInterruptListener(ChipInterface* listener)
    {
        std::lock_guard lock(int_mutex_);
        interfaces_.erase(listener);
    }

    void SetChipEnabled(bool enabled)
    {
        std::lock_guard lock(int_mutex_);
        CHECK4(FT4222_GPIO_Write(gpio_handle, GPIO_X4_X7_ENABLE, enabled));
    }


#ifdef UNIXLIKE
    void SetInterruptThreadEnabled(bool enabled) {
        if (enabled && !int_thread.joinable()) {
            int_thread_exit = false;
            CHECK(FT_SetEventNotification(gpio_handle, FT_EVENT_RXCHAR, (void*)&eh));
            std::thread thread(&Ft4222GpioDriver::RunInterruptThread, this);
            int_thread.swap(thread);

        } else if (int_thread.joinable()){
            pthread_mutex_lock(&eh.eMutex);
            int_thread_exit = true;
            pthread_cond_broadcast(&eh.eCondVar);
            pthread_mutex_unlock(&eh.eMutex);
            int_thread.join();
        }
    }
#else
    void SetInterruptThreadEnabled(bool enabled) {
        if (enabled && !int_thread.joinable()) {
            int_thread_exit = false;
            CHECK(FT_SetEventNotification(gpio_handle, FT_EVENT_RXCHAR, hEvent));
            std::thread thread(&Ft4222GpioDriver::RunInterruptThread, this);
            int_thread.swap(thread);

        } else if (int_thread.joinable()) {
			int_thread_exit = true;
			SetEvent(hEvent);
			int_thread.join();
        }
    }
#endif

    ChipInterface::InterruptState GetInterruptState()
    {
        BOOL value{};
        int_mutex_.lock();
        // The FT4222 does not allow normal read operations while the interrupt
        // is configured. Temoparily disabling the interrupt is a ugly workaround
        // and causes the interrupt thread to wake up and fire interrupts when the
        // pin is asserted. Don't use this function while having interrupt callbacks
        // registered.
        CHECK4(FT4222_SetWakeUpInterrupt(gpio_handle, false));
        FT4222_STATUS stat = FT4222_GPIO_Read(gpio_handle, GPIO_PORT3, &value);
        CHECK4(FT4222_SetWakeUpInterrupt(gpio_handle, true));
        int_mutex_.unlock();
        if (stat != FT4222_OK) {
            std::stringstream msg;
            msg << "Read interrupt event failure: "
                << ft4222_status_to_str(stat)
                << " (" << stat << ")\n";
            throw std::runtime_error(msg.str());
        }
        return value ? ChipInterface::InterruptState::Asserted : ChipInterface::InterruptState::Deasserted;
    }

    GpioSettings gpioSettings_{};
    FT_HANDLE gpio_handle{};

protected:
#ifdef UNIXLIKE
    class MutexLockGuard
    {
    public:
        explicit MutexLockGuard(pthread_mutex_t &mutex)
            : m_mutex(mutex)
        {
            pthread_mutex_lock(&m_mutex);
        }
        ~MutexLockGuard()
        {
            pthread_mutex_unlock(&m_mutex);
        }

        MutexLockGuard(const MutexLockGuard &) = delete;
        MutexLockGuard &operator=(const MutexLockGuard &) = delete;
        MutexLockGuard(MutexLockGuard &&) = delete;
        MutexLockGuard &operator=(MutexLockGuard &&) = delete;

    private:
        pthread_mutex_t &m_mutex;
    };
#endif

    void RunInterruptThread()
    {
#ifdef UNIXLIKE
        MutexLockGuard lock(eh.eMutex);
#endif

        while (true) {
    #ifdef UNIXLIKE
            pthread_cond_wait(&eh.eCondVar, &eh.eMutex);
    #else
            WaitForSingleObject(hEvent, INFINITE);
    #endif
            if (int_thread_exit)
                break;

            BOOL value{};
            int_mutex_.lock();
            FT4222_STATUS stat = FT4222_GPIO_Read(gpio_handle, GPIO_PORT3, &value);
            int_mutex_.unlock();

            if (stat != FT4222_OK) {
                std::stringstream msg;
                msg << "Read interrupt event failure: "
                    << ft4222_status_to_str(stat)
                    << " (" << stat << ")\n";
                throw std::runtime_error(msg.str());
            }

            if (value) {
                std::lock_guard lock(int_mutex_);
                for (auto& ifc: interfaces_) {
                    if (ifc->GetInterruptCallback())
                        ifc->GetInterruptCallback()();
                }
            }

            // If in continuous mode (i.e. LEVEL_HIGH or LEVEL_LOW), the above
            // callback is expected to hang while the IRQ is handled. We then
            // clear the input queue to wait for the next event.
            if (gpioSettings_.triggerMode == TriggerMode::Continuous) {
                int_mutex_.lock();
                FT4222_GPIO_Read(gpio_handle, GPIO_PORT3, &value);
                int_mutex_.unlock();
            }
        }
    }

#ifdef UNIXLIKE
	EVENT_HANDLE eh = { {}, {}, 0 };
#else
	HANDLE hEvent = nullptr;
#endif
	std::thread int_thread;
	std::mutex int_mutex_;
	volatile bool int_thread_exit = false;
	std::set<ChipInterface*> interfaces_;
};

enum class SpiBusClockFrequency
{
    BusFrequency_0_94MHz = 940'000,
    BusFrequency_1_25MHz = 1'250'000,
    BusFrequency_2_5MHz = 2'500'000,
    BusFrequency_5MHz = 5'000'000,
    BusFrequency_6MHz = 6'000'000,
    BusFrequency_7_5MHz = 7'500'000,
    BusFrequency_10MHz = 10'000'000,
    BusFrequency_12MHz = 12'000'000,
    BusFrequency_15MHz = 15'000'000,
    BusFrequency_20MHz = 20'000'000,
};

enum class I2cBusClockFrequency
{
    Standard = 100'000,
    Fast = 400'000,
    FastPlus = 1'000'000,
    HighSpeed = 3'400'000,
    UltraFast = 5'000'000,
};

template<typename BusClockFrequency>
static BusClockFrequency GetQuantizedClockFrequencyEnum(uint32_t UserFrequency)
{
    if constexpr( std::is_same_v<BusClockFrequency, SpiBusClockFrequency> ) {
        if( UserFrequency >= 20'000'000 ) /* 20MHz */
        {
            return SpiBusClockFrequency::BusFrequency_20MHz;
        } else if( UserFrequency >= 15'000'000 ) /* 15MHz */
        {
            return SpiBusClockFrequency::BusFrequency_15MHz;
        } else if( UserFrequency >= 12'000'000 ) /* 12MHz */
        {
            return SpiBusClockFrequency::BusFrequency_12MHz;
        } else if( UserFrequency >= 10'000'000 ) /* 10MHz */
        {
            return SpiBusClockFrequency::BusFrequency_10MHz;
        } else if( UserFrequency >= 7'500'000 ) /* 7.5MHz */
        {
            return SpiBusClockFrequency::BusFrequency_7_5MHz;
        } else if( UserFrequency >= 6'000'000 ) /* 6MHz */
        {
            return SpiBusClockFrequency::BusFrequency_6MHz;
        } else if( UserFrequency >= 5'000'000 ) /* 5MHz */
        {
            return SpiBusClockFrequency::BusFrequency_5MHz;
        } else if( UserFrequency >= 2'500'000 ) /* 2.5MHz */
        {
            return SpiBusClockFrequency::BusFrequency_2_5MHz;
        } else if( UserFrequency >= 1'250'000 ) /* 1.25MHz */
        {
            return SpiBusClockFrequency::BusFrequency_1_25MHz;
        } else {
            return SpiBusClockFrequency::BusFrequency_0_94MHz;
        }
    } else if constexpr( std::is_same_v<BusClockFrequency, I2cBusClockFrequency> ) {
        if( UserFrequency >= 5'000'000 ) /* 5MHz */
        {
            return I2cBusClockFrequency::UltraFast;
        } else if( UserFrequency >= 3'400'000 ) /* 3.4MHz */
        {
            return I2cBusClockFrequency::HighSpeed;
        } else if( UserFrequency >= 1'000'000 ) /* 1MHz */
        {
            return I2cBusClockFrequency::FastPlus;
        } else if( UserFrequency >= 400'000 ) /* 400KHz */
        {
            return I2cBusClockFrequency::Fast;
        } else {
            return I2cBusClockFrequency::Standard;
        }
    } else {
        static_assert(!sizeof(BusClockFrequency *), "Unknown bus clock frequency type");
    }
}

template<typename BusClockFrequency>
static uint32_t GetQuantizedClockFrequency(BusClockFrequency UserFrequency)
{
    return static_cast<uint32_t>(std::underlying_type_t<BusClockFrequency>(UserFrequency));
}

template<typename BusClockFrequency>
static uint32_t GetQuantizedClockFrequency(uint32_t UserFrequency)
{
    return GetQuantizedClockFrequency<BusClockFrequency>(GetQuantizedClockFrequencyEnum<BusClockFrequency>(UserFrequency));
}

[[maybe_unused]]
std::ostream& operator<<( std::ostream& out, const SpiBusClockFrequency freq )
{
    switch( freq )
    {
    case SpiBusClockFrequency::BusFrequency_20MHz:
        out << "QSPI clock configuration ";
        out << "  FTDI clock rate: 80MHz ";
        out << "  FTDI clock divisor: 4 ";
        break;

    case SpiBusClockFrequency::BusFrequency_15MHz:
        out << "QSPI clock configuration ";
        out << "  FTDI clock rate: 60MHz ";
        out << "  FTDI clock divisor: 4 ";
        break;

    case SpiBusClockFrequency::BusFrequency_12MHz:
        out << "QSPI clock configuration ";
        out << "  FTDI clock rate: 48MHz ";
        out << "  FTDI clock divisor: 4 ";
        break;

    case SpiBusClockFrequency::BusFrequency_10MHz:
        out << "QSPI clock configuration" << '\n';
        out << "  FTDI clock rate: 80MHz" << '\n';
        out << "  FTDI clock divisor: 8" << '\n';
        break;

    case SpiBusClockFrequency::BusFrequency_7_5MHz:
        out << "QSPI clock configuration" << '\n';
        out << "  FTDI clock rate: 60MHz" << '\n';
        out << "  FTDI clock divisor: 8" << '\n';
        break;

    case SpiBusClockFrequency::BusFrequency_5MHz:
        out << "QSPI clock configuration" << '\n';
        out << "  FTDI clock rate: 80MHz" << '\n';
        out << "  FTDI clock divisor: 16" << '\n';
        break;

    case SpiBusClockFrequency::BusFrequency_2_5MHz:
        out << "QSPI clock configuration" << '\n';
        out << "  FTDI clock rate: 80MHz" << '\n';
        out << "  FTDI clock divisor: 32" << '\n';
        break;

    case SpiBusClockFrequency::BusFrequency_1_25MHz:
        out << "QSPI clock configuration" << '\n';
        out << "  FTDI clock rate: 80MHz" << '\n';
        out << "  FTDI clock divisor: 64MHz" << '\n';
        break;

    case SpiBusClockFrequency::BusFrequency_0_94MHz:
        out << "QSPI clock configuration" << '\n';
        out << "  FTDI clock rate: 60MHz" << '\n';
        out << "  FTDI clock divisor: 64" << '\n';
        break;

    default:
        out << "Invalid QSPI clock configuration" << '\n';
        break;
    }
    return out;
}

//
// Base class for all FTDI chip interface implementations.
// Takes care of the GPIO singleton.
//
template<typename DerivedClass>
class BasicFt4222Interface
{
public:
    BasicFt4222Interface(ChipInterface::Identifier id, GpioSettings gpioSettings = {})
    {
        DevicesInfoList devices = list_ft_usb_devices(false);
        if (devices.empty()) {
            throw std::runtime_error("Could not find a FT4222 device configured in "
                                     "mode 0. Check the hardware connection and "
                                     "make sure that the DCNF0/1 jumpers are in "
                                     "position LL.");
        }

        if (devices.size() > 1 && !id) {
            for (const auto & device: devices)
                print_device_info_list(device);
            throw std::runtime_error("Multiple FT4222 devices are connected and "
                                     "one of them must be explicitly selected by "
                                     "the HostInterfaceId parameter.");
        }

        const DeviceInfoList &infos = [&devices, &id]() {
            if (!id)
                return devices[DeviceAIndex];

            const uint32_t busLocationId = [&id] {
                try {
                    return std::stoul(id.value());
                }
                catch( const std::exception &ex ) {
                    std::stringstream ss;
                    ss << "The HostInterfaceID '" << id.value() << "' is not a valid number. (" << ex.what() << ")";
                    throw std::runtime_error(ss.str());
                }
            }();
            auto device = find_if(devices.begin(), devices.end(),
                                  [&busLocationId](const DeviceInfoList &device) {
                                        return device[DeviceAIndex].LocId == busLocationId;
            });
            if (device == devices.end()) {
                std::stringstream ss;
                ss << "A FT4222 device with the HostInterfaceId '" << id.value() << "' is not connected.";
                throw std::runtime_error(ss.str());
            }
            return *device;
        }();

        // The info list is sorted. Entry 0 is the data device, 1 is the GPIO device
        auto data_dev_number = get_device_number(infos[0]);
        auto gpio_dev_number = get_device_number(infos[1]);

        gpio_ = std::make_unique<Ft4222GpioDriver>(gpio_dev_number);
        gpio_->gpioSettings_ = gpioSettings;
        CHECK(FT_Open(data_dev_number, &data_handle));
        gpio_->RegisterInterruptListener(CastToChipInterface());

        start_time_ = std::chrono::high_resolution_clock::now();
    }

    BasicFt4222Interface(const BasicFt4222Interface &other) = delete;
    BasicFt4222Interface &operator=(const BasicFt4222Interface &other) = delete;
    BasicFt4222Interface(const BasicFt4222Interface &&other) = delete;
    BasicFt4222Interface &operator=(const BasicFt4222Interface &&other) = delete;

    ~BasicFt4222Interface()
    {
        try {
            gpio_->SetInterruptThreadEnabled(false);
            gpio_->UnregisterInterruptListener(CastToChipInterface());
            FT4222_UnInitialize(data_handle);
            FT_Close(data_handle);
        } catch (const std::exception& ex) {
            std::cerr << "~BasicFt4222Interface: " << ex.what();
        }
    }

protected:
    ChipInterface* CastToChipInterface()
    {
        return static_cast<DerivedClass*>(this);
    }

    std::chrono::microseconds GetTimeMicroseconds()
    {
        const auto now = std::chrono::high_resolution_clock::now();
        return std::chrono::duration_cast<std::chrono::microseconds>(now - start_time_);
    }

    static constexpr uint8_t SlaveSelectOutput = 1;

    std::unique_ptr<Ft4222GpioDriver> gpio_;
    FT_HANDLE data_handle{nullptr};
    std::chrono::time_point<std::chrono::high_resolution_clock> start_time_;
};

class Ft4222I2cInterface :
        public I2cChipInterface,
        protected BasicFt4222Interface<Ft4222I2cInterface>
{
    friend class BasicFt4222Interface<Ft4222I2cInterface>;

public:
    Ft4222I2cInterface(uint32_t frequencyHz, uint8_t slaveAddress, GpioSettings gpioSettings,
                       ChipInterface::Identifier identifier = {})
        : I2cChipInterface(GetQuantizedClockFrequency<I2cBusClockFrequency>(frequencyHz),
                           slaveAddress, gpioSettings),
          BasicFt4222Interface<Ft4222I2cInterface>(identifier)
    {
        uint32_t kbps = frequencyHz / 1000;

        CHECK4(FT4222_I2CMaster_Init(data_handle, kbps));

        // "SS0O low on I2C init" vendor workaround
        const uint8_t CHIPTOP_DEBUG_REQUEST = 0xFF;
        std::array<uint8_t, 3> vendorcmd{ 0x04, 0xAF, 0x01 };
        // This gives error 4, but it works.
        FT_VendorCmdSet(gpio_->gpio_handle, CHIPTOP_DEBUG_REQUEST, vendorcmd.data(), sizeof(vendorcmd));
        // The above affects I2C speed for some reason, so set it back to 400 using
        // magic.
        // There is no problem with 400 or 1000 on Linux. Keeping if persists on X4 and 400kbps.
        if (kbps == 400) {
            const uint8_t I2C_MASTER_SET_I2CMTP = 0x52;
            std::array<uint8_t, 1> i2cmtp_400{ 0x10 }; //@60MHz (standard) the best value for 400kHz is 0x10
            CHECK(FT_VendorCmdSet(
                gpio_->gpio_handle, I2C_MASTER_SET_I2CMTP,
            i2cmtp_400.data(), sizeof(i2cmtp_400)));
        }
        // Workaround end.

        std::array dirs{
            GPIO_INPUT,
            GPIO_INPUT,
            GPIO_OUTPUT,
            GPIO_INPUT
        };

        CHECK4(FT4222_GPIO_Init(gpio_->gpio_handle, dirs.data()));
        CHECK4(FT4222_SetSuspendOut(gpio_->gpio_handle, false));
        CHECK4(FT4222_SetWakeUpInterrupt(gpio_->gpio_handle, true));

        if (gpioSettings.triggerMode == TriggerMode::Continuous)
            CHECK4(FT4222_SetInterruptTrigger(gpio_->gpio_handle, ((gpioSettings.triggerEdge == Novelda::TriggerEdge::Rising) ? GPIO_TRIGGER_LEVEL_HIGH : GPIO_TRIGGER_LEVEL_LOW)));
        else
            CHECK4(FT4222_SetInterruptTrigger(gpio_->gpio_handle, ((gpioSettings.triggerEdge == Novelda::TriggerEdge::Rising) ? GPIO_TRIGGER_RISING : GPIO_TRIGGER_FALLING)));

        gpio_->SetInterruptThreadEnabled(true);

        CHECK4(FT4222_GPIO_Write(gpio_->gpio_handle, GPIO_X4_X7_ENABLE, 1));
    }

    void WaitMicroseconds(std::chrono::microseconds microseconds) override
    {
        wait_us(microseconds);
    }

    void GetTimeMicroseconds(std::chrono::microseconds *time_us) override
    {
        if(!time_us) {
            throw std::runtime_error("FT4222ChipInterface: GetTimeMicroseconds() time_us is nullptr");
        }
        *time_us = BasicFt4222Interface::GetTimeMicroseconds();
    }

    bool WaitForInterrupt(std::chrono::microseconds) override
    {
        throw std::runtime_error("FT4222ChipInterface: WaitForInterrupt() Not implemented.");
    }

    void Transfer(const uint8_t* wdata, size_t wlength, uint8_t* rdata, size_t rlength) override
    {
        assert(wdata || rdata);

        if (wdata) {
            assert(wlength <= UINT16_MAX);

            uint16_t bytesWritten{};
            FT4222_STATUS stat = FT4222_I2CMaster_Write(
                data_handle, slaveAddress_, const_cast<uint8_t*>(wdata), (uint16_t)wlength, &bytesWritten);
            if (stat != FT4222_OK)
                throw std::runtime_error("Error writing data over FT4222");

            // FT4222_I2CMaster_Write() returns before all bits are sent. While this optimises
            // the throughput in general, it causes non-deterministic timing problems when
            // talking to the X4. We may send another command before the X4 is able to handle
            // it. Additional waits on the host would not solve the problem as they might be
            // masked by ongoing transfers (wait may complete before a large message is flushed).
            // The only reliable way to make sure that a I2C transaction has been finished is,
            // to wait until the bus is idle.
            uint8_t flags = 0;
            do {
                // FT4222_I2CMaster_GetStatus() fails sporadically. The problem is
                for (uint32_t retries = 3; retries > 0; --retries) {
                    // The wait is necessary because of FT4222 Errata 3.4.2:
                    // I2C data is corrupt when FT4222_I2CMaster_GetStatus is being called
                    // The wait has to happen between Write() and GetStatus().
                    WaitMicroseconds(100us);
                    stat = FT4222_I2CMaster_GetStatus(data_handle, &flags);
                    if (stat == FT4222_OK)
                        break;
                }
                if (stat != FT4222_OK)
                    throw std::runtime_error("Error reading status from FT4222");
                if (I2CM_DATA_NACK(flags) || I2CM_ADDRESS_NACK(flags))
                    throw std::runtime_error("The chip did not acknowledge the message as expected");
            } while (!I2CM_IDLE(flags));
        }

        if (rdata) {
            uint16_t bytesRead{};

            assert(rlength <= UINT16_MAX);

            FT4222_STATUS stat = FT4222_I2CMaster_Read(
                data_handle, slaveAddress_, rdata, (uint16_t)rlength, &bytesRead);
            if (stat != FT4222_OK)
                throw std::runtime_error("Error reading data from FT4222");
        }
    }

    void SetChipEnabled(bool enabled) override
    {
        gpio_->SetChipEnabled(enabled);
    }

    ChipInterface::InterruptState GetInterruptState() override
    {
        return gpio_->GetInterruptState();
    }

    uint32_t AdjustClockFrequency(uint32_t frequencyHz) override
    {
        return GetQuantizedClockFrequency<I2cBusClockFrequency>(frequencyHz);
    }

};

class Ft4222SpiInterface :
        public SpiChipInterface,
        protected BasicFt4222Interface<Ft4222SpiInterface>
{
    friend class BasicFt4222Interface<Ft4222SpiInterface>;
public:
    Ft4222SpiInterface(SpiSettings spiSettings,
                        GpioSettings gpioSettings,
                        uint32_t frequencyHz,
                        ChipInterface::Identifier identifier = {})
        : SpiChipInterface(spiSettings, gpioSettings, GetQuantizedClockFrequency<SpiBusClockFrequency>(frequencyHz)),
          BasicFt4222Interface<Ft4222SpiInterface>(identifier, gpioSettings)
    {
        GetClockDividers(GetQuantizedClockFrequencyEnum<SpiBusClockFrequency>(frequencyHz));
        //The X7 requires the SPI clock speed to be less than 13,5 MHz. 80/13,5 ~=6, so the CLK_DIV could be as low as 8
        CHECK4(FT4222_SetClock(data_handle, FTClockRate_));
        CHECK4(FT4222_SPIMaster_Init(data_handle,
            SPI_IO_QUAD,
            FTSpiClockDiv_,
            ((spiSettings.clockPolarity == Novelda::ClockPolarity::Low) ? CLK_IDLE_LOW : CLK_IDLE_HIGH),
            ((spiSettings.clockPhase == Novelda::ClockPhase::Trailing) ? CLK_TRAILING : CLK_LEADING),
            SlaveSelectOutput));

        /* Enforce weakest driving strength */
        CHECK4(FT4222_SPI_SetDrivingStrength(data_handle, DS_4MA, DS_4MA, DS_4MA));

        std::array dirs{
            GPIO_INPUT,
            GPIO_INPUT,
            GPIO_OUTPUT,
            GPIO_INPUT
        };

        CHECK4(FT4222_GPIO_Init(gpio_->gpio_handle, dirs.data()));
        CHECK4(FT4222_SetSuspendOut(gpio_->gpio_handle, false));
        CHECK4(FT4222_SetWakeUpInterrupt(gpio_->gpio_handle, true));
        if (gpioSettings.triggerMode == TriggerMode::Continuous)
            CHECK4(FT4222_SetInterruptTrigger(gpio_->gpio_handle, ((gpioSettings.triggerEdge == Novelda::TriggerEdge::Rising) ? GPIO_TRIGGER_LEVEL_HIGH : GPIO_TRIGGER_LEVEL_LOW)));
        else
            CHECK4(FT4222_SetInterruptTrigger(gpio_->gpio_handle, ((gpioSettings.triggerEdge == Novelda::TriggerEdge::Rising) ? GPIO_TRIGGER_RISING : GPIO_TRIGGER_FALLING)));

        gpio_->SetInterruptThreadEnabled(true);

        CHECK4(FT4222_GPIO_Write(gpio_->gpio_handle, GPIO_X4_X7_ENABLE, 1)); // TODO should not be done here

        SetSpiLineNumber(spiSettings_.spiLineNumber);
    }

    void SetSpiLineNumber(Novelda::SpiLineNumber mode)
    {
        FT4222_SPIMode ftmode{SPI_IO_NONE};
        switch (mode) {
        case Novelda::SpiLineNumber::Spi:
            ftmode = SPI_IO_SINGLE;
            break;
        case Novelda::SpiLineNumber::DSpi:
            ftmode = SPI_IO_DUAL;
            break;
        case Novelda::SpiLineNumber::QSpi:
            ftmode = SPI_IO_QUAD;
            break;
        default:
            throw std::runtime_error("Invalid Spi mode");

        }
        CHECK4(FT4222_SPIMaster_SetLines(data_handle, ftmode));
    }

    uint32_t AdjustClockFrequency(uint32_t frequencyHz) override
    {
        const auto freq = GetQuantizedClockFrequencyEnum<SpiBusClockFrequency>(frequencyHz);
        GetClockDividers(freq);
        CHECK4(FT4222_SetClock(data_handle, FTClockRate_));
        return GetQuantizedClockFrequency(freq);
    }

    void WaitMicroseconds(std::chrono::microseconds microseconds) override
    {
        wait_us(microseconds);
    }

    void GetTimeMicroseconds(std::chrono::microseconds *time_us) override
    {
        *time_us = BasicFt4222Interface::GetTimeMicroseconds();
    }

    bool WaitForInterrupt(std::chrono::microseconds) override
    {
        throw std::runtime_error("FT4222ChipInterface: WaitForInterrupt() Not implemented.");
    }

    void Transfer(const uint8_t* wdata, size_t wlength, uint8_t* rdata, size_t rlength) override
    {
        //NOTE: WE EITHER READ OR WRITE, REGARDLESS OF THE FTDI's CAPABILITIES OF DOING BOTH SIMULTANEOUSLY

        // X7 AHB Lite Bridge spec says: "although not strictly enforced, a
        // reasonable upper limit on N might be 1024", i.e. 4096 bytes. But it
        // works fine with more, so let's just blast it.
#ifndef NDEBUG
        const size_t maxBytesToTransfer = 64*1024;
#endif // !NDEBUG

        constexpr auto X7_ADDRESS_LENGTH = sizeof(uint32_t);

        assert(wlength <= maxBytesToTransfer);
        assert(rlength <= maxBytesToTransfer);

        uint32_t no_read_bytes{};
        std::vector<uint8_t> wbuf(wdata, wdata + wlength);

        // The command is always transmitted in (single) SPI mode. Therefore,
        // a bit reversal satisfies all SPI modes.
        if( spiSettings_.bitOrder == Novelda::BitOrder::LSB ) {
            // Novelda::BitOrder::LSB only supported with X7 which has 32bit command width
            assert(wlength >= X7_ADDRESS_LENGTH); // write buffers must at least contain an address
            reverse_bits_per_byte(wbuf.data(), X7_ADDRESS_LENGTH);
        }

        if (rlength > 0) {

            FT4222_STATUS stat{};

            if( spiSettings_.spiLineNumber == Novelda::SpiLineNumber::Spi )
            {
                wbuf.resize(wlength + rlength);
                auto rbuf = wbuf;

                uint16_t no_bytes{};
                stat = FT4222_SPIMaster_SingleReadWrite(
                        data_handle, rbuf.data(), wbuf.data(),
                        (uint16_t)(wbuf.size()), &no_bytes, true);
                memcpy(rdata, &rbuf[wlength], rlength);
                no_read_bytes = no_bytes - uint32_t(wlength);
            } else {
                stat = FT4222_SPIMaster_MultiReadWrite(
                        data_handle, rdata,
                        wbuf.data(), X7_ADDRESS_LENGTH, 0, (uint16_t)rlength, &no_read_bytes);
            }

            // NOTE: The `stat` variable is only checking status of the FTDI device, not the SPI connection to the novelda sensor.
            if (stat != FT4222_OK || no_read_bytes != rlength)
                throw std::runtime_error("Error reading data over FT4222");

            if( spiSettings_.bitOrder == Novelda::BitOrder::LSB ) {
                switch( spiSettings_.spiLineNumber ) {
                case Novelda::SpiLineNumber::QSpi:
                    reverse_nibbles(rdata, rlength);
                    break;
                case Novelda::SpiLineNumber::DSpi:
                    assert(0 && "TODO");
                    break;
                case Novelda::SpiLineNumber::Spi:
                    reverse_bits_per_byte(rdata, rlength);
                    break;
                default:
                    assert(false);
                }
            }

        } else if (wlength > 0) {

            if( spiSettings_.bitOrder == Novelda::BitOrder::LSB ) {
                // Restructure outgoing data to accomodate for bit and byte order
                switch( spiSettings_.spiLineNumber ) {
                case Novelda::SpiLineNumber::QSpi:
                    reverse_nibbles(&wbuf[X7_ADDRESS_LENGTH], wlength - X7_ADDRESS_LENGTH);
                    break;
                case Novelda::SpiLineNumber::DSpi:
                    assert(0 && "TODO");
                    break;
                case Novelda::SpiLineNumber::Spi:
                    reverse_bits_per_byte(&wbuf[X7_ADDRESS_LENGTH], wlength - X7_ADDRESS_LENGTH);
                    break;
                default:
                    assert(false);
                }
            }

            FT4222_STATUS stat{FT4222_OTHER_ERROR};
            if (spiSettings_.spiLineNumber == Novelda::SpiLineNumber::Spi) {
                uint16_t no_written_bytes{};
                stat = FT4222_SPIMaster_SingleWrite(
                        data_handle, wbuf.data(),
                        static_cast<uint16_t>(wlength), &no_written_bytes, true);
            } else {
                stat = FT4222_SPIMaster_MultiReadWrite(
                        data_handle, nullptr, wbuf.data(), X7_ADDRESS_LENGTH,
                        static_cast<uint16_t>(wlength) - X7_ADDRESS_LENGTH, 0, &no_read_bytes);
            }

            if (stat != FT4222_OK)
                throw std::runtime_error("Error writing data over FT4222:QSPI");
        }
    }

    void SetChipEnabled(bool enabled) override
    {
        gpio_->SetChipEnabled(enabled);
    }

    ChipInterface::InterruptState GetInterruptState() override
    {
        return gpio_->GetInterruptState();
    }

protected:
    /**
     * Reverse the nibbles per byte, for QSPI
     */
    uint32_t reverse_nibbles(uint32_t n)
    {
        n = ((n >> 4) & 0x0f0f0f0f) | ((n << 4) & 0xf0f0f0f0);
        return n;
    }

    void reverse_nibbles(uint8_t *ns, size_t len)
    {
        for (size_t i = 0; i < len / sizeof(uint32_t); ++i) {
            uint32_t word{};
            memcpy(&word, &ns[i * sizeof(uint32_t)], sizeof(uint32_t));
            word = reverse_nibbles(word);
            memcpy(&ns[i * sizeof(uint32_t)], &word, sizeof(uint32_t));
        }
    }

    inline uint8_t swapcharacters(const uint8_t byte) {
        return (uint8_t)(((byte & 0xf0) >> 4) | ((byte & 0x0f) << 4));
    }

private:
    void GetClockDividers(SpiBusClockFrequency RequestedFrequency)
    {
        switch( RequestedFrequency )
        {
        case SpiBusClockFrequency::BusFrequency_20MHz:
            FTClockRate_ = SYS_CLK_80;
            FTSpiClockDiv_ = CLK_DIV_4;
            break;

        case SpiBusClockFrequency::BusFrequency_15MHz:
            FTClockRate_ = SYS_CLK_60;
            FTSpiClockDiv_ = CLK_DIV_4;
            break;

        case SpiBusClockFrequency::BusFrequency_12MHz:
            FTClockRate_ = SYS_CLK_48;
            FTSpiClockDiv_ = CLK_DIV_4;
            break;

        case SpiBusClockFrequency::BusFrequency_10MHz:
            FTClockRate_ = SYS_CLK_80;
            FTSpiClockDiv_ = CLK_DIV_8;
            break;

        case SpiBusClockFrequency::BusFrequency_7_5MHz:
            FTClockRate_ = SYS_CLK_60;
            FTSpiClockDiv_ = CLK_DIV_8;
            break;

        case SpiBusClockFrequency::BusFrequency_6MHz:
            FTClockRate_ = SYS_CLK_24;
            FTSpiClockDiv_ = CLK_DIV_4;
            break;

        case SpiBusClockFrequency::BusFrequency_5MHz:
            FTClockRate_ = SYS_CLK_80;
            FTSpiClockDiv_ = CLK_DIV_16;
            break;

        case SpiBusClockFrequency::BusFrequency_2_5MHz:
            FTClockRate_ = SYS_CLK_80;
            FTSpiClockDiv_ = CLK_DIV_32;
            break;

        case SpiBusClockFrequency::BusFrequency_1_25MHz:
            FTClockRate_ = SYS_CLK_80;
            FTSpiClockDiv_ = CLK_DIV_64;
            break;

        case SpiBusClockFrequency::BusFrequency_0_94MHz:
            FTClockRate_ = SYS_CLK_60;
            FTSpiClockDiv_ = CLK_DIV_64;

            break;

        default:
            throw std::runtime_error("Wrong QSPI frequency, check SpiBusClockFrequency available values");
        }
    }

private:
    FT4222_ClockRate FTClockRate_{};
    FT4222_SPIClock FTSpiClockDiv_{};
};

template<>
CHIPINTERFACE_SYMBOL_EXPORT std::unique_ptr<I2cChipInterface>
CreateI2cChipInterface<ChipInterface::InterfaceType::Ft4222>(
        uint32_t frequencyHz, uint8_t slaveAddress, GpioSettings gpioSettings,
        ChipInterface::Identifier identifier)
{
    return std::make_unique<Ft4222I2cInterface>(frequencyHz, slaveAddress, gpioSettings,
                                                identifier);
}

template<>
CHIPINTERFACE_SYMBOL_EXPORT std::unique_ptr<SpiChipInterface>
CreateSpiChipInterface<ChipInterface::InterfaceType::Ft4222>(
        SpiSettings spiSettings,
        GpioSettings gpioSettings,
        uint32_t frequencyHz,
        ChipInterface::Identifier instance)
{
    // FIXME: chipType currently ignored for Ft4222SpiInterface
    return std::make_unique<Ft4222SpiInterface>(spiSettings, gpioSettings, frequencyHz,
                                                instance);
}

} // namespace Novelda

CHIPINTERFACE_SYMBOL_EXPORT uint32_t* get_ft4222_host_interface_ids(int32_t* size)
{
    try {
        const auto devices = Novelda::list_ft_usb_devices(false);

        *size = int32_t(devices.size());
        auto *ids = new uint32_t[*size];
        std::transform(devices.begin(), devices.end(), ids, [](const auto& device) { return uint32_t( device[Novelda::DeviceAIndex].LocId ); });
        return ids;
    }
    catch( const std::exception& ex ) {
        std::cerr << "get_ft4222_host_interface_ids: " << ex.what();
        *size = 0;
        return nullptr;
    }
}

CHIPINTERFACE_SYMBOL_EXPORT void free_ft4222_host_interface_ids(uint32_t* ids)
{
    if( ids ) {
        delete[] ids;
    } else {
        std::cerr << "free_ft4222_host_interface_ids: ids is nullptr";
    }
}

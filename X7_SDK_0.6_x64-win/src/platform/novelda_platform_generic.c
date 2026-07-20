#include "novelda_platform_generic.h"

#include <inttypes.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h> // snprintf

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#define FILENAME_MAX 4096
#endif

const uint32_t HOST_INTERFACE_ID = 2186521779UL; // "HostInterfaceId"
const uint32_t HOST_GPIO_ENABLE = 266385155UL; // "HostGpioEnable"
const uint32_t HOST_GPIO_IRQ = 4250243434UL; // "HostGpioIrq"
const uint32_t CHIP_GPIO_IRQ = 2042098954UL; // "ChipGpioIrq"

const uint32_t IO_CONFIG_CONNECTION_PARAMETERS_SECTION_ID = 1614025149UL; //  ConnectionParameters
const uint32_t IO_CONFIG_PRIMARY_SOURCE_SECTION_ID = 1946922724UL; // "PrimarySource"
const uint32_t IO_CONFIG_SECONDARY_SOURCE_SECTION_ID = 2715700012UL; // "SecondarySource"

novelda_product_error_t set_io_config(signalflow_context_t *sf, io_config_t *config)
{
#ifdef NOVELDA_CHIPINTERFACE_FT4222
    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(sf, 0, IO_CONFIG_CONNECTION_PARAMETERS_SECTION_ID, HOST_INTERFACE_ID, SF_DATATYPE_STRING, NULL, 0, (uint8_t *)config->host_interface_id, strlen(config->host_interface_id)),
        PRODUCT_ERROR_IO_CONFIG);
#else
    uint32_t section_id = 0;
    if( config->chip_count == 1 ) {
        section_id = IO_CONFIG_CONNECTION_PARAMETERS_SECTION_ID;
    } else if( config->chip_count == 2 ) {
        if( config->chip_number == 0 ) {
            section_id = IO_CONFIG_PRIMARY_SOURCE_SECTION_ID;
        } else if( config->chip_number == 1 ) {
            section_id = IO_CONFIG_SECONDARY_SOURCE_SECTION_ID;
        } else {
            return PRODUCT_ERROR_INVALID_ARGUMENT;
        }
    } else {
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(sf, 0, section_id, HOST_INTERFACE_ID, SF_DATATYPE_STRING, NULL, 0, (uint8_t *)config->interface, strlen(config->interface)),
        PRODUCT_ERROR_IO_CONFIG);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(sf, 0, section_id, HOST_GPIO_ENABLE, SF_DATATYPE_STRING, NULL, 0, (uint8_t *)config->gpio_host_enable, strlen(config->gpio_host_enable)),
        PRODUCT_ERROR_IO_CONFIG);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(sf, 0, section_id, HOST_GPIO_IRQ, SF_DATATYPE_STRING, NULL, 0, (uint8_t *)config->gpio_host_irq, strlen(config->gpio_host_irq)),
        PRODUCT_ERROR_IO_CONFIG);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(sf, 0, section_id, CHIP_GPIO_IRQ, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&config->gpio_chip_irq, 1),
        PRODUCT_ERROR_IO_CONFIG);
#endif

    return PRODUCT_ERROR_SUCCESS;
}

// Firmware paths are by default supplied as paths relative to the current working directory.
// This function converts the path to a path relative to the executable.
novelda_product_error_t get_full_fw_path(char *output_path, char *firmware_path)
{
#ifdef _WIN32
    char *pathToExecutable = (char *)malloc(_MAX_PATH);
    if( pathToExecutable == NULL ) {
        return PRODUCT_ERROR_FAILURE;
    }

    DWORD len = GetModuleFileNameA(NULL, pathToExecutable, _MAX_PATH);
    if( len == 0 || len == _MAX_PATH ) {
        // Handle error or buffer size limit reached
        free(pathToExecutable);
        return PRODUCT_ERROR_FAILURE;
    }
    pathToExecutable[len] = '\0'; // Ensure null termination

    char *last_backslash = strrchr(pathToExecutable, '\\');
    if( last_backslash == NULL ) {
        free(pathToExecutable);
        return PRODUCT_ERROR_FAILURE;
    }
    *last_backslash = '\0'; // Truncate string to remove filename

    const int result = snprintf(output_path, MAX_PATH, "%s\\%s", pathToExecutable, firmware_path);

    free(pathToExecutable);
    return result < 0 ? PRODUCT_ERROR_FAILURE : PRODUCT_ERROR_SUCCESS;
#else
    const size_t bufsize = FILENAME_MAX - strlen(firmware_path);
    char pathToExecutable[bufsize];
    ssize_t len = readlink("/proc/self/exe", pathToExecutable, FILENAME_MAX - strlen(firmware_path));

    if( len == -1 || len == (ssize_t)bufsize ) {
        return PRODUCT_ERROR_FAILURE;
    }

    char *last_slash = strrchr(pathToExecutable, '/');
    if( last_slash == NULL ) {
        return PRODUCT_ERROR_FAILURE;
    }
    // Truncate string to remove filename
    *last_slash = '\0';

    const int result = snprintf(output_path, FILENAME_MAX, "%s/%s", pathToExecutable, firmware_path);
    if( result < 0 || result >= FILENAME_MAX ) {
        return PRODUCT_ERROR_FAILURE;
    }
    return PRODUCT_ERROR_SUCCESS;
#endif
}

novelda_product_error_t set_firmware_paths(signalflow_context_t *sf, uint32_t chip_number, uint32_t chip_count)
{
    // Section: [ConnectionParameters]
    const uint32_t BA22_FIRMWARE_PATH_IC003 = 3498276135UL; // "BA22FirmwarePathIC003"
    const uint32_t BA22_FIRMWARE_PATH_IC004 = 3447943278UL; // "BA22FirmwarePathIC004"
    uint32_t section_id = 0;
    if( chip_count == 1 ) {
        section_id = IO_CONFIG_CONNECTION_PARAMETERS_SECTION_ID;
    } else if( chip_count == 2 ) {
        if( chip_number == 0 ) {
            section_id = IO_CONFIG_PRIMARY_SOURCE_SECTION_ID;
        } else if( chip_number == 1 ) {
            section_id = IO_CONFIG_SECONDARY_SOURCE_SECTION_ID;
        } else {
            return PRODUCT_ERROR_INVALID_ARGUMENT;
        }
    } else {
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }

    typedef struct
    {
        const char *path;
        uint32_t id;
    } FirmwareInfo;

    char full_fw_path_ic003[FILENAME_MAX];
    char full_fw_path_ic004[FILENAME_MAX];

    novelda_product_error_t result = get_full_fw_path(full_fw_path_ic003, FIRMWARE_PATH_IC003);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        return result;
    }
    result = get_full_fw_path(full_fw_path_ic004, FIRMWARE_PATH_IC004);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        return result;
    }

    FirmwareInfo firmwareInfos[] = {
        { full_fw_path_ic003, BA22_FIRMWARE_PATH_IC003 },
        { full_fw_path_ic004, BA22_FIRMWARE_PATH_IC004 }
    };

    for( size_t i = 0; i < sizeof(firmwareInfos) / sizeof(firmwareInfos[0]); i++ ) {
        const char *firmware = firmwareInfos[i].path;
        const uint32_t id = firmwareInfos[i].id;
        VALIDATE_PRODUCT_CONFIGURATION(
            signalflow_set_parameter_array(sf, 0, section_id, id, SF_DATATYPE_STRING, NULL, 0, (uint8_t *)firmware, strlen(firmware)),
            PRODUCT_ERROR_FAILURE);
    }

    return PRODUCT_ERROR_SUCCESS;
}

novelda_product_error_t disable_secondary_reset(signalflow_context_t *sf)
{
    const uint32_t RESET_X7 = 2625136077UL; // "ResetX7"
    const int32_t reset = 0;
    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(sf, 0, IO_CONFIG_SECONDARY_SOURCE_SECTION_ID, RESET_X7, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&reset, 1),
        PRODUCT_ERROR_RESET_X7);

    return PRODUCT_ERROR_SUCCESS;
}

volatile sig_atomic_t g_running = 1;
#ifdef _WIN32
BOOL WINAPI win_sigint_handler(DWORD dwType)
{
    switch( dwType ) {
    case CTRL_C_EVENT:
    case CTRL_BREAK_EVENT:
        g_running = 0;
        return TRUE;
    default:
        return FALSE;
    }
}
#else
void sigint_handler(int signum)
{
    switch( signum ) {
    case SIGINT:
    case SIGTERM:
        g_running = 0;
        break;
    }
}
#endif

void platform_add_signal_handlers()
{
    // Set up signal handling
#ifdef _WIN32
    // Windows-specific setup
    SetConsoleCtrlHandler(win_sigint_handler, TRUE);
#else
    // Unix/Linux-specific setup
    struct sigaction sa;
    sa.sa_handler = sigint_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);
#endif
}

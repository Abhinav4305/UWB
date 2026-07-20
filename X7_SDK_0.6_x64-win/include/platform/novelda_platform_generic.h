#ifndef NOVELDA_PLATFORM_GENERIC_H
#define NOVELDA_PLATFORM_GENERIC_H

#include "novelda_signalflow.h"
#include "novelda_platform.h"

/**
 * Special value for the gpio settings in @ref io_config_t
 * to indicate that the line is not used.
 */
#define GPIO_HOST_OFF "gpiochip0:255"

/**
 * @file
 *
 * Generic platform specific functions.
 */

/**
 * IO configuration for the radar.
 */
typedef struct
{
#ifdef NOVELDA_CHIPINTERFACE_FT4222
    /// The bus location id where the radar is connected.
    /// If only one device is connected "0" can be passed as the bus location id.
    const char *host_interface_id;
#else
    /// The chip number for this chip, 0-indexed
    uint32_t chip_number;
    /// The total number of chips in the system
    uint32_t chip_count;
    /// The interface to use for communication with the radar
    const char *interface;
    /// The GPIO to use for enabling the radar on the host
    const char *gpio_host_enable;
    /// The GPIO to use for receiving interrupts from the radar on the host
    const char *gpio_host_irq;
    /// The GPIO to use for receiving interrupts from the radar on the target
    int32_t gpio_chip_irq;
#endif
} io_config_t;

/**
 * Set the IO configuration for the radar.
 *
 * @param sf The SignalFlow context.
 * @param config The IO configuration for the radar.
 *
 * @return PRODUCT_ERROR_SUCCESS on success, otherwise an error code.
 */
novelda_product_error_t set_io_config(signalflow_context_t *sf, io_config_t *config);

/**
 * Get an IO configuation for a specific chip to be used in set_io_config
 *
 * @param chip_number The chip number to get the IO configuration for
 * @param chip_count The total number of chips in the system
 * @param config The IO configuration to fill in
 * @return PRODUCT_ERROR_SUCCESS on success, otherwise an error code
 *
 * @note This function has to be provided by the user/build system
 */
novelda_product_error_t get_io_config(int chip_number, int chip_count, io_config_t *config);

/**
 * Set the firmware paths for the BA22
 *
 * @param sf The SignalFlow context
 * @param chip_number The chip number to set the firmware paths for
 * @param chip_count The total number of chips in the system
 *
 * @return PRODUCT_ERROR_SUCCESS on success, otherwise an error code
 */
novelda_product_error_t set_firmware_paths(signalflow_context_t *sf, uint32_t chip_number, uint32_t chip_count);

/**
 * Disable the secondary reset.
 *
 * Workaround if there is a single reset line for both chips in a dual chip setup.
 *
 * @param sf The SignalFlow context
 *
 * @return PRODUCT_ERROR_SUCCESS on success, otherwise an error code
 */
novelda_product_error_t disable_secondary_reset(signalflow_context_t *sf);

#endif // NOVELDA_PLATFORM_GENERIC_H
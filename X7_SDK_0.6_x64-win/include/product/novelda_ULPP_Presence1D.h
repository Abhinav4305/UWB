#ifndef NOVELDA_ULPP_PRESENCE1D_H
#define NOVELDA_ULPP_PRESENCE1D_H

#include "novelda_product.h"
#include "novelda_signalflow.h"

#include <stdbool.h>

/**
 * @file
 * API for the ULPP_Presence1D application
 */

/**
 * ULPP specific context object passed to all ULPP functions
 * It has to be created by calling the ulpp_create() function
 */
typedef struct ulpp_context ulpp_context_t;

/**
 * Create a ULPP context object
 *
 * @param sf The SignalFlow context.
 * @note This will have to be deleted by calling ulpp_delete()
 * @return ulpp_context_t* The ULPP context object.
 */
ulpp_context_t *ulpp_create(signalflow_context_t *sf);

/**
 * Uninitialize and release the ULPP context
 * This will also delete the embedded signalflow context
 *
 * @param ulpp The ULPP context.
 * @return novelda_product_error_t The status of the deletion process.
 */
novelda_product_error_t ulpp_delete(ulpp_context_t *ulpp);

/**
 * Represents the configuration for the ULPP.
 */
typedef struct
{
    /**
     * 1x2 array of values specifying start/stop of the 1D detection zone in
     * meters. E.g. {0.5, 2.0}
     */
    const float detection_zone[2];

    /**
     * 1x4 vector of values in range [0,100] 0=Weight for presence, 1=Weight no
     * presence, 2=Confidence threshold for Presence, 3=Confidence Threshold
     * for No Presence. For more info see  ULPP_Presence1D_description.md.
     */
    const int32_t confidence_values[4];

    /**
     * Number of micro frames (mframes) per pulse. Each mframe consists of 16
     * range bins, each bin having a length of 0.0714 meters. The first mframe
     * starts at -1.145 meters.
     */
    const int32_t num_mframes_per_pulse;

    /**
     * Scalar value in linear scale which is multiplied with the detection
     * threshold vector to scale it up or down. To calculate the adjustment
     * level in dB: threshold_level_adjustment_db =
     * 10*log10(threshold_level_adjustment_linear). Default is 1.0.
     */
    const float threshold_level_adjustment_linear;

    /**
     * Enable low power mode - this is the default and recommended mode.
     *
     * A setting of true will enable the low power mode in which the X7 will
     * go into hibernation mode between frames to minimize power consumption.
     *
     * A setting of false will enable the normal mode in which the X7 is kept
     * active while running. This mode is mainly intended for debug purposes
     * and will have a much higher power consumption than the low power mode.
     */
    bool low_power_mode;

    /**
     * If enabled, the callback will only be called when the presence state
     * changes. This results in significant power savings depending on how
     * often the state normally changes.
     */
    bool send_output_on_presence_change_only;
} ulpp_config_t;

/**
 * Sets the configuration for the ULPP.
 *
 * @param ulpp The ULPP context.
 * @param config The configuration for the ULPP.
 * @return signalflow_error_t The status of the configuration process.
 *
 * @note This function must be called after ulpp_load_flow()
 */
novelda_product_error_t ulpp_set_ulpp_config(ulpp_context_t *ulpp, ulpp_config_t *config);

/**
 * Set spi speed
 *
 * This is the speed used during frame streaming. Note that this is not the
 * only speed requested from the chip interface. The chip interface
 * implementation should be able to handle requests of other speeds in:
 *
 * * `chipinterface_set_clock_frequency(uint32_t)` (C)
 * * `AdjustClockFrequency(uint32_t)` (c++).
 *
 * @param rd The ULPP context.
 * @param spi_speed The speed to set the SPI to in Hz.
 * @return novelda_product_error_t The status of the configuration process.
 *
 * @note This function must be called after ulpp_load_flow()
 */
novelda_product_error_t ulpp_set_spi_speed(ulpp_context_t *rd, int32_t spi_speed);

#ifdef NOVELDA_FILESYSTEM_CAPABILITY
/**
 * Enables or disables file output.
 *
 * @param ulpp The ULPP context.
 * @param output_path The path to the file to write to. If NULL, file output is disabled.
 * @return novelda_product_error_t The status of the configuration call.
 *
 * @note This function must be called after ulpp_load_flow()
 */
novelda_product_error_t ulpp_configure_file_output(ulpp_context_t *ulpp, const char *output_path);
#endif // NOVELDA_FILESYSTEM_CAPABILITY

/**
 * Read human presence signal
 *
 * For more information about the signal content see the documentation in ULPP_Presence1D_description.md.
 *
 * @param ulpp The ULPP context.
 * @param data_buffer The data buffer to read from.
 * @param data_buffer_size The size of the data buffer.
 * @param signal The signal to write to.
 * @return signalflow_error_t The return status of the read call.
 */
signalflow_error_t ulpp_read_human_presence(ulpp_context_t *ulpp, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal);

/**
 * Read detection 1D signal
 *
 * For more information about the signal content see the documentation in ULPP_Presence1D_description.md.
 *
 * @param ulpp The ULPP context.
 * @param data_buffer The data buffer to read from.
 * @param data_buffer_size The size of the data buffer.
 * @param signal The signal to write to.
 * @return signalflow_error_t The return status of the read call.
 */
signalflow_error_t ulpp_read_detection_1d(ulpp_context_t *ulpp, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal);

/**
 * Read power per bin signal
 *
 * For more information about the signal content see the documentation in ULPP_Presence1D_description.md.
 *
 * @param ulpp The ULPP context.
 * @param data_buffer The data buffer to read from.
 * @param data_buffer_size The size of the data buffer.
 * @param signal The signal to write to.
 * @return signalflow_error_t The return status of the read call.
 */
signalflow_error_t ulpp_read_power_per_bin(ulpp_context_t *ulpp, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal);

/**
 * Configure signalflow for ULPP
 *
 * @param ulpp The ULPP context.
 * @return novelda_product_error_t The status of the configuration process.
 */
novelda_product_error_t ulpp_load_flow(ulpp_context_t *ulpp);

#endif // NOVELDA_ULPP_PRESENCE1D_H
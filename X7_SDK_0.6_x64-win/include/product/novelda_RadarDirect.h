#ifndef NOVELDA_RADAR_DIRECT_H
#define NOVELDA_RADAR_DIRECT_H

#include "novelda_product.h"
#include "novelda_signalflow.h"

/**
 * @file
 * API for the RadarDirect application
 */

/**
 * RadarDirect specific context object passed to all RadarDirect functions
 * It has to be created by calling the radar_direct_create() function
 */
typedef struct radar_direct_context radar_direct_context_t;

/**
 * Create a RadarDirect context object
 *
 * @param sf The SignalFlow context.
 * @note This will have to be deleted by calling radar_direct_delete()
 * @return radar_direct_context_t* The RadarDirect context object.
 */
radar_direct_context_t *radar_direct_create(signalflow_context_t *sf);

/**
 * Uninitialize and release the RadarDirect context
 * This will also delete the embedded signalflow context
 *
 * @param rd The RadarDirect context.
 * @return novelda_product_error_t The status of the deletion process.
 */
novelda_product_error_t radar_direct_delete(radar_direct_context_t *rd);

/**
 * Represents the configuration for transmitter and receiver channels.
 */
typedef struct
{
    /**
     * Represents the sequence of active transmitter channels.
     *
     * This variable is a pointer to a sequence of active transmitter (Tx) channels.
     * Each value (or tuple in multi-chip configuration) corresponds to the
     * active Tx channel for a particular frame.
     *
     * For a single chip configuration, the sequence can include 0 (Tx0 active) or 1 (Tx1 active).
     * For a dual-chip configuration, the sequence can include 0 (Tx0 active), 1 (Tx1 active),
     * 2 (Tx2 active), and 3 (Tx3 active).
     *
     * The length of the sequence is described by an additional parameter, tx_channel_sequence_length.
     */
    const uint16_t *tx_channel_sequence;
    /** Number of elements in tx_channel_sequence */
    size_t tx_channel_sequence_length;

    /**
     * Represents the sequence of active receiver channels.
     *
     * This variable is a pointer to a sequence of bitmasks for active receiver (Rx) channels.
     * Each bitmask corresponds to the active Rx channels for a particular frame.
     *
     * For a single chip configuration, the bitmask can be 0b01 (Rx0 active), 0b10 (Rx1 active),
     * or 0b11 (both Rx0 and Rx1 active).
     *
     * For a multi-chip configuration, the bitmask can represent any combination of channels,
     * with each pair of bits corresponding to a chip's channels.
     *
     * The length of the sequence is described by an additional parameter, rx_mask_sequence_length.
     */
    const uint16_t *rx_mask_sequence;
    /** Number of elements in rx_mask_sequence */
    size_t rx_mask_sequence_length;
} trx_config_t;

/**
 * Configures the transmitter and receiver channels for the radar.
 *
 * @param rd The RadarDirect context.
 * @param config The configuration for the transmitter and receiver channels.
 * @return novelda_product_error_t The status of the configuration process.
 *
 * @note This function must be called after radar_direct_load_flow()
 */
novelda_product_error_t radar_direct_configure_trx(radar_direct_context_t *rd, trx_config_t *config);

/**
 * Represents the configuration for the X7 radar chip.
 */
typedef struct
{
    /** Frame rate of the radar in frames per second. */
    float fps;

    /** The period of the radar pulse in number of mframes. */
    int32_t pulse_period;

    /** The number of microframes per radar pulse. */
    int32_t mframes_per_pulse;

    /** The number of pulses per iteration. */
    int32_t pulses_per_iteration;

    /** The number of iterations per frame. An iteration consists of pulses_per_iteration number of pulses. */
    int32_t iterations_per_frame;

    /** The transmission power of the radar. */
    int32_t tx_power;

    /** The number of interleaved frames. */
    int32_t interleaved_frames;
} x7_chip_config_t;

/**
 * Set radar chip config
 *
 * @param rd The RadarDirect context.
 * @param params The configuration parameters for the X7 radar chip.
 * @return novelda_product_error_t The status of the configuration process.
 *
 * @note Only one of the radar_direct_set_x7_user_config or radar_direct_set_x7_chip_config can be set at a time.
 * @note This function must be called after radar_direct_load_flow()
 */
novelda_product_error_t radar_direct_set_x7_chip_config(radar_direct_context_t *rd, x7_chip_config_t *params);

/**
 * Set SPI speed
 *
 * This is the speed used during frame streaming. Note that this is not the
 * only speed requested from the chip interface. The chip interface
 * implementation should be able to handle requests of other speeds in:
 *
 * * `chipinterface_set_clock_frequency(uint32_t)` (C)
 * * `AdjustClockFrequency(uint32_t)` (C++).
 *
 * @param rd The RadarDirect context.
 * @param spi_speed The speed to set the SPI to in Hz.
 * @return novelda_product_error_t The status of the configuration process.
 *
 * @note This function must be called after radar_direct_load_flow()
 */
novelda_product_error_t radar_direct_set_spi_speed(radar_direct_context_t *rd, int32_t spi_speed);

/**
 * Read radar frame
 *
 * @param rd The RadarDirect context.
 * @param data_buffer The buffer to store the radar frame data.
 * @param data_buffer_size The size of the data buffer.
 * @param signal The signal information.
 * @return signalflow_error_t The status of the read operation.
 */
signalflow_error_t radar_direct_read_radar_frame(radar_direct_context_t *rd, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal);

/**
 * Read TRX mask
 *
 * @param rd The RadarDirect context.
 * @param data_buffer The buffer to store the TRX mask data.
 * @param data_buffer_size The size of the data buffer.
 * @param signal The signal information.
 * @return signalflow_error_t The status of the read operation.
 */
signalflow_error_t radar_direct_read_trx_mask(radar_direct_context_t *rd, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal);

#ifdef NOVELDA_FILESYSTEM_CAPABILITY
/**
 * Enables or disables file output.
 *
 * @param rd The RadarDirect context.
 * @param output_path The path to the file to write to. If NULL, file output is disabled.
 * @return novelda_product_error_t The status of the configuration process.
 *
 * @note This function must be called after radar_direct_load_flow()
 */
novelda_product_error_t radar_direct_configure_file_output(radar_direct_context_t *rd, const char *output_path);

/**
 * Enables or disables file input.
 *
 * @param rd The RadarDirect context.
 * @param input_path The path to the file to read from. If NULL, file input is disabled.
 * @return novelda_product_error_t The status of the configuration process.
 *
 * @note This function must be called before radar_direct_load_flow()
 */
novelda_product_error_t radar_direct_set_file_input(radar_direct_context_t *rd, const char *input_path);
#endif // NOVELDA_FILESYSTEM_CAPABILITY

/**
 * Set the number of radar chips to use.
 *
 * @param rd The RadarDirect context.
 * @param chip_count The number of radar chips to use.
 * @return novelda_product_error_t The status of the configuration process.
 *
 * @note This function must be called before radar_direct_load_flow()
 */
novelda_product_error_t radar_direct_set_chip_count(radar_direct_context_t *rd, int chip_count);

/**
 * Load flow for RadarDirect
 *
 * @param rd The RadarDirect context.
 * @return novelda_product_error_t The status of the load process.
 */
novelda_product_error_t radar_direct_load_flow(radar_direct_context_t *rd);

#endif // NOVELDA_RADAR_DIRECT_H
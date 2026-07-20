#ifndef NOVELDA_PRODUCT_H
#define NOVELDA_PRODUCT_H

#include "novelda_signalflow.h"
#include <inttypes.h>

/**
 * @file
 *
 * Common API for all product implementations
 */

/**
 * Macro for use on unused parameters to avoid compiler warnings.
 *
 * The macro makes it more clear that something is unsed than a
 * direct cast to void.
 */
#define UNUSED(x) (void)(x)

/**
 * Error codes used in novelda products API
 */
typedef int32_t novelda_product_error_t;

#define PRODUCT_ERROR_SUCCESS 0 /**< SUCCESS */
#define PRODUCT_ERROR_FAILURE -1 /**< Unspecified failure */
#define PRODUCT_ERROR_NOT_IMPLEMENTED -2 /**< Functionality not implemented */
#define PRODUCT_ERROR_NULLPTR -3 /**< NULL pointer */
#define PRODUCT_ERROR_INVALID_ARGUMENT -4 /**< Invalid argument */
#define PRODUCT_ERROR_FILE_ERROR -5 /**< File related error */
#define PRODUCT_ERROR_INVALID_FLOW_REF -6 /**< Invalid flow reference */
#define PRODUCT_ERROR_TX_CHANNEL_SEQUENCE -7 /**< Invalid Tx channel sequence */
#define PRODUCT_ERROR_RX_MASK_SEQUENCE -8 /**< Invalid Rx mask sequence */
#define PRODUCT_ERROR_FPS -9 /**< Error when configuring FPS */
#define PRODUCT_ERROR_DUTY_CYCLE -10 /**< Error when configuring duty cycle */
#define PRODUCT_ERROR_MAX_RANGE -11 /**< Error when configuring max range */
#define PRODUCT_ERROR_SCALING_FACTOR -12 /**< Error when configuring scaling factor */
#define PRODUCT_ERROR_ANTENNA_GAIN -13 /**< Error when configuring antenna gain */
#define PRODUCT_ERROR_INTERLEAVING_MODE -14 /**< Error when configuring interleaving mode */
#define PRODUCT_ERROR_PULSE_PERIOD -15 /**< Error when configuring pulse period */
#define PRODUCT_ERROR_MFRAMES_PER_PULSE -16 /**< Error when configuring mframes per pulse */
#define PRODUCT_ERROR_PULSES_PER_ITERATION -17 /**< Error when configuring pulses per iteration */
#define PRODUCT_ERROR_ITERATIONS_PER_FRAME -18 /**< Error when configuring iterations per frame */
#define PRODUCT_ERROR_TX_POWER -19 /**< Error when configuring Tx power */
#define PRODUCT_ERROR_INTERLEAVED_FRAMES -20 /**< Error when configuring interleaved frames */
#define PRODUCT_ERROR_DETECTION_ZONE_XY_POINTS -21 /**< Error when configuring detection zone xy points */
#define PRODUCT_ERROR_THRESHOLD_LEVEL_ADJUSTMENT_DB -22 /**< Error when configuring threshold level adjustment db */
#define PRODUCT_ERROR_CONFIDENCE_VALUES -23 /**< Error when configuring confidence values */
#define PRODUCT_ERROR_MAX_NUM_DETECTIONS -24 /**< Error when configuring max number of detections */
#define PRODUCT_ERROR_MAX_NUM_HUMAN_DETECTION_2D_OUTPUTS -25 /**< Error when configuring max_num_human_detection_2d_outputs */
#define PRODUCT_ERROR_ELEMENT_DISTANCE -26 /**< Error when configuring element distance */
#define PRODUCT_ERROR_IO_CONFIG -27 /**< Error when configuring IO */
#define PRODUCT_ERROR_RESET_X7 -28 /**< Error when configuring X7 reset */
#define PRODUCT_ERROR_DETECTION_ZONE -29 /**< Error when configuring detection zone */
#define PRODUCT_ERROR_MODE -30 /**< Error when configuring mode */
#define PRODUCT_ERROR_SYSTEM_CLOCK_SOURCE -31 /**< Error when configuring system clock source */
#define PRODUCT_ERROR_STREAMING_TIMEOUT -32 /**< Error when configuring streaming timeout */

/**
 * Helper macro for validating product configuration.
 *
 * Returns the specified error code if the signal flow error is not SFERR_SUCCESS.
 */
#define VALIDATE_PRODUCT_CONFIGURATION(sf_error, product_error) \
    {                                                           \
        if( (sf_error) != SFERR_SUCCESS )                       \
            return (product_error);                             \
    }

/**
 * Information about a signal frame.
 */
typedef struct
{
    signalflow_datatype_t datatype; /**< The data type of the signal. */
    const uint16_t *shape; /**< The shape of the signal, e.g. {2, 3} for a 2x3 matrix. */
    size_t shape_size; /**< The size of the shape array, e.g 2 for a 2x3 matrix. */
    const uint8_t *array; /**< The array byte buffer. */
    size_t array_element_count; /**< The number of elements in the array of type @ref datatype. */
} signal_info_t;

/**
 * Read signal from data buffer.
 *
 * @param data_buffer The data buffer to read from.
 * @param data_buffer_size The size of the data buffer in bytes.
 * @param signal_semantic The semantic ID of the signal.
 * @param array_semantic The semantic ID of the array.
 * @param signal The signal to write to.
 *
 * @return SFERR_SUCCESS on success, otherwise an error code.
 */
signalflow_error_t read_signal(const uint8_t *data_buffer, size_t data_buffer_size, uint32_t signal_semantic, uint32_t array_semantic, signal_info_t *signal);

#endif // NOVELDA_PRODUCT_H
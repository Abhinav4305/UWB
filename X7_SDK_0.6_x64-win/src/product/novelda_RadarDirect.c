#include "novelda_RadarDirect.h"
#include "novelda_platform.h"
#include "novelda_product.h"

#include <stdbool.h> // for bool
#include <stdlib.h> // for malloc, free
#include <string.h> // for strlen

// Section: [public]
const uint32_t PUBLIC_SECTION_ID = 3432027008UL; // "public"
const uint32_t FPS_PARAM_ID = 11362760UL; // "FPS"
const uint32_t TX_CHANNEL_SEQUENCE_ID = 4269504277UL; // "TxChannelSequence"
const uint32_t RX_MASK_SEQUENCE_ID = 3217867522UL; // "RxMaskSequence"

// Radar chip settings (X7)
const uint32_t PULSE_PERIOD_ID = 3574707063UL; // "PulsePeriod"
const uint32_t MFRAMES_PER_PULSE_ID = 452857946UL; // "MframesPerPulse"
const uint32_t PULSES_PER_ITERATION_ID = 3802288709UL; // "PulsesPerIteration"
const uint32_t ITERATIONS_PER_FRAME_ID = 2612959833UL; // "IterationsPerFrame"
const uint32_t TX_POWER_ID = 1250849890UL; // "TxPower"
const uint32_t INTERLEAVED_FRAMES_ID = 4152055922UL; // "InterleavedFrames"

struct radar_direct_context
{
    signalflow_context_t *sf;
    int chip_count;
    const char *playback_input_path;
    bool loaded;
};

radar_direct_context_t *radar_direct_create(signalflow_context_t *sf)
{
    if( !sf ) {
        return NULL;
    }
    radar_direct_context_t *rd = (radar_direct_context_t *)malloc(sizeof(radar_direct_context_t));
    if( !rd ) {
        return NULL;
    }
    rd->sf = sf;
    rd->chip_count = 0;
    rd->playback_input_path = NULL;
    rd->loaded = false;
    return rd;
}

novelda_product_error_t radar_direct_delete(radar_direct_context_t *rd)
{
    if( !rd ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( rd->playback_input_path ) {
        free((void *)rd->playback_input_path);
        rd->playback_input_path = NULL;
    }

    signalflow_error_t signalflow_delete_result = signalflow_delete(rd->sf);
    rd->sf = NULL;

    free(rd);
    rd = NULL;

    VALIDATE_PRODUCT_CONFIGURATION(signalflow_delete_result, PRODUCT_ERROR_FAILURE);
    return PRODUCT_ERROR_SUCCESS;
}

novelda_product_error_t radar_direct_configure_trx(radar_direct_context_t *rd, trx_config_t *config)
{
    if( !rd || !config ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( !rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, TX_CHANNEL_SEQUENCE_ID, SF_DATATYPE_UINT16, NULL, 0, (uint8_t *)config->tx_channel_sequence, config->tx_channel_sequence_length),
        PRODUCT_ERROR_TX_CHANNEL_SEQUENCE);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, RX_MASK_SEQUENCE_ID, SF_DATATYPE_UINT16, NULL, 0, (uint8_t *)config->rx_mask_sequence, config->rx_mask_sequence_length),
        PRODUCT_ERROR_RX_MASK_SEQUENCE);

    return PRODUCT_ERROR_SUCCESS;
}

novelda_product_error_t radar_direct_set_x7_chip_config(radar_direct_context_t *rd, x7_chip_config_t *params)
{
    if( !rd || !params ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( !rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, PULSE_PERIOD_ID, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&params->pulse_period, 1),
        PRODUCT_ERROR_PULSE_PERIOD);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, MFRAMES_PER_PULSE_ID, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&params->mframes_per_pulse, 1),
        PRODUCT_ERROR_MFRAMES_PER_PULSE);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, PULSES_PER_ITERATION_ID, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&params->pulses_per_iteration, 1),
        PRODUCT_ERROR_PULSES_PER_ITERATION);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, ITERATIONS_PER_FRAME_ID, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&params->iterations_per_frame, 1),
        PRODUCT_ERROR_ITERATIONS_PER_FRAME);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, TX_POWER_ID, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&params->tx_power, 1),
        PRODUCT_ERROR_TX_POWER);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, INTERLEAVED_FRAMES_ID, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&params->interleaved_frames, 1),
        PRODUCT_ERROR_INTERLEAVED_FRAMES);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, PUBLIC_SECTION_ID, FPS_PARAM_ID, SF_DATATYPE_FLOAT, NULL, 0, (uint8_t *)&params->fps, 1),
        PRODUCT_ERROR_FPS);

    return PRODUCT_ERROR_SUCCESS;
}

novelda_product_error_t radar_direct_set_spi_speed(radar_direct_context_t *rd, int32_t spi_speed)
{
    if( !rd ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( !rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    const uint32_t SPI_SPEED_ID = 0x4EF172F8UL; // "SpiSpeed"
    const uint32_t CONNECTION_PARAMETERS_SECTION_ID = 0x603411BDUL; // "ConnectionParameters"

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, CONNECTION_PARAMETERS_SECTION_ID, SPI_SPEED_ID, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&spi_speed, 1),
        PRODUCT_ERROR_FAILURE);

    return PRODUCT_ERROR_SUCCESS;
}

const uint32_t FILESINK_PARAMETERS_SECTION_ID = 2156828940UL; // "fileSink"
const uint32_t FILESINK_ENABLED = 2626085950UL; // "Enabled"

static novelda_product_error_t radar_direct_configure_file_output_enabled(radar_direct_context_t *rd, uint8_t enabled)
{
    if( !rd ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    if( !rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(rd->sf, 0, FILESINK_PARAMETERS_SECTION_ID, FILESINK_ENABLED, SF_DATATYPE_BOOL, NULL, 0, &enabled, 1),
        PRODUCT_ERROR_FILE_ERROR);

    return PRODUCT_ERROR_SUCCESS;
}

#ifdef NOVELDA_FILESYSTEM_CAPABILITY

novelda_product_error_t radar_direct_configure_file_output(radar_direct_context_t *rd, const char *output_path)
{
    if( !rd ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    if( !rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }
    const uint8_t enable = output_path != NULL ? 1 : 0;
    VALIDATE_PRODUCT_CONFIGURATION(radar_direct_configure_file_output_enabled(rd, enable), PRODUCT_ERROR_FILE_ERROR);
    const uint32_t FILESINK_PATH = 3949388886UL; // "Path"
    if( enable ) {
        VALIDATE_PRODUCT_CONFIGURATION(
            signalflow_set_parameter_array(rd->sf, 0, FILESINK_PARAMETERS_SECTION_ID, FILESINK_PATH, SF_DATATYPE_STRING, NULL, 0, (uint8_t *)output_path, strlen(output_path)),
            PRODUCT_ERROR_FILE_ERROR);
    }
    return PRODUCT_ERROR_SUCCESS;
}

const uint32_t FILE_SOURCE_SECTION_ID = 2235041238UL; // "fileSource = 0x853805D6"
const uint32_t FILE_SOURCE_PATH_ID = 3949388886UL; // "Path = 0xEB66E456"

novelda_product_error_t radar_direct_set_file_input(radar_direct_context_t *rd, const char *input_path)
{
    if( !rd ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    if( rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    if( rd->playback_input_path ) {
        free((void *)rd->playback_input_path);
        rd->playback_input_path = NULL;
    }
    if( input_path ) {
        // store away the path in the context
#ifdef _WIN32
        rd->playback_input_path = _strdup(input_path);
#else
        rd->playback_input_path = strdup(input_path);
#endif
        if( !rd->playback_input_path ) {
            return PRODUCT_ERROR_FILE_ERROR;
        }
    }
    return PRODUCT_ERROR_SUCCESS;
}

static novelda_product_error_t radar_direct_configure_file_input(radar_direct_context_t *rd)
{
    if( !rd ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    if( !rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    if( rd->playback_input_path ) {
        VALIDATE_PRODUCT_CONFIGURATION(
            signalflow_set_parameter_array(rd->sf, 0, FILE_SOURCE_SECTION_ID, FILE_SOURCE_PATH_ID, SF_DATATYPE_STRING, NULL, 0, (uint8_t *)rd->playback_input_path, strlen(rd->playback_input_path)),
            PRODUCT_ERROR_FILE_ERROR);
    }
    return PRODUCT_ERROR_SUCCESS;
}
#endif // NOVELDA_FILESYSTEM_CAPABILITY

// Signal and Array semantics for signalflow_get_frame_array()
const uint32_t SIGNAL_SEMANTIC_RADAR_X7 = 1576343857UL; // "radar_x7"
const uint32_t ARRAY_SEMANTIC_BBIQ_FLOAT32 = 2015020171UL; // "bbiq_float32"
const uint32_t ARRAY_SEMANTIC_RADAR_TRXMASK = 1728571907UL; // "radar_trx_mask"
const uint32_t ARRAY_SEMANTIC_RADAR_FRAME_VALID_STATUS = 1655653667UL; // "radar_frame_valid_status"

signalflow_error_t radar_direct_read_radar_frame(radar_direct_context_t *rd, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal)
{
    UNUSED(rd);
    const uint32_t signal_semantic = SIGNAL_SEMANTIC_RADAR_X7;
    const uint32_t array_semantic = ARRAY_SEMANTIC_BBIQ_FLOAT32;
    return read_signal(data_buffer, data_buffer_size, signal_semantic, array_semantic, signal);
}

signalflow_error_t radar_direct_read_trx_mask(radar_direct_context_t *rd, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal)
{
    UNUSED(rd);
    const uint32_t signal_semantic = SIGNAL_SEMANTIC_RADAR_X7;
    const uint32_t array_semantic = ARRAY_SEMANTIC_RADAR_TRXMASK;
    return read_signal(data_buffer, data_buffer_size, signal_semantic, array_semantic, signal);
}

novelda_product_error_t radar_direct_set_chip_count(radar_direct_context_t *rd, int chip_count)
{
    if( !rd ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    if( rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }
    rd->chip_count = chip_count;
    return PRODUCT_ERROR_SUCCESS;
}

#ifdef NOVELDA_STATIC_LIBS
signalflow_error_t signalflow_load_flow_ref_RadarDirect_CAPI_Host( signalflow_context_t* ctx, signalflow_ref_t flow_ref );
signalflow_error_t signalflow_load_flow_ref_specific( signalflow_context_t* ctx, signalflow_ref_t flow_ref )
{
    return signalflow_load_flow_ref_RadarDirect_CAPI_Host( ctx, flow_ref );
}
#endif // NOVELDA_STATIC_LIBS


novelda_product_error_t radar_direct_load_flow(radar_direct_context_t *rd)
{
    if( !rd ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( rd->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    flow_info_t flow_info;
    if( rd->playback_input_path ) {
        flow_info.flow_ref = 0x2C974E83; // RadarDirect_Playback_CAPI_Host
    } else if( rd->chip_count == 1 ) {
        flow_info.flow_ref = 648513283UL; // RadarDirect_CAPI_Host
    } else if( rd->chip_count == 2 ) {
        flow_info.flow_ref = 2450464466UL; // RadarDirect_DualChip_CAPI_Host
    } else {
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }

    novelda_product_error_t result = platform_load_flow(rd->sf, &flow_info);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        return result;
    }
    rd->loaded = true;

#ifdef NOVELDA_FILESYSTEM_CAPABILITY
    // Apply post load parameters
    return radar_direct_configure_file_input(rd);
#else
    VALIDATE_PRODUCT_CONFIGURATION(radar_direct_configure_file_output_enabled(rd, 0), PRODUCT_ERROR_FILE_ERROR);
    return PRODUCT_ERROR_SUCCESS;
#endif // NOVELDA_FILESYSTEM_CAPABILITY
}

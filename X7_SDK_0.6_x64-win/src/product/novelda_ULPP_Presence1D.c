#include "novelda_ULPP_Presence1D.h"

#include "novelda_platform.h"

#include <stdbool.h> // for bool
#include <stdlib.h> // for malloc, free
#include <string.h> // for strlen

#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))

// Section [public]
const uint32_t PUBLIC_SECTION_ID = 0xCC909380UL; // "public"
const uint32_t DETECTION_ZONE = 0x5287C15AUL; // "DetectionZone"
const uint32_t CONFIDENCE_VALUES = 0x8CB328D7UL; // "ConfidenceValues"
const uint32_t NUM_MFRAMES_PER_PULSE = 0x1AFE105AUL; // "MframesPerPulse"
const uint32_t THRESHOLD_LEVEL_ADJUSTMENT_LINEAR = 0x5E58BD9FUL; // "ThresholdLevelAdjustment_Linear"
const uint32_t SEND_OUTPUT_ON_PRESENCE_CHANGE_ONLY = 0x6D09B668UL; // "SendOutputOnPresenceChangeOnly"
const uint32_t MODE_ID = 0x534E7732UL; // "Mode"
const uint32_t MODE_LOWPOWER_ID = 0x10030FA2UL; // "LowPower"
const uint32_t MODE_NORMAL_ID = 0x58DE2772UL; // "Normal"

// Section [ConnectionParameters]
const uint32_t CONNECTION_PARAMETERS_SECTION_ID = 0x603411BDUL; // "ConnectionParameters"
const uint32_t STREAMING_TIMEOUT_ID = 0x9E0C9FC3UL; // "StreamingTimeout_ms"
const uint32_t BREAK_TIMEOUT_ID = 0x1C408CB0UL; // "BreakTimeout_ms"

struct ulpp_context
{
    signalflow_context_t *sf;
    bool loaded;
};

ulpp_context_t *ulpp_create(signalflow_context_t *sf)
{
    if( !sf ) {
        return NULL;
    }
    ulpp_context_t *ctx = (ulpp_context_t *)malloc(sizeof(ulpp_context_t));
    if( !ctx ) {
        return NULL;
    }
    ctx->sf = sf;
    ctx->loaded = false;
    return ctx;
}

novelda_product_error_t ulpp_delete(ulpp_context_t *ulpp)
{
    if( !ulpp ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    signalflow_error_t signalflow_delete_result = signalflow_delete(ulpp->sf);
    ulpp->sf = NULL;

    free(ulpp);
    ulpp = NULL;

    VALIDATE_PRODUCT_CONFIGURATION(signalflow_delete_result, PRODUCT_ERROR_FAILURE);
    return PRODUCT_ERROR_SUCCESS;
}

novelda_product_error_t ulpp_set_ulpp_config(ulpp_context_t *ulpp, ulpp_config_t *config)
{
    if( !ulpp ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( !ulpp->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(
            ulpp->sf,
            0,
            PUBLIC_SECTION_ID,
            DETECTION_ZONE,
            SF_DATATYPE_FLOAT,
            NULL,
            0,
            (uint8_t *)config->detection_zone,
            ARRAY_SIZE(config->detection_zone)),
        PRODUCT_ERROR_DETECTION_ZONE);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(
            ulpp->sf,
            0,
            PUBLIC_SECTION_ID,
            CONFIDENCE_VALUES,
            SF_DATATYPE_INT32,
            NULL,
            0,
            (uint8_t *)config->confidence_values,
            ARRAY_SIZE(config->confidence_values)),
        PRODUCT_ERROR_CONFIDENCE_VALUES);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(
            ulpp->sf,
            0,
            PUBLIC_SECTION_ID,
            NUM_MFRAMES_PER_PULSE,
            SF_DATATYPE_INT32,
            NULL,
            0,
            (uint8_t *)&config->num_mframes_per_pulse,
            1),
        PRODUCT_ERROR_MAX_NUM_DETECTIONS);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(
            ulpp->sf,
            0,
            PUBLIC_SECTION_ID,
            THRESHOLD_LEVEL_ADJUSTMENT_LINEAR,
            SF_DATATYPE_FLOAT,
            NULL,
            0,
            (uint8_t *)&config->threshold_level_adjustment_linear,
            1),
        PRODUCT_ERROR_THRESHOLD_LEVEL_ADJUSTMENT_DB);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(
            ulpp->sf,
            0,
            PUBLIC_SECTION_ID,
            SEND_OUTPUT_ON_PRESENCE_CHANGE_ONLY,
            SF_DATATYPE_BOOL,
            NULL,
            0,
            (uint8_t *)&config->send_output_on_presence_change_only,
            1),
        PRODUCT_ERROR_FAILURE);

    const uint32_t mode = config->low_power_mode ? MODE_LOWPOWER_ID : MODE_NORMAL_ID;
    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(
            ulpp->sf,
            0,
            PUBLIC_SECTION_ID,
            MODE_ID,
            SF_DATATYPE_UINT32,
            NULL,
            0,
            (uint8_t *)&mode,
            1),
        PRODUCT_ERROR_MODE);

    if( config->send_output_on_presence_change_only ) {
        // If we reduce the output to only happen on state changes we need to
        // adjust the ServiceSource StreamingTimeout to 0 to avoid timeouts
        // when waiting for data.
        uint32_t timeout = 0;
        VALIDATE_PRODUCT_CONFIGURATION(
            signalflow_set_parameter_array(
                ulpp->sf,
                0,
                CONNECTION_PARAMETERS_SECTION_ID,
                STREAMING_TIMEOUT_ID,
                SF_DATATYPE_INT32,
                NULL,
                0,
                (uint8_t *)&timeout,
                1),
            PRODUCT_ERROR_STREAMING_TIMEOUT);

        // This adjust the timeout for breaking out of the flow processing
        // such that the cancellation handler can be called. This is thus
        // the maximum time in ms to wait between each call to cancel_flow.
        timeout = 1000;
        VALIDATE_PRODUCT_CONFIGURATION(
            signalflow_set_parameter_array(
                ulpp->sf,
                0,
                CONNECTION_PARAMETERS_SECTION_ID,
                BREAK_TIMEOUT_ID,
                SF_DATATYPE_INT32,
                NULL,
                0,
                (uint8_t *)&timeout,
                1),
            PRODUCT_ERROR_STREAMING_TIMEOUT);
    }

    return PRODUCT_ERROR_SUCCESS;
}

novelda_product_error_t ulpp_set_spi_speed(ulpp_context_t *ulpp, int32_t spi_speed)
{
    if( !ulpp ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( !ulpp->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    const uint32_t SPI_SPEED_ID = 0x4EF172F8UL; // "SpiSpeed"

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(ulpp->sf, 0, CONNECTION_PARAMETERS_SECTION_ID, SPI_SPEED_ID, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&spi_speed, 1),
        PRODUCT_ERROR_FAILURE);

    return PRODUCT_ERROR_SUCCESS;
}

const uint32_t FILESINK_PARAMETERS_SECTION_ID = 2156828940UL; // "fileSink"
const uint32_t FILESINK_ENABLED = 2626085950UL; // "Enabled"

static novelda_product_error_t ulpp_configure_file_output_enabled(ulpp_context_t *ulpp, uint8_t enabled)
{
    if( !ulpp ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    if( !ulpp->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(ulpp->sf, 0, FILESINK_PARAMETERS_SECTION_ID, FILESINK_ENABLED, SF_DATATYPE_BOOL, NULL, 0, &enabled, 1),
        PRODUCT_ERROR_FILE_ERROR);

    return PRODUCT_ERROR_SUCCESS;
}

#ifdef NOVELDA_FILESYSTEM_CAPABILITY
const uint32_t FILESINK_PATH = 3949388886UL; // "Path"

novelda_product_error_t ulpp_configure_file_output(ulpp_context_t *ulpp, const char *output_path)
{
    if( !ulpp ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( !ulpp->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    const uint8_t enable = output_path != NULL ? 1 : 0;
    VALIDATE_PRODUCT_CONFIGURATION(ulpp_configure_file_output_enabled(ulpp, enable), PRODUCT_ERROR_FILE_ERROR);
    if( enable ) {
        VALIDATE_PRODUCT_CONFIGURATION(
            signalflow_set_parameter_array(ulpp->sf, 0, FILESINK_PARAMETERS_SECTION_ID, FILESINK_PATH, SF_DATATYPE_STRING, NULL, 0, (uint8_t *)output_path, strlen(output_path)),
            PRODUCT_ERROR_FILE_ERROR);
    }
    return PRODUCT_ERROR_SUCCESS;
}
#endif // NOVELDA_FILESYTEM_CAPABILITY

// Signal and Array semantics for signalflow_get_frame_array()
const uint32_t SIGNAL_SEMANTIC_HUMAN_PRESENCE = 0xFA107E6EUL; // "human_presence"
const uint32_t ARRAY_SEMANTIC_HUMAN_PRESENCE = 0xB1533373UL; // "human_presence_basic"
const uint32_t ARRAY_SEMANTIC_DETECTION_1D = 0x9D5BDDA4UL; // "detection_1d"
const uint32_t ARRAY_SEMANTIC_POWER_PER_BIN = 0xD0B6792EUL; // "PowerPerBin"

signalflow_error_t ulpp_read_human_presence(ulpp_context_t *ulpp, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal)
{
    UNUSED(ulpp);
    return read_signal(data_buffer, data_buffer_size, SIGNAL_SEMANTIC_HUMAN_PRESENCE, ARRAY_SEMANTIC_HUMAN_PRESENCE, signal);
}

signalflow_error_t ulpp_read_detection_1d(ulpp_context_t *ulpp, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal)
{
    UNUSED(ulpp);
    return read_signal(data_buffer, data_buffer_size, SIGNAL_SEMANTIC_HUMAN_PRESENCE, ARRAY_SEMANTIC_DETECTION_1D, signal);
}

signalflow_error_t ulpp_read_power_per_bin(ulpp_context_t *ulpp, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal)
{
    UNUSED(ulpp);
    return read_signal(data_buffer, data_buffer_size, SIGNAL_SEMANTIC_HUMAN_PRESENCE, ARRAY_SEMANTIC_POWER_PER_BIN, signal);
}

#ifdef NOVELDA_STATIC_LIBS
signalflow_error_t signalflow_load_flow_ref_ULPP_Presence1D_CAPI_Host(signalflow_context_t *ctx, signalflow_ref_t flow_ref);
signalflow_error_t signalflow_load_flow_ref_specific(signalflow_context_t *ctx, signalflow_ref_t flow_ref)
{
    return signalflow_load_flow_ref_ULPP_Presence1D_CAPI_Host(ctx, flow_ref);
}
#endif // NOVELDA_STATIC_LIBS

novelda_product_error_t ulpp_load_flow(ulpp_context_t *ulpp)
{
    if( !ulpp ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    flow_info_t flow_info = {
        .flow_ref = 0x3966A990UL // ULPP_Presence1D_CAPI_Host
    };

    novelda_product_error_t result = platform_load_flow(ulpp->sf, &flow_info);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        return result;
    }
    ulpp->loaded = true;

#ifndef NOVELDA_FILESYSTEM_CAPABILITY
    VALIDATE_PRODUCT_CONFIGURATION(ulpp_configure_file_output_enabled(ulpp, 0), PRODUCT_ERROR_FILE_ERROR);
    return PRODUCT_ERROR_SUCCESS;
#endif // NOVELDA_FILESYSTEM_CAPABILITY

    return PRODUCT_ERROR_SUCCESS;
}
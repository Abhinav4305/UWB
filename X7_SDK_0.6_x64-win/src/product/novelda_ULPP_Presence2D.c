#include "novelda_ULPP_Presence2D.h"

#include "novelda_platform.h"

#include <stdbool.h> // for bool
#include <stdlib.h> // for malloc, free
#include <string.h> // for strlen

// Section [public]
const uint32_t PUBLIC_SECTION_ID = 3432027008UL; // "public"
const uint32_t DETECTION_ZONE_XY_POINTS = 2154239902UL; // "DetectionZoneXYPoints"
const uint32_t CONFIDENCE_VALUES = 2360551639UL; // "ConfidenceValues"
const uint32_t THRESHOLD_LEVEL_ADJUSTMENT_LINEAR = 0x5E58BD9FUL; // "ThresholdLevelAdjustment_Linear"
const uint32_t MAX_NUM_DETECTIONS = 1414105503UL; // "MaxNumDetections"
const uint32_t MAX_NUM_HUMAN_DETECTION_2D_OUTPUTS = 2544629713UL; // "MaxNumHumanDetection2DOutputs"

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
        signalflow_set_parameter_array(ulpp->sf, 0, PUBLIC_SECTION_ID, DETECTION_ZONE_XY_POINTS, SF_DATATYPE_FLOAT, NULL, 0, (uint8_t *)config->detection_zone_xy_points, config->detection_zone_xy_points_length),
        PRODUCT_ERROR_DETECTION_ZONE_XY_POINTS);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(ulpp->sf, 0, PUBLIC_SECTION_ID, THRESHOLD_LEVEL_ADJUSTMENT_LINEAR, SF_DATATYPE_FLOAT, NULL, 0, (uint8_t *)&config->threshold_level_adjustment_linear, 1),
        PRODUCT_ERROR_THRESHOLD_LEVEL_ADJUSTMENT_DB);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(ulpp->sf, 0, PUBLIC_SECTION_ID, CONFIDENCE_VALUES, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)config->confidence_values, 4),
        PRODUCT_ERROR_CONFIDENCE_VALUES);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(ulpp->sf, 0, PUBLIC_SECTION_ID, MAX_NUM_DETECTIONS, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&config->max_num_detections, 1),
        PRODUCT_ERROR_MAX_NUM_DETECTIONS);

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(ulpp->sf, 0, PUBLIC_SECTION_ID, MAX_NUM_HUMAN_DETECTION_2D_OUTPUTS, SF_DATATYPE_INT32, NULL, 0, (uint8_t *)&config->max_num_human_detection_2d_outputs, 1),
        PRODUCT_ERROR_MAX_NUM_HUMAN_DETECTION_2D_OUTPUTS);

    return PRODUCT_ERROR_SUCCESS;
}

// Section [Detector2D]
const uint32_t DETECTOR2D_SECTION_ID = 1319041273UL; // "Detector2D"
const uint32_t ELEMENT_DISTANCE = 2097001904UL; // "ElementDistance"

novelda_product_error_t ulpp_set_x7t02_module(ulpp_context_t *ulpp)
{
    if( !ulpp ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    if( !ulpp->loaded ) {
        return PRODUCT_ERROR_FAILURE;
    }

    const float x7t02_element_distance = 0.0205f;

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_set_parameter_array(ulpp->sf, 0, DETECTOR2D_SECTION_ID, ELEMENT_DISTANCE, SF_DATATYPE_FLOAT, NULL, 0, (uint8_t *)&x7t02_element_distance, 1),
        PRODUCT_ERROR_ELEMENT_DISTANCE);

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
    const uint32_t CONNECTION_PARAMETERS_SECTION_ID = 0x603411BDUL; // "ConnectionParameters"

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
const uint32_t SIGNAL_SEMANTIC_HUMAN_PRESENCE = 4195384942UL; // "human_presence"
const uint32_t ARRAY_SEMANTIC_HUMAN_PRESENCE_2D = 738115132UL; // "human_presence_2d_basic"
const uint32_t ARRAY_SEMANTIC_HUMAN_DETECTION_2D_FLOAT32 = 1716047956UL; // "human_detection_2d_float"

signalflow_error_t ulpp_read_human_presence(ulpp_context_t *ulpp, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal)
{
    UNUSED(ulpp);
    const uint32_t signal_semantic = SIGNAL_SEMANTIC_HUMAN_PRESENCE;
    const uint32_t array_semantic = ARRAY_SEMANTIC_HUMAN_PRESENCE_2D;
    return read_signal(data_buffer, data_buffer_size, signal_semantic, array_semantic, signal);
}

signalflow_error_t ulpp_read_human_detection(ulpp_context_t *ulpp, const uint8_t *data_buffer, size_t data_buffer_size, signal_info_t *signal)
{
    UNUSED(ulpp);
    const uint32_t signal_semantic = SIGNAL_SEMANTIC_HUMAN_PRESENCE;
    const uint32_t array_semantic = ARRAY_SEMANTIC_HUMAN_DETECTION_2D_FLOAT32;
    return read_signal(data_buffer, data_buffer_size, signal_semantic, array_semantic, signal);
}

#ifdef NOVELDA_STATIC_LIBS
signalflow_error_t signalflow_load_flow_ref_ULPP_Presence2D_CAPI_Host( signalflow_context_t* ctx, signalflow_ref_t flow_ref );
signalflow_error_t signalflow_load_flow_ref_specific(signalflow_context_t* ctx, signalflow_ref_t flow_ref)
{
    return signalflow_load_flow_ref_ULPP_Presence2D_CAPI_Host(ctx, flow_ref);
}
#endif // NOVELDA_STATIC_LIBS


novelda_product_error_t ulpp_load_flow(ulpp_context_t *ulpp)
{
    if( !ulpp ) {
        return PRODUCT_ERROR_NULLPTR;
    }
    flow_info_t flow_info = {
        .flow_ref = 4062059279UL // ULPP_Presence2D_CAPI_Host
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
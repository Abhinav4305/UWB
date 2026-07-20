#include "novelda_signalflow.h"
#include "novelda_platform.h"
#include "novelda_product.h"
#include "novelda_ULPP_Presence1D.h"

#include <inttypes.h>
#include <stdio.h>

// Host application callback to log message from the flow.
static void log_flow_message(void *host_context, uint32_t level, const char *message)
{
    UNUSED(host_context);

    printf("LOG: %" PRIu32 ": %s", level, message);
}

// Host application callback to allow cancellation aka stopping of the flow.
static signalflow_runstate_t cancel_flow(void *host_context)
{
    UNUSED(host_context);
    return g_running ? SF_RUNSTATE_RUN : SF_RUNSTATE_CANCEL;
}

// Host application callback to process output from the flow.
static signalflow_error_t ulpp_process_output(void *host_context, uint32_t node_name, const uint8_t *buffer, size_t buffer_size)
{
    UNUSED(node_name);

    ulpp_context_t *ulpp = (ulpp_context_t *)host_context;
    signal_info_t data;

    signalflow_error_t result = ulpp_read_human_presence(ulpp, buffer, buffer_size, &data);
    if( result != SFERR_SUCCESS ) {
        printf("Failed to read human presence: %" PRId32 "\n", result);
        return result;
    }

    signalflow_frame_info_t frame_info;
    result = signalflow_get_frame_info(buffer, buffer_size, &frame_info);
    if( result != SFERR_SUCCESS ) {
        printf("Failed to get frame info\n");
        return result;
    }

    if( data.datatype != SF_DATATYPE_INT32 ) {
        printf("Unexpected data type: %" PRIu16 "\n", data.datatype);
        return PRODUCT_ERROR_FAILURE;
    }

    printf("Sequence number: %" PRIu32 " Timestamp: %" PRIu64 " Data: [ ", frame_info.sequence_number, frame_info.timestamp);
    if( data.array_element_count > 0 ) {
        // Note the fifth element is currently not in use and thus not printed
        printf("Presence: %01d, Range (cm): %03d, Confidence: %03d, Signal power: %03d",
               ((int32_t *)data.array)[0],
               ((int32_t *)data.array)[1],
               ((int32_t *)data.array)[2],
               ((int32_t *)data.array)[3]);
    }
    printf(" ]\n");

    static state_info_t was_presence = STATE_NO_PRESENCE;
    state_info_t presence = ( ((int16_t *)data.array)[0] & 0x01 ) ? STATE_PRESENCE : STATE_NO_PRESENCE;
    if (was_presence != presence) {
        platform_state_toggle(presence);
        was_presence = presence;
    }

    //    result = ulpp_read_detection_1d(ulpp, buffer, buffer_size, &data);
    //    printf("  Detection 1D raw data: [ ");
    //    for( size_t i = 0; i < data.array_element_count; i++ ) {
    //        printf("%.2f ", ((float *)data.array)[i]);
    //    }
    //    printf("]\n");
    //
    //    result = ulpp_read_power_per_bin(ulpp, buffer, buffer_size, &data);
    //    printf("  Power per bin raw data: [ ");
    //    for( size_t i = 0; i < data.array_element_count; i++ ) {
    //        printf("%.2f ", ((float *)data.array)[i]);
    //    }
    //    printf("]\n");

    return SFERR_SUCCESS;
}

static novelda_product_error_t ulpp_configure(ulpp_context_t *ulpp, int argc, char *argv[])
{
    novelda_product_error_t result = ulpp_load_flow(ulpp);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to load flow: %" PRId32 "\n", result);
        return result;
    }

    // Define the ULPP configuration
    ulpp_config_t ulpp_config = {
        .detection_zone = { 0.5, 2.0 },
        .confidence_values = { 30, 80, 75, 25 },
        .num_mframes_per_pulse = 3,
        .threshold_level_adjustment_linear = 1.0f,
        .low_power_mode = true,
        .send_output_on_presence_change_only = true
    };

    // Set the ULPP configuration
    result = ulpp_set_ulpp_config(ulpp, &ulpp_config);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to set ULPP configuration: %" PRId32 "\n", result);
        return result;
    }

    result = ulpp_set_spi_speed(ulpp, 16000000);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to set SPI speed: %" PRId32 "\n", result);
        return result;
    }

#ifdef NOVELDA_FILESYSTEM_CAPABILITY
    if( argc > 2 ) {
        fprintf(stderr, "Too many arguments provided\n");
        fprintf(stderr, "Usage: %s <optional_output_file_path>\n", argv[0]);
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }

    const char *output_path = argc > 1 ? argv[1] : NULL;
    result = ulpp_configure_file_output(ulpp, output_path);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to configure file output: %" PRId32 "\n", result);
        return result;
    }
#endif // NOVELDA_FILESYSTEM_CAPABILITY

    return PRODUCT_ERROR_SUCCESS;
}

int main(int argc, char *argv[])
{
    platform_configure();

    platform_add_signal_handlers();

    // Configure logger function
    signalflow_set_logger(log_flow_message, NULL);

    // Create the SignalFlow instance
    signalflow_context_t *sf = signalflow_create(NULL, 0);

    // Create the ULPP context
    ulpp_context_t *ulpp = ulpp_create(sf);
    if( !ulpp ) {
        printf("Failed to create ULPP context\n");
        signalflow_delete(sf);
        return SFERR_FAILURE;
    }

    // Setup the host services (callbacks) for the flow
    signalflow_host_services_t host_svc = {
        ulpp_process_output,
        NULL
    };

    signalflow_error_t sf_result = signalflow_set_host_services(sf, &host_svc, ulpp);
    if( sf_result != SFERR_SUCCESS ) {
        printf("Failed to set host services: %" PRId32 "\n", sf_result);
        ulpp_delete(ulpp);
        return sf_result;
    }

    novelda_product_error_t product_result = ulpp_configure(ulpp, argc, argv);
    if( product_result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to configure product: %" PRId32 "\n", product_result);
        ulpp_delete(ulpp);
        return product_result;
    }

    // Run the flow until cancel_flow() returns SF_RUNSTATE_CANCEL
    signalflow_run(sf, cancel_flow, NULL);

    // Cleanup after the flow
    ulpp_delete(ulpp);

    signalflow_set_logger(NULL, NULL);

    return 0;
}

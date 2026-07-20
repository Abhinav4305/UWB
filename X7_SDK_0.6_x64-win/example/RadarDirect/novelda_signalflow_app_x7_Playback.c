#include "novelda_signalflow.h"
#include "novelda_platform.h"
#include "novelda_product.h"
#include "novelda_RadarDirect.h"

#include <inttypes.h>
#include <stdio.h>

#ifndef NOVELDA_FILESYSTEM_CAPABILITY
#error "Example makes no sense without filesystem capability"
#endif // NOVELDA_FILESYSTEM_CAPABILITY

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
static signalflow_error_t radar_direct_process_output(void *host_context, uint32_t node_name, const uint8_t *buffer, size_t buffer_size)
{
    UNUSED(node_name);

    radar_direct_context_t *rd = (radar_direct_context_t *)host_context;

    // To reduce console output, only print every 101th frame
    static int frame_count = 0;
    int print = frame_count++ % 101 == 0;

    if( print ) {
        printf("Got output of size: %zu bytes\n", buffer_size);
    }

    signal_info_t data;

    signalflow_error_t result = radar_direct_read_radar_frame(rd, buffer, buffer_size, &data);
    if( result != SFERR_SUCCESS ) {
        printf("Failed to read radar frame: %" PRId32 "\n", result);
        return result;
    }
    if( data.datatype != SF_DATATYPE_FLOAT ) {
        printf("Unexpected data type for radar frame\n");
        return SFERR_INVALID_ARGUMENT;
    }

    // Example of how to access the radar data
    // Baseband non-interleaved IQ data for RX0 and RX1
    // Format per RX: [I0, I1, ..., IN, Q0, Q1, ..., QN]
    const float *iqmat_Rx0 = (float *)(data.array);
    const float *iqmat_Rx1 = iqmat_Rx0 + (data.array_element_count / 2);
    UNUSED(iqmat_Rx0);
    UNUSED(iqmat_Rx1);
    //
    //    Insert your signal processing code here
    //
    //    Note that this function is called from the
    //    scheduler for each signal frame and is time critical i.e. no time-consuming
    //    operations can be done here, instead, use a separate thread or similar.
    //    Also note that the data pointers are only valid for the duration of the call,
    //    so any data that is needed for later processing must be copied and stored in
    //    a separate buffer.

    result = radar_direct_read_trx_mask(rd, buffer, buffer_size, &data);
    if( result != SFERR_SUCCESS ) {
        printf("Failed to read TRX mask: %" PRId32 "\n", result);
        return result;
    }
    // The format of the trx mask is as follows:
    // [ChipNumber, TxChannelActive, RxMask]
    if( data.datatype != SF_DATATYPE_UINT16 ) {
        printf("Unexpected data type for TRX mask\n");
        return SFERR_INVALID_ARGUMENT;
    }
    if( print ) {
        printf("    [ ");
    }
    for( size_t i = 0; i < data.array_element_count; i++ ) {
        if( print ) {
            printf("0x%02X ", ((uint16_t *)data.array)[i]);
        }
    }
    if( print ) {
        printf("]\n");
    }

    signalflow_frame_info_t frame_info;
    result = signalflow_get_frame_info(buffer, buffer_size, &frame_info);
    if( result != SFERR_SUCCESS ) {
        printf("Failed to get frame info\n");
    } else {
        if( print ) {
            printf("  Frame info: sequence_number=%" PRIu32 " timestamp=%" PRIu64 "\n", frame_info.sequence_number, frame_info.timestamp);
        }
    }

    return SFERR_SUCCESS;
}

static novelda_product_error_t radar_direct_configure(radar_direct_context_t *rd, int argc, char *argv[])
{
    if( argc < 2 ) {
        fprintf(stderr, "ERROR: Missing argument\n");
        fprintf(stderr, "Usage: %s <playback_file_path> <optional_output_file_path>\n", argv[0]);
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }
    if( argc > 3 ) {
        fprintf(stderr, "Too many arguments provided\n");
        fprintf(stderr, "Usage: %s <playback_file_path> <optional_output_file_path>\n", argv[0]);
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }

    novelda_product_error_t result = radar_direct_set_file_input(rd, argv[1]);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to set file input: %" PRId32 "\n", result);
        return result;
    }

    result = radar_direct_load_flow(rd);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to load flow: %" PRId32 "\n", result);
        return result;
    }

    result = radar_direct_set_spi_speed(rd, 16000000);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to set SPI speed: %" PRId32 "\n", result);
        return result;
    }

    const char *output_path = argc > 2 ? argv[2] : NULL;
    result = radar_direct_configure_file_output(rd, output_path);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to configure file output: %" PRId32 "\n", result);
        return result;
    }

    return PRODUCT_ERROR_SUCCESS;
}

int main(int argc, char *argv[])
{
    platform_add_signal_handlers();

    // Configure logger function
    signalflow_set_logger(log_flow_message, NULL);

    // Create the SignalFlow instance
    signalflow_context_t *sf = signalflow_create(NULL, 0);

    radar_direct_context_t *rd = radar_direct_create(sf);
    if( !rd ) {
        printf("Failed to create radar direct context\n");
        signalflow_delete(sf);
        return PRODUCT_ERROR_FAILURE;
    }

    // Setup the host services (callbacks) for the flow
    signalflow_host_services_t host_svc = {
        radar_direct_process_output,
        NULL
    };

    signalflow_error_t sf_result = signalflow_set_host_services(sf, &host_svc, rd);
    if( sf_result != SFERR_SUCCESS ) {
        printf("Failed to set host services: %" PRId32 "\n", sf_result);
        radar_direct_delete(rd);
        return sf_result;
    }

    novelda_product_error_t product_result = radar_direct_configure(rd, argc, argv);
    if( product_result != PRODUCT_ERROR_SUCCESS ) {
        printf("Failed to configure product: %" PRId32 "\n", product_result);
        radar_direct_delete(rd);
        return product_result;
    }

    // Run the flow until cancel_flow() returns SF_RUNSTATE_CANCEL
    signalflow_run(sf, cancel_flow, NULL);

    // Cleanup after the flow
    radar_direct_delete(rd);

    signalflow_set_logger(NULL, NULL);

    return 0;
}

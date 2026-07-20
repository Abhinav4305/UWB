#include "novelda_platform.h"
#include "novelda_platform_generic.h"

novelda_product_error_t platform_load_flow(signalflow_context_t *sf, const flow_info_t *flow_info)
{
    if( !flow_info ) {
        return PRODUCT_ERROR_NULLPTR;
    }

    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_load_flow_ref(sf, flow_info->flow_ref),
        PRODUCT_ERROR_INVALID_FLOW_REF);

    novelda_product_error_t result = set_firmware_paths(sf, 0, 1);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        return result;
    }

    // Get and set the IO configuration
    io_config_t io_config;
    result = get_io_config(0, 1, &io_config);
    if( result != PRODUCT_ERROR_SUCCESS ) {
        return result;
    }

    return set_io_config(sf, &io_config);
}
novelda_product_error_t platform_configure()
{
    // Not implemented for now
    return PRODUCT_ERROR_SUCCESS;
}

void platform_state_toggle(state_info_t state_info) 
{
    // Not implemented for now
    UNUSED(state_info);
}
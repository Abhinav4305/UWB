#include "novelda_platform.h"

novelda_product_error_t platform_load_flow(signalflow_context_t *sf, const flow_info_t *flow_info)
{
    VALIDATE_PRODUCT_CONFIGURATION(
        signalflow_load_flow_ref(sf, flow_info->flow_ref),
        PRODUCT_ERROR_INVALID_FLOW_REF);

    return PRODUCT_ERROR_SUCCESS;
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
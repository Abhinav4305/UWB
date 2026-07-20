#ifndef NOVELDA_PLATFORM_H
#define NOVELDA_PLATFORM_H

#include "novelda_signalflow.h"
#include "novelda_product.h"
#include <inttypes.h>
#include <signal.h>

/**
 * Flow information for the platform.
 *
 * This struct is used to identify the correct flow for the product on
 * the platform.
 */
typedef struct
{
    signalflow_ref_t flow_ref; /**< Value provided by Novelda in the example implementation */
} flow_info_t;

typedef enum
{
    STATE_NO_PRESENCE = 0,
    STATE_PRESENCE = 1
} state_info_t;

/**
 * Load flow depending on the platform support.
 */
novelda_product_error_t platform_load_flow(signalflow_context_t *sf, const flow_info_t *flow_info);

/**
 * Signal handler for termination signals like SIGINT and SIGTERM.
 */
extern volatile sig_atomic_t g_running;

/**
 * Optional - but ensures that g_running is set to 0 when the application is gracefully terminated.
 */
void platform_add_signal_handlers();

/**
 * Optional - used for platform dependent configuration.
 */
novelda_product_error_t platform_configure();

/**
 * Optional - used for notification of state. ex. LED
 */
void platform_state_toggle(state_info_t state_info);

#endif // NOVELDA_PLATFORM_H

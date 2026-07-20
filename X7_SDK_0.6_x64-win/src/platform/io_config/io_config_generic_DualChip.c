#include "novelda_platform_generic.h"

novelda_product_error_t get_io_config(int chip_number, int chip_count, io_config_t *config)
{
    if( config == NULL ) {
        return PRODUCT_ERROR_NULLPTR;
    }

#ifdef NOVELDA_CHIPINTERFACE_FT4222

    if( chip_count != 1 || chip_number != 0) {
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }

    config->host_interface_id = "0";

    return PRODUCT_ERROR_SUCCESS;
#else
    if( chip_count < 1 || chip_count > 2 ) {
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }

    if( chip_number == 0 ) {
        config->chip_number = chip_number;
        config->chip_count = chip_count;
        config->interface = "/dev/spidev0.0";
        config->gpio_host_enable = "gpiochip0:22";
        config->gpio_host_irq = "gpiochip0:27";
        config->gpio_chip_irq = 6;
    } else if( chip_number == 1 ) {
        config->chip_number = chip_number;
        config->chip_count = chip_count;
        config->interface = "/dev/spidev0.1";
        config->gpio_host_enable = GPIO_HOST_OFF;
        config->gpio_host_irq = "gpiochip0:15";
        config->gpio_chip_irq = 6;
    } else {
        return PRODUCT_ERROR_INVALID_ARGUMENT;
    }

    return PRODUCT_ERROR_SUCCESS;
#endif
}
#include "novelda_product.h"

signalflow_error_t read_signal(const uint8_t *data_buffer, size_t data_buffer_size, uint32_t signal_semantic, uint32_t array_semantic, signal_info_t *signal)
{
    return signalflow_get_frame_array(data_buffer, data_buffer_size, signal_semantic, array_semantic, &signal->datatype, &signal->shape, &signal->shape_size, &signal->array, &signal->array_element_count);
}

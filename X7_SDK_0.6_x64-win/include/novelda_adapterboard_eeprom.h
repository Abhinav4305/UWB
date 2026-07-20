#ifndef NOVELDA_ADAPTERBOARD_EEPROM_H
#define NOVELDA_ADAPTERBOARD_EEPROM_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifdef BUILDING_NOVELDA_ADAPTERBOARD_EEPROM
// When building a dynamic library
#ifdef _MSC_VER
#define ADAPTERBOARD_EEPROM_SYMBOL_EXPORT __declspec(dllexport)
#else // _MSC_VER
#define ADAPTERBOARD_EEPROM_SYMBOL_EXPORT __attribute__((visibility("default")))
#endif // _MSC_VER
#elif USING_NOVELDA_ADAPTERBOARD_EEPROM
// When using a dynamic library
#ifdef _MSC_VER
#define ADAPTERBOARD_EEPROM_SYMBOL_EXPORT __declspec(dllimport)
#else // _MSC_VER
#define ADAPTERBOARD_EEPROM_SYMBOL_EXPORT
#endif // _MSC_VER
#endif

typedef int8_t adapterboard_eeprom_error_t;

static const adapterboard_eeprom_error_t ADAPTERBOARD_EEPROM_SUCCESS = 0;
static const adapterboard_eeprom_error_t ADAPTERBOARD_EEPROM_FAILURE = -1;

static const uint32_t INVALID_IC_VERSION = 0xBADBADBA;
static const uint64_t INVALID_SAMPLE_ID = 0xBADBADBADBADBADB;

typedef enum adapterboard_eeprom_field
{
    EEPROM_SENSOR_MODULE_NAME,
    EEPROM_SENSOR_MODULE_REVISION,
    EEPROM_ADAPTER_BOARD_NAME,
    EEPROM_ADAPTER_BOARD_REVISION,
    EEPROM_WRITE_DATE,
    EEPROM_BOOT_MODE,
    EEPROM_FIELD_COUNT
} adapterboard_eeprom_field_t;

typedef struct
{
    const char* data;
    size_t size;
} calibration_data_t;

typedef struct
{
    char* eeprom_data[EEPROM_FIELD_COUNT];
    uint64_t sample_id;
    uint32_t ic_revision;
    uint64_t ft4222_interface_id;
} adapterboard_sensor_info_t;

typedef struct
{
    adapterboard_sensor_info_t *sensors;
    size_t num_sensors;
} adapterboard_sensors_info_t;

typedef struct adapterboard_eeprom_context adapterboard_eeprom_context_t;

ADAPTERBOARD_EEPROM_SYMBOL_EXPORT adapterboard_eeprom_context_t* adapterboard_eeprom_create();
ADAPTERBOARD_EEPROM_SYMBOL_EXPORT adapterboard_eeprom_context_t* adapterboard_eeprom_create_from_id(int location_id);

ADAPTERBOARD_EEPROM_SYMBOL_EXPORT adapterboard_eeprom_error_t adapterboard_eeprom_delete( adapterboard_eeprom_context_t* ctx );

ADAPTERBOARD_EEPROM_SYMBOL_EXPORT const char* adapterboard_eeprom_read( adapterboard_eeprom_context_t* ctx, adapterboard_eeprom_field_t field );

ADAPTERBOARD_EEPROM_SYMBOL_EXPORT calibration_data_t adapterboard_eeprom_read_calibration( adapterboard_eeprom_context_t* ctx );

ADAPTERBOARD_EEPROM_SYMBOL_EXPORT adapterboard_sensors_info_t* adapterboard_eeprom_get_connected_sensors();
ADAPTERBOARD_EEPROM_SYMBOL_EXPORT void adapterboard_eeprom_sensors_info_delete(adapterboard_sensors_info_t *sensors_info);

#ifdef __cplusplus
}
#endif

#endif // NOVELDA_ADAPTERBOARD_EEPROM_H

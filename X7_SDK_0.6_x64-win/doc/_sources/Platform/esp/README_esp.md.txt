# Novelda examples for ESP32S3

## Build instructions

1. Install ESP-IDF according to https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html
2. Launch and ESP-IDF shell
3. Unzip the novelda sdk archive
4. cd into one of the example folders such as examples/RadarDirect
5. Run:
    1. `idf.py -DCUSTOM_CHIPINTERFACE=ON set-target esp32s3`
    2. `idf.py build`

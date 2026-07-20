# Novelda examples for Nordic nRF52840DK / ESP32S3

The Novelda examples are made to be used with a Nordic nRF52840DK or a ESP32S3
with a X7-shield connected.  It can either be flashed directly to the board with
default settings or built with configured settings using zephyr. Both
alternatives are described in this file.

## Using pre-built example with default settings

A pre-built .hex-file is provided in one of the example folders. This can be
directly flashed to the Nordic nRF52840DK board for easy evaluation. The
pre-built file uses the default settings for the product. For information about
these settings please check the product description.

To flash the example to the Nordic board, use the following instructions
(for Windows):

* Connect the board with the X7 shield attached to the computer via a USB-cable.
  Make sure that the board is switched on.
* A File Explorer window should open automatically in the JLINK drive.
* Drag and drop the pre-built .hex-file into the JLINK File Explorer window.
* See the output with a serial terminal, see hardware specific steps below.

## Building the Novelda examples using Zephyr:

### Prerequisites

The following needs to be installed on the computer:

- Install [Zephyr version >=3.7.0](https://docs.zephyrproject.org/latest/develop/getting_started/index.html)
   - **Note**: After installing Chocolatey (for windows only), restart the
     computer to avoid problems with the next steps.

### Instructions

#### Nordic

1. Install Nordic prerequisites:
   - An ARM gcc >=13 compiler for the target board: [ARM gcc compiler](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
   - Install [nRF Util](https://www.nordicsemi.com/Products/Development-tools/nRF-Util) with 'nrf5sdk-tools' and 'device' components.
   - Install [nRF Util prerequisites](https://docs.nordicsemi.com/bundle/nrfutil/page/guides/installing.html) for your OS.
2. Set up the following environment variables:
   - `ZEPHYR_BASE`: Path to your Zephyr installation
     (could look like this in Windows cmd: `%USERPROFILE%\zephyrproject\zephyr`)
   - `ZEPHYR_TOOLCHAIN_VARIANT`: Set this to `gnuarmemb`.
   - `GNUARMEMB_TOOLCHAIN_PATH`: Path to the ARM compiler.
   - In Path: Add the folder containing nrfutil
3. Open a terminal and navigate into one of the example folders such as
   "example\ULPP_Presence2D" in the unpacked archive.
4. Run:
     `west build -b nrf52840dk/nrf52840 -- -DNOVELDA_FIRMWARE_HEADER=<path_to_firmware_header>`
   inside the example folder to build the example app. The CMake option
   `NOVELDA_FIRMWARE_HEADER` must point to the IC version for your hardware.
   e.g. "firmware_IC003.h" or "firmware_IC004.h".
5. Connect the Nordic nRF52840DK with the X7 Shield to the computer. Make sure
   that the board is switched on.
   - **Note**: The application does only work with the X7F202 sensor.
6. Run `west flash` to flash the app to the board.
7. See the console outout with a serial terminal to watch the application
   running. More info [here](https://infocenter.nordicsemi.com/index.jsp?topic=%2Fug_gsg_ses%2FUG%2Fgsg%2Fconnect_uart.html).

#### ESP32S3

1. Install the xtensa-espressif_esp32s3 compiler. Install the full version of the SDK from the
   [Zephyr SDK](https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/v0.16.8). Install the xtensa-espressif_esp32s3 compiler using:
   `setup.cmd /t xtensa-espressif_esp32s3_zephyr-elf` from inside the downloaded SDK.
2. Set up the following environment variables:
   - `ZEPHYR_BASE`: Path to your Zephyr installation
     (could look like this in Windows cmd: `%USERPROFILE%\zephyrproject\zephyr`)
   - `ZEPHYR_TOOLCHAIN_VARIANT`: Set this to `zephyr`.
   - `ESPRESSIF_TOOLCHAIN_PATH`: Path to the xtensa compiler.
      (could look like this in Windows cmd: %USERPROFILE%\zephyr-sdk-0.16.8\xtensa-espressif_esp32s3_zephyr-elf)
3. Open a terminal and navigate into one of the example folders such as
   "example\ULPP_Presence2D" in the unpacked archive.
4. Run:
     `west build -b esp32s3_devkitc/esp32s3/procpu -- -DNOVELDA_FIRMWARE_HEADER=<path_to_firmware_header>`
   inside the example folder to build the example app. The CMake option
   `NOVELDA_FIRMWARE_HEADER` must point to the IC version for your hardware.
   e.g. "firmware_IC003.h" or "firmware_IC004.h".
5. Connect the ESP32S3 with the X7 Shield to the computer. Make sure
   that the board is switched on.
   - **Note**: The application does only work with the X7F202 sensor.
6. Run `west flash` to flash the app to the board.
7. Run `west espressif monitor` to see the console output.

#### Porting to other boards

1. Check that the MCU is compatible with the pre-built libraries.
2. Create an overlay file for the new, zephyr supported, development board in
   the boards folder. Filename format: <boardname>_<zephyr_qualifiers>.overlay
   See: [set devicetree overlays](https://docs.zephyrproject.org/latest/build/dts/howtos.html#set-devicetree-overlays).
3. Define the following aliases for the nodes and pins you want to use for
   connections:
   ```
   novelda-radar-spi = &spi2;
   novelda-radar-en = &enable0;
   novelda-radar-cs = &cs0;
   novelda-radar-irq = &irq0;
   ```

4. Select the board when building. e.g.
   `west build -b <boardname>\<zephyr\qualifiers>`

### Custom chipinterface

By default the provided novelda_chipinterface_zephyr.c is used.

If you need your own custom implementation you can look at
the header novelda_chipinterface.h and the novelda_chipinterface_stub.c
and replace the stubs with your own implementation.

You can build with the custom stub implementation instead of the default one with:

```
west build -b <board> -- -DCUSTOM_CHIPINTERFACE=ON
```

or point to a specific implementation using:

```
west build -b <board> -- -DCUSTOM_CHIPINTERFACE=ON -DCUSTOM_CHIPINTERFACE_SRC="/path/to/implementation.c"
```
### Regulatory test app for Nordic

Regulatory test app is available in example/RadarDirect/. Follow the Instruction/Nordic above.

At build (step 5), run `west build -b nrf52840dk/nrf52840 -- -DNOVELDA_FIRMWARE_HEADER=<path_to_firmware_header> -DPRODUCT_VARIANT=Regulatory` instead.

The app switch different regulatory test modes by button and led indicates selected mode.
Open UART terminal (ex. Putty) with speed 115200.

When the application is programmed, the sensor starts in `Normal Operation` mode.

#### Regulatory test modes

|  Test Mode                |  LED1         |  LED2                                                                         |
| ------------------------- | ------------- | ----------------------------------------------------------------------------- |
| `Normal Operation`        |  ON           | ON: sensor is running, OFF: sensor is not running, Blink: sensor doesn't stop |
| `Tx`                      |  Blink-1      | ON: sensor is running, OFF: sensor is not running, Blink: sensor doesn't stop |
| `Tx Digital`              |  Blink-2      | ON: sensor is running, OFF: sensor is not running, Blink: sensor doesn't stop |
| `Normal Operation, Tx off`|  Blink-3      | ON: sensor is running, OFF: sensor is not running, Blink: sensor doesn't stop |
| `FCC 10 second rule test` |  Blink-4      | ON: sensor is running, OFF: sensor is not running, Blink: sensor doesn't stop |

#### *BUTTON1* button
*BUTTON1* toggles modes. LED1 shows selected mode by blink. Sensor doesn't start until pushing BUTTON2.
It stops sensor if sensor is running, then LED2 turns OFF. If the app cannot stop sensor, then LED2 blinks.

`Normal Operation` -> `Tx` -> `Tx Digital` -> `Normal Operation, Tx off` -> `FCC 10 second rule test` -> `Normal Operation` -> ...

#### *BUTTON2* button
*BUTTON2* starts sensor. LED2 turns ON when sensor is running.

#### *BUTTON3* button
*BUTTON3* only available on `FCC 10 second rule test` mode and sensor is running.
*BUTTON3* toggles between receiver fault (rx_counter_lsb = 45) test phase and detection phase (rx_counter_lsb = 9).

#### *RESET* button
*RESET* resets system. It can be used when LED2 blinks (sensor doesn't stop).

The application should output something like:

    *** Booting Zephyr OS build vX.X.X ***
    Start "Normal Operation" mode. Press Button-1 to toggle mode.
    [Button-1] Stop Sensor.
    Selected "Tx" mode. Press Button-2 to start sensor or Button-1 to toggle mode.
    [Button-2] Start Sensor.
    [Button-1] Stop Sensor.
    Selected "Tx Digital" mode. Press Button-2 to start sensor or Button-1 to toggle mode.
    [Button-2] Start Sensor.
    [Button-1] Stop Sensor.
    Selected "Normal Operation Tx off" mode. Press Button-2 to start sensor or Button-1 to toggle mode.
    [Button-2] Start Sensor.
    [Button-1] Stop Sensor.
    Selected "FCC 10 second rule" mode. Press Button-2 to start sensor or Button-1 to toggle mode.
    [Button-2] Start Sensor with Tx Power 3.
    [Button-3] Tx Power= 0. Press Button-3 to toggle Tx Power or Button-1 to toggle mode.
    [Button-1] Stop Sensor.
    Selected "Normal Operation" mode. Press Button-2 to start sensor or Button-1 to toggle mode.
    ...

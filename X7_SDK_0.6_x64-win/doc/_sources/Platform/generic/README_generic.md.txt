# Novelda examples for Windows / Linux / Raspberry Pi

## Building the example app

### Raspberry Pi

To build the example Novelda SignalFlow app you need
(assuming you are on the target platform and not cross-compiling):

1. Raspberry Pi 4/5 with 32/64-bit OS
2. CMake - run the following in a terminal to install:
   - `sudo apt update && sudo apt upgrade`
   - `sudo apt install cmake libgpiod-dev -y`
   - To confirm that CMake was installed properly, run the following command:
     `cmake --version`
3. gcc (default on Raspberry Pi)

Open a terminal and go to the downloaded SW folder. Navigate into the example
folder and run the following commands to build the project:

* `cmake -B build -DCMAKE_INSTALL_PREFIX=<install_dir>`
* `cmake --build build --target install`

In the `install_dir` folder there should now be a bin folder with a
`novelda_signalflow_app_x7_<product>` binary.

### Linux

#### Prerequisites

1. `sudo apt install cmake libgpiod-dev pkg-config gcc g++`
2. `cmake -B build -DCMAKE_INSTALL_PREFIX=<install_dir> -DFT4222=ON`
3. `cmake --build build --target install`

### Windows

#### Prerequisites

* [Visual Studio 2022 build environment](https://visualstudio.microsoft.com/downloads/)
* [FT4222 1.4.5 libraries](https://ftdichip.com/wp-content/uploads/2022/06/LibFT4222-v1.4.5.zip)

#### Building

1. Open a command prompt for Visual Studio, for example
   `x64 Native Tools Command Prompt for VS 2022`.
2. Run:
   - `cmake -B build -DCMAKE_INSTALL_PREFIX=<install_dir> -DFT4222=ON -DLibFT4222_ROOT=<libft4222_dir>`
     (`<libft4222_dir>` should point to the root directory of the unzipped
     LibFT4222 zip archive)
   - `cmake --build build --target install --config release`

In the `install_dir` folder there should now be a bin folder with a
`novelda_signalflow_app_x7_<product>.exe` binary.

## Runtime prerequisites

If you are on a Raspberry Pi you need to:

* Enable SPI communication interface using `sudo raspi-config`.
  * `Interface Options` -> `SPI` -> `Yes`.
* Add the user that will run to the `gpio` and `spi` groups using:
  * `sudo usermod -a -G gpio,spi $USER`
* Connect the X7 sensor to the Raspberry Pi.

## Configuring

### IO Config

In *platform_generic.c*, the `io_config` struct is initialized. The call to
`get_io_config` fetches and applies the default settings which are configured
for the Raspberry Pi. To use a different IO configuration, set the
`GET_IO_CONFIG_C` CMake variable to point to a .c file with an alternative
implementation of the `get_io_config` function.

### Product config

The product-specific settings are configured in *novelda_signalflow_app_x7\*.c*,
see the `<product>_configure(...)` function there.

## Running

To run it with the provided flow:

* `<install_dir>/bin/novelda_signalflow_app_x7_<product>`

You will then get console output depending on the product being run.
For more information about the output, see the product description.

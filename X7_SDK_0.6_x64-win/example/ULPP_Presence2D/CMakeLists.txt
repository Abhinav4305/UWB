#
# Minimal CMakeLists.txt example for building the novelda_signalflow_app example
#

cmake_minimum_required(VERSION 3.13)
project(ULPP_Presence2D C CXX)

# Define the list of variants
set(variants "default" )

include(${CMAKE_CURRENT_SOURCE_DIR}/../../CMake/Novelda.cmake)

foreach(variant IN LISTS variants)
    add_novelda_product_interface(ULPP_Presence2D ${variant})
    # Generate the file name and app name
    if(variant STREQUAL "default")
        set(product_implementation "novelda_signalflow_app_x7.c")
        set(platform_implementation "platform_generic.c")
        set(target "ULPP_Presence2D")
        set(output_name "novelda_signalflow_app_x7_ULPP_Presence2D")
    else()
        set(product_implementation "novelda_signalflow_app_x7_${variant}.c")
        set(platform_implementation "platform_generic_${variant}.c")
        set(target "ULPP_Presence2D${variant}")
        set(output_name "novelda_signalflow_app_x7_ULPP_Presence2D_${variant}")
    endif()

    add_executable(${target}
        "${platform_implementation}"
        "${product_implementation}"
    )

    set_target_properties(${target} PROPERTIES
        OUTPUT_NAME ${output_name}
        LINKER_LANGUAGE CXX
    )

    target_link_libraries(${target} PRIVATE NoveldaInterface ULPP_Presence2D_${variant}Interface)

    set_target_properties(${target} PROPERTIES INSTALL_RPATH "$ORIGIN/../lib")
    install(TARGETS ${target} RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endforeach()

function(add_novelda_product_interface PRODUCT VARIANT)
    include("${NOVELDA_SDK_DIR}/CMake/FirmwarePaths.cmake")
    message(DEBUG "Adding Novelda ${PRODUCT} interface")
    set(IC_VERSIONS IC003 IC004)
    set(PRODUCT_VARIANT "${PRODUCT}_${VARIANT}")
    if(NOT "${VARIANT}" STREQUAL "default")
        set(VARIANT_SUFFIX "_${VARIANT}")
    else()
        set(VARIANT_SUFFIX "")
    endif()


    if(NOT TARGET novelda_${PRODUCT})
        if(MSVC)
            add_library(novelda_${PRODUCT})
        else()
            add_library(novelda_${PRODUCT} SHARED)
        endif()
        target_sources(novelda_${PRODUCT} PRIVATE
            ${NOVELDA_SDK_DIR}/src/product/novelda_product.c
            ${NOVELDA_SDK_DIR}/src/product/novelda_${PRODUCT}.c
        )
        apply_compile_flags(novelda_${PRODUCT} PRIVATE)
        target_include_directories(novelda_${PRODUCT} PUBLIC
            ${NOVELDA_SDK_DIR}/include/product
            ${NOVELDA_SDK_DIR}/include/platform
            ${NOVELDA_SDK_DIR}/include
        )
        install(TARGETS novelda_${PRODUCT} DESTINATION ${CMAKE_INSTALL_LIBDIR})
    endif()

    if(NOT TARGET novelda_platform_generic${PRODUCT})
        add_library(novelda_platform_generic${PRODUCT} "${NOVELDA_SDK_DIR}/src/platform/novelda_platform_generic.c")
        target_include_directories(novelda_platform_generic${PRODUCT} PRIVATE
            ${NOVELDA_SDK_DIR}/include/product
            ${NOVELDA_SDK_DIR}/include/platform
            ${NOVELDA_SDK_DIR}/include
        )
        foreach(IC_VERSION ${IC_VERSIONS})
            target_compile_definitions(novelda_platform_generic${PRODUCT}
                PRIVATE
                    FIRMWARE_PATH_${IC_VERSION}="../share/${FIRMWARE_PATH_${PRODUCT}_${IC_VERSION}}"
            )
        endforeach()
        target_link_libraries(novelda_${PRODUCT} PUBLIC novelda_platform_generic${PRODUCT})

        set(GET_IO_CONFIG_C "${NOVELDA_SDK_DIR}/src/platform/io_config/io_config_generic_SingleChip.c" CACHE PATH "Path to file providing implementation of get_io_config")
        if(NOT EXISTS ${GET_IO_CONFIG_C})
            message(FATAL_ERROR "GET_IO_CONFIG_C not found at ${GET_IO_CONFIG_C}")
        endif()
        target_sources(novelda_platform_generic${PRODUCT} PRIVATE ${GET_IO_CONFIG_C})
        apply_compile_flags(novelda_platform_generic${PRODUCT} PRIVATE)
    endif()

    if(NOT TARGET ${PRODUCT_VARIANT}Interface)
        add_library(${PRODUCT_VARIANT}Interface INTERFACE)
        foreach(IC_VERSION ${IC_VERSIONS})
            if(NOT DEFINED FIRMWARE_PATH_${PRODUCT}_${IC_VERSION})
                message(FATAL_ERROR "FIRMWARE_PATH_${PRODUCT}_${IC_VERSION} missing in ${NOVELDA_SDK_DIR}/CMake/FirmwarePaths.cmake")
            endif()
            message(DEBUG "Adding: ${FIRMWARE_PATH_${PRODUCT}_${IC_VERSION}}")
            install(FILES "${NOVELDA_SDK_DIR}/firmware/${FIRMWARE_PATH_${PRODUCT}_${IC_VERSION}}" DESTINATION ${CMAKE_INSTALL_DATADIR})
        endforeach()
        target_link_directories(${PRODUCT_VARIANT}Interface INTERFACE ${NOVELDA_SDK_DIR}/lib)
        target_link_libraries(${PRODUCT_VARIANT}Interface INTERFACE novelda_${PRODUCT} novelda_platform_generic${PRODUCT})
    endif()
endfunction()

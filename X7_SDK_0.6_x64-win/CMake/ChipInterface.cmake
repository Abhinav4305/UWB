option(FT4222 "Use the FT4222 chip interface" OFF)

find_package(SignalFlowDLLocal CMAKE_FIND_ROOT_PATH_BOTH REQUIRED)

if(NOT TARGET ChipInterface)
    add_library(ChipInterface SHARED)

    target_sources(ChipInterface PRIVATE
        "${NOVELDA_SDK_DIR}/src/ChipInterfaceCommon.cpp"
        $<$<BOOL:${UNIX}>:${NOVELDA_SDK_DIR}/src/LinuxNativeChipInterface.cpp>
        $<$<BOOL:${FT4222}>:${NOVELDA_SDK_DIR}/src/FT4222ChipInterface.cpp>
    )

    target_compile_definitions(ChipInterface PRIVATE BUILDING_CHIPINTERFACE)

    set_target_properties(ChipInterface PROPERTIES OUTPUT_NAME "ChipInterface")
    target_link_libraries(ChipInterface PRIVATE Novelda::SignalFlowDLLocal NoveldaInterface)

    if(FT4222)
        set(LibFT4222_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." CACHE PATH "Path to LibFT4222")
        find_package(LibFT4222 REQUIRED)
        find_package(LibFTD2XX REQUIRED)
        target_link_libraries(ChipInterface PRIVATE
            LibFT4222::LibFT4222
            LibFTD2XX::LibFTD2XX
        )
        target_compile_features(ChipInterface PRIVATE cxx_std_17)
        if(WIN32)
            install(FILES
                "${CMAKE_CURRENT_SOURCE_DIR}/../../bin/libusb-1.0.dll"
                "${CMAKE_CURRENT_SOURCE_DIR}/../../bin/usbpp11.dll"
                "${CMAKE_CURRENT_SOURCE_DIR}/../../bin/LibFT4222-64.dll"
                DESTINATION ${CMAKE_INSTALL_BINDIR}
            )
        else()
            install(FILES
                "${CMAKE_CURRENT_SOURCE_DIR}/../../lib/libusbpp11.so"
                "${CMAKE_CURRENT_SOURCE_DIR}/../../lib/libft4222.so"
                "${CMAKE_CURRENT_SOURCE_DIR}/../../lib/libModuleConnector.so" # wasn't being installed before, not sure if it should be here, perhaps another file?
                DESTINATION ${CMAKE_INSTALL_LIBDIR}
            )
        endif()
    endif()

    if(UNIX)
        find_package(libgpiodcxx REQUIRED)
        target_include_directories(ChipInterface PUBLIC ${libgpiodcxx_INCLUDE_DIRS})
        target_link_libraries(ChipInterface PRIVATE ${libgpiodcxx_LIBRARIES})
        target_compile_features(ChipInterface PRIVATE cxx_std_11)
    endif()

    target_compile_features(ChipInterface PRIVATE cxx_std_11)
    apply_compile_flags(ChipInterface PRIVATE)
    install(TARGETS ChipInterface LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
endif()

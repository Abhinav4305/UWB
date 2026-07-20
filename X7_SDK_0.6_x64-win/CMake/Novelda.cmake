include(GNUInstallDirs)
include(CPack)

function(apply_compile_flags target scope)
    if(MSVC)
        target_link_options(${target} ${scope}
            /IGNORE:4199 # Ignore warnings about /DELAYLOAD - it's not used by the SDK
        )
        target_compile_options(${target} ${scope}
            /W4
        )
    else()
        target_compile_options(${target} ${scope}
            -Wall
            -Wextra
            $<$<COMPILE_LANGUAGE:C>:-Werror=implicit-function-declaration>
        )
    endif()
    target_compile_definitions(${target} ${scope}
        $<$<BOOL:${FT4222}>:NOVELDA_CHIPINTERFACE_FT4222>
        NOVELDA_FILESYSTEM_CAPABILITY
    )
endfunction()

set(NOVELDA_SDK_DIR "${CMAKE_CURRENT_LIST_DIR}/.." CACHE PATH "Top level SDK dir" FORCE)

if(NOT TARGET NoveldaInterface)
    list(APPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}/../bin")
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../bin")

    add_library(NoveldaInterface INTERFACE)

    execute_process(COMMAND bash -c "lscpu | grep -q Cortex-A72" RESULT_VARIABLE CPUINFO)
    if(CPUINFO EQUAL 0)
        target_compile_options(NoveldaInterface INTERFACE -mcpu=cortex-a72)
    endif()

    include("${CMAKE_CURRENT_LIST_DIR}/ChipInterface.cmake")

    find_package(SignalFlowDLLocal CMAKE_FIND_ROOT_PATH_BOTH REQUIRED)
    find_package(Threads REQUIRED)

    find_file(PROVIDED_LIBSTDCXX libstdc++.so.6 PATHS "${CMAKE_CURRENT_LIST_DIR}/../lib" NO_DEFAULT_PATH)

    if(PROVIDED_LIBSTDCXX)
        # Skip default libs if we need to link with the provided libstdc++
        add_link_options(-nodefaultlibs)
    endif()

    target_compile_features(NoveldaInterface INTERFACE cxx_std_11 c_std_11)

    target_link_libraries(NoveldaInterface
        INTERFACE
            Novelda::SignalFlowDLLocal
            Threads::Threads
            ChipInterface
    )

    if(PROVIDED_LIBSTDCXX)
        target_link_libraries(NoveldaInterface INTERFACE ${PROVIDED_LIBSTDCXX} c)
    endif()

    if(FT4222)
        target_link_directories(NoveldaInterface INTERFACE ../lib)
        target_link_libraries(NoveldaInterface INTERFACE LibFT4222::LibFT4222)
    endif()

    apply_compile_flags(NoveldaInterface INTERFACE)

    install(
        FILES
            $<TARGET_FILE:Novelda::SignalFlowDLLocal>
            $<$<BOOL:${PROVIDED_LIBSTDCXX}>:${PROVIDED_LIBSTDCXX}>
            DESTINATION $<$<BOOL:${WIN32}>:${CMAKE_INSTALL_BINDIR}>$<$<NOT:$<BOOL:${WIN32}>>:${CMAKE_INSTALL_LIBDIR}>
    )

    include("${CMAKE_CURRENT_LIST_DIR}/Product.cmake")

endif()

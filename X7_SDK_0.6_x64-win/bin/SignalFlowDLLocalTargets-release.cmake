#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "Novelda::SignalFlowDLLocal" for configuration "Release"
set_property(TARGET Novelda::SignalFlowDLLocal APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(Novelda::SignalFlowDLLocal PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/SignalFlow.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/SignalFlow.dll"
  )

list(APPEND _cmake_import_check_targets Novelda::SignalFlowDLLocal )
list(APPEND _cmake_import_check_files_for_Novelda::SignalFlowDLLocal "${_IMPORT_PREFIX}/bin/SignalFlow.lib" "${_IMPORT_PREFIX}/bin/SignalFlow.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)

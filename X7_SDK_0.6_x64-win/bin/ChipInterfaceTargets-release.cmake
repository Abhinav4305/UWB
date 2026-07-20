#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "Novelda::ChipInterface" for configuration "Release"
set_property(TARGET Novelda::ChipInterface APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(Novelda::ChipInterface PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/ChipInterface.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/ChipInterface.dll"
  )

list(APPEND _cmake_import_check_targets Novelda::ChipInterface )
list(APPEND _cmake_import_check_files_for_Novelda::ChipInterface "${_IMPORT_PREFIX}/lib/ChipInterface.lib" "${_IMPORT_PREFIX}/bin/ChipInterface.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)

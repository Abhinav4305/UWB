# Based on the example at https://cmake.org/cmake/help/latest/manual/cmake-developer.7.html#a-sample-find-module

if(NOT UNIX)
    message(FATAL_ERROR "libgpiod is only supported on Linux.")
endif()

message(DEBUG "PKG_CONFIG_DIR: $ENV{PKG_CONFIG_DIR}")
message(DEBUG "PKG_CONFIG_LIBDIR: $ENV{PKG_CONFIG_LIBDIR}")
message(DEBUG "PKG_CONFIG_SYSROOT_DIR: $ENV{PKG_CONFIG_SYSROOT_DIR}")

find_package(PkgConfig)
pkg_check_modules(PC_libgpiodcxx REQUIRED libgpiodcxx)

find_path(libgpiodcxx_INCLUDE_DIR
  NAMES gpiod.hpp
  PATHS ${PC_libgpiodcxx_INCLUDE_DIRS}
  PATH_SUFFIXES libgpiodcxx
)

find_library(libgpiodcxx_LIBRARY
  NAMES gpiodcxx
  PATHS ${PC_libgpiodcxx_LIBRARY_DIRS}
)

find_library(libgpiod_LIBRARY
  NAMES gpiod
  PATHS ${PC_libgpiodcxx_LIBRARY_DIRS}
)

set(libgpiodcxx_VERSION ${PC_libgpiodcxx_VERSION})

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(libgpiodcxx
  FOUND_VAR libgpiodcxx_FOUND
  REQUIRED_VARS
    libgpiodcxx_LIBRARY
    libgpiodcxx_INCLUDE_DIR
  VERSION_VAR libgpiodcxx_VERSION
)

if(libgpiodcxx_FOUND)
  set(libgpiodcxx_LIBRARIES ${libgpiodcxx_LIBRARY} ${libgpiod_LIBRARY})
  set(libgpiodcxx_INCLUDE_DIRS ${libgpiodcxx_INCLUDE_DIR})
  set(libgpiodcxx_DEFINITIONS ${PC_libgpiodcxx_CFLAGS_OTHER})
endif()

mark_as_advanced(
  libgpiodcxx_INCLUDE_DIR
  libgpiodcxx_LIBRARY
)
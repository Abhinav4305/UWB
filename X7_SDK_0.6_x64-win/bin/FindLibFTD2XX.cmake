if (NOT LibFT4222_ROOT)
	if (NOT $ENV{LibFT4222_ROOT} STREQUAL "")
		set(LibFT4222_ROOT $ENV{LibFT4222_ROOT})
	else()
		message(WARNING "LibFT4222_ROOT needed.")
	endif()
endif()

if (NOT LibFT4222_LINUX_ARCH)
    set(LibFT4222_LINUX_ARCH "x86_64")
endif()

find_path(
	LibFTD2XX_INCLUDE_DIR
	NAMES
		"ftd2xx.h"
	PATHS
		"${LibFT4222_ROOT}"
	PATH_SUFFIXES
		"imports/ftd2xx"
		"include"
	NO_CMAKE_FIND_ROOT_PATH
	NO_DEFAULT_PATH
)

find_library(
	LibFTD2XX_LIBS
	NAMES
		"ftd2xx"
		"ft4222"
	PATHS
		"${LibFT4222_ROOT}"
	PATH_SUFFIXES
		"imports/ftd2xx/amd64"
		"build-${LibFT4222_LINUX_ARCH}"
		"lib"
	NO_CMAKE_FIND_ROOT_PATH
	NO_DEFAULT_PATH
)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(LibFTD2XX DEFAULT_MSG LibFTD2XX_INCLUDE_DIR LibFTD2XX_LIBS)

if (LIBFTD2XX_FOUND)
    if (NOT TARGET LibFTD2XX::LibFTD2XX)
		add_library(LibFTD2XX::LibFTD2XX UNKNOWN IMPORTED GLOBAL)
		set_target_properties(LibFTD2XX::LibFTD2XX
			PROPERTIES IMPORTED_LOCATION ${LibFTD2XX_LIBS})
		target_include_directories(LibFTD2XX::LibFTD2XX
			INTERFACE
				${LibFTD2XX_INCLUDE_DIR}
				${LibFTD2XX_INCLUDE_DIR})
	endif()
endif()

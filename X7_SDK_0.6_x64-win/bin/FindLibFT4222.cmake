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
	LibFT4222_INCLUDE_DIR
	NAMES
		"libft4222.h"
		"LibFT4222.h"
	PATHS
		"${LibFT4222_ROOT}"
	PATH_SUFFIXES
		"imports/LibFT4222/inc"
		"include"
	NO_CMAKE_FIND_ROOT_PATH
	NO_DEFAULT_PATH
)

find_library(
	LibFT4222_LIBS
	NAMES
		"ft4222"
		"LibFT4222-64"
	PATHS
		"${LibFT4222_ROOT}"
	PATH_SUFFIXES
		"imports/LibFT4222/dll/amd64" # Windows only
		"build-${LibFT4222_LINUX_ARCH}"
		"lib"
	NO_CMAKE_FIND_ROOT_PATH
	NO_DEFAULT_PATH
)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(LibFT4222 DEFAULT_MSG LibFT4222_INCLUDE_DIR LibFT4222_LIBS)

if (LIBFT4222_FOUND)
    if (NOT TARGET LibFT4222::LibFT4222)
		add_library(LibFT4222::LibFT4222 UNKNOWN IMPORTED GLOBAL)
		set_target_properties(LibFT4222::LibFT4222
			PROPERTIES IMPORTED_LOCATION ${LibFT4222_LIBS})
		target_include_directories(LibFT4222::LibFT4222
			INTERFACE
				${LibFT4222_INCLUDE_DIR})

	endif()
endif()

cmake_minimum_required(VERSION 3.16)
project(orbit_rev_f LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(land "${CMAKE_CURRENT_SOURCE_DIR}/../../backend/app/static/land.geojson")
set(coastlines "${CMAKE_CURRENT_BINARY_DIR}/coastlines.hpp")
add_custom_command(
    OUTPUT "${coastlines}"
    COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/pack_coastlines.py"
            "${land}" "${coastlines}"
    DEPENDS pack_coastlines.py "${land}"
    VERBATIM
)

add_library(orbit_ui orbit_ui.cpp "${coastlines}")
target_compile_features(orbit_ui PUBLIC cxx_std_17)
target_include_directories(orbit_ui
    PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}"
    PRIVATE "${CMAKE_CURRENT_BINARY_DIR}"
)
target_compile_options(orbit_ui PRIVATE -Wall -Wextra -Wpedantic)

option(ORBIT_BUILD_DESKTOP "Build the native X11 preview" ON)
if(ORBIT_BUILD_DESKTOP)
    find_package(X11 REQUIRED)
    add_executable(orbit-rev-f desktop.cpp sample_scene.cpp)
    target_link_libraries(orbit-rev-f PRIVATE orbit_ui X11::X11)
    target_compile_options(orbit-rev-f PRIVATE -Wall -Wextra -Wpedantic)
endif()

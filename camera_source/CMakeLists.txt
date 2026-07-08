cmake_minimum_required(VERSION 3.5)

project(custom_cv25_ipcam CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# [O] Cross-compilation options matching Ambarella SDK setup
option(CROSS_COMPILE "ENABLE CROSS_COMPILE" ON)
if(CROSS_COMPILE)
    set(AMBARELLA_SDK_DIR "/opt/ambarella-sdk") 
    set(TOOLCHAIN_DIR "${AMBARELLA_SDK_DIR}/toolchain/usr/bin/aarch64-oclea-linux")
    set(CMAKE_C_COMPILER "${TOOLCHAIN_DIR}/aarch64-oclea-linux-gcc")
    set(CMAKE_CXX_COMPILER "${TOOLCHAIN_DIR}/aarch64-oclea-linux-g++")
    set(ROOTFS_DIR "${AMBARELLA_SDK_DIR}/rootfs")
    set(CMAKE_SYSROOT "${ROOTFS_DIR}" CACHE STRING "" FORCE)
    set(CMAKE_FIND_ROOT_PATH "${CMAKE_SYSROOT}")
else()
    set(ROOTFS_DIR "")
endif(CROSS_COMPILE)

# Search include and library paths in sysroot first
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIB REQUIRED glib-2.0)
pkg_check_modules(GSTREAMER REQUIRED gstreamer-1.0)
pkg_check_modules(GSTREAMER_PLUGINS_BASE REQUIRED gstreamer-base-1.0)
pkg_check_modules(GSTREAMER_APP REQUIRED gstreamer-app-1.0)

# OpenCV include directories
if(CROSS_COMPILE)
    include_directories(
        ${ROOTFS_DIR}/usr
        ${ROOTFS_DIR}/usr/include
        ${ROOTFS_DIR}/usr/include/opencv4
    )
else()
    find_package(OpenCV REQUIRED)
    include_directories(${OpenCV_INCLUDE_DIRS})
endif()

# Global include directories
include_directories(
    src
    ${GLIB_INCLUDE_DIRS}
    ${GSTREAMER_INCLUDE_DIRS}
    ${GSTREAMER_BASE_INCLUDE_DIRS}
    ${GSTREAMER_APP_INCLUDE_DIRS}
)

# Search for all sources
file(GLOB_RECURSE SOURCES
    "src/*.cpp"
)

add_executable(custom_cv25_ipcam ${SOURCES})

# Link libraries
set(OPENCV_LIBS
    opencv_core
    opencv_imgproc
    opencv_imgcodecs
)

set(GST_LIBS
    gstreamer-1.0
    gstbase-1.0
    gstapp-1.0
)

set(GLIB_LIBS
    glib-2.0
    gobject-2.0
)

target_link_libraries(custom_cv25_ipcam
    ${OPENCV_LIBS}
    ${GST_LIBS}
    ${GLIB_LIBS}
    pthread
)

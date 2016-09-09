#
# Copyright (C) 2016 The Android Open Source Project
#
# This software is licensed under the terms of the GNU General Public
# License version 2, as published by the Free Software Foundation, and
# may be copied, distributed, and modified under those terms.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#

include $(CLEAR_VARS)

module_name := libltp_$(module_libname)

LOCAL_MODULE := $(module_name)
LOCAL_MODULE_TAGS := optional

LOCAL_CFLAGS := $(module_cflags) \
    $(ltp_cflags) \
    $(ltp_cflags_arm) \
    $(ltp_cflags_x86)

LOCAL_C_INCLUDES := $(addprefix $(local_ltp_root)/,$(module_c_includes)) \
    $(ltp_c_includes)

LOCAL_STATIC_LIBRARIES := $(ltp_static_libraries)

LOCAL_SRC_FILES := $(addprefix ../,$(module_src_files))
LOCAL_ADDITIONAL_DEPENDENCIES := $(LOCAL_PATH)/Android.library.mk

include $(BUILD_STATIC_LIBRARY)

module_name :=

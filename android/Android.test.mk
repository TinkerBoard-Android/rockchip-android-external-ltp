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

module_name := ltp_$(subst /,_,$(module_testname))
module_stem := $(notdir $(module_testname))

LOCAL_MODULE := $(module_name)
LOCAL_MODULE_STEM_32 := $(module_stem)
LOCAL_MODULE_STEM_64 := $(module_stem)
LOCAL_MODULE_PATH_32 := $($(TARGET_2ND_ARCH_VAR_PREFIX)TARGET_OUT_DATA_NATIVE_TESTS)/ltp/testcases/bin
LOCAL_MODULE_PATH_64 := $(TARGET_OUT_DATA_NATIVE_TESTS)/ltp/testcases/bin
LOCAL_MODULE_TAGS := optional
LOCAL_MULTILIB := both

LOCAL_CFLAGS := $(ltp_cflags) $(module_cflags)
LOCAL_CFLAGS_arm := $(ltp_cflags_arm)
LOCAL_CFLAGS_x86 := $(ltp_cflags_x86)

LOCAL_C_INCLUDES := $(ltp_c_includes) \
    $(addprefix $(local_ltp_root)/,$(module_c_includes))

LOCAL_STATIC_LIBRARIES := $(ltp_static_libraries) \
    $(addprefix libltp_,$(module_static_libraries))

LOCAL_SHARED_LIBRARIES := $(ltp_shared_libraries) \
    $(addprefix lib,$(module_shared_libraries))

LOCAL_SRC_FILES := $(addprefix ../,$(module_src_files))
LOCAL_ADDITIONAL_DEPENDENCIES := $(LOCAL_PATH)/Android.test.mk

include $(BUILD_EXECUTABLE)
vts_src_file_32 := $(LOCAL_MODULE_PATH_32)/$(LOCAL_MODULE_STEM_32)
vts_src_file_64 := $(LOCAL_MODULE_PATH_64)/$(LOCAL_MODULE_STEM_64)
vts_dst_file_32 := testcases/bin/$(LOCAL_MODULE_STEM_32)
vts_dst_file_64 := testcases/bin/$(LOCAL_MODULE_STEM_64)
include $(LOCAL_PATH)/Android.vts_testcase.mk

module_name :=
module_stem :=
vts_src_file_32 :=
vts_dst_file_32 :=
vts_src_file_64 :=
vts_dst_file_64 :=

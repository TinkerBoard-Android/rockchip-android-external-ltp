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

module_name := ltp_$(subst /,_,$(module_prebuilt))
module_stem := $(notdir $(module_prebuilt))
module_path := $(patsubst %/,%,$(dir $(module_prebuilt)))

prebuilt_src_file := $(local_ltp_root)/$(module_src_files)

LOCAL_MODULE := $(module_name)-32
LOCAL_INSTALLED_MODULE_STEM := $(module_stem)
LOCAL_MODULE_PATH := $($(TARGET_2ND_ARCH_VAR_PREFIX)TARGET_OUT_DATA_NATIVE_TESTS)/ltp/$(module_path)
LOCAL_MODULE_CLASS := EXECUTABLES
LOCAL_MODULE_TAGS := optional
LOCAL_MULTILIB := 32

include $(BUILD_SYSTEM)/base_rules.mk
$(LOCAL_BUILT_MODULE): $(prebuilt_src_file) $(LOCAL_PATH)/Android.prebuilt.mk
	$(transform-generated-source)
vts_src_file_32 := $(LOCAL_MODULE_PATH)/$(LOCAL_INSTALLED_MODULE_STEM)
vts_dst_file_32 := $(module_path)/$(module_stem)

ifeq (1, $(target_support_64bit))
include $(CLEAR_VARS)

LOCAL_MODULE := $(module_name)-64
LOCAL_INSTALLED_MODULE_STEM := $(module_stem)
LOCAL_MODULE_PATH := $(TARGET_OUT_DATA_NATIVE_TESTS)/ltp/$(module_path)
LOCAL_MODULE_CLASS := EXECUTABLES
LOCAL_MODULE_TAGS := optional
LOCAL_MULTILIB := 64

include $(BUILD_SYSTEM)/base_rules.mk
$(LOCAL_BUILT_MODULE): $(prebuilt_src_file) $(LOCAL_PATH)/Android.prebuilt.mk
	$(transform-generated-source)
vts_src_file_64 := $(LOCAL_MODULE_PATH)/$(LOCAL_INSTALLED_MODULE_STEM)
vts_dst_file_64 := $(module_path)/$(module_stem)

include $(LOCAL_PATH)/Android.vts_testcase.mk
endif

module_name :=
module_stem :=
module_path :=
prebuilt_src_file :=
vts_src_file_32 :=
vts_dst_file_32 :=
vts_src_file_64 :=
vts_dst_file_64 :=

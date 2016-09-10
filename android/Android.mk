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

disabled_target := 0

# TODO: enable LTP for darwin and windows hosts
ifneq (linux, $(HOST_OS))
disabled_target := 1
endif

# TODO: enable LTP for mips eng
ifneq (,$(findstring mips, $(TARGET_PRODUCT)))
ifeq (eng, $(TARGET_BUILD_VARIANT))
disabled_target := 1
endif
endif

# LTP is only for development and not for production
ifeq (,$(filter userdebug eng, $(TARGET_BUILD_VARIANT)))
disabled_target := 1
endif


ifeq (0, $(disabled_target))

LOCAL_PATH := $(call my-dir)
local_ltp_root := $(LOCAL_PATH)/..

include $(CLEAR_VARS)
LOCAL_MODULE := ltp_vts_testcases
vts_src_file_32 := $(LOCAL_PATH)/$(LOCAL_MODULE).txt
vts_src_file_64 := $(vts_src_file_32)
vts_dst_file_32 := $(LOCAL_MODULE).txt
vts_dst_file_64 := $(LOCAL_MODULE).txt
include $(LOCAL_PATH)/Android.vts_testcase.mk
vts_src_file_32 :=
vts_dst_file_32 :=
vts_src_file_64 :=
vts_dst_file_64 :=

# linux_syscall_numbers.h doesn't really "belong" to any module, so give it
# its own fake static library that the other targets can depend on
include $(CLEAR_VARS)
LOCAL_MODULE := ltp_linux_syscall_numbers
LOCAL_MODULE_CLASS := STATIC_LIBRARIES
LOCAL_MODULE_TAGS := optional

regen_sh := $(local_ltp_root)/testcases/kernel/include/regen.sh

intermediates := $(local-generated-sources-dir)
GEN := $(intermediates)/linux_syscall_numbers.h
$(GEN): PRIVATE_INPUT_FILE := $(wildcard $(local_ltp_root)/testcases/kernel/include/*.in)
$(GEN): PRIVATE_CUSTOM_TOOL = $(regen_sh) out/target/product/$(TARGET_DEVICE)/gen/STATIC_LIBRARIES/ltp_linux_syscall_numbers_intermediates/linux_syscall_numbers.h -o $@
$(GEN): $(regen_sh) $(PRIVATE_INPUT_FILE)
	$(transform-generated-source)
LOCAL_GENERATED_SOURCES += $(GEN)

$(LOCAL_BUILT_MODULE): $(GEN)

LOCAL_EXPORT_C_INCLUDE_DIRS := $(intermediates)
include $(BUILD_STATIC_LIBRARY)


include $(CLEAR_VARS)

# Hacks for bionic compatibility
ltp_cflags := \
    -include $(LOCAL_PATH)/include/bionic-compat.h

# Silence noisy warnings
ltp_cflags += \
    -Wno-deprecated \
    -Wno-format \
    -Wno-gnu-designator \
    -Wno-macro-redefined \
    -Wno-missing-field-initializers \
    -Wno-parentheses-equality \
    -Wno-pointer-arith \
    -Wno-sign-compare \
    -Wno-unused-parameter

# bionic has broken signal handling for signum > 32 on 32-bit ARM and x86
# (for ABI reasons this can't be fixed)
ltp_cflags_arm := -DNUMSIGS=32
ltp_cflags_x86 := -DNUMSIGS=32

ltp_c_includes := \
    $(LOCAL_PATH)/include \
    $(local_ltp_root)/include \

ltp_static_libraries := \
    ltp_linux_syscall_numbers \

ifeq ($(PLATFORM_SDK_VERSION),23)  # MNC
ltp_static_libraries += \
    libcap-ng \

else
ltp_static_libraries += \
    libcap \

endif

# TODO: recover libaio when the external project created
ltp_shared_libraries := \
    libselinux \

ltp_build_test := $(LOCAL_PATH)/Android.test.mk
ltp_build_library := $(LOCAL_PATH)/Android.library.mk
ltp_build_prebuilt := $(LOCAL_PATH)/Android.prebuilt.mk

include $(LOCAL_PATH)/Android.ltp.mk

endif

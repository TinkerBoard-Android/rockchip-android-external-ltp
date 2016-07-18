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

# TODO(yuexima) temporally skip ltp build for target shamu
ifneq (shamu, $(TARGET_PRODUCT))
# LTP is for linux
ifeq (linux, $(HOST_OS))
# LTP is only for development and not for production
ifneq (,$(filter userdebug eng, $(TARGET_BUILD_VARIANT)))

LOCAL_PATH := $(call my-dir)
local_ltp_root := $(LOCAL_PATH)

include $(CLEAR_VARS)
LOCAL_MODULE := ltp
LOCAL_MODULE_CLASS := NATIVE_TESTS
LOCAL_MODULE_TAGS := optional

gen_testcases := $(LOCAL_PATH)/android/tools/gen_ltp_testcases.py
disabled_tests_file := $(LOCAL_PATH)/android/tools/disabled_tests.txt
disabled_gtests_file := $(LOCAL_PATH)/android/tools/disabled_gtests.txt

intermediates := $(local-generated-sources-dir)
GEN := $(intermediates)/ltp-testcases.h
$(GEN): PRIVATE_INPUT_FILE := $(local_ltp_root)/scenario_groups/default
$(GEN): PRIVATE_CUSTOM_TOOL = $(gen_testcases) --ltp-root=$(local_ltp_root) --disabled-tests=$(disabled_tests_file) --disabled-gtests=$(disabled_gtests_file) $(PRIVATE_INPUT_FILE) > $@
$(GEN): $(gen_testcases) $(disabled_tests_file) $(disabled_gtests_file) $(PRIVATE_INPUT_FILE)
	$(transform-generated-source)
LOCAL_GENERATED_SOURCES += $(GEN)

LOCAL_SRC_FILES := ltp.cpp \
    RecursiveTemporaryDir.cpp

include $(BUILD_NATIVE_TEST)


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
    -include $(LOCAL_PATH)/android/include/bionic-compat.h

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
    $(LOCAL_PATH)/android/include \
    $(LOCAL_PATH)/include \

ltp_static_libraries := \
    ltp_linux_syscall_numbers

# TODO: recover libaio when the external project created
ltp_shared_libraries := \
    libcap \
    libselinux \

ltp_build_test := $(LOCAL_PATH)/Android.test.mk
ltp_build_library := $(LOCAL_PATH)/Android.library.mk
ltp_build_prebuilt := $(LOCAL_PATH)/Android.prebuilt.mk

include $(LOCAL_PATH)/Android.ltp.mk

endif
endif
endif

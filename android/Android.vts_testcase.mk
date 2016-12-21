#
# Copyright (C) 2016 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

VTS_TESTCASES_OUT := $(HOST_OUT)/vts/android-vts/testcases

ifdef vts_src_file_32

vts_testcases_out_32 := $(VTS_TESTCASES_OUT)/32/ltp
vts_testcase_dst_file_32 := $(vts_testcases_out_32)/$(vts_dst_file_32)

$(vts_testcase_dst_file_32): $(vts_src_file_32) | $(ACP)
	$(hide) mkdir -p $(dir $(vts_testcase_dst_file_32))
	$(hide) $(ACP) -fp $< $@
vts: $(vts_testcase_dst_file_32)

endif

ifeq (1, $(target_support_64bit))
ifdef vts_src_file_64

vts_testcases_out_64 := $(VTS_TESTCASES_OUT)/64/ltp
vts_testcase_dst_file_64 := $(vts_testcases_out_64)/$(vts_dst_file_64)

$(vts_testcase_dst_file_64): $(vts_src_file_64) | $(ACP)
	$(hide) mkdir -p $(dir $(vts_testcase_dst_file_64))
	$(hide) $(ACP) -fp $< $@
vts: $(vts_testcase_dst_file_64)

endif
endif

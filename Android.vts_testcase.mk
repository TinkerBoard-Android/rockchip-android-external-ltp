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
vts_testcases_out_32 := $(VTS_TESTCASES_OUT)/ltp/32
vts_testcases_out_64 := $(VTS_TESTCASES_OUT)/ltp/64

vts_ltp_testcase_file_32 := $(vts_testcases_out_32)/$(LOCAL_MODULE_STEM_32)
vts_ltp_testcase_file_64 := $(vts_testcases_out_64)/$(LOCAL_MODULE_STEM_64)

$(vts_ltp_testcase_file_32): $(LOCAL_MODULE_PATH_32)/$(LOCAL_MODULE_STEM_32) | $(ACP)
	$(hide) mkdir -p $(vts_testcases_out_32)
	$(hide) $(ACP) -fp $< $@

$(vts_ltp_testcase_file_64): $(LOCAL_MODULE_PATH_64)/$(LOCAL_MODULE_STEM_64) | $(ACP)
	$(hide) mkdir -p $(vts_testcases_out_64)
	$(hide) $(ACP) -fp $< $@

vts: $(vts_ltp_testcase_file_32)
vts: $(vts_ltp_testcase_file_64)


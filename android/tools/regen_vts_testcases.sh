#!/usr/bin/env bash
#
# Copyright 2016 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

TOOLS_DIR=$(realpath $(dirname $0))
LTP_ANDROID_DIR=$(realpath $TOOLS_DIR/..)
LTP_ROOT=$(realpath $LTP_ANDROID_DIR/..)
OUTPUT=$LTP_ROOT/Android.ltp.mk

cat $LTP_ROOT/scenario_groups/vts |
python $TOOLS_DIR/gen_ltp_testcases.py \
    --ltp-root=$LTP_ROOT \
    --disabled-tests=$TOOLS_DIR/disabled_tests.txt > \
    $LTP_ANDROID_DIR/ltp_vts_testcases.txt \

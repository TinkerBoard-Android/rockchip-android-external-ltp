#!/usr/bin/env python
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

import os
import argparse
import ntpath

class LtpModuleFilter(object):
    """LTP module result check and filter class.
    Checks for success build of each module in LTP's Android.mk file
    and rewrite it with only successfully built modules.
    """
    output_dir = ""
    file_path_android_ltp_mk = ""
    file_path_android_ltp_mk_filtered = ""
    module_check_options = {}

    def __init__(self, android_build_top, ltp_dir, target_product):
        self.output_dir = android_build_top + \
                          '/out/target/product/' + \
                          target_product + \
                          '/data/nativetest/ltp/'
        self.file_path_android_ltp_mk = ltp_dir + \
                                        '/Android.ltp.mk'
        self.file_path_android_ltp_mk_filtered = ltp_dir + \
                                                 '/Android.ltp.mk'
        self.module_check_options = {
            "module_testname" : self.IsBuildSuccessModuleTestname,
            "module_libname" : self.IsBuildSuccessModuleLibname,
            "module_prebuilt" : self.IsBuildSuccessModulePrebuilt,
            }

    def IsBuildSuccess(self, module_text):
        """Check whether a given module specified in Android.mk file
           is succesfully built

           Args:
               module_text: one block of ltp module build rule.

           Returns:
               True if success
        """
        module_lines = module_text.split('\n')
        if len(module_lines) < 2:
            return False
        module_header = module_lines[0].split(' := ')
        module_type = module_header[0]
        module_path = module_header[1]

        return self.module_check_options[module_type](module_path)

    def IsBuildSuccessModuleTestname(self, module_path):
        """Check whether a given ltp test module in Android.mk file
           is succesfully built

           Args:
               module_path: the path of module on the first line of
                            the block

           Returns:
               True if success
        """
        return os.path.isfile(self.output_dir + \
                              "testcases/bin/" + \
                              ntpath.basename(module_path))

    def IsBuildSuccessModuleLibname(self, module_path):
        """Check whether a given ltp lib module in Android.mk file
           is succesfully built

           Args:
               module_path: the path of module on the first line of
                            the block

           Returns:
               True if success
        """
        # TODO(yuexima) check lib build
        return self.IsBuildSuccessModulePrebuilt(module_path)

    def IsBuildSuccessModulePrebuilt(self, module_path):
        """Check whether a given prebuilt module in Android.mk file
           is succesfully built

           Args:
               module_path: the path of module on the first line of
                            the block

           Returns:
               True if success
        """
        return os.path.isfile(self.output_dir + module_path)

    def Read(self, file_path):
        """Read a file and return its entire content

           Args:
               file_path: file path

           Returns:
               entire file content in string format
        """
        with open(file_path, 'r') as file:
            return file.read()

    def LoadModules(self):
        """Read the LTP Android.mk file and seperate modules into
           a list of string
        """
        return self.Read(self.file_path_android_ltp_mk).split("\n\n");

    def FilterModules(self):
        """Start the LTP module build result check and filtering process."""
        modules = self.LoadModules()
        print str(len(modules)) + \
              " blocks loaded (including comments and empty blocks)."

        modules_filtered = \
            [module for module in modules[1:] if self.IsBuildSuccess(module)]

        with open(self.file_path_android_ltp_mk_filtered,
                  'w') as file_android_ltp_mk:
            file_android_ltp_mk.write(modules[0])
            file_android_ltp_mk.write("\n")
            if "filtered" not in modules[0]:
                file_android_ltp_mk.write("# filtered for success build only")
                file_android_ltp_mk.write("\n")
            file_android_ltp_mk.write("\n")
            file_android_ltp_mk.write("\n\n".join(modules_filtered))

        print str(len(modules_filtered) - 1) + \
              " modules were succesfully built."
        print "--Filtering complete. Android.ltp.mk file modified."


def main():
    parser = argparse.ArgumentParser(
        description = 'Generate Android.mk from parsed LTP make output')
    parser.add_argument('--android_build_top',
                        dest = 'android_build_top',
                        required = True,
                        help = 'android build top directory')
    parser.add_argument('--ltp_dir',
                        dest = 'ltp_dir',
                        required = True,
                        help = 'directory for the forked ltp project')
    parser.add_argument('--target_product',
                        dest = 'target_product',
                        required = True,
                        help = 'target product name, \
                                such as "bullhead", "angler", etc.')
    args = parser.parse_args()

    filter = LtpModuleFilter(args.android_build_top,
                             args.ltp_dir, args.target_product)
    filter.FilterModules()

if __name__ == '__main__':
    main()

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

# Parses the output of parse_ltp_{make,make_install} and generates a
# corresponding Android.mk.
#
# This process is split into two steps so this second step can later be replaced
# with an Android.bp generator.

import argparse
import fileinput
import os.path
import re

import make_parser
import make_install_parser

MAKE_DRY_RUN_FILE_NAME = 'make_dry_run.dump'
MAKE_INSTALL_DRY_RUN_FILE_NAME = 'make_install_dry_run.dump'
DISABLED_TESTS_FILE_NAME = 'disabled_tests.txt'
DISABLED_LIBS_FILE_NAME = 'disabled_libs.txt'
DISABLED_CFLAGS_FILE_NAME = 'disabled_cflags.txt'


class AndroidMkGenerator(object):
    '''A class to parse make output and convert the result to Android.ltp.mk modules.

    Attributes:
        result: list of string, result string buffer
    '''

    def __init__(self):
        self.result = []

    def UniqueKeepOrder(self, sequence):
        '''Get a copy of list where items are unique and order is preserved.

        Args:
          sequence: a sequence, can be a list, tuple, or other iterable

        Returns:
            a list where items copied from input sequence are unique
            and order is preserved.
        '''
        seen = set()
        return [x for x in sequence if not (x in seen or seen.add(x))]

    def ReadCommentedText(self, file_path):
        '''Read pound commented text file into a list of lines.

        Comments or empty lines will be excluded

        Args:
            file_path: string
        '''
        ret = set()
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
            ret = set([s for s in lines if s and not s.startswith('#')])

        return ret

    def ArTargetToLibraryName(self, ar_target):
        '''Convert ar target to library name.

        Args:
            ar_target: string
        '''
        return os.path.basename(ar_target)[len('lib'):-len('.a')]

    def BuildExecutable(self, cc_target, local_src_files, local_cflags,
                        local_c_includes, local_libraries, ltp_libs,
                        ltp_libs_used, ltp_names_used):
        '''Build a test module.

        Args:
            cc_target: string
            local_src_files: list of string
            local_cflags: list of string
            local_c_includes: list of string
            local_libraries: list of string
            ltp_libs: list of string
            ltp_libs_used: set of string
            ltp_names_used: set of string, set of already used cc_target basenames
        '''
        base_name = os.path.basename(cc_target)
        if base_name in ltp_names_used:
            print 'ERROR: base name {} of cc_target {} already used. Skipping...'.format(
                base_name, cc_target)
            return
        ltp_names_used.add(base_name)

        self.result.append('module_testname := %s' % cc_target)
        self.result.append('module_src_files := %s' %
                           ' '.join(local_src_files))
        self.result.append('module_cflags := %s' % ' '.join(local_cflags))
        self.result.append('module_c_includes := %s' %
                           ' '.join(local_c_includes))

        bionic_builtin_libs = set(['rt', 'pthread'])
        filtered_libs = set(local_libraries).difference(bionic_builtin_libs)

        static_libraries = set(i for i in local_libraries if i in ltp_libs)
        self.result.append('module_static_libraries := %s' %
                           ' '.join(static_libraries))
        for lib in static_libraries:
            ltp_libs_used.add(lib)

        shared_libraries = set(i for i in filtered_libs if i not in ltp_libs)
        self.result.append('module_shared_libraries := %s' %
                           ' '.join(shared_libraries))

        self.result.append('include $(ltp_build_test)')
        self.result.append('')

    def BuildStaticLibrary(self, ar_target, local_src_files, local_cflags,
                           local_c_includes):
        '''Build a library module.

        Args:
            ar_target: string
            local_src_files: list of string
            local_cflags: list of string
            local_c_includes: list of string
        '''
        self.result.append('module_libname := %s' %
                           self.ArTargetToLibraryName(ar_target))
        self.result.append('module_src_files := %s' %
                           ' '.join(local_src_files))
        self.result.append('module_cflags := %s' % ' '.join(local_cflags))
        self.result.append('module_c_includes := %s' %
                           ' '.join(local_c_includes))

        self.result.append('include $(ltp_build_library)')
        self.result.append('')

    def BuildPrebuilt(self, install_target, local_src_file):
        '''Build a prebuild module.

        Args:
            install_target: string
            local_src_file: string
        '''
        self.result.append('module_prebuilt := %s' % install_target)
        self.result.append('module_src_files := %s' % local_src_file)
        module_dir = os.path.dirname(install_target)
        module_stem = os.path.basename(install_target)
        module = 'ltp_%s' % install_target.replace('/', '_')

        self.result.append('include $(ltp_build_prebuilt)')
        self.result.append('')

    def HandleParsedRule(self, line, rules):
        '''Prepare parse rules.

        Args:
            line: string
            rules: dictionary {string, dictionary}
        '''
        groups = re.match(r'(.*)\[\'(.*)\'\] = \[(.*)\]', line).groups()
        rule = groups[0]
        rule_key = groups[1]
        if groups[2] == '':
            rule_value = []
        else:
            rule_value = list(i.strip()[1:-1] for i in groups[2].split(','))

        rule_value = self.UniqueKeepOrder(rule_value)
        rules.setdefault(rule, {})[rule_key] = rule_value

    def ParseInput(self, input_list):
        '''Parse a interpreted make output and produce Android.ltp.mk module.

        Args:
            input_list: list of string
        '''
        disabled_tests = self.ReadCommentedText(DISABLED_TESTS_FILE_NAME)
        disabled_libs = self.ReadCommentedText(DISABLED_LIBS_FILE_NAME)
        disabled_cflags = self.ReadCommentedText(DISABLED_CFLAGS_FILE_NAME)

        rules = {}
        for line in input_list:
            self.HandleParsedRule(line.strip(), rules)

        # .a target -> .o files
        ar = rules.get('ar', {})
        # executable target -> .o files
        cc_link = rules.get('cc_link', {})
        # .o target -> .c file
        cc_compile = rules.get('cc_compile', {})
        # executable target -> .c files
        cc_compilelink = rules.get('cc_compilelink', {})
        # Target name -> CFLAGS passed to gcc
        cc_flags = rules.get('cc_flags', {})
        # Target name -> -I paths passed to gcc
        cc_includes = rules.get('cc_includes', {})
        # Target name -> -l paths passed to gcc
        cc_libraries = rules.get('cc_libraries', {})
        # target -> prebuilt source
        install = rules.get('install', {})

        # All libraries used by any LTP test (built or not)
        ltp_libs = set(self.ArTargetToLibraryName(i) for i in ar.keys())
        # All libraries used by the LTP tests we actually build
        ltp_libs_used = set()
        ltp_names_used = set()

        print(
            "Disabled lib tests: Test cases listed here are"
            "suggested to be disabled since they require a disabled library. "
            "Please copy and paste them into disabled_tests.txt\n")
        for i in cc_libraries:
            if len(set(cc_libraries[i]).intersection(disabled_libs)) > 0:
                print os.path.basename(i)

        print("Disabled_cflag tests: Test cases listed here are"
              "suggested to be disabled since they require a disabled cflag. "
              "Please copy and paste them into disabled_tests.txt\n")
        for i in cc_flags:
            if len(set(cc_flags[i]).intersection(disabled_cflags)) > 0:
                module_name = os.path.basename(i)
                idx = module_name.find('_')
                if idx > 0:
                    module_name = module_name[:idx]
                print module_name

        for target in cc_compilelink:
            module_name = os.path.basename(target)
            if module_name in disabled_tests:
                continue
            local_src_files = cc_compilelink[target]
            local_cflags = cc_flags[target]
            local_c_includes = cc_includes[target]
            local_libraries = cc_libraries[target]
            if len(set(local_libraries).intersection(disabled_libs)) > 0:
                continue
            if len(set(local_cflags).intersection(disabled_cflags)) > 0:
                continue
            self.BuildExecutable(target, local_src_files, local_cflags,
                                 local_c_includes, local_libraries, ltp_libs,
                                 ltp_libs_used, ltp_names_used)

        for target in cc_link:
            if os.path.basename(target) in disabled_tests:
                continue
            local_src_files = set()
            local_cflags = set()
            local_c_includes = set()
            local_libraries = cc_libraries[target]
            # Accumulate flags for all .c files needed to build the .o files.
            # (Android.mk requires a consistent set of flags across a given target.
            # Thankfully using the superset of all flags in the target works fine
            # with LTP tests.)
            for obj in cc_link[target]:
                for i in cc_compile[obj]:
                    local_src_files.add(i)
                for i in cc_flags[obj]:
                    local_cflags.add(i)
                for i in cc_includes[obj]:
                    local_c_includes.add(i)
            if len(set(local_libraries).intersection(disabled_libs)) > 0:
                continue
            if len(set(local_cflags).intersection(disabled_cflags)) > 0:
                continue

            self.BuildExecutable(target, local_src_files, local_cflags,
                                 local_c_includes, local_libraries, ltp_libs,
                                 ltp_libs_used, ltp_names_used)

        for target in ar:
            # Disabled ltp library is already excluded
            # since it won't be in ltp_libs_used
            if not self.ArTargetToLibraryName(target) in ltp_libs_used:
                continue

            local_src_files = set()
            local_cflags = set()
            local_c_includes = set()

            # TODO: disabled cflags

            for obj in ar[target]:
                for i in cc_compile[obj]:
                    local_src_files.add(i)
                for i in cc_flags[obj]:
                    local_cflags.add(i)
                for i in cc_includes[obj]:
                    local_c_includes.add(i)

            if len(set(local_cflags).intersection(disabled_cflags)) > 0:
                continue

            self.BuildStaticLibrary(target, local_src_files, local_cflags,
                                    local_c_includes)

        for target in install:
            if os.path.basename(target) in disabled_tests:
                continue
            local_src_files = install[target]
            assert len(local_src_files) == 1

            self.BuildPrebuilt(target, local_src_files[0])

    def WriteResult(self, output_path):
        '''Write parse result to output file.

        Args:
            output_path: string
        '''
        with open(output_path, 'a') as f:
            f.write('\n'.join(self.result))
            self.result = []

    def ParseAll(self, ltp_root):
        '''Parse outputs from both 'make' and 'make install'.

        Args:
            ltp_root: string
        '''
        parser = make_parser.MakeParser(ltp_root)
        self.ParseInput(parser.ParseFile(MAKE_DRY_RUN_FILE_NAME))
        parser = make_install_parser.MakeInstallParser(ltp_root)
        self.ParseInput(parser.ParseFile(MAKE_INSTALL_DRY_RUN_FILE_NAME))


def main():
    parser = argparse.ArgumentParser(
        description='Generate Android.mk from parsed LTP make output')
    parser.add_argument(
        '--ltp_root', dest='ltp_root', required=True, help='LTP root dir')
    parser.add_argument(
        '--output_path',
        dest='output_path',
        required=True,
        help='output file path')
    args = parser.parse_args()

    generator = AndroidMkGenerator()
    generator.ParseAll(args.ltp_root)
    generator.WriteResult(args.output_path)

    print 'Finished!'


if __name__ == '__main__':
    main()

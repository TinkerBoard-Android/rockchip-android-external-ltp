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

# Parses the output of parse_ltp_{make,make_install} and generates a
# corresponding Android.mk.
#
# This process is split into two steps so this second step can later be replaced
# with an Android.bp generator.

import argparse
import fileinput
import os.path
import re

def read_commented_txt(filename):
    ret = set()
    with open(filename, 'r') as f:
        for line in f.readlines():
            s = line.strip()
            if s and not s.startswith('#'):
                ret.add(s)

    return ret


def ar_target_to_library_name(ar_target):
    return os.path.basename(ar_target)[len('lib'):-len('.a')]


def build_executable(cc_target, local_src_files, local_cflags,
                     local_c_includes, local_libraries, ltp_libs,
                     ltp_libs_used):
    print 'module_testname := %s' % cc_target
    print 'module_src_files := %s' % ' '.join(local_src_files)
    print 'module_cflags := %s' % ' '.join(local_cflags)
    print 'module_c_includes := %s' % ' '.join(local_c_includes)

    bionic_builtin_libs = set(['rt', 'pthread'])
    filtered_libs = set(local_libraries).difference(bionic_builtin_libs)

    static_libraries = set(i for i in local_libraries if i in ltp_libs)
    print 'module_static_libraries := %s' % ' '.join(static_libraries)
    for lib in static_libraries:
        ltp_libs_used.add(lib)

    shared_libraries = set(i for i in filtered_libs if i not in ltp_libs)
    print 'module_shared_libraries := %s' % ' '.join(shared_libraries)

    print 'include $(ltp_build_test)'
    print ''


def build_static_library(ar_target, local_src_files, local_cflags,
                         local_c_includes):
    print 'module_libname := %s' % ar_target_to_library_name(ar_target)
    print 'module_src_files := %s' % ' '.join(local_src_files)
    print 'module_cflags := %s' % ' '.join(local_cflags)
    print 'module_c_includes := %s' % ' '.join(local_c_includes)

    print 'include $(ltp_build_library)'
    print ''

def build_prebuilt(install_target, local_src_file):
    print 'module_prebuilt := %s' % install_target
    print 'module_src_files := %s' % local_src_file
    module_dir = os.path.dirname(install_target)
    module_stem = os.path.basename(install_target)
    module = 'ltp_%s' % install_target.replace('/', '_')

    print 'include $(ltp_build_prebuilt)'
    print ''

def handle_parsed_rule(line, rules):
    groups = re.match(r'(.*)\[\'(.*)\'\] = \[(.*)\]', line).groups()
    rule = groups[0]
    rule_key = groups[1]
    if groups[2] == '':
        rule_value = []
    else:
        rule_value = list(i.strip()[1:-1] for i in groups[2].split(','))

    rules.setdefault(rule, {})[rule_key] = rule_value


def parse_input(infile, disabled_tests_filename):
    disabled_tests = read_commented_txt(disabled_tests_filename)

    rules = {}
    for line in fileinput.input(infile):
        handle_parsed_rule(line.strip(), rules)

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
    ltp_libs = set(ar_target_to_library_name(i) for i in ar.keys())
    # All libraries used by the LTP tests we actually build
    ltp_libs_used = set()

    for target in cc_compilelink:
        if os.path.basename(target) in disabled_tests:
            continue

        local_src_files = cc_compilelink[target]
        local_cflags = cc_flags[target]
        local_c_includes = cc_includes[target]
        local_libraries = cc_libraries[target]

        build_executable(target, local_src_files, local_cflags,
                         local_c_includes, local_libraries, ltp_libs,
                         ltp_libs_used)

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

        build_executable(target, local_src_files, local_cflags,
                         local_c_includes, local_libraries, ltp_libs,
                         ltp_libs_used)

    for target in ar:
        if not ar_target_to_library_name(target) in ltp_libs_used:
            continue

        local_src_files = set()
        local_cflags = set()
        local_c_includes = set()

        for obj in ar[target]:
            for i in cc_compile[obj]:
                local_src_files.add(i)
            for i in cc_flags[obj]:
                local_cflags.add(i)
            for i in cc_includes[obj]:
                local_c_includes.add(i)

        build_static_library(target, local_src_files, local_cflags,
                             local_c_includes)

    for target in install:
        if os.path.basename(target) in disabled_tests:
            continue

        local_src_files = install[target]
        assert len(local_src_files) == 1

        build_prebuilt(target, local_src_files[0])


def main():
    parser = argparse.ArgumentParser(description = 'Generate Android.mk from parsed LTP make output')
    parser.add_argument('infile', nargs = '?', default = '-')
    parser.add_argument('--disabled-tests', dest = 'disabled_tests',
                    required = True, help = 'file with a list of disabled tests')
    args = parser.parse_args()

    parse_input(args.infile, args.disabled_tests)


if __name__ == '__main__':
    main()

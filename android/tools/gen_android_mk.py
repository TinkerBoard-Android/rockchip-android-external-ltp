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

def unique_keep_order(sequence):
    '''Get a copy of list where items are unique and order is preserved.

    Args:
      sequence: a sequence, can be a list, tuple, or other iterable
    Returns:
        a list where items copied from input sequence are unique
        and order is preserved.
    '''
    seen = set()
    return [x for x in sequence if not (x in seen or seen.add(x))]


def read_commented_txt(filename):
    ret = set()
    with open(filename, 'r') as f:
        lines = [line.strip() for line in f.readlines()]
        ret = set([s for s in lines if s and not s.startswith('#')])

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

    rule_value = unique_keep_order(rule_value)
    rules.setdefault(rule, {})[rule_key] = rule_value


def parse_input(infile, disabled_tests_filename, disabled_libs_filename, disabled_cflags_filename):
    disabled_tests = read_commented_txt(disabled_tests_filename)
    disabled_libs = read_commented_txt(disabled_libs_filename)
    disabled_cflags = read_commented_txt(disabled_cflags_filename)

    disabled_libstests_filename = os.path.dirname(disabled_libs_filename) + \
        "/disabled_libs'tests.txt"
    disabled_cflagstests_filename = os.path.dirname(disabled_cflags_filename) + \
        "/disabled_cflags'tests.txt"

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

    with open(disabled_libstests_filename, 'a') as f:
        f.write("# This file is autogenerated. Test cases listed here are")
        f.write("suggested to be disabled since they require a disabled library. ")
        f.write("Please copy and paste them into disabled_tests.txt\n")
        for i in cc_libraries:
            if len(set(cc_libraries[i]).intersection(disabled_libs)) > 0:
                f.write(os.path.basename(i))
                f.write('\n')

    with open(disabled_cflagstests_filename, 'a') as f:
        f.write("# This file is autogenerated. Test cases listed here are")
        f.write("suggested to be disabled since they require a disabled cflag. ")
        f.write("Please copy and paste them into disabled_tests.txt\n")
        for i in cc_flags:
            if len(set(cc_flags[i]).intersection(disabled_cflags)) > 0:
                module_name = os.path.basename(i)
                idx = module_name.find('_')
                if idx > 0:
                    module_name = module_name[:idx]
                f.write(module_name)
                f.write('\n')

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
        if len(set(local_libraries).intersection(disabled_libs)) > 0:
            continue
        if len(set(local_cflags).intersection(disabled_cflags)) > 0:
            continue

        build_executable(target, local_src_files, local_cflags,
                         local_c_includes, local_libraries, ltp_libs,
                         ltp_libs_used)

    for target in ar:
        # Disabled ltp library is already excluded
        # since it won't be in ltp_libs_used
        if not ar_target_to_library_name(target) in ltp_libs_used:
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
    parser.add_argument('--disabled-libs', dest = 'disabled_libs',
                    required = True, help = 'file with a list of disabled libs')
    parser.add_argument('--disabled-cflags', dest = 'disabled_cflags',
                    required = True, help = 'file with a list of disabled cflags')
    args = parser.parse_args()

    parse_input(args.infile, args.disabled_tests, args.disabled_libs, args.disabled_cflags)


if __name__ == '__main__':
    main()

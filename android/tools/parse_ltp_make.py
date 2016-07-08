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

import argparse
import os
import os.path
import sys
import re
import fileinput

# Parses the output of make --dry-run and generates directives in the form
#
#   ar['target.a'] = [ 'srcfile1.o, 'srcfile2.o', ... ]
#   cc_link['target'] = [ 'srcfile1.o', 'srcfile2.o', ... ]
#   cc_compile['target.o'] = [ 'srcfile1.c' ]
#   cc_compilelink['target'] = [ 'srcfile1.c' ]
#
# along with optional flags for the above directives in the form
#
#	cc_flags['target'] = [ '-flag1', '-flag2', ...]
#	cc_includes['target'] = [ 'includepath1', 'includepath2', ...]
#	cc_libraries['target'] = [ 'library1', 'library2', ...]
#
# This output is then fed into gen_android_mk which generates Android.mk.
#
# This process is split into two steps so the second step can later be replaced
# with an Android.bp generator.

ar_parser = argparse.ArgumentParser()
ar_parser.add_argument('-r', dest = 'r', action = 'store_true')
ar_parser.add_argument('-c', dest = 'c', action = 'store')

cc_parser = argparse.ArgumentParser()
cc_parser.add_argument('-D', dest = 'defines', action = 'append')
cc_parser.add_argument('-I', dest = 'includes', action = 'append')
cc_parser.add_argument('-l', dest = 'libraries', action = 'append')
cc_parser.add_argument('-c', dest = 'compile', action = 'store_true')
cc_parser.add_argument('-o', dest = 'target', action = 'store')


def relative_path(path, ltp_root, dir_stack):
    if path[0] == '/':
        path = os.path.realpath(path)
    else:
        path = os.path.realpath(ltp_root + os.sep + dir_stack[-1] + os.sep + path)

    return os.path.realpath(path).replace(ltp_root + os.sep, '')

def relative_path_for_extensions(paths, extensions, ltp_root, dir_stack):
    return [relative_path(i, ltp_root, dir_stack) for i in paths if i[-1] in extensions]


def parse_ar(line, ltp_root, dir_stack):
    args, unparsed = ar_parser.parse_known_args(line.split()[1:])

    sources = relative_path_for_extensions(unparsed, ['o'], ltp_root, dir_stack)
    target = relative_path(args.c.replace('"', ""), ltp_root, dir_stack)

    assert len(sources) > 0

    print "ar['%s'] = %s" % (target, sources)


def parse_cc(line, ltp_root, dir_stack):
    args, unparsed = cc_parser.parse_known_args(line.split()[1:])

    sources = relative_path_for_extensions(unparsed, ['c', 'o'], ltp_root, dir_stack)
    includes = [relative_path(i, ltp_root, dir_stack) for i in args.includes] if args.includes else []
    flags = []
    defines = args.defines if args.defines else []
    target = relative_path(args.target, ltp_root, dir_stack)

    if args.defines:
        for define in args.defines:
            flags.append('-D%s' % define)

    flags.extend(i for i in unparsed if i.startswith('-Wno'))

    assert len(sources) > 0

    if args.compile:
        print "cc_compile['%s'] = %s" % (target, sources)
    else:
        libraries = args.libraries if args.libraries else []
        if sources[0].endswith('.o'):
            print "cc_link['%s'] = %s" % (target, sources)
        else:
            print "cc_compilelink['%s'] = %s" % (target, sources)
        print "cc_libraries['%s'] = %s" % (target, libraries)

    print "cc_flags['%s'] = %s" % (target, flags)
    print "cc_includes['%s'] = %s" % (target, includes)


def parse_input(infile, ltp_root):
    dir_stack = []

    entering_directory = re.compile(r"make.*: Entering directory `(.*)'")
    leaving_directory = re.compile(r"make.*: Leaving directory `(.*)'")
    ar = 'ar'
    cc = 'gcc'

    for line in fileinput.input(infile):
        line = line.strip()

        m = entering_directory.match(line)
        if m:
            dir_stack.append(relative_path(m.group(1), ltp_root, dir_stack))
            continue

        m = leaving_directory.match(line)
        if m:
            dir_stack.pop()
            continue

        if line.startswith(ar):
            parse_ar(line, ltp_root, dir_stack)
            continue

        if line.startswith(cc):
            parse_cc(line, ltp_root, dir_stack)


def main():
    parser = argparse.ArgumentParser(description = 'Parse LTP "make --dry-run" output')
    parser.add_argument('infile', nargs = '?', default = '-')
    parser.add_argument('--ltp-root', dest = 'ltp_root', required = True,
                    help = 'location of LTP root directory')
    args = parser.parse_args()

    parse_input(args.infile, args.ltp_root)


if __name__ == '__main__':
    main()
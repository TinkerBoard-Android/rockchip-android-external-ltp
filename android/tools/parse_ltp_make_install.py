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
import fileinput
import os
import os.path
import re

# Parses the output of make install --dry-run and generates directives in the
# form
#
#   install['target'] = [ 'srcfile' ]
#
# This output is then fed into gen_android_mk which generates Android.mk.
#
# This process is split into two steps so the second step can later be replaced
# with an Android.bp generator.

def parse_input(infile, ltp_root):
    install = re.compile(r'install -m \d+ "%s%s(.*)" "/opt/ltp/(.*)"' % (os.path.realpath(ltp_root), os.sep))

    for line in fileinput.input(infile):
        line = line.strip()

        m = install.match(line)
        if not m:
        	continue

        src, target = m.groups()
        # If the file isn't in the source tree, it's not a prebuilt
        if not os.path.isfile(os.path.realpath(ltp_root) + os.sep + src):
        	continue

        print "install['%s'] = ['%s']" % (target, src)


def main():
    parser = argparse.ArgumentParser(description = 'Parse LTP "make install --dry-run" output')
    parser.add_argument('infile', nargs = '?', default = '-')
    parser.add_argument('--ltp-root', dest = 'ltp_root', required = True,
                    help = 'location of LTP root directory')
    args = parser.parse_args()

    parse_input(args.infile, args.ltp_root)


if __name__ == '__main__':
     main()

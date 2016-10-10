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

import argparse
import fileinput
import os
import sys
import logging


class LtpTestScriptGenerator(object):
    '''Generate LTP test script from scenario group.

    Attributes:
        ltp_root: string, directory path of LTP root
        disabled_tests: string, file path of disabled_test.txt
        disabled_tests_list: list of string, list of disabled test names
    '''

    def __init__(self, ltp_root, disabled_tests):
        self.ltp_root = ltp_root
        self.disabled_tests = disabled_tests

    def ReadCommentedTxt(self, filepath):
        '''Read a lines of a file that are not commented by #.

        Args:
            filepath: string, path of file to read
        '''
        if not filepath:
            logging.error('Invalid file path')
            return None

        with open(filepath, 'r') as f:
            lines_gen = (line.strip() for line in f)
            return set(
                line for line in lines_gen
                if line and not line.startswith('#'))

    def GenerateLtpTestCases(self, testsuite):
        '''Generate test cases for each ltp test suite.

        Args:
            testsuite: string, test suite name
        '''
        testsuite_script = os.path.join(self.ltp_root, 'runtest', testsuite)
        testsuite = testsuite.replace('-', '_')

        for line in open(testsuite_script, 'r'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            testname = line.split()[0]
            testname_prefix = ('DISABLED_'
                               if testname in self.disabled_tests_list else '')
            testname_modified = testname_prefix + testname.replace('-', '_')

            print("\t".join([testsuite, testname_modified, line[len(
                testname):].strip()]))

    def GenerateLtpRunScript(self, scenario_group):
        '''Given a scenario group generate test case script.

        Args:
            scenario_group: string, file path of scanerio group file
        '''
        self.disabled_tests_list = self.ReadCommentedTxt(self.disabled_tests)

        ltp_testsuites = [line.strip()
                          for line in fileinput.input(scenario_group)
                          if line.strip()]

        for testsuite in ltp_testsuites:
            self.GenerateLtpTestCases(testsuite)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate ltp-testcases.h from an LTP test scenario')
    parser.add_argument('infile', nargs='?', default='-')
    parser.add_argument(
        '--ltp-root',
        dest='ltp_root',
        required=True,
        help='location of LTP root directory')
    parser.add_argument(
        '--disabled-tests',
        dest='disabled_tests',
        help='file with a list of disabled tests')

    args = parser.parse_args()

    generator = LtpTestScriptGenerator(args.ltp_root, args.disabled_tests)
    generator.GenerateLtpRunScript(args.infile)

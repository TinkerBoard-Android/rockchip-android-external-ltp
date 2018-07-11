#!/usr/bin/python
#
# Copyright 2017 - The Android Open Source Project
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

"""Generates a report on CKI syscall coverage in VTS LTP.

This module generates a report on the syscalls in the Android CKI and
their coverage in VTS LTP.

The coverage report provides, for each syscall in the CKI, the number of
enabled and disabled LTP tests for the syscall in VTS. If VTS test output is
supplied, the report instead provides the number of disabled, skipped, failing,
and passing tests for each syscall.

Assumptions are made about the structure of files in LTP source
and the naming convention.
"""

import argparse
import os.path
import re
import sys
import xml.etree.ElementTree as ET
import subprocess

if "ANDROID_BUILD_TOP" not in os.environ:
  print ("Please set up your Android build environment by running "
         "\". build/envsetup.sh\" and \"lunch\".")
  sys.exit(-1)

sys.path.append(os.path.join(os.environ["ANDROID_BUILD_TOP"],
                "bionic/libc/tools"))
import gensyscalls

sys.path.append(os.path.join(os.environ["ANDROID_BUILD_TOP"],
                             "test/vts-testcase/kernel/ltp/configs"))
import disabled_tests as vts_disabled
import stable_tests as vts_stable

bionic_libc_root = os.path.join(os.environ["ANDROID_BUILD_TOP"], "bionic/libc")

unistd_h_url = 'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/include/uapi/asm-generic/unistd.h'
arm64_unistd32_h_url = 'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/arch/arm64/include/asm/unistd32.h'
arm_syscall_tbl_url = 'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/arch/arm/tools/syscall.tbl'
x86_syscall_tbl_url = 'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/arch/x86/entry/syscalls/syscall_32.tbl'
x86_64_syscall_tbl_url = 'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/arch/x86/entry/syscalls/syscall_64.tbl'


class CKI_Coverage(object):
  """Determines current test coverage of CKI system calls in LTP.

  Many of the system calls in the CKI are tested by LTP. For a given
  system call an LTP test may or may not exist, that LTP test may or may
  not be currently compiling properly for Android, the test may not be
  stable, the test may not be running due to environment issues or
  passing. This class looks at various sources of information to determine
  the current test coverage of system calls in the CKI from LTP.

  Note that due to some deviations in LTP of tests from the common naming
  convention there there may be tests that are flagged here as not having
  coverage when in fact they do.
  """

  LTP_SYSCALL_ROOT = os.path.join(os.environ["ANDROID_BUILD_TOP"],
                                  "external/ltp/testcases/kernel/syscalls")
  DISABLED_IN_LTP_PATH = os.path.join(os.environ["ANDROID_BUILD_TOP"],
                        "external/ltp/android/tools/disabled_tests.txt")

  ltp_full_set = []

  cki_syscalls = []

  disabled_in_ltp = []
  disabled_in_vts_ltp = vts_disabled.DISABLED_TESTS
  stable_in_vts_ltp = vts_stable.STABLE_TESTS

  syscall_tests = {}
  disabled_tests = {}
  failing_tests = {}
  skipped_tests = {}
  passing_tests = {}

  test_results = {}

  def __init__(self, arch):
    self._arch = arch

  def load_ltp_tests(self):
    """Load the list of LTP syscall tests.

    Load the list of all syscall tests existing in LTP.
    """
    for path, dirs, files in os.walk(self.LTP_SYSCALL_ROOT):
      for filename in files:
        basename, ext = os.path.splitext(filename)
        if ext != ".c": continue
        self.ltp_full_set.append(basename)

  def load_ltp_disabled_tests(self):
    """Load the list of LTP tests not being compiled.

    The LTP repository in Android contains a list of tests which are not
    compiled due to incompatibilities with Android.
    """
    with open(self.DISABLED_IN_LTP_PATH) as fp:
      for line in fp:
        line = line.strip()
        if not line: continue
        test_re = re.compile(r"^(\w+)")
        test_match = re.match(test_re, line)
        if not test_match: continue
        self.disabled_in_ltp.append(test_match.group(1))

  def ltp_test_special_cases(self, syscall, test):
    """Detect special cases in syscall to LTP mapping.

    Most syscall tests in LTP follow a predictable naming
    convention, but some do not. Detect known special cases.

    Args:
      syscall: The name of a syscall.
      test: The name of a testcase.

    Returns:
      A boolean indicating whether the given syscall is tested
      by the given testcase.
    """
    if syscall == "clock_nanosleep" and test == "clock_nanosleep2_01":
      return True
    if syscall == "fadvise" and test.startswith("posix_fadvise"):
      return True
    if syscall == "futex" and test.startswith("futex_"):
      return True
    if syscall == "inotify_add_watch" or syscall == "inotify_rm_watch":
      test_re = re.compile(r"^inotify\d+$")
      if re.match(test_re, test):
        return True
    if syscall == "newfstatat":
      test_re = re.compile(r"^fstatat\d+$")
      if re.match(test_re, test):
        return True

    return False

  def match_syscalls_to_tests(self, syscalls):
    """Match syscalls with tests in LTP.

    Create a mapping from CKI syscalls and tests in LTP. This mapping can
    largely be determined using a common naming convention in the LTP file
    hierarchy but there are special cases that have to be taken care of.

    Args:
      syscalls: List of syscall structures containing all syscalls
        in the CKI.
    """
    for syscall in syscalls:
      if self._arch is not None and self._arch not in syscall:
        continue
      self.cki_syscalls.append(syscall["name"])
      self.syscall_tests[syscall["name"]] = []
      # LTP does not use the 64 at the end of syscall names for testcases.
      ltp_syscall_name = syscall["name"]
      if ltp_syscall_name.endswith("64"):
        ltp_syscall_name = ltp_syscall_name[0:-2]
      # Most LTP syscalls have source files for the tests that follow
      # a naming convention in the regexp below. Exceptions exist though.
      # For now those are checked for specifically.
      test_re = re.compile(r"^%s_?0?\d\d?$" % ltp_syscall_name)
      for test in self.ltp_full_set:
        if (re.match(test_re, test) or
            self.ltp_test_special_cases(ltp_syscall_name, test)):
          # The filenames of the ioctl tests in LTP do not match the name
          # of the testcase defined in that source, which is what shows
          # up in VTS.
          if ltp_syscall_name == "ioctl":
            test = "ioctl01_02"
          self.syscall_tests[syscall["name"]].append(test)
    self.cki_syscalls.sort()

  def update_test_status(self):
    """Populate test configuration and output for all CKI syscalls.

    Go through VTS test configuration to populate data for all CKI syscalls.
    """
    for syscall in self.cki_syscalls:
      self.disabled_tests[syscall] = []
      if not self.syscall_tests[syscall]:
        continue
      for test in self.syscall_tests[syscall]:
        if (test in self.disabled_in_ltp or
            "syscalls.%s" % test in self.disabled_in_vts_ltp or
            ("syscalls.%s_32bit" % test not in self.stable_in_vts_ltp and
             "syscalls.%s_64bit" % test not in self.stable_in_vts_ltp)):
          self.disabled_tests[syscall].append(test)
          continue

  def output_results(self):
    """Pretty print the CKI syscall LTP coverage."""
    count = 0
    uncovered = 0

    print ""
    print "         Covered Syscalls"
    for syscall in self.cki_syscalls:
      if (len(self.syscall_tests[syscall]) -
          len(self.disabled_tests[syscall]) <= 0):
        continue
      if not count % 20:
        print ("%25s   Disabled Enabled -------------" %
               "-------------")
      sys.stdout.write("%25s   %s        %s\n" %
                       (syscall, len(self.disabled_tests[syscall]),
                        len(self.syscall_tests[syscall]) -
                        len(self.disabled_tests[syscall])))
      count += 1

    count = 0
    print "\n"
    print "       Uncovered Syscalls"
    for syscall in self.cki_syscalls:
      if (len(self.syscall_tests[syscall]) -
          len(self.disabled_tests[syscall]) > 0):
        continue
      if not count % 20:
        print ("%25s   Disabled Enabled -------------" %
               "-------------")
      sys.stdout.write("%25s   %s        %s\n" %
                       (syscall, len(self.disabled_tests[syscall]),
                        len(self.syscall_tests[syscall]) -
                        len(self.disabled_tests[syscall])))
      uncovered += 1
      count += 1

    print ""
    print ("Total uncovered syscalls: %s out of %s" %
           (uncovered, len(self.cki_syscalls)))

  def output_summary(self):
    """Print a one line summary of the CKI syscall LTP coverage.

    Pretty prints a one line summary of the CKI syscall coverage in LTP
    for the specified architecture.
    """
    uncovered_with_test = 0
    uncovered_without_test = 0
    for syscall in self.cki_syscalls:
      if (len(self.syscall_tests[syscall]) -
          len(self.disabled_tests[syscall]) > 0):
        continue
      if (len(self.disabled_tests[syscall]) > 0):
        uncovered_with_test += 1
      else:
        uncovered_without_test += 1
    print ("arch, cki syscalls, uncovered with disabled test(s), "
           "uncovered with no tests, total uncovered")
    print ("%s, %s, %s, %s, %s" % (self._arch, len(self.cki_syscalls),
                                uncovered_with_test, uncovered_without_test,
                                uncovered_with_test + uncovered_without_test))

  def add_syscall(self, cki, syscall, arch):
    """Note that a syscall has been seen for a particular arch."""
    seen = False
    for s in cki.syscalls:
      if s["name"] == syscall:
        s[arch]= True
        seen = True
        break
    if not seen:
      cki.syscalls.append({"name":syscall, arch:True})

  def get_x86_64_kernel_syscalls(self, cki):
    """Retrieve the list of syscalls for x86_64."""
    proc = subprocess.Popen(['curl', x86_64_syscall_tbl_url], stdout=subprocess.PIPE)
    while True:
      line = proc.stdout.readline()
      if line != b'':
        test_re = re.compile(r"^\d+\s+\w+\s+(\w+)\s+(__x64_sys|__x32_compat_sys)")
        test_match = re.match(test_re, line)
        if test_match:
          syscall = test_match.group(1)
          self.add_syscall(cki, syscall, "x86_64")
      else:
        break

  def get_x86_kernel_syscalls(self, cki):
    """Retrieve the list of syscalls for x86."""
    proc = subprocess.Popen(['curl', x86_syscall_tbl_url], stdout=subprocess.PIPE)
    while True:
      line = proc.stdout.readline()
      if line != b'':
        test_re = re.compile(r"^\d+\s+i386\s+(\w+)\s+sys_")
        test_match = re.match(test_re, line)
        if test_match:
          syscall = test_match.group(1)
          self.add_syscall(cki, syscall, "x86")
      else:
        break

  def get_arm_kernel_syscalls(self, cki):
    """Retrieve the list of syscalls for arm."""
    proc = subprocess.Popen(['curl', arm_syscall_tbl_url], stdout=subprocess.PIPE)
    while True:
      line = proc.stdout.readline()
      if line != b'':
        test_re = re.compile(r"^\d+\s+\w+\s+(\w+)\s+sys_")
        test_match = re.match(test_re, line)
        if test_match:
          syscall = test_match.group(1)
          self.add_syscall(cki, syscall, "arm")
      else:
        break

  def get_arm64_kernel_syscalls(self, cki):
    """Retrieve the list of syscalls for arm64."""
    # Add AArch64 syscalls
    proc = subprocess.Popen(['curl', unistd_h_url], stdout=subprocess.PIPE)
    while True:
      line = proc.stdout.readline()
      if line != b'':
        test_re = re.compile(r"^#define __NR(3264)?_(\w+)\s+(\d+)$")
        test_match = re.match(test_re, line)
        if test_match:
          syscall = test_match.group(2)
          if (syscall == "sync_file_range2" or
              syscall == "arch_specific_syscall" or
              syscall == "syscalls"):
              continue
          self.add_syscall(cki, syscall, "arm64")
      else:
        break
    # Add AArch32 syscalls
    proc = subprocess.Popen(['curl', arm64_unistd32_h_url], stdout=subprocess.PIPE)
    while True:
      line = proc.stdout.readline()
      if line != b'':
        test_re = re.compile(r"^#define __NR(3264)?_(\w+)\s+(\d+)$")
        test_match = re.match(test_re, line)
        if test_match:
          syscall = test_match.group(2)
          self.add_syscall(cki, syscall, "arm64")
      else:
        break

  def get_kernel_syscalls(self, cki, arch):
    self.get_arm64_kernel_syscalls(cki)
    self.get_arm_kernel_syscalls(cki)
    self.get_x86_kernel_syscalls(cki)
    self.get_x86_64_kernel_syscalls(cki)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Output list of system calls "
          "in the Common Kernel Interface and their VTS LTP coverage.")
  parser.add_argument("-a", "--arch", help="only show syscall CKI for specific arch")
  parser.add_argument("-l", action="store_true",
                      help="list CKI syscalls only, without coverage")
  parser.add_argument("-s", action="store_true",
                      help="print one line summary of CKI coverage for arch")
  parser.add_argument("-f", action="store_true",
                      help="only check syscalls with known Android use")

  args = parser.parse_args()
  if args.arch is not None and args.arch not in gensyscalls.all_arches:
    print "Arch must be one of the following:"
    print gensyscalls.all_arches
    exit(-1)

  cki = gensyscalls.SysCallsTxtParser()
  cki_cov = CKI_Coverage(args.arch)

  if args.f:
    cki.parse_file(os.path.join(bionic_libc_root, "SYSCALLS.TXT"))
    cki.parse_file(os.path.join(bionic_libc_root, "SECCOMP_WHITELIST_APP.TXT"))
    cki.parse_file(os.path.join(bionic_libc_root, "SECCOMP_WHITELIST_COMMON.TXT"))
    cki.parse_file(os.path.join(bionic_libc_root, "SECCOMP_WHITELIST_SYSTEM.TXT"))
    cki.parse_file(os.path.join(bionic_libc_root, "SECCOMP_WHITELIST_GLOBAL.TXT"))
  else:
    cki_cov.get_kernel_syscalls(cki, args.arch)

  if args.l:
    for syscall in cki.syscalls:
      if args.arch is None or syscall[args.arch]:
        print syscall["name"]
    exit(0)

  cki_cov.load_ltp_tests()
  cki_cov.load_ltp_disabled_tests()
  cki_cov.match_syscalls_to_tests(cki.syscalls)
  cki_cov.update_test_status()

  beta_string = ("*** WARNING: This script is still in development and may\n"
                 "*** report both false positives and negatives.")
  print beta_string

  if args.s:
    cki_cov.output_summary()
    exit(0)

  cki_cov.output_results()
  print beta_string

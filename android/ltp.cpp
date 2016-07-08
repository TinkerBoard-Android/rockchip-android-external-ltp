/*
 * Copyright (C) 2016 The Android Open Source Project
 *
 *
 * This software is licensed under the terms of the GNU General Public
 * License version 2, as published by the Free Software Foundation, and
 * may be copied, distributed, and modified under those terms.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 */

#include <libgen.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <gtest/gtest.h>

#include "RecursiveTemporaryDir.h"

static bool fileExists(const char *path) {
    struct stat s;
    return stat(path, &s) == 0;
}

class LtpTestcase : public ::testing::Test {
protected:
    LtpTestcase() {}
    virtual ~LtpTestcase() {}

    void runTest(const std::string &testexe,
		    std::vector<std::string> extraArgs = {}) {
        // Some tests (e.g. access02) drop to a lower-privileged user like
        // nobody.  Make sure they have permission to poke at the sandbox we've
        // set up for them.
        int err = chmod(tmpdir.path, S_IRWXU | S_IRWXG);
        if (err < 0) {
            perror("chmod() failed");
            exit(1);
        }

        pid_t pid = fork();
        ASSERT_NE(-1, pid);

        if (pid == 0) {
            runChild(testexe, extraArgs);
        } else {
            int status;
            pid_t waited = waitpid(pid, &status, 0);
            ASSERT_NE(-1, waited);

            int exitStatus = WEXITSTATUS(status);
            if (exitStatus == TCONF) {
                GTEST_LOG_(WARNING) << "testcase skipped" << std::endl;
                return;
            }
            EXPECT_EQ(TPASS, exitStatus);
        }
    }

    std::string executableDirectory() {
        char selfpath[PATH_MAX]{0};
        ssize_t err = readlink("/proc/self/exe", selfpath, sizeof(selfpath));
        if (err < 0) {
            perror("realpath() failed");
            return "";
        }

        return dirname(selfpath);
    }

    const RecursiveTemporaryDir tmpdir;

private:
    void runChild(std::string testexe, std::vector<std::string> &extraArgs) {
        auto err = chdir(tmpdir.path);
        if (err < 0) {
            perror("chdir() failed");
            exit(1);
        }

        auto ltpRoot = executableDirectory();
        if (ltpRoot == "")
            exit(1);
        auto binDir = ltpRoot + "/testcases/bin";

        char cmdline[PATH_MAX];
        snprintf(cmdline, sizeof(cmdline), "%s/%s", binDir.c_str(),
                testexe.c_str());
        if (!fileExists(cmdline)) {
            /* Some test names have underscores in place of hyphens, since C++
             * doesn't allow hyphens in class names
             */
            std::replace(testexe.begin(), testexe.end(), '_', '-');
            snprintf(cmdline, sizeof(cmdline), "%s/%s", binDir.c_str(),
                    testexe.c_str());
        }

        std::vector<char *> argv;
        argv.push_back(cmdline);
        for (auto &arg : extraArgs) {
            while (true) {
                auto ltpRootVar = arg.find("$LTPROOT");
                if (ltpRootVar == std::string::npos)
                    break;
                arg.replace(ltpRootVar, strlen("$LTPROOT"), ltpRoot);
            }
            argv.push_back(&arg[0]);
        }
        argv.push_back(nullptr);

        char tmpdir_envp[PATH_MAX];
        snprintf(tmpdir_envp, sizeof(tmpdir_envp), "TMPDIR=%s", tmpdir.path);
        char tmp_envp[PATH_MAX];
        snprintf(tmp_envp, sizeof(tmp_envp), "TMP=%s", tmpdir.path);
        char ltproot_envp[PATH_MAX];
        snprintf(ltproot_envp, sizeof(ltproot_envp), "LTPROOT=%s",
                ltpRoot.c_str());
        char path_envp[PATH_MAX];
        snprintf(path_envp, sizeof(path_envp), "PATH=/system/bin:%s",
                binDir.c_str());
        char fs_type_envp[PATH_MAX];
        snprintf(fs_type_envp, sizeof(fs_type_envp), "LTP_DEV_FS_TYPE=ext4");
        char *envp[] = { tmpdir_envp, tmp_envp, ltproot_envp, path_envp, fs_type_envp, nullptr };

        execve(cmdline, &argv[0], envp);
        perror("execve() failed");
        exit(1);
    }

    const int TPASS = 0;
    const int TCONF = 32;
};

#define LTP_TESTSUITE(testsuite)                                	\
    class testsuite : public LtpTestcase { }

#define LTP_TESTCASE(testsuite, testname, testexe, ...)         	\
    TEST_F(testsuite, testname) {                               	\
        ASSERT_NO_FATAL_FAILURE(runTest(#testexe, ##__VA_ARGS__));	\
    }

#include "ltp-testcases.h"

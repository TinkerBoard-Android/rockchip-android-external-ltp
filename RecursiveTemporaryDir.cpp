/*
 * Copyright (C) 2016 The Android Open Source Project
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

#include "RecursiveTemporaryDir.h"

#include <ftw.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

RecursiveTemporaryDir::RecursiveTemporaryDir() {
    memcpy(path, tempDirTemplate, sizeof(path));
    mkdtemp(path);
}

static int nftwCallback(const char *fpath, const struct stat */*sb*/,
        int typeflag, struct FTW */*ftwbuf*/) {
    if (typeflag == FTW_DP)
        rmdir(fpath);
    else if (typeflag == FTW_F || typeflag == FTW_SL)
        unlink(fpath);

    return 0;
}

RecursiveTemporaryDir::~RecursiveTemporaryDir() {
    nftw(path, nftwCallback, 1, FTW_DEPTH | FTW_PHYS);
    rmdir(path);
}

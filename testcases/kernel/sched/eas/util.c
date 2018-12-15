/*
 * Copyright (c) 2018 Google, Inc.
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#define _GNU_SOURCE
#include <fcntl.h>
#include <sched.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#include "tst_cpu.h"

#include "util.h"

void affine(int cpu)
{
	cpu_set_t cpuset;
	CPU_ZERO(&cpuset);
	CPU_SET(cpu, &cpuset);
	ERROR_CHECK(sched_setaffinity(0, sizeof(cpu_set_t), &cpuset));
}

/*
 * Busywait for a certain amount of wallclock time.
 * If sleep is nonzero, sleep for 1ms between each check.
 */
void burn(unsigned int usec, int sleep)
{
	unsigned long long now_usec, end_usec;
	struct timespec ts;

	if (clock_gettime(CLOCK_MONOTONIC, &ts)) {
		printf("clock_gettime() reported an error\n");
		return;
	}
	end_usec = (ts.tv_sec) * USEC_PER_SEC + (ts.tv_nsec / 1000) + usec;
	while(1) {
		if (clock_gettime(CLOCK_MONOTONIC, &ts)) {
			printf("clock_gettime() reported an error\n");
			return;
		}
		now_usec = ts.tv_sec * USEC_PER_SEC + ts.tv_nsec / 1000;
		if (now_usec > end_usec)
			return;
		if (sleep)
			usleep(1000);
	}
}

/*
 * get_bigs = 0, search for smallest CPUs
 * get_bigs = 1, search for CPUs other than the smallest CPUs
 */
#define CAP_STATE_FILE_SIZE 1024
int find_cpus_with_capacity(int get_bigs, cpu_set_t *cpuset)
{
	int i, bytes, rv;
	unsigned int smallest = -1;
	char cap_states_file[100];

	CPU_ZERO(cpuset);

	for (i = 0; i < tst_ncpus(); i++) {
		int cap_states_fd;
		unsigned int cap;
		char *filebuf, *tmp1, *tmp2;

		sprintf(cap_states_file,
			"/proc/sys/kernel/sched_domain/cpu%d/domain0/group0/energy/cap_states",
			i);
		cap_states_fd = open(cap_states_file, O_RDONLY);
		if (cap_states_fd == -1) {
			printf("Could not open cap_states file %s: ",
			       cap_states_file);
			perror(NULL);
			return -1;
		}
		bytes = CAP_STATE_FILE_SIZE;
		filebuf = calloc(1, CAP_STATE_FILE_SIZE + 1);
		if (!filebuf) {
			printf("Failed to calloc buffer for cap_states\n");
			return -1;
		}
		tmp1 = filebuf;
		while (bytes) {
			rv = read(cap_states_fd, tmp1, bytes);
			if (rv == -1) {
				printf("Could not read cap_states\n");
				return -1;
			}
			if (rv == 0)
				break;
			tmp1 += rv;
			bytes -= rv;
		}
		if (tmp1 - filebuf == CAP_STATE_FILE_SIZE) {
			printf("CAP_STATE_FILE_SIZE exhausted, increase\n");
			return -1;
		}
		tmp1 = strrchr(filebuf, '\t');
		if (!tmp1 || tmp1 == filebuf ) {
			printf("Malformatted cap_states_file (1).\n%s\n",
			       filebuf);
			return -1;
		}
		tmp1 = strrchr(tmp1 - 1, '\t');
		if (!tmp1 || tmp1 == filebuf) {
			printf("Malformatted cap_states_file (2).\n%s\n",
			       filebuf);
			return -1;
		}
		tmp1 = strrchr(tmp1 - 1, '\t');
		if (!tmp1 || tmp1 == filebuf) {
			printf("Malformatted cap_states_file (3).\n%s\n",
			       filebuf);
			return -1;
		}
		/* tmp1 now points to tab after the capacity we want. */
		*tmp1 = 0;
		tmp2 = strrchr(tmp1 - 1, '\t');
		if (!tmp2)
			tmp2 = filebuf;
		else
			tmp2++;
		if (sscanf(tmp2,"%d", &cap) != 1) {
		       printf("Failed to parse capacity from cap_states.\n");
		       return -1;
		}
		if (close(cap_states_fd)) {
			printf("Failed to close cap_states file.\n");
			return -1;
		}

		if (cap < smallest) {
			smallest = cap;
			CPU_ZERO(cpuset);
			CPU_SET(i, cpuset);
		} else if (cap == smallest) {
			CPU_SET(i, cpuset);
		}
	}

	if (!get_bigs)
		return 0;

	for (i = 0; i < tst_ncpus(); i++)
		if (CPU_ISSET(i, cpuset))
			CPU_CLR(i, cpuset);
		else
			CPU_SET(i, cpuset);

	return 0;
}


#include <linux/msg.h>
#include <sys/types.h>

int msgget(key_t, int);
ssize_t msgrcv(int, void *, size_t, long, int);
int msgsnd(int, const void *, size_t, int);
int msgctl(int, int, struct msqid_ds *);


#include <stdlib.h>
#include <stdio.h>
#include <signal.h>

int
main(int argc, char *argv[])
{
	int res;

	if (argc == 1) {
		printf("Usage: raise SIGNAL_NUMBER\n");
		return 1;
	}
	res = raise(atoi(argv[1]));
	if (res != 0)
		perror("raise");
	return res;
}

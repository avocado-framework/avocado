#include <stdlib.h>
#include <stdio.h>
#include <signal.h>

/*
 * Signal numbers are translated to exit code by the shell.
 * For example, if SIGUSR1 is raised (sinal number 10) then
 * the exit code will be 128+10 = 138.
 *
 * In the case of avocado.utils.process.SubProcess, the exit code is
 * the negative value of the signal, so SIGUSR1 will return -10.
 *
 * See http://tldp.org/LDP/abs/html/exitcodes.html
 */

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
	else
		printf("I'm alive!\n");
	return res;
}

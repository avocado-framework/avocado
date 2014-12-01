#include <stdlib.h>

int main(int argc, char *argv[])
{
	void *p = malloc(1024);
	free(p);
	free(p);
	return 0;
}

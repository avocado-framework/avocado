#include <stdlib.h>
#include <stdio.h>
#include <time.h>

void handle_exception() {
    void *p = malloc(1024);
    free(p);
    free(p);
}

int main(int argc, char *argv[])
{
    int num;
    srand(time(NULL));
    num = rand();
    if (num < (RAND_MAX / 10)) {
        handle_exception();
    }
    return 0;
}

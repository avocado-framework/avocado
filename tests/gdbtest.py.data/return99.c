#include <stdio.h>
#include <stdlib.h>

void empty()
{
}

void write_stdout()
{
  fprintf(stdout, "testing output to stdout\n");
}

void write_stderr()
{
  fprintf(stderr, "testing output to stderr\n");
}

int forkme()
{
  int pid;

  pid = fork();
  if (pid != 0)
    pid = fork();
  if (pid != 0)
    pid = fork();

  return pid;
}

int main(int argc, char *argv[])
{
  int exit_status = 99;

  if (argc > 1)
    exit_status = atoi(argv[1]);

  empty();
  write_stdout();
  write_stderr();

  if (forkme()) {
    fprintf(stdout, "return %i\n", exit_status);
  }

  return exit_status;
}

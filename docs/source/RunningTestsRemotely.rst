========================
 Running Tests Remotely
========================

Running Tests on a Remote Host
==============================

Avocado lets you run tests directly in a remote machine with SSH
connection, provided that you properly set it up by installing Avocado
in it.

You can check if this feature (a plugin) is enabled by running::

    $ avocado plugins
    ...
    remote  Remote machine options for 'run' subcommand
    ...

Assuming this feature is enabled, you should be able to pass the following options
when using the ``run`` command in the Avocado command line tool::

   --remote-hostname REMOTE_HOSTNAME
                         Specify the hostname to login on remote machine
   --remote-port REMOTE_PORT
                         Specify the port number to login on remote machine.
                         Default: 22
   --remote-username REMOTE_USERNAME
                         Specify the username to login on remote machine
   --remote-password REMOTE_PASSWORD
                         Specify the password to login on remote machine

From these options, you are normally going to use `--remote-hostname` and
`--remote-username` in case you did set up your VM with password-less
SSH connection (through SSH keys).

Remote Setup
------------

Make sure you have:

 1) Avocado packages installed. You can see more info on how to do that in
    the :ref:`get-started` section.
 2) The remote machine IP address or fully qualified hostname and the SSH port number.
 3) All pre-requisites for your test to run installed inside the remote machine
    (gcc, make and others if you want to compile a 3rd party test suite written
    in C, for example).

Optionally, you may have password less SSH login on your remote machine enabled.

Running your test
-----------------

Once the remote machine is properly setup, you may run your test. Example::

    $ scripts/avocado run --remote-hostname 192.168.122.30 --remote-username fedora examples/tests/sleeptest.py examples/tests/failtest.py
    REMOTE LOGIN  : fedora@192.168.122.30:22
    JOB ID    : 60ddd718e7d7bb679f258920ce3c39ce73cb9779
    JOB LOG   : $HOME/avocado/job-results/job-2014-10-23T11.45-a329461/job.log
    TESTS     : 2
     (1/2) examples/tests/sleeptest.py: PASS (1.00 s)
     (2/2) examples/tests/failtest.py: FAIL (0.00 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    TESTS TIME : 1.01 s

As you can see, Avocado will copy the tests you have to your remote machine and
execute them. A bit of extra logging information is added to your job summary,
mainly to distinguish the regular execution from the remote one. Note here that
we did not need `--remote-password` because an SSH key was already setup.

Running Tests on a Virtual Machine
==================================

Sometimes you don't want to run a given test directly in your own machine
(maybe the test is dangerous, maybe you need to run it in another Linux
distribution, so on and so forth).

For those scenarios, Avocado lets you run tests directly in VMs
defined as libvirt domains in your system, provided that you properly
set them up.

You can check if this feature (a plugin) is enabled by running::

    $ avocado plugins
    ...
    vm      Virtual Machine options for 'run' subcommand
    ...

Assuming this feature is enabled, you should be able to pass the following options
when using the ``run`` command in the Avocado command line tool::

      --vm                  Run tests on Virtual Machine
      --vm-hypervisor-uri VM_HYPERVISOR_URI
                            Specify hypervisor URI driver connection
      --vm-domain VM_DOMAIN
                            Specify domain name (Virtual Machine name)
      --vm-hostname VM_HOSTNAME
                            Specify VM hostname to login. By default Avocado
                            attempts to automatically find the VM IP address.
      --vm-username VM_USERNAME
                            Specify the username to login on VM
      --vm-password VM_PASSWORD
                            Specify the password to login on VM
      --vm-cleanup          Restore VM to a previous state, before running the
                            tests

From these options, you are normally going to use `--vm-domain`,
`--vm-hostname` and `--vm-username` in case you did set up your VM with
password-less SSH connection (through SSH keys).

If your VM has the ``qemu-guest-agent`` installed, you can skip the
``--vm-hostname`` option. Avocado will then probe the VM IP from the
agent.

Virtual Machine Setup
---------------------

Make sure you have:

 1) A libvirt domain with the Avocado packages installed. You can see
    more info on how to do that in the :ref:`get-started` section.
 2) The domain IP address or fully qualified hostname.
 3) All pre-requesites for your test to run installed inside the VM
    (gcc, make and others if you want to compile a 3rd party test suite written
    in C, for example).

Optionally, you may have password less SSH login on your VM enabled.

Running your test
-----------------

Once the virtual machine is properly setup, you may run your test. Example::

    $ scripts/avocado run --vm-domain fedora20 --vm-username autotest --vm examples/tests/sleeptest.py examples/tests/failtest.py
    VM DOMAIN : fedora20
    VM LOGIN  : autotest@192.168.122.30
    JOB ID    : 60ddd718e7d7bb679f258920ce3c39ce73cb9779
    JOB LOG   : $HOME/avocado/job-results/job-2014-09-16T18.41-60ddd71/job.log
    TESTS     : 2
     (1/2) examples/tests/sleeptest.py:SleepTest.test: PASS (1.00 s)
     (2/2) examples/tests/failtest.py:FailTest.test: FAIL (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    TESTS TIME : 1.01 s

As you can see, Avocado will copy the tests you have to your libvirt domain and
execute them. A bit of extra logging information is added to your job summary,
mainly to distinguish the regular execution from the remote one. Note here that
we did not need `--vm-password` because the SSH key is already setup.

Running Tests on a Docker container
===================================

Avocado also lets you run tests on a Docker container, starting and
cleaning it up automatically with every execution.

You can check if this feature (a plugin) is enabled by running::

    $ avocado plugins
    ...
    docker  Run tests inside docker container
    ...

Docker container images
-----------------------

Avocado needs to be present inside the container image in order for
the test execution to be properly performed.  There's one ready to use
image (``ldoktor/fedora-avocado``) in the default image repository
(``docker.io``)::

    $ sudo docker pull ldoktor/fedora-avocado
    Using default tag: latest
    Trying to pull repository docker.io/ldoktor/fedora-avocado ...
    latest: Pulling from docker.io/ldoktor/fedora-avocado
    ...
    Status: Downloaded newer image for docker.io/ldoktor/fedora-avocado:latest

Use custom docker images
------------------------

One of the possible ways to use (and develop) Avocado is to create a
docker image with your development tree.  This is a good way to test
your development branch without breaking your system.

To do so, you can following a few simple steps. Begin by fetching the
source code as usual::

  $ git clone github.com/avocado-framework/avocado.git avocado.git

You may want to make some changes to Avocado::

  $ cd avocado.git
  $ patch -p1 < MY_PATCH

Finally build a docker image::

  $ docker build -t fedora-avocado-custom -f contrib/docker/Dockerfile.fedora .

And now you can run tests with your modified Avocado inside your
container::

  $ avocado run --docker fedora-avocado-custom examples/tests/passtest.py

Running your test
-----------------

Assuming your system is properly setup to run Docker, including having
an image with Avocado, you can run a test inside the container with a
command similar to::

    $ avocado run passtest.py warntest.py failtest.py --docker ldoktor/fedora-avocado --docker-cmd "sudo docker"
    DOCKER     : Container id '4bcbcd69801211501a0dde5926c0282a9630adbe29ecb17a21ef04f024366943'
    JOB ID     : db309f5daba562235834f97cad5f4458e3fe6e32
    JOB LOG    : $HOME/avocado/job-results/job-2016-07-25T08.01-db309f5/job.log
    TESTS      : 3
     (1/3) /avocado_remote_test_dir/$HOME/passtest.py:PassTest.test: PASS (0.00 s)
     (2/3) /avocado_remote_test_dir/$HOME/warntest.py:WarnTest.test: WARN (0.00 s)
     (3/3) /avocado_remote_test_dir/$HOME/failtest.py:FailTest.test: FAIL (0.00 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 1 | INTERRUPT 0
    TESTS TIME : 0.00 s
    JOB HTML   : $HOME/avocado/job-results/job-2016-07-25T08.01-db309f5/html/results.html

Environment Variables
=====================

Running remote instances os Avocado, for example using `remote` or `vm`
plugins, the remote environment has a different set of environment variables.
If you want to make available remotely variables that are available in the
local environment, you can use the `run` option `--env-keep`. See the example
below::

    $ export MYVAR1=foobar
    $ env MYVAR2=foobar2 avocado run passtest.py --env-keep MYVAR1,MYVAR2 --remote-hostname 192.168.122.30 --remote-username fedora

By doing that, both `MYVAR1` and `MYVAR2` will be available in remote
environment.

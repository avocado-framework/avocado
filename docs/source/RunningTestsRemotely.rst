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

If you have the VM already running, or have had it running a "while"
back, you can probably skip the `--vm-hostname` option as Avocado will
attempt to find out the VM IP address based on the MAC address and ARP
table.

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

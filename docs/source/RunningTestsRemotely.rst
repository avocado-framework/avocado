========================
 Running Tests Remotely
========================

Running Tests on a Remote Host
==============================

Avocado implements a feature that lets
you run tests directly in a remote machine with SSH connection,
provided that you properly set it up by installing Avocado in it.

The remote plugin is one of the basic plugins provided by Avocado.
You can check for its presence by listing your plugins::

    $ scripts/avocado plugins
    Plugins loaded:
        ...
        run_remote - Run tests on a remote machine (Enabled)
        ...

This plugin adds a number of options to the Avocado test runner::

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

 1) Avocado RPM installed. You can see more info on
    how to do that in the Getting Started Guide.
 2) The domain IP address or fully qualified hostname and the port number.
 3) All pre-requesites for your test to run installed inside the remote machine
    (gcc, make and others if you want to compile a 3rd party test suite written
    in C, for example).
 4) Optionally, you may have password less SSH login on your remote machine enabled.


Running your test
-----------------

Once everything is verified and covered, you may run your test. Example::

    $ scripts/avocado run --remote-hostname 192.168.122.30 --remote-username fedora examples/tests/sleeptest.py examples/tests/failtest.py
    REMOTE LOGIN  : fedora@192.168.122.30:22
    JOB ID    : 60ddd718e7d7bb679f258920ce3c39ce73cb9779
    JOB LOG   : $HOME/avocado/job-results/job-2014-10-23T11.45-a329461/job.log
    TESTS     : 2
    (1/2) examples/tests/sleeptest.py: PASS (1.00 s)
    (2/2) examples/tests/failtest.py: FAIL (0.00 s)
    PASS      : 1
    ERROR     : 0
    FAIL      : 1
    SKIP      : 0
    WARN      : 0
    TIME      : 1.01 s

As you can see, Avocado will copy the tests you have to your remote machine and
execute them. A bit of extra logging information is added to your job summary,
mainly to distinguish the regular execution from the remote one. Note here that
we did not need `--remote-password` because the SSH key is already setup.

Running Tests on a Virtual Machine
==================================

Sometimes you don't want to run a given test directly in your laptop
(maybe the test is dangerous, maybe you need to run it in another linux
distribution, so on and so forth). Avocado implements a feature that lets
you run tests directly in VMs defined as libvirt domains in your system,
provided that you properly set up that VM.

The vm plugin is one of the basic plugins provided by Avocado. You can check
for its presence by listing your plugins::

    $ scripts/avocado plugins
    Plugins loaded:
        ...
        run_vm - Run tests on a Virtual Machine (Enabled)
        ...

This plugin adds a number of options to the Avocado test runner::

      --vm                  Run tests on Virtual Machine
      --vm-hypervisor-uri VM_HYPERVISOR_URI
                            Specify hypervisor URI driver connection
      --vm-domain VM_DOMAIN
                            Specify domain name (Virtual Machine name)
      --vm-hostname VM_HOSTNAME
                            Specify VM hostname to login
      --vm-username VM_USERNAME
                            Specify the username to login on VM
      --vm-password VM_PASSWORD
                            Specify the password to login on VM
      --vm-cleanup          Restore VM to a previous state, before running the
                            tests

From these options, you are normally going to use `--vm-domain`,
`--vm-hostname` and `--vm-username` in case you did set up your VM with
password-less SSH connection (through SSH keys).

Virtual Machine Setup
---------------------

Make sure you have:

 1) A libvirt domain with an Avocado RPM installed. You can see more info on
    how to do that in the Getting Started Guide.
 2) The domain IP address or fully qualified hostname
 3) All pre-requesites for your test to run installed inside the VM
    (gcc, make and others if you want to compile a 3rd party test suite written
    in C, for example).
 4) Optionally, you may have password less SSH login on your VM enabled.


Running your test
-----------------

Once everything is verified and covered, you may run your test. Example::

    $ scripts/avocado run --vm-domain fedora20 --vm-hostname 192.168.122.30 --vm-username autotest --vm examples/tests/sleeptest.py examples/tests/failtest.py
    VM DOMAIN : fedora20
    VM LOGIN  : autotest@192.168.122.30
    JOB ID    : 60ddd718e7d7bb679f258920ce3c39ce73cb9779
    JOB LOG   : $HOME/avocado/job-results/job-2014-09-16T18.41-60ddd71/job.log
    TESTS     : 2
    (1/2) examples/tests/sleeptest.py: PASS (1.00 s)
    (2/2) examples/tests/failtest.py: FAIL (0.00 s)
    PASS      : 1
    ERROR     : 0
    FAIL      : 1
    SKIP      : 0
    WARN      : 0
    TIME      : 1.01 s

As you can see, Avocado will copy the tests you have to your libvirt domain and
execute them. A bit of extra logging information is added to your job summary,
mainly to distinguish the regular execution from the remote one. Note here that
we did not need `--vm-password` because the SSH key is already setup.

README
======

Here is a basic playbook (`deployment.yml`) to test the deployment of
Avocado in a number of different environments, and installed via
different methods.

This code is intended to be used as regular playbook, so roughly the
following steps should be followed:

 1) Install ansible. If you need help, refer to
    https://docs.ansible.com/ansible/latest/installation_guide

 2) Adjust your inventory, that is, the hosts that will be used on the
    playbook execution. The simplest way is to edit the `inventory`
    file this directory.

 3) (OPTIONAL) adjust your variables on `vars.yml` or change the -e option via
    command-line. Example::

    $ ansible-playbook .... -e "method=pip"

 4) Run a playbook with::

    $ ansible-playbook -i inventory -c local deployment.yml -e "method=pip"

.. note:: Note that `-e` option it is not mandatory.

Main variables
==============

Besides the basic variables (visit `vars.yml`) we have two main variables to
control the execution model: `method` and `avocado_vt`.

method
------

 1. `pip`: Install Avocado and Plugins using pip on a Python virtual
 environment (this is the default method).

 2. `copr`: Install Avocado and Plugins using RPM, from a Copr
 repository;

 3. `official`: Install Avocado and Plugins using RPM, from the official
 release repository.

You can set this method using the variable `method` inside the
`vars.yml` file or via command line.  Example::

    $ ansible-playbook .... -e "method=pip"

avocado_vt variable
-------------------

If you would like to test Avocado-vt, just enable with::


    $ ansible-playbook .... -e "method=pip avocado_vt=true"

Usage Examples
==============

Only Avocado
------------

 1. Test Avocado from PIP::

    $ ansible-playbook -i inventory -c local deployment.yml -e "method=pip"

 2. Test Avocado from Copr repository::

    $ ansible-playbook -i inventory -c local deployment.yml -e "method=copr"

 3. Test Avocado from Official repository::

    $ ansible-playbook -i inventory -c local deployment.yml -e "method=official"

Avocado + Avocado-VT
--------------------

 1. Test Avocado + Avocado-VT from PIP::

    $ ansible-playbook -i inventory -c local deployment.yml -e "method=pip avocado_vt=true"

 2. Test Avocado + Avocado-VT from Copr repository::

    $ ansible-playbook -i inventory -c local deployment.yml -e "method=copr avocado_vt=true"

 3. Test Avocado + Avocado-VT from Official repository::

    $ ansible-playbook -i inventory -c local deployment.yml -e "method=official avocado_vt=true"


All-in-one execution in container:
----------------------------------

It may be useful to run a playbook in a fresh container. One example of
a onliner that can achieve that::

  $ RUN_BEFORE='dnf install -y git ansible'
  $ GIT_URL='git://github.com/avocado-framework/avocado'
  $ INVENTORY='selftests/deployment/inventory'
  $ PLAYBOOK='selftests/deployment/deployment.yml'
  $ podman run --rm -ti fedora:30 /bin/bash -c '${RUN_BEFORE} && ansible-pull \
    -v -U ${GIT_URL} -i ${INVENTORY} -c local ${PLAYBOOK}'

.. _get-started:

Getting started guide - users
=============================

If you want to simply use avocado as a test runner/test API, you can install a distro package. For Ubuntu, you can look at `lmr's autotest PPA`_, while for Fedora, you can look at `lmr's autotest COPR`_.

.. _lmr's autotest PPA: https://launchpad.net/~lmr/+archive/autotest
.. _lmr's autotest COPR: http://copr.fedoraproject.org/coprs/lmr/Autotest

Installing avocado - Ubuntu
===========================

You can install the debian package by performing the following commands:

::

    sudo add-apt-repository ppa:lmr/autotest
    sudo apt-get update
    sudo apt-get install avocado


Installing avocado - Fedora
===========================

You can install the rpm package by performing the following commands:

::

    sudo curl http://copr.fedoraproject.org/coprs/lmr/Autotest/repo/fedora-20-i386/ > /etc/yum.repos.d/autotest.repo
    sudo yum update
    sudo yum install avocado
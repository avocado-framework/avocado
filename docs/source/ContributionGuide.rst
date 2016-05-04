================================
Contribution and Community Guide
================================

Useful pointers on how to participate of the Avocado community and contribute.

.. _hacking-and-using:

Hacking and Using Avocado
=========================

Since version 0.31.0, our plugin system requires Setuptools entry points to be
registered. If you're hacking on Avocado and want to use the same, possibly modified,
source for running your tests and experiments, you may do so with one additional step::

  $ make develop

On POSIX systems this will create an "egg link" to your original source tree under
"$HOME/.local/lib/pythonX.Y/site-packages". Then, on your original source tree, an
"egg info" directory will be created, containing, among other things, the Setuptools
entry points mentioned before.

Contact information
===================

- Avocado-devel mailing list: `https://www.redhat.com/mailman/listinfo/avocado-devel <https://www.redhat.com/mailman/listinfo/avocado-devel>`_
- Avocado IRC channel: `irc.oftc.net #avocado <irc://irc.oftc.net/#avocado>`_

Contributing to Avocado
=======================

Avocado uses github and the github pull request development model. You can
find a primer on how to use github pull requests
`here <https://help.github.com/articles/using-pull-requests>`_. Every Pull
Request you send will be automatically tested by
`Travis CI <https://travis-ci.org/avocado-framework/avocado>`_ and review will
take place in the Pull Request as well.

For people who don't like the github development model, there is the option
of sending the patches to the Mailing List, following a workflow more
traditional in Open Source development communities. The patches will be
reviewed in the Mailing List, should you opt for that. Then a maintainer will
collect the patches, integrate them on a branch, and then those patches will
be submitted as a github Pull Request. This process tries to ensure that every
contributed patch goes through the CI jobs before it is considered good for
inclusion.

Signing commits
---------------

Optionally we encourage people to sign the commits using GPG signatures. Doing
it is simple and it helps from unauthorized code being merged without notice.

All you need is a valid GPG signature, git configuration, slightly modified
workflow to use the signature and eventually even setup in github so one
benefits from the "nice" UI.

Get a GPG signature::

    # Google for howto, but generally it works like this
    $ gpg --gen-key  # defaults are usually fine (using expiration is recommended)
    $ gpg --send-keys $YOUR_KEY    # to propagate the key to outer world

Enable it in git::

    $ git config --global user.signingkey $YOUR_KEY

(optional) Link the key with your GH account::

    1. Login to github
    2. Go to settings->SSH and GPG keys
    3. Add New GPG key
    4. run $(gpg -a --export $YOUR_EMAIL) in shell to see your key
    5. paste the key there

Use it::

    # You can sign commits by using '-S'
    $ git commit -S
    # You can sign merges by using '-S'
    $ git merge -S

.. warning::
   You can not use the merge button on github to do signed merges as github
   does not have your private key.

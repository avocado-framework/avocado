================================
Contribution and Community Guide
================================

Useful pointers on how to participate of the avocado community and contribute.

Contact information
===================

- Avocado-devel mailing list: `https://www.redhat.com/mailman/listinfo/avocado-devel <https://www.redhat.com/mailman/listinfo/avocado-devel>`_
- Avocado IRC channel: `irc.oftc.net #avocado <irc://irc.oftc.net/#avocado>`_

Contributing to avocado
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
reviewed in the Mailing List, should you opt for that.

As soon as we have a mailing list functional, just send
patches to the list, and we'll have a sub-maintainer that will collect the
patches, integrate them on a branch, and then those patches will be submitted
as a github Pull Request. This process tries to ensure that every contributed
patch goes through the CI jobs before it is considered good for inclusion.

Avocado development tools
=========================

Debug
-----

You can find handy utils in `avocado.utils.debug`:

measure_duration
~~~~~~~~~~~~~~~~

Decorator can be used to print current duration of the executed function
and accumulated duration of this decorated function. It's very handy
when optimizing.

Usage::

    from avocado.utils import debug
    ...
    @debug.measure_duration
    def your_function(...):

During the execution look for::

    Function <function your_function at 0x29b17d0>: (0.1, 11.3)
    Function <function your_function at 0x29b17d0>: (0.2, 11.5)


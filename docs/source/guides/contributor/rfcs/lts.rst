.. _rfc-long-term-stability:

RFC: Long Term Stability
========================

This RFC contains proposals and clarifications regarding the
maintenance and release processes of Avocado.

We understand there are multiple teams currently depending on the
stability of Avocado and we don't want their work to be disrupted by
incompatibilities nor instabilities in new releases.

This version is a minor update to previous versions of the same RFC
(see `Changelog`_) which drove the release of Avocado 36.0 LTS.  The
Avocado team has plans for a new LTS release in the near future, so
please consider reading and providing feedback on the proposals here.

TL;DR
-----

We plan to keep the current approach of sprint releases every 3-4
weeks, but we're introducing "Long Term Stability" releases which
should be adopted in production environments where users can't keep up
with frequent upgrades.

Introduction
------------

We make new releases of Avocado every 3-4 weeks on average.  In theory
at least, we're very careful with backwards compatibility.  We test
Avocado for regressions and we try to document any issues, so
upgrading to a new version should be (again, in theory) safe.

But in practice both intended and unintended changes are introduced
during development, and both can be frustrating for conservative
users. We also understand it's not feasible for users to upgrade
Avocado very frequently in a production environment.

The objective of this RFC is to clarify our maintenance practices and
introduce Long Term Stability (LTS) releases, which are intended to
solve, or at least mitigate, these problems.


Our definition of maintained, or stable
---------------------------------------

First of all, Avocado and its sub-projects are provided 'AS IS' and
WITHOUT ANY WARRANTY, as described in the LICENSE file.

The process described here doesn't imply any commitments or
promises. It's just a set of best practices and recommendations.

When something is identified as "stable" or "maintained", it means the
development community makes a conscious effort to keep it working and
consider reports of bugs and issues as high priorities.  Fixes
submitted for these issues will also be considered high priorities,
although they will be accepted only if they pass the general
acceptance criteria for new contributions (design, quality,
documentation, testing, etc), at the development team discretion.


Maintained projects and platforms
---------------------------------

The only maintained project as of today is the Avocado Test Runner,
including its APIs and core plugins (the contents of the main avocado
git repository).

Other projects kept under the "Avocado Umbrella" in github may be
maintained by different teams (e.g.: Avocado-VT) or be considered
experimental (e.g.: avocado-server and avocado-virt).

More about Avocado-VT in its own section further down.

As a general rule, fixes and bug reports for Avocado when running in
any modern Linux distribution are welcome.

But given the limited capacity of the development team, packaged
versions of Avocado will be tested and maintained only for the
following Linux distributions:

 * RHEL 7.x (latest)
 * Fedora (stable releases from the Fedora projects)

Currently all packages produced by the Avocado projects are "noarch".
That means that they could be installable on any hardware platform.
Still, the development team will currently attempt to provide versions
that are stable for the following platforms:

 * x86
 * ppc64le

Contributions from the community to maintain other platforms and
operating systems are very welcome.

The lists above may change without prior notice.

Avocado Releases
----------------

The proposal is to have two different types of Avocado releases:

Sprint Releases
~~~~~~~~~~~~~~~

(This is the model we currently adopt in Avocado)

They happen every 3-4 weeks (the schedule is not fixed) and
their versions are numbered serially, with decimal digits in
the format <major>.<minor>.  Examples: 47.0, 48.0, 49.0.  Minor
releases are rare, but necessary to correct some major issue
with the original release (47.1, 47.2, etc).

Only the latest Sprint Release is maintained.

In Sprint Releases we make a conscious effort to keep backwards
compatibility with the previous version (APIs and behavior) and
as a general rule and best practice, incompatible changes in
Sprint Releases should be documented in the release notes and
if possible deprecated slowly, to give users time to adapt
their environments.

But we understand changes are inevitable as the software
evolves and therefore there's no absolute promise for API and
behavioral stability.

Long Term Stability (LTS) Releases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LTS releases should happen whenever the team feels the code is
stable enough to be maintained for a longer period of time, ideally
once or twice per year (no fixed schedule).

They should be maintained for 18 months, receiving fixes for major
bugs in the form of minor (sub-)releases. With the exception of
these fixes, no API or behavior should change in a minor LTS
release.

They will be versioned just like Sprint Releases, so looking at the
version number alone will not reveal the differentiate release
process and stability characteristics.

In practice each major LTS release will imply in the creation of a git
branch where only important issues affecting users will be fixed,
usually as a backport of a fix initially applied upstream. The code in
a LTS branch is stable, frozen for new features.

Notice that although within a LTS release there's a expectation
of stability because the code is frozen, different (major) LTS
releases may include changes in behavior, API incompatibilities
and new features. The development team will make a considerable
effort to minimize and properly document these changes (changes
when comparing it to the last major LTS release).

Sprint Releases are replaced by LTS releases. I.e., in the cycle
when 52.0 (LTS) is released, that's also the version used as a
Sprint Release (there's no 52.0 -- non LTS -- in this case).

New LTS releases should be done carefully, with ample time for
announcements, testing and documentation.  It's recommended
that one or two sprints are dedicated as preparations for a LTS
release, with a Sprint Release serving as a "LTS beta" release.

Similarly, there should be announcements about the end-of-life
(EOL) of a LTS release once it approaches its 18 months of
life.


Deployment details
------------------

Sprint and LTS releases, when packaged, whenever possible, will be
preferably distributed through different package channels
(repositories).

This is possible for repository types such as :ref:`YUM/DNF repos
<fedora-from-avocados-own-repo>`. In such cases, users can disable the
regular channel, and enable the LTS version.  A request for the
installation of Avocado packages will fetch the latest version
available in the enabled repository.  If the LTS repository channel is
enabled, the packages will receive minor updates (bugfixes only),
until a new LTS version is released (roughly every 12 months).

If the non-LTS channel is enabled, users will receive updates every
3-4 weeks.

On other types of repos such as `PyPI`_ which have no concept of
"sub-repos" or "channels", users can request a version smaller than
the version that succeeds the current LTS to get the latest LTS
(including minor releases).  Suppose the current LTS major version is
52, but there have been minor releases 52.1 and 52.2.  By running::

  pip install 'avocado-framework<53.0'

pip provide LTS version 52.2.  If 52.3 gets released, they will be
automatically deployed instead.  When a new LTS is released, users
would still get the latest minor release from the 52.0 series, unless
they update the version specification.

The existence of LTS releases should never be used as an excuse
to break a Sprint Release or to introduce gratuitous
incompatibilities there. In other words, Sprint Releases should
still be taken seriously, just as they are today.


Timeline example
----------------

Consider the release numbers as date markers.  The bullet points
beneath them are information about the release itself or events that
can happen anytime between one release and the other.  Assume each
sprint is taking 3 weeks.

 36.0
   * **LTS** release (the only LTS release available at the time of
     writing)

 37.0 .. 49.0
   * sprint releases
   * 36.1 LTS release
   * 36.2 LTS release
   * 36.3 LTS release
   * 36.4 LTS release

 50.0
   * sprint release
   * start preparing a LTS release, so 51.0 will be a **beta LTS**

 51.0
   * sprint release
   * **beta LTS** release

 52.0
   * **LTS** release
   * 52lts branch is created
   * packages go into LTS repo
   * both **36.x LTS** and **52.x LTS** maintained from this point on

 53.0
   * sprint release
   * minor bug that affects 52.0 is found, fix gets added to master and
     52lts branches
   * bug does **not** affect 36.x LTS, so a backport is **not** added to
     the 36lts branch

 54.0
   * sprint release 54.0
   * LTS release 52.1
   * minor bug that also affects 52.x LTS and 36.x LTS is found, fix
     gets added to master, 52lts and 36lts branches

 55.0
   * sprint release
   * LTS release 36.5
   * LTS release 52.2
   * critical bug that affects 52.2 *only* is found, fix gets added to
     52lts and **52.3 LTS is immediately released**

 56.0
  * sprint release

 57.0
  * sprint release

 58.0
  * sprint release

 59.0
  * sprint release
  * EOL for **36.x LTS** (18 months since the release of 36.0), 36lts
    branch is frozen permanently.

A few points are worth taking notice here:

 * Multiple LTS releases can co-exist before EOL

 * Bug discovery can happen at any time

 * The bugfix occurs ASAP after its discovery

 * The severity of the defect determines the timing of the release

   - moderate and minor bugfixes to lts branches are held until the
     next sprint release

   - critical bugs are released asynchronously, without waiting for
     the next sprint release


Avocado-VT
----------

Avocado-VT is an Avocado plugin that allows "VT tests" to be run
inside Avocado.  It's a third-party project maintained mostly by
Engineers from Red Hat QE with assistance from the Avocado team
and other community members.

It's a general consensus that QE teams use Avocado-VT directly
from git, usually following the master branch, which they
control.

There's no official maintenance or stability statement for
Avocado-VT.  Even though the upstream community is quite
friendly and open to both contributions and bug reports,
Avocado-VT is made available without any promises for
compatibility or supportability.

When packaged and versioned, Avocado-VT rpms should be considered
just snapshots, available in packaged form as a convenience to
users outside of the Avocado-VT development community.  Again,
they are made available without any promises of compatibility or
stability.

* Which Avocado version should be used by Avocado-VT?

  This is up to the Avocado-VT community to decide, but the
  current consensus is that to guarantee some stability in
  production environments, Avocado-VT should stick to a specific
  LTS release of Avocado. In other words, the Avocado team
  recommends production users of Avocado-VT not to install Avocado
  from its master branch or upgrade it from Sprint Releases.

  Given each LTS release will be maintained for 18 months, it
  should be reasonable to expect Avocado-VT to upgrade to a new
  LTS release once a year or so. This process will be done with
  support from the Avocado team to avoid disruptions, with proper
  coordination via the avocado mailing lists.

  In practice the Avocado development team will keep watching
  Avocado-VT to detect and document incompatibilities, so when
  the time comes to do an upgrade in production, it's expected
  that it should happen smoothly.

* Will it be possible to use the latest Avocado and Avocado-VT
  together?

  Users are welcome to *try* this combination.  The Avocado
  development team itself will do it internally as a way to monitor
  incompatibilities and regressions.

  Whenever Avocado is released, a matching versioned snapshot of
  Avocado-VT will be made.  Packages containing those Avocado-VT
  snapshots, for convenience only, will be made available in the
  regular Avocado repository.

Changelog
---------

Changes from `Version 4`_:

 * Moved changelog to the bottom of the document
 * Changed wording on bug handling for LTS releases ("important
   issues")
 * Removed ppc64 (big endian) from list of platforms
 * If bugs also affect older LTS release during the transition period,
   a backport will also be added to the corresponding branch
 * Further work on the `Timeline example`_, adding summary of
   important points and more release examples, such as the whole list
   of 36.x releases and the (fictional) 36.5 and 52.3

Changes from `Version 3`_:

 * Converted formatting to REStructuredText
 * Replaced "me" mentions on version 1 changelog with proper name
   (Ademar Reis)
 * Renamed section "Misc Details" to `Deployment Details`_
 * Renamed "avocado-vt" to "Avocado-VT"
 * Start the timeline example with version 36.0
 * Be explicit on timeline example that a minor bug did not generate
   an immediate release

Changes from `Version 2`_:

 * Wording changes on second paragraph ("... nor instabilities...")
 * Clarified on "Introduction" that change of behavior is introduced
   between regular releases
 * Updated distro versions for which official packages are built
 * Add more clear explanation on official packages on the various
   hardware platforms
 * Used more recent version numbers as examples, and the planned
   new LTS version too
 * Explain how users can get the LTS version when using tools such as
   pip
 * Simplified the timeline example, with examples that will possibly
   match the future versions and releases
 * Documented current status of Avocado-VT releases and packages

Changes from `Version 1`_:

 * Changed "Support" to "Stability" and "supported" to "maintained"
   [Jeff Nelson]
 * Misc improvements and clarifications in the
   supportability/stability statements [Jeff Nelson, Ademar Reis]
 * Fixed a few typos [Jeff Nelson, Ademar Reis]

.. _Version 1: https://www.redhat.com/archives/avocado-devel/2016-April/msg00006.html
.. _Version 2: https://www.redhat.com/archives/avocado-devel/2016-April/msg00038.html
.. _Version 3: https://www.redhat.com/archives/avocado-devel/2017-April/msg00032.html
.. _Version 4: https://www.redhat.com/archives/avocado-devel/2017-April/msg00041.html
.. _PyPI: https://pypi.python.org/pypi

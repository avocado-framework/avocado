How can I contribute?
=====================

.. note:: Except where otherwise indicated in a given source file, all original
  contributions to Avocado are licensed under the GNU General Public
  License version 2 `(GPLv2) <https://www.gnu.org/licenses/gpl-2.0.html>`_
  or any later version.

  By contributing you agree with: a) our code of conduct; b) that these
  contributions are your own (or approved by your employer), and c) you grant a
  full, complete, irrevocable copyright license to all users and developers of
  the Avocado project, present and future, pursuant to the license of the
  project.


Report a bug
------------

If Avocado crashes on you, or if one of the Avocado "selftests" fail,
congratulations, you may have just found a bug. And If you have
precise steps to reproduce, awesome! You're on your way to reporting a
useful bug report.

Don't be afraid to report bugs, even if you're not sure if they're valid. The
most that can happen is that we find out together that this is a feature
instead!

Avocado is using GitHub's issue tracking system for collecting and discussing
issues. If you have a possible candidate, do not hesitate, share with us by
`creating a new bug report
<https://github.com/avocado-framework/avocado/issues/new?assignees=&labels=bug%2C+triage&template=bug_report.md&title=>`_.

Suggest enhancements
--------------------

The same is valid when suggesting a new feature or enhancements: Don't think
twice, just `submit the feature request
<https://github.com/avocado-framework/avocado/issues/new?assignees=&labels=enhancement&template=feature_request.md&title=>`_
using the same link.  Our community will evaluate if the feature
request is valid and when it might become a part of the Avocado
Framework.

Contribute with code
--------------------

Avocado uses GitHub and its pull request development model. You can find
a primer on how to use GitHub pull requests `here
<https://help.github.com/articles/using-pull-requests>`_.

Every Pull Request you send will be automatically tested by the
`CI system <https://github.com/avocado-framework/avocado/actions>`_ and review
will take place in the Pull Request as well.

For people who don’t like the GitHub development model, there is an option to
send the patches to the Mailing List, following a more traditional workflow in
Open Source development communities. The patches are reviewed in the Mailing
List, should you opt for that. Then a maintainer will collect the patches,
integrate them on a branch, and submit it as a GitHub Pull Request. This
process ensures that every contributed patch goes through the CI jobs before
being considered suitable for inclusion.

Remember that we do have a small “Feature Freeze” period right before the
release day (usually no longer than one week). It means that during this time,
no new feature can be merged into the master branch.

Git workflow
~~~~~~~~~~~~

- `Fork the repository <https://github.com/avocado-framework/avocado/fork>`_
  in GitHub.

- Clone from your fork::

    $ git clone git@github.com:<username>/avocado.git

- Enter the directory::

    $ cd avocado

- Create a ``remote``, pointing to the upstream::

    $ git remote add upstream git@github.com:avocado-framework/avocado.git

- Configure your name and e-mail in git::

    $ git config --global user.name "Your Name"
    $ git config --global user.email email@foo.bar

- Golden tip: never work on local branch master. Instead, create a new
  local branch and checkout to it::

    $ git checkout -b my_new_local_branch

- Code and then commit your changes::

    $ git add new-file.py
    $ git commit -s
    # or "git commit -as" to commit all changes

.. seealso:: Please, read our Commit Style Guide on Style Guides section
  manual.

- Make sure your code is working (install your version of avocado, test
  your change, run ``make check`` to make sure you didn't introduce any
  regressions).

- Rebase your local branch on top of upstream master::

    $ git fetch
    $ git rebase upstream/master
    (resolve merge conflicts, if any)

- Push your commit(s) to your fork::

    $ git push origin my_new_local_branch

- `Create the Pull Request
  <https://github.com/avocado-framework/avocado/compare>`_ on
  GitHub. Add the relevant information to the Pull Request
  description.

- Check if your Pull Request passes the CI system. Your Pull Request will
  probably be ignored until it's all green.

Now you're waiting for feedback on GitHub Pull Request page. Once you get some,
join the discussion, answer the questions, make clear if you're going to change
the code based on some review and, if not, why. Feel free to disagree with the
reviewer, they probably have different use cases and opinions, which is
expected. Try describing yours and suggest other solutions, if necessary.

Then, proceed to make the changes.  This is a typical workflow:

- Code, and amend the commit(s) and/or create new commits. If you have
  more than one commit in the PR, you will probably need to rebase
  interactively to amend the right commits. ``git cola`` or ``git citool``
  can be handy here.

- Rebase your local branch on top of upstream master::

    $ git fetch
    $ git rebase upstream/master
    (resolve merge conflicts, if any)

- Push your changes::

    $ git push --force origin my_new_local_branch

Please communicate to the reviewers what the summary of changes are.
Also, make use of GitHub's features to ease the reviewers' life, such
as marking comments as "resolved".  Reviewers should make use of
GitHub's "compare" feature to more easily verify the changes since the
last iteration.

After your PR gets merged, you can sync the master branch on your local
repository propagate the sync to the master branch in your fork repository on
GitHub::

    $ git checkout master
    $ git pull upstream master
    $ git push

From time to time, you can remove old branches to avoid pollution::

    # To list branches along with time reference:
    $ git for-each-ref --sort='-authordate:iso8601' --format=' %(authordate:iso8601)%09%(refname)' refs/heads
    # To remove branches from your fork repository:
    $ git push origin :my_old_branch

Code Review
~~~~~~~~~~~

Every single Pull Request in Avocado has to be reviewed by at least one other
developer. All members of the core team have permission to merge a Pull
Request, but some conditions have to be fulfilled before merging the code:

- Pull Request has to pass the CI tests.
- One 'Approved' code review should be given.
- No explicit disapproval should be present.

Pull Requests failing in CI will not be merged, and reviews won't be given to
them until all the problems are sorted out. In case of a weird failure, or
false-negative (eg. due to too many commits in a single PR), please reach the
developers by @name/email/irc or other means.

While reviewing the code, one should:

- Verify that the code is sound and clean.
- Run the highest level of selftests per each new commit in the merge.
  The ``contrib/scripts/avocado-check-pr.sh`` contrib script should
  simplify this step.
- Verify that code works to its purpose.
- Make sure the commits organization is proper (i.e. code is well
  organized in atomic commits, there's no extra/unwanted commits, ...).
- Provide an in-line feedback with explicit questions and/or requests of
  improvements.
- Provide a general feedback in the review message, being explicit about
  what's expected for the next Pull Request version, if that's the case.

When the Pull Request is approved, the reviewer will merge the code or
wait for someone with merge permission to merge it.

Using ``avocado-check-pr.sh``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``contrib/scripts/avocado-check-pr.sh`` script is here to simplify the
per-commit-check. You can simply prepare the merge and initiate
``AVOCADO_CHECK_LEVEL=99 contrib/scripts/avocado-check-pr.sh`` to run all
checks per each commit between your branch and the same branch on the
``origin/master`` (you can specify different remote origin).

Use ``./contrib/scripts/avocado-check-pr.sh -h`` to learn more about the
options. We can recommend the following command::

  $ AVOCADO_CHECK_LEVEL=99
  $ ./contrib/scripts/avocado-check-pr.sh -i -v

.. note:: Before first use you might need to create
  ``~/.config/github_checker.ini`` and fill GitHub user/token entries (while on
  it you can also specify some defaults)


Share your tests
----------------

We encourage you or your company to create public Avocado tests repositories so
the community can also benefit of your tests. We will be pleased to advertise
your repository here in our documentation.

List of known community and third party maintained repositories:

- https://github.com/avocado-framework-tests/avocado-misc-tests:
  Community maintained Avocado miscellaneous tests repository. There you
  will find, among others, performance tests like ``lmbench``,
  ``stress``, cpu tests like ``ebizzy`` and generic tests like ``ltp``.
  Some of them were ported from Autotest Client Tests repository.

Documentation
-------------

.. warning:: TODO: Create how to contribute with documentation.

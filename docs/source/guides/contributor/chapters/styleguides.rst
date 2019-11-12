Style guides
============

Commit style guide
------------------

Write a good commit message, pointing motivation, issues that you're
addressing. Usually you should try to explain 3 points in the commit message:
motivation, approach and effects::

    header          <- Limited to 72 characters. No period.
                    <- Blank line
    message         <- Any number of lines, limited to 72 characters per line.
                    <- Blank line
    Reference:      <- External references, one per line (issue, trello, ...)
    Signed-off-by:  <- Signature and acknowledgment of licensing terms when
                       contributing to the project (created by git commit -s)

Signing commits
~~~~~~~~~~~~~~~

Optionally you can sign the commits using GPG signatures. Doing
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



Code style guide
----------------

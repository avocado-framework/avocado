========================
Avocado development tips
========================

Interrupting test
=================

In case you want to "pause" the running test, you can use SIGTSTP (ctrl+z)
signal sent to the main avocado process. This signal is forwarded to test
and it's children processes. To resume testing you repeat the same signal.

Note: that the job/test timeouts are still enabled on stopped processes.

In tree utils
=============

You can find handy utils in `avocado.utils.debug`:

measure_duration
----------------

Decorator can be used to print current duration of the executed function
and accumulated duration of this decorated function. It's very handy
when optimizing.

Usage::

    from avocado.utils import debug
    ...
    @debug.measure_duration
    def your_function(...):

During the execution look for::

    PERF: <function your_function at 0x29b17d0>: (0.1s, 11.3s)
    PERF: <function your_function at 0x29b17d0>: (0.2s, 11.5s)

Line-profiler
=============

You can measure line-by-line performance by using line_profiler. You can
install it using pip::

    pip install line_profiler

and then simply mark the desired function with `@profile` (no need to import
it from anywhere). Then you execute::

    kernprof -l -v ./scripts/avocado run ...

and when the process finishes you'll see the profiling information. (sometimes
the binary is called `kernprof.py`)

Remote debug with Eclipse
=========================

Eclipse is a nice debugging frontend which allows remote debugging. It's very
simple. The only thing you need is Eclipse with pydev plugin. Then you
need to locate the pydevd path (usually
`$INSTALL_LOCATION/plugins/org.python.pydev_*/pysrc` or
`~/.eclipse/plugins/org.python.pydev_*/pysrc`. Then you set the breakpoint by::

    import sys
    sys.path.append("$PYDEV_PATH")
    import pydevd
    pydevd.settrace("$IP_ADDR_OF_ECLIPSE_MACHINE")

Alternatively you can export PYTHONPATH=$PYDEV_PATH and use only last 2 lines.

Before you run the code, you need to start the Eclipse's debug server. Switch
to `Debug` perspective (you might need to open it first
`Window->Perspective->Open Perspective`). Then start the server from
`Pydev->Start Debug Server`.

Now whenever the pydev.settrace() code is executed, it contacts Eclipse debug
server (port `8000` by default, don't forget to open it) and you can
easily continue in execution. This works on every remote machine which
has access to your Eclipse's port `8000` (you can override it).

Using Trello cards in Eclipse
=============================

Eclipse allows us to create tasks. They are pretty cool as you see the
status (not started, started, current, done) and by switching tasks it
automatically resumes where you previously finished (opened files, ...)

Avocado is planned using Trello, which is not yet supported by Eclipse.
Anyway there is a way to at least get read-only list of your commits.
This guide is based on `<https://docs.google.com/document/d/1jvmJcCStE6QkJ0z5ASddc3fNmJwhJPOFN7X9-GLyabM/>`_ which didn't work well with lables and
descriptions. The only difference is you need to use `Query Pattern`::

    \"url\":\"https://trello.com/[^/]*/[^/]*/({Id}[^\"]+)({Description})\"

Setup Trello key:

#. Create a Trello account
#. Get (developer_key) here:
   `<https://trello.com/1/appKey/generate>`_
#. Get user_token from following address (replace key with your key):
   `<https://trello.com/1/authorize?key=$developer_key&name=Mylyn%20Tasks&expiration=never&response_type=token>`_
#. Address with your assigned tasks (task_addr) is:
   `<https://trello.com/1/members/my/cards?key=developer_key&token=$user_token>`_
   Open it in web browser and you should see `[]` or `[$list_of_cards]`
   without any passwords.

Configure Eclipse:

#. We're going to need Web Templates, which are not yet upstream. We need to
   use incubator version.
#. `Help->Install New Software...`
#. -> `Add`
#. Name: `Incubator`
#. Location: `<http://download.eclipse.org/mylyn/incubator/3.10>`_
#. -> `OK`
#. Select `Mylyn Tasks Connector: Web Templates (Advanced) (Incubation)` (use filter text to find it)
#. Install it (`Next->Agree->Next...`)
#. Restart Eclipse
#. Open the Mylyn Team Repositories `Window->Show View->Other...->Mylyn->Team Repositories`
#. Right click the `Team Repositories` and select `New->Repository`
#. Use `Task Repository` -> `Next`
#. Use `Web Template (Advanced)` -> `Next`
#. In the Properties for Task Repository dialog box, enter
   `<https://trello.com>`_
#. In the Server field and give the repository a label (eg. `Trello API`).
#. In the Additional Settings section set `applicationkey = $developer_key`
   and `userkey = $user_token`.
#. In the Advanced Configuration set the Task URL to `<https://trello.com/c/>`_
#. Set New Task URL to `<https://trello.com>`_
#. Set the Query Request URL (no changes required):
   `<https://trello.com/1/members/my/cards?key=${applicationkey}&token=${userkey}>`_
#. For the Query Pattern enter `\"url\":\"https://trello.com/[^/]*/[^/]*/({Id}[^\"]+)({Description})\"`
#. -> `Finish`

Create task query:

#. Create a query by opening the `Mylyn Task List`.
#. Right click the pane and select `New Query`.
#. Select Trello API as the repository.
#. -> `Next`
#. Enter the name of your query.
#. Expand the Advanced Configuration and make sure the Query Pattern is filled in
#. Press `Preview` to confirm that there are no errors.
#. Press `Finish`.
#. Trello tasks assigned to you will now appear in the Mylyn Task List.

Noy you can start using tasks by clicking the small bubble in front of the
name. This closes all editors. Try openning some and then click the bubble
again. They should get closed. When you click the bubble third time, it should
resume all the open editors from before.

My usual workflow is:

#. git checkout $branch
#. Eclipse: select task
#. git commit ...
#. Eclipse: unselect task
#. git checkout $other_branch
#. Eclipse: select another_task

This way you always have all the files present and you can easily resume
your work.

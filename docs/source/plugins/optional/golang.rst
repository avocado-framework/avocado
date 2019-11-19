.. _golang-plugin:

=============
Golang Plugin
=============

This optional plugin enables Avocado to list and run tests written using
the `Go testing package <https://golang.org/pkg/testing/>`_.

To install the Golang plugin from pip, use::

    $ sudo pip install avocado-framework-plugin-golang

After installed, you can list/run Golang tests providing the package name::

    ~$ avocado list golang.org/x/text/unicode/norm
    GOLANG golang.org/x/text/unicode/norm:TestFlush
    GOLANG golang.org/x/text/unicode/norm:TestInsert
    GOLANG golang.org/x/text/unicode/norm:TestDecomposition
    GOLANG golang.org/x/text/unicode/norm:TestComposition
    GOLANG golang.org/x/text/unicode/norm:TestProperties
    GOLANG golang.org/x/text/unicode/norm:TestIterNext
    GOLANG golang.org/x/text/unicode/norm:TestIterSegmentation
    GOLANG golang.org/x/text/unicode/norm:TestPlaceHolder
    GOLANG golang.org/x/text/unicode/norm:TestDecomposeSegment
    GOLANG golang.org/x/text/unicode/norm:TestFirstBoundary
    GOLANG golang.org/x/text/unicode/norm:TestNextBoundary
    GOLANG golang.org/x/text/unicode/norm:TestDecomposeToLastBoundary
    GOLANG golang.org/x/text/unicode/norm:TestLastBoundary
    GOLANG golang.org/x/text/unicode/norm:TestSpan
    GOLANG golang.org/x/text/unicode/norm:TestIsNormal
    GOLANG golang.org/x/text/unicode/norm:TestIsNormalString
    GOLANG golang.org/x/text/unicode/norm:TestAppend
    GOLANG golang.org/x/text/unicode/norm:TestAppendString
    GOLANG golang.org/x/text/unicode/norm:TestBytes
    GOLANG golang.org/x/text/unicode/norm:TestString
    GOLANG golang.org/x/text/unicode/norm:TestLinking
    GOLANG golang.org/x/text/unicode/norm:TestReader
    GOLANG golang.org/x/text/unicode/norm:TestWriter
    GOLANG golang.org/x/text/unicode/norm:TestTransform
    GOLANG golang.org/x/text/unicode/norm:TestTransformNorm
    GOLANG golang.org/x/text/unicode/norm:TestCharacterByCharacter
    GOLANG golang.org/x/text/unicode/norm:TestStandardTests
    GOLANG golang.org/x/text/unicode/norm:TestPerformance

And the Avocado test reference syntax to filter the tests you want to
execute is also available in this plugin::

    ~$ avocado list golang.org/x/text/unicode/norm:TestTransform
    GOLANG golang.org/x/text/unicode/norm:TestTransform
    GOLANG golang.org/x/text/unicode/norm:TestTransformNorm

To run the tests, just switch from `list` to `run`::

    ~$ avocado run golang.org/x/text/unicode/norm:TestTransform
    JOB ID     : aa6e36547ba304fd724779eff741b6180ee78a54
    JOB LOG    : $HOME/avocado/job-results/job-2017-10-06T16.06-aa6e365/job.log
     (1/2) golang.org/x/text/unicode/norm:TestTransform: PASS (1.89 s)
     (2/2) golang.org/x/text/unicode/norm:TestTransformNorm: PASS (1.87 s)
    RESULTS    : PASS 2 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 4.61 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-10-06T16.06-aa6e365/results.html

The content of the individual tests output is recorded in the default location::

    ~$ head  ~/avocado/job-results/latest/test-results/1-golang.org_x_text_unicode_norm_TestTransform/debug.log
    16:06:53 INFO | Running '/usr/bin/go test -v golang.org/x/text/unicode/norm -run TestTransform'
    16:06:55 DEBUG| [stdout] === RUN   TestTransform
    16:06:55 DEBUG| [stdout] --- PASS: TestTransform (0.00s)
    16:06:55 DEBUG| [stdout] === RUN   TestTransformNorm
    16:06:55 DEBUG| [stdout] === RUN   TestTransformNorm/NFC/0
    16:06:55 DEBUG| [stdout] === RUN   TestTransformNorm/NFC/0/fn
    16:06:55 DEBUG| [stdout] === RUN   TestTransformNorm/NFC/0/NFD
    16:06:55 DEBUG| [stdout] === RUN   TestTransformNorm/NFC/0/NFKC
    16:06:55 DEBUG| [stdout] === RUN   TestTransformNorm/NFC/0/NFKD
    16:06:55 DEBUG| [stdout] === RUN   TestTransformNorm/NFC/1


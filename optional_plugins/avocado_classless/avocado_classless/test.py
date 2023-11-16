#! /usr/bin/env avocado-runner-avocado-classless

# SPDX-License-Identifier: GPL-2.0-or-later
#
# Copyright Red Hat
# Author: David Gibson <david@gibson.dropbear.id.au>

"""
Test writer facing interface to avocodo-classless
"""

MANIFEST = "__avocado_classless__"


def test(func):
    """Function decorator to mark a function as a classless test"""
    mfest = func.__globals__.setdefault(MANIFEST, {})
    mfest[func.__name__] = func
    return func


@test
def trivial():  # pylint: disable=C0116
    pass


@test
def assert_true():  # pylint: disable=C0116
    assert True


#
# Assertion helpers without unnecessary OOP nonsense
#


def assert_eq(left, right):
    """assert_eq(left, right)

    If left != right, fail with message showing both values
    """
    assert left == right, f"{left} != {right}"


@test
def test_assert_eq():  # pylint: disable=C0116
    assert_eq(1, 1)


def assert_raises(exc, func, *args, **kwargs):
    """assert_raises(exc, func, *args, **kwargs)

    If func(*args, **kwargs) does not raise exc, fail
    """
    try:
        func(*args, **kwargs)
        raise AssertionError(f"Expected {exc.__name__} exception")
    except exc:
        pass


@test
def test_assert_raises():  # pylint: disable=C0116
    def boom(exc):
        raise exc

    assert_raises(ValueError, boom, ValueError)

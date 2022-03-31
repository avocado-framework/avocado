from avocado.utils import astring


class TestID:

    """
    Test ID construction and representation according to specification

    This class wraps the representation of both Avocado's Test ID
    specification and Avocado's Test Name, which is part of a Test ID.
    """

    def __init__(self, uid, name, variant=None, no_digits=None):
        """
        Constructs a TestID instance

        :param uid: unique test id (within the job)
        :param name: test name, as returned by the Avocado test resolver
                     (AKA as test loader)
        :param variant: the variant applied to this Test ID
        :type variant: dict
        :param no_digits: number of digits of the test uid
        """
        self.uid = uid
        if no_digits is not None and no_digits >= 0:
            self.str_uid = str(uid).zfill(no_digits if no_digits else 3)
        else:
            self.str_uid = str(uid)
        self.name = name or "<unknown>"
        if variant is None or variant["variant_id"] is None:
            self.variant = None
            self.str_variant = ""
        else:
            self.variant = variant["variant_id"]
            self.str_variant = f";{self.variant}"

    def __str__(self):
        return f"{self.str_uid}-{self.name}{self.str_variant}"

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return repr(str(self))

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other
        else:
            return self.__dict__ == other.__dict__

    @property
    def str_filesystem(self):
        """
        Test ID in a format suitable for use in file systems

        The string returned should be safe to be used as a file or
        directory name.  This file system version of the test ID may
        have to shorten either the Test Name or the Variant ID.

        The first component of a Test ID, the numeric unique test id,
        AKA "uid", will be used as a an stable identifier between the
        Test ID and the file or directory created based on the return
        value of this method.  If the filesystem can not even
        represent the "uid", than an exception will be raised.

        For Test ID "001-mytest;foo", examples of shortened file
        system versions include "001-mytest;f" or "001-myte;foo".

        :raises: RuntimeError if the test ID cannot be converted to a
                 filesystem representation.
        """
        test_id = str(self)
        test_id_fs = astring.string_to_safe_path(test_id)
        if len(test_id) == len(test_id_fs):    # everything fits in
            return test_id_fs
        idx_fit_variant = len(test_id_fs) - len(self.str_variant)
        if idx_fit_variant > len(self.str_uid):     # full uid+variant
            return (test_id_fs[:idx_fit_variant] +
                    astring.string_to_safe_path(self.str_variant))
        elif len(self.str_uid) <= len(test_id_fs):   # full uid
            return astring.string_to_safe_path(self.str_uid + self.str_variant)
        else:       # not even uid could be stored in fs
            raise RuntimeError(f'Test ID is too long to be stored on the '
                               f'filesystem: "{self.str_uid}"\n'
                               f'Full Test ID: "{str(self)}"')

    @classmethod
    def from_identifier(cls, identifier):
        """
        It wraps an identifier by the TestID class.

        :param identifier: Any identifier that is guaranteed to be unique
                           within the context of an avocado Job.
        :returns: TestID with `uid` as string representation of `identifier`
                 and `name` "test".
        :rtype: :class:`avocado.core.test_id.TestID`
        """
        if type(identifier) is cls:
            return identifier
        else:
            return cls(str(identifier), "test")

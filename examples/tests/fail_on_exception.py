#!/usr/bin/env python

import avocado


class FailOnException(avocado.Test):

    """
    Test illustrating the behavior of the fail_on decorator.

    :avocado: tags=failure_expected
    """

    # @avocado.fail_on(ValueError) also possible
    @avocado.fail_on
    def test(self):
        """
        This should end with FAIL.

        Avocado tests should end with ERROR when a generic exception such as
        ValueError is raised. The avocado.fail_on_error decorator allows you
        to override this behavior, and turn your generic exceptions into
        errors.
        """
        raise ValueError('This raises a ValueError and should end as a FAIL')


if __name__ == "__main__":
    avocado.main()

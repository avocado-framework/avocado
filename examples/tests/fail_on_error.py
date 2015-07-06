#!/usr/bin/python

import avocado


class FailOnError(avocado.Test):

    """
    Test illustrating the behavior of the fail_on_error decorator.
    """

    @avocado.fail_on_error
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

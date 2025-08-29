import unittest
from unittest import mock

from avocado import Test
from avocado.utils import dmesg


class TestCheckKernelLogs(Test):
    @mock.patch("avocado.utils.dmesg.process.run")
    def test_pattern_found_in_dmesg(self, mock_run):
        # Simulate `dmesg` output containing the pattern
        mock_run.return_value.stdout_text = "kernel: test_pattern detected"
        mock_run.return_value.exit_status = 0

        result = dmesg.check_kernel_logs("test_pattern")
        self.assertTrue(result)
        mock_run.assert_called_with(
            "dmesg", ignore_status=True, verbose=False, sudo=True
        )

    @mock.patch("avocado.utils.dmesg.process.run")
    def test_pattern_found_in_journalctl(self, mock_run):
        dmesg_out = mock.Mock()
        dmesg_out.stdout_text = "kernel: something else"
        dmesg_out.exit_status = 0

        journal_out = mock.Mock()
        journal_out.stdout_text = "kernel: test_pattern here"
        journal_out.exit_status = 0

        mock_run.side_effect = [dmesg_out, journal_out]

        result = dmesg.check_kernel_logs("test_pattern")
        self.assertTrue(result)

    @mock.patch("avocado.utils.dmesg.process.run")
    def test_pattern_not_found(self, mock_run):
        dmesg_out = mock.Mock()
        dmesg_out.stdout_text = "kernel: no match"
        dmesg_out.exit_status = 0

        journal_out = mock.Mock()
        journal_out.stdout_text = "kernel: still no match"
        journal_out.exit_status = 0

        mock_run.side_effect = [dmesg_out, journal_out]

        result = dmesg.check_kernel_logs("test_pattern")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()

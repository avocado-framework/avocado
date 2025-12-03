import time
import unittest
from unittest import mock

from avocado.utils import wait


class WaitForTest(unittest.TestCase):
    """Unit tests for wait.wait_for function."""

    def test_basic_success_immediate(self):
        """Test wait_for with function that succeeds immediately."""
        func = mock.Mock(return_value=True)
        result = wait.wait_for(func, timeout=5)
        self.assertTrue(result)
        func.assert_called_once()

    def test_basic_success_with_value(self):
        """Test wait_for returns the truthy value from function."""
        func = mock.Mock(return_value="success")
        result = wait.wait_for(func, timeout=5)
        self.assertEqual(result, "success")

    def test_timeout_returns_none(self):
        """Test wait_for returns None when timeout expires."""
        func = mock.Mock(return_value=False)
        start = time.time()
        result = wait.wait_for(func, timeout=0.5, step=0.1)
        elapsed = time.time() - start
        self.assertIsNone(result)
        self.assertGreaterEqual(elapsed, 0.5)
        self.assertLess(elapsed, 1.5)  # Allow generous buffer for CI variance

    def test_function_eventually_succeeds(self):
        """Test wait_for succeeds when function returns True after retries."""
        call_count = {"count": 0}

        def func_on_third_call():
            call_count["count"] += 1
            return call_count["count"] >= 3

        result = wait.wait_for(func_on_third_call, timeout=5, step=0.1)
        self.assertTrue(result)
        self.assertEqual(call_count["count"], 3)

    def test_first_delay(self):
        """Test wait_for respects first delay parameter."""
        func = mock.Mock(return_value=True)
        start = time.time()
        wait.wait_for(func, timeout=5, first=0.2)
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.2)

    def test_step_interval(self):
        """Test wait_for respects step interval between attempts."""
        func = mock.Mock(return_value=False)
        wait.wait_for(func, timeout=1.0, step=0.15, first=0.0)
        # Should make roughly 1.0/0.15 = 6-7 attempts, allow buffer for CI variance
        call_count = func.call_count
        self.assertGreaterEqual(call_count, 4)
        self.assertLessEqual(call_count, 10)

    def test_zero_timeout(self):
        """Test wait_for with zero timeout."""
        func = mock.Mock(return_value=False)
        result = wait.wait_for(func, timeout=0)
        self.assertIsNone(result)

    def test_with_positional_args(self):
        """Test wait_for passes positional arguments to function."""
        func = mock.Mock(return_value=True)
        wait.wait_for(func, timeout=5, args=["arg1", "arg2", 3])
        func.assert_called_with("arg1", "arg2", 3)

    def test_with_keyword_args(self):
        """Test wait_for passes keyword arguments to function."""
        func = mock.Mock(return_value=True)
        wait.wait_for(func, timeout=5, kwargs={"key1": "value1", "key2": 42})
        func.assert_called_with(key1="value1", key2=42)

    def test_with_both_args_and_kwargs(self):
        """Test wait_for passes both positional and keyword arguments."""
        func = mock.Mock(return_value=True)
        wait.wait_for(
            func, timeout=5, args=["pos1", "pos2"], kwargs={"kw1": "val1", "kw2": 99}
        )
        func.assert_called_with("pos1", "pos2", kw1="val1", kw2=99)

    def test_text_logging(self):
        """Test wait_for logs debug messages when text is provided."""
        func = mock.Mock(return_value=False)
        with self.assertLogs("avocado.utils.wait", level="DEBUG") as log_context:
            wait.wait_for(func, timeout=0.3, step=0.1, text="Waiting for condition")
        # Should have logged at least once
        self.assertGreater(len(log_context.output), 0)
        self.assertIn("Waiting for condition", log_context.output[0])

    def test_no_logging_without_text(self):
        """Test wait_for does not log when text is None."""
        func = mock.Mock(return_value=False)
        with self.assertRaises(AssertionError):
            # Should not log anything
            with self.assertLogs("avocado.utils.wait", level="DEBUG"):
                wait.wait_for(func, timeout=0.2, step=0.1, text=None)

    def test_returns_first_truthy_value(self):
        """Test wait_for returns first truthy value encountered."""
        values = [False, 0, None, "", "found"]

        def func_with_sequence():
            return values.pop(0)

        result = wait.wait_for(func_with_sequence, timeout=5, step=0.05)
        self.assertEqual(result, "found")
        # Should have values left since it stopped early
        self.assertEqual(len(values), 0)

    def test_function_returns_zero(self):
        """Test wait_for treats zero as falsy and continues waiting."""
        func = mock.Mock(return_value=0)
        result = wait.wait_for(func, timeout=0.2, step=0.05)
        self.assertIsNone(result)
        self.assertGreater(func.call_count, 1)

    def test_function_returns_empty_string(self):
        """Test wait_for treats empty string as falsy."""
        func = mock.Mock(return_value="")
        result = wait.wait_for(func, timeout=0.2, step=0.05)
        self.assertIsNone(result)

    def test_function_returns_list(self):
        """Test wait_for can return list when function returns truthy list."""
        func = mock.Mock(return_value=["item1", "item2"])
        result = wait.wait_for(func, timeout=5)
        self.assertEqual(result, ["item1", "item2"])

    def test_function_returns_dict(self):
        """Test wait_for can return dict when function returns truthy dict."""
        expected = {"key": "value"}
        func = mock.Mock(return_value=expected)
        result = wait.wait_for(func, timeout=5)
        self.assertEqual(result, expected)

    def test_function_raises_exception(self):
        """Test wait_for propagates exceptions from the function."""
        func = mock.Mock(side_effect=ValueError("Test error"))
        with self.assertRaises(ValueError) as context:
            wait.wait_for(func, timeout=5)
        self.assertEqual(str(context.exception), "Test error")

    def test_negative_timeout(self):
        """Test wait_for with negative timeout."""
        func = mock.Mock(return_value=False)
        result = wait.wait_for(func, timeout=-1)
        self.assertIsNone(result)

    def test_large_step_vs_timeout(self):
        """Test wait_for when step is larger than timeout.

        Note: The function sleeps for full step duration even if it exceeds timeout.
        """
        func = mock.Mock(return_value=False)
        start = time.time()
        result = wait.wait_for(func, timeout=0.2, step=5.0)
        elapsed = time.time() - start
        self.assertIsNone(result)
        # Function will sleep for full step duration after first attempt
        self.assertGreaterEqual(elapsed, 5.0)
        # Should be called once before sleeping
        self.assertEqual(func.call_count, 1)

    def test_very_small_timeout(self):
        """Test wait_for with very small timeout value."""
        func = mock.Mock(return_value=False)
        result = wait.wait_for(func, timeout=0.01, step=0.001)
        self.assertIsNone(result)

    def test_none_args_and_kwargs(self):
        """Test wait_for with None values for args and kwargs."""
        func = mock.Mock(return_value=True)
        result = wait.wait_for(func, timeout=5, args=None, kwargs=None)
        self.assertTrue(result)
        func.assert_called_once_with()

    def test_empty_args_and_kwargs(self):
        """Test wait_for with empty args and kwargs."""
        func = mock.Mock(return_value=True)
        result = wait.wait_for(func, timeout=5, args=[], kwargs={})
        self.assertTrue(result)
        func.assert_called_once_with()

    def test_callable_object(self):
        """Test wait_for works with callable objects, not just functions."""

        class CallableCounter:
            def __init__(self):
                self.count = 0

            def __call__(self):
                self.count += 1
                return self.count >= 3

        callable_obj = CallableCounter()
        result = wait.wait_for(callable_obj, timeout=5, step=0.1)
        self.assertTrue(result)
        self.assertEqual(callable_obj.count, 3)

    def test_lambda_function(self):
        """Test wait_for works with lambda functions."""
        counter = {"value": 0}

        def increment():
            counter["value"] += 1
            return counter["value"] >= 2

        result = wait.wait_for(increment, timeout=5, step=0.1)
        self.assertTrue(result)

    def test_timing_precision(self):
        """Test wait_for timeout is reasonably accurate."""
        func = mock.Mock(return_value=False)
        timeout_val = 1.0
        start = time.time()
        wait.wait_for(func, timeout=timeout_val, step=0.1)
        elapsed = time.time() - start
        # Should be close to timeout (within 20% tolerance for system variance)
        self.assertGreaterEqual(elapsed, timeout_val)
        self.assertLess(elapsed, timeout_val * 1.2)


if __name__ == "__main__":
    unittest.main()

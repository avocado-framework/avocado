import unittest
from unittest.mock import patch

from avocado.utils import output


class UtilsOutputTest(unittest.TestCase):
    def test_display_data_size_factor_1024(self):
        self.assertEqual(output.display_data_size(103), "103.00 B")
        self.assertEqual(output.display_data_size(1024**1), "1.02 KB")
        self.assertEqual(output.display_data_size(1024**2), "1.05 MB")
        self.assertEqual(output.display_data_size(1024**3), "1.07 GB")
        self.assertEqual(output.display_data_size(1024**4), "1.10 TB")
        self.assertEqual(output.display_data_size(1024**5), "1.13 PB")
        self.assertEqual(output.display_data_size(1024**6), "1152.92 PB")

    def test_display_data_size_factor_1000(self):
        self.assertEqual(output.display_data_size(1000**1), "1.00 KB")
        self.assertEqual(output.display_data_size(1000**2), "1.00 MB")
        self.assertEqual(output.display_data_size(1000**3), "1.00 GB")
        self.assertEqual(output.display_data_size(1000**4), "1.00 TB")
        self.assertEqual(output.display_data_size(1000**5), "1.00 PB")
        self.assertEqual(output.display_data_size(1000**6), "1000.00 PB")


class ProgressBarTest(unittest.TestCase):
    def test_init_default_values(self):
        """Test ProgressBar initialization with default values."""
        pb = output.ProgressBar()
        self.assertEqual(pb.minimum, 0)
        self.assertEqual(pb.maximum, 100)
        self.assertEqual(pb.width, 75)
        self.assertEqual(pb.title, "")
        self.assertEqual(pb.current_amount, 0)

    def test_init_custom_values(self):
        """Test ProgressBar initialization with custom values."""
        pb = output.ProgressBar(minimum=10, maximum=200, width=50, title="Test")
        self.assertEqual(pb.minimum, 10)
        self.assertEqual(pb.maximum, 200)
        self.assertEqual(pb.width, 46)  # width reduced by title length
        self.assertEqual(pb.title, "Test")
        self.assertEqual(pb.current_amount, 10)

    def test_init_assertion_error(self):
        """Test ProgressBar initialization with invalid values raises AssertionError."""
        with self.assertRaises(AssertionError):
            output.ProgressBar(minimum=100, maximum=50)

    def test_append_amount(self):
        """Test append_amount method."""
        pb = output.ProgressBar(minimum=0, maximum=100)
        pb.append_amount(25)
        self.assertEqual(pb.current_amount, 25)
        pb.append_amount(30)
        self.assertEqual(pb.current_amount, 55)

    def test_update_percentage(self):
        """Test update_percentage method."""
        pb = output.ProgressBar(minimum=0, maximum=200)
        pb.update_percentage(50)
        self.assertEqual(pb.current_amount, 100.0)  # 50% of 200
        pb.update_percentage(75)
        self.assertEqual(pb.current_amount, 150.0)  # 75% of 200

    def test_update_amount(self):
        """Test update_amount method with clamping."""
        pb = output.ProgressBar(minimum=10, maximum=90)

        # Test normal update
        pb.update_amount(50)
        self.assertEqual(pb.current_amount, 50)

        # Test clamping to minimum
        pb.update_amount(5)
        self.assertEqual(pb.current_amount, 10)

        # Test clamping to maximum
        pb.update_amount(100)
        self.assertEqual(pb.current_amount, 90)

    def test_update_progress_bar_empty(self):
        """Test _update_progress_bar method with empty progress."""
        pb = output.ProgressBar(minimum=0, maximum=100, width=20)
        pb.current_amount = 0
        pb._update_progress_bar()
        self.assertIn(">", pb.prog_bar)
        self.assertIn("0%", pb.prog_bar)

    def test_update_progress_bar_full(self):
        """Test _update_progress_bar method with full progress."""
        pb = output.ProgressBar(minimum=0, maximum=100, width=20)
        pb.current_amount = 100
        pb._update_progress_bar()
        self.assertIn("=" * 18, pb.prog_bar)  # width-2 for brackets
        self.assertIn("100%", pb.prog_bar)

    def test_update_progress_bar_partial(self):
        """Test _update_progress_bar method with partial progress."""
        pb = output.ProgressBar(minimum=0, maximum=100, width=20)
        pb.current_amount = 50
        pb._update_progress_bar()
        self.assertIn("=", pb.prog_bar)
        self.assertIn(">", pb.prog_bar)
        self.assertIn("50%", pb.prog_bar)

    def test_update_progress_bar_with_title(self):
        """Test _update_progress_bar method with title."""
        pb = output.ProgressBar(minimum=0, maximum=100, width=30, title="Loading")
        pb.current_amount = 25
        pb._update_progress_bar()
        self.assertIn("Loading:", pb.prog_bar)
        self.assertIn("25%", pb.prog_bar)

    @patch("sys.stdout")
    def test_draw_no_change(self, mock_stdout):
        """Test draw method when progress bar hasn't changed."""
        pb = output.ProgressBar()
        mock_stdout.reset_mock()  # Reset mock after initialization
        pb.prog_bar = "test bar"
        pb.old_prog_bar = "test bar"
        pb.draw()
        mock_stdout.write.assert_not_called()
        mock_stdout.flush.assert_not_called()

    @patch("sys.stdout")
    def test_draw_with_change(self, mock_stdout):
        """Test draw method when progress bar has changed."""
        pb = output.ProgressBar()
        mock_stdout.reset_mock()  # Reset mock after initialization
        pb.prog_bar = "new bar"
        pb.old_prog_bar = "old bar"
        pb.draw()
        mock_stdout.write.assert_called_once_with("\rnew bar")
        mock_stdout.flush.assert_called_once()

    def test_str_representation(self):
        """Test __str__ method."""
        pb = output.ProgressBar()
        pb.prog_bar = "test progress bar"
        self.assertEqual(str(pb), "test progress bar")

    def test_integration_workflow(self):
        """Test complete workflow integration."""
        pb = output.ProgressBar(minimum=0, maximum=50, width=25, title="Test")

        # Test initial state
        self.assertEqual(pb.current_amount, 0)

        # Test percentage update
        pb.update_percentage(40)  # 40% of 50 = 20
        self.assertEqual(pb.current_amount, 20.0)

        # Test append amount
        pb.append_amount(10)  # 20 + 10 = 30
        self.assertEqual(pb.current_amount, 30)

        # Test direct amount update
        pb.update_amount(45)
        self.assertEqual(pb.current_amount, 45)

        # Test string representation contains expected elements
        result = str(pb)
        self.assertIn("Test:", result)
        self.assertIn("%", result)
        self.assertIn("[", result)
        self.assertIn("]", result)


if __name__ == "__main__":
    unittest.main()

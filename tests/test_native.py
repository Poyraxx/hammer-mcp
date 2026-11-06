import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native
import win32gui


class NativeTests(unittest.TestCase):
    def test_destroyed_transient_window_is_omitted(self):
        with patch.object(win32gui, 'GetClassName', side_effect=win32gui.error(1400, 'GetClassName', 'Invalid window handle')):
            self.assertEqual(native.class_name(123), '')

    def test_other_window_errors_are_retained(self):
        with patch.object(win32gui, 'GetClassName', side_effect=win32gui.error(5, 'GetClassName', 'Access denied')):
            with self.assertRaises(win32gui.error):
                native.class_name(123)


if __name__ == '__main__':
    unittest.main()

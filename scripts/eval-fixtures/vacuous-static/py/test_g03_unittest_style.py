import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


import unittest


class TestClamp(unittest.TestCase):
    def test_clamp_bounds(self):
        self.assertEqual(clamp(9, 0, 3), 3)
        self.assertEqual(clamp(-9, 0, 3), 0)

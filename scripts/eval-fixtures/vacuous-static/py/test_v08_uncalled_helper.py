import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_squares_helper_never_called():
    def check():
        assert squares(3) == [0, 1, 5]

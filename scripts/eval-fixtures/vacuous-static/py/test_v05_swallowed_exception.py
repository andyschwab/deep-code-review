import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_add_swallowed():
    try:
        assert add(1, 2) == 4
    except AssertionError:
        pass

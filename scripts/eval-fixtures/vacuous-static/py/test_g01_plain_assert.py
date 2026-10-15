import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_add_values():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

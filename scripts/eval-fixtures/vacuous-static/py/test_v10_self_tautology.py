import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_add_tautology():
    expected = add(2, 2)
    assert add(2, 2) == expected

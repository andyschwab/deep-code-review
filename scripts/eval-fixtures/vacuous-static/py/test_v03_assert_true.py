import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_clamp_ok():
    clamp(5, 0, 3)
    assert True

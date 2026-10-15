import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_add_float():
    assert add(0.1, 0.2) == pytest.approx(0.3)

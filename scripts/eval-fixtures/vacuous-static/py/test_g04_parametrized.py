import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


@pytest.mark.parametrize("n,want", [(1, False), (2, True), (9, False), (11, True)])
def test_is_prime(n, want):
    assert is_prime(n) is want

import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_prime_truthy():
    assert is_prime(13)
    assert not is_prime(15)

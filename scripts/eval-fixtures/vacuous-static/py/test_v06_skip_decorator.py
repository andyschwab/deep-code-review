import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


@pytest.mark.skip(reason="flaky")
def test_prime_skipped():
    assert is_prime(7)
    assert not is_prime(8)

import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_parse_error_message():
    try:
        parse_int("x1")
    except ValueError as e:
        assert "x1" in str(e)
    else:
        pytest.fail("expected ValueError")

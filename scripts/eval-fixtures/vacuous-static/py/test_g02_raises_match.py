import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_parse_rejects_text():
    with pytest.raises(ValueError, match="bad int"):
        parse_int("abc")

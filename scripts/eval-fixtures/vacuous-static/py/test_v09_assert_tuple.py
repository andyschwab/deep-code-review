import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_parse_tuple_assert():
    assert (parse_int("4") == 5, "parse_int is wrong")

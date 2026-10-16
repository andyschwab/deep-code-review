import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def check_sorted_squares(xs):
    assert xs == sorted(xs)
    assert xs[0] == 0


def test_squares_sorted():
    check_sorted_squares(squares(5))

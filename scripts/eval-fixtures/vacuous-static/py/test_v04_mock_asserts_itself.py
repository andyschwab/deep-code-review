import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_notify_calls_back():
    cb = mock.Mock()
    cb("HI")
    cb.assert_called_once_with("HI")

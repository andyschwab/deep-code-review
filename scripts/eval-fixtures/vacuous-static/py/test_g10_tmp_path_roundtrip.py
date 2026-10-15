import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_save_load(tmp_path):
    p = tmp_path / "a.txt"
    save(p, "  hello ")
    assert load(p) == "hello"

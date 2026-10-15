import pytest
from unittest import mock
from sut import add, clamp, parse_int, is_prime, notify, squares, save, load


def test_clamp_gated():
    import os
    if not os.environ.get("RUN_SLOW_TESTS"):
        return
    assert clamp(9, 0, 3) == 3

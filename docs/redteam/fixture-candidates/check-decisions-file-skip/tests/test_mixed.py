import pytest


def test_this_one_passes():
    assert True


@pytest.mark.skip(reason="the enforcement this binding claims never actually runs")
def test_this_one_is_skipped():
    assert False

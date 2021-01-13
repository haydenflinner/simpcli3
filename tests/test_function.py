"""Test simpcli3 functions."""

from simpcli3 import app


def test_app():
    """Test app.main function."""
    assert app.main("ah ", 3) == "ah ah ah "

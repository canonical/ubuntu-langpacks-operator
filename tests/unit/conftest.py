# Copyright 2026 Canonical
# See LICENSE file for licensing details.

"""Shared fixtures for the unit tests."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def no_subprocess():
    """Fail loudly if a test reaches a real subprocess call.

    Unit tests must mock out the Langpacks methods that touch the machine
    (for example, an unmocked setup_crontab would replace the crontab of
    whoever runs the tests).
    """
    with patch(
        "langpacks.run",
        side_effect=AssertionError(
            "unit test attempted to run a real subprocess; mock the Langpacks method"
        ),
    ):
        yield

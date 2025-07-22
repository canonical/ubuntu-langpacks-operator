#!/usr/bin/env python3
# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""A simple Launchpad client implementation."""

import logging
import os
from abc import ABC
from typing import Optional

import httplib2
from launchpadlib.launchpad import Launchpad

logger = logging.getLogger(__name__)


class LaunchpadClientBase(ABC):
    """Basic Launchpad client interface."""

    def active_series(self):
        """Return a list of the active ubuntu series."""
        return []


class LaunchpadClient(LaunchpadClientBase):
    """Launchpad client implementation."""

    def active_series(self):
        """Return a list of the active ubuntu series."""
        try:
            lp = Launchpad.login_anonymously(
                "langpacks",
                "production",
            )
        except Exception as e:
            logger.warning("Launchpad login failed: %s", e)
            return []

        ubuntu = lp.distributions["ubuntu"]

        active_series = []
        for s in ubuntu.series:
            if s.active:
                active_series.append(s.name)

        return active_series


class MockLaunchpadClient(LaunchpadClientBase):
    """Mock Launchpad client implementation."""

    def active_series(self):
        """Return a list of the active ubuntu series."""
        active_series = ["noble", "plucky", "questing"]

        return active_series

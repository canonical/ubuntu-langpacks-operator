#!/usr/bin/env python3
# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""A simple Launchpad client implementation."""

import os
from abc import ABC
from typing import Optional

import httplib2
from launchpadlib.launchpad import Launchpad


class LaunchpadClientBase(ABC):
    """Basic Launchpad client interface."""

    def active_series(self):
        """Return a list of the active ubuntu series."""
        return []


class LaunchpadClient(LaunchpadClientBase):
    """Launchpad client implementation."""

    def active_series(self):
        """Return a list of the active ubuntu series."""
        lp = Launchpad.login_anonymously(
            "langpacks",
            "production",
            proxy_info=_proxy_config,
        )
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


def _proxy_config(method="https") -> Optional[httplib2.ProxyInfo]:
    """Get charm proxy information from juju charm environment."""
    if method not in ("http", "https"):
        return

    env_var = f"JUJU_CHARM_{method.upper()}_PROXY"
    url = os.environ.get(env_var)

    if not url:
        return

    noproxy = os.environ.get("JUJU_CHARM_NO_PROXY", None)

    return httplib2.proxy_info_from_url(url, method, noproxy)

#!/usr/bin/env python3
# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""Charmed Operator for Ubuntu langpacks."""

import logging
from subprocess import CalledProcessError

import ops
from charms.operator_libs_linux.v0.apt import PackageError, PackageNotFoundError
from ops.model import Secret
from requests.exceptions import RequestException

from langpacks import Langpacks
from launchpad import LaunchpadClient

logger = logging.getLogger(__name__)


class UbuntuLangpacksCharm(ops.CharmBase):
    """Charmed Operator for Ubuntu langpacks."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.upgrade_charm, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.build_langpacks_action, self._on_build_langpacks)
        self.framework.observe(self.on.upload_langpacks_action, self._on_upload_langpacks)
        self.framework.observe(self.on.stop, self._on_stop)

        self._langpacks = Langpacks(LaunchpadClient())

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        self.unit.status = ops.MaintenanceStatus("Updating langpack-o-matic checkout")

        try:
            self._langpacks.update_checkout()
        except CalledProcessError:
            self.unit.status = ops.BlockedStatus(
                "Failed to start services. Check `juju debug-log` for details."
            )
            return

        self.unit.status = ops.ActiveStatus()

    def _on_install(self, event: ops.InstallEvent):
        """Handle install event."""
        self.unit.status = ops.MaintenanceStatus("Setting up environment")
        try:
            self._langpacks.install()
        except (CalledProcessError, PackageError, PackageNotFoundError):
            self.unit.status = ops.BlockedStatus(
                "Failed to set up the environment. Check `juju debug-log` for details."
            )
            return

        self.unit.status = ops.MaintenanceStatus("Setting up crontab")
        self._langpacks.setup_crontab()

        self.unit.status = ops.ActiveStatus()

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Update configuration and fetch code updates."""
        self.unit.status = ops.MaintenanceStatus("Importing signing key")

        try:
            secret_id = self.config["uploader-secret-id"]
        except KeyError:
            logger.warning("No 'uploader-secret-id' config, can't set up signing key")
            self.unit.status = ops.ActiveStatus(
                "Signing disabled. Set the 'uploader-secret-id' to enable."
            )
            return

        try:
            uploader_secret: Secret = self.model.get_secret(id=secret_id)
        except (ops.SecretNotFoundError, ops.model.ModelError):
            logger.warning("Error getting secret")
            self.unit.status = ops.ActiveStatus(
                "Secret not available. Check that access was granted."
            )
            return

        gpgkey = uploader_secret.get_content().get("gpgkey")
        if not gpgkey:
            logger.warning("Signing key secret not found")
            self.unit.status = ops.ActiveStatus(
                "Secret not available. Check that the 'gpgkey' key exists."
            )
            return
        try:
            self._langpacks.import_gpg_key(gpgkey)
        except CalledProcessError:
            self.unit.status = ops.ActiveStatus(
                "Failed to import the signing key. Check `juju debug-log` for details."
            )
            return

        dputcfg = self.config["dput-ng-config"]
        try:
            self._langpacks.set_dput_config(dputcfg)
        except IOError:
            self.unit.status = ops.ActiveStatus(
                "Failed to write dput config. Check `juju debug-log` for details."
            )
            return

        sshkey = uploader_secret.get_content().get("sshkey")
        if not sshkey:
            logger.warning("Uploader key secret not found")
            self.unit.status = ops.ActiveStatus(
                "Secret not available. Check that the 'sshkey' key exists."
            )
            return
        try:
            self._langpacks.import_ssh_key(sshkey)
        except IOError:
            self.unit.status = ops.ActiveStatus(
                "Failed to import the uploader key. Check `juju debug-log` for details."
            )
            return

        logger.debug("Signing and upload keys imported")
        self.unit.status = ops.ActiveStatus()

    def _on_build_langpacks(self, event: ops.ActionEvent):
        """Build new langpacks."""
        release = event.params["release"]
        base = event.params["base"]

        self.unit.status = ops.MaintenanceStatus("Building langpacks")

        try:
            event.log("Building langpacks, it may take a while")
            self._langpacks.build_langpacks(base, release)
        except (CalledProcessError, IOError, RequestException):
            event.log("Langpacks build failed")
            self.unit.status = ops.ActiveStatus(
                "Failed to build langpacks. Check `juju debug-log` for details."
            )
            return
        self.unit.status = ops.ActiveStatus()

    def _on_upload_langpacks(self, event: ops.ActionEvent):
        """Upload pending langpacks."""
        self.unit.status = ops.MaintenanceStatus("Uploading langpacks")

        if not self._langpacks.check_gpg_key():
            event.log("Can't upload langpacks without a signing key")
            logger.warning("Can't upload langpacks without a signing key")
            self.unit.status = ops.ActiveStatus(
                "Upload disabled. Set and grant 'uploader-secret-id' to enable."
            )
            return

        try:
            event.log("Uploading langpacks, it may take a while")
            self._langpacks.upload_langpacks()
        except CalledProcessError:
            self.unit.status = ops.ActiveStatus(
                "Failed to upload langpacks. Check `juju debug-log` for details."
            )
            return

        self.unit.status = ops.ActiveStatus()

    def _on_stop(self, event: ops.StopEvent):
        """Handle stop event."""
        self.unit.status = ops.MaintenanceStatus("Removing crontab")

        try:
            self._langpacks.disable_crontab()
        except CalledProcessError as e:
            logger.exception("Failed to disable the crontab: %s", e)
            return


if __name__ == "__main__":  # pragma: nocover
    ops.main(UbuntuLangpacksCharm)

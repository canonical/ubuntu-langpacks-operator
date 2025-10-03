# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""Unit tests for the charm.

These tests only cover those methods that do not require internet access,
and do not attempt to manipulate the underlying machine.
"""

from subprocess import CalledProcessError
from unittest.mock import patch

import pytest
from charms.operator_libs_linux.v0.apt import PackageError, PackageNotFoundError
from ops.testing import (
    ActiveStatus,
    BlockedStatus,
    Context,
    MaintenanceStatus,
    Secret,
    State,
)
from requests.exceptions import RequestException

from charm import UbuntuLangpacksCharm


@pytest.fixture
def ctx():
    return Context(UbuntuLangpacksCharm)


@pytest.fixture
def base_state(ctx):
    return State(leader=True)


@patch("charm.Langpacks.install")
def test_install_success(install_mock, ctx, base_state):
    install_mock.return_value = True
    out = ctx.run(ctx.on.install(), base_state)
    assert out.unit_status == ActiveStatus("")
    assert install_mock.called


@patch("charm.Langpacks.install")
@pytest.mark.parametrize(
    "exception",
    [
        PackageError,
        PackageNotFoundError,
        CalledProcessError(1, "foo"),
    ],
)
def test_install_failure(mock, exception, ctx, base_state):
    mock.side_effect = exception
    out = ctx.run(ctx.on.install(), base_state)
    assert out.unit_status == BlockedStatus(
        "Failed to set up the environment. Check `juju debug-log` for details."
    )


@patch("charm.Langpacks.install")
def test_upgrade_success(install_mock, ctx, base_state):
    install_mock.return_value = True
    out = ctx.run(ctx.on.upgrade_charm(), base_state)
    assert out.unit_status == ActiveStatus("")
    assert install_mock.called


@patch("charm.Langpacks.install")
@pytest.mark.parametrize(
    "exception",
    [
        PackageError,
        PackageNotFoundError,
        CalledProcessError(1, "foo"),
    ],
)
def test_upgrade_failure(mock, exception, ctx, base_state):
    mock.side_effect = exception
    out = ctx.run(ctx.on.upgrade_charm(), base_state)
    assert out.unit_status == BlockedStatus(
        "Failed to set up the environment. Check `juju debug-log` for details."
    )


def test_config_changed_no_secret(ctx, base_state):
    out = ctx.run(ctx.on.config_changed(), base_state)
    assert out.unit_status == ActiveStatus(
        "Signing disabled. Set the 'uploader-secret-id' to enable."
    )


# needs to mock ops.SecretNotFoundError, ops.model.ModelError
def test_config_changed_secret_not_granted(ctx, base_state):
    config_secret = Secret(tracked_content={"gpgkey": "GPG_PRIVATE_KEY"})
    state = State(leader=True, config={"uploader-secret-id": config_secret.id})
    out = ctx.run(ctx.on.config_changed(), state)
    assert out.unit_status == ActiveStatus("Secret not available. Check that access was granted.")


def test_config_changed_no_gpgkey(ctx, base_state):
    config_secret = Secret(
        tracked_content={"nogpgkey": "GPG_PRIVATE_KEY", "sshkey": "SSH_PRIVATE_KEY"}
    )
    state = State(
        leader=True,
        secrets=[config_secret],
        config={"uploader-secret-id": config_secret.id},
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert out.unit_status == ActiveStatus(
        "Secret not available. Check that the 'gpgkey' key exists."
    )


@patch("charm.Langpacks.import_gpg_key")
def test_config_changed_import_gpg_key_failure(mock_gpg, ctx, base_state):
    mock_gpg.side_effect = CalledProcessError(1, "gpg")
    config_secret = Secret(
        tracked_content={"gpgkey": "GPG_PRIVATE_KEY", "sshkey": "SSH_PRIVATE_KEY"}
    )
    state = State(
        leader=True,
        secrets=[config_secret],
        config={"uploader-secret-id": config_secret.id},
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert out.unit_status == ActiveStatus(
        "Failed to import the signing key. Check `juju debug-log` for details."
    )


@patch("charm.Langpacks.import_gpg_key")
def test_config_changed_no_sshkey(mock_gpg, ctx, base_state):
    mock_gpg.return_value = True
    config_secret = Secret(
        tracked_content={"gpgkey": "GPG_PRIVATE_KEY", "nosshkey": "SSH_PRIVATE_KEY"}
    )
    state = State(
        leader=True,
        secrets=[config_secret],
        config={"uploader-secret-id": config_secret.id},
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert out.unit_status == ActiveStatus(
        "Secret not available. Check that the 'sshkey' key exists."
    )


@patch("charm.Langpacks.import_gpg_key")
@patch("charm.Langpacks.import_ssh_key")
def test_config_changed_import_ssh_key_failure(mock_ssh, mock_gpg, ctx, base_state):
    mock_gpg.return_value = True
    mock_ssh.side_effect = IOError(1, "gpg")
    config_secret = Secret(
        tracked_content={"gpgkey": "GPG_PRIVATE_KEY", "sshkey": "SSH_PRIVATE_KEY"}
    )
    state = State(
        leader=True,
        secrets=[config_secret],
        config={"uploader-secret-id": config_secret.id},
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert out.unit_status == ActiveStatus(
        "Failed to import the uploader key. Check `juju debug-log` for details."
    )


@patch("charm.Langpacks.import_gpg_key")
@patch("charm.Langpacks.import_ssh_key")
def test_config_changed(import_gpg_key_mock, import_ssh_key_mock, ctx, base_state):
    config_secret = Secret(
        tracked_content={"gpgkey": "GPG_PRIVATE_KEY", "sshkey": "SSH_PRIVATE_KEY"}
    )
    state = State(
        leader=True,
        secrets=[config_secret],
        config={"uploader-secret-id": config_secret.id},
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert out.unit_status == ActiveStatus()
    assert import_gpg_key_mock.called
    assert import_ssh_key_mock.called


@patch("charm.Langpacks.update_checkout")
def test_start_checkout_update_fail(update_checkout_mock, ctx, base_state):
    update_checkout_mock.side_effect = CalledProcessError(1, "checkout")
    out = ctx.run(ctx.on.start(), base_state)
    assert out.unit_status == BlockedStatus(
        "Failed to start services. Check `juju debug-log` for details."
    )
    assert update_checkout_mock.called


@patch("charm.Langpacks.update_checkout")
def test_start_success(update_checkout_mock, ctx, base_state):
    update_checkout_mock.return_value = True
    out = ctx.run(ctx.on.start(), base_state)
    assert out.unit_status == ActiveStatus()
    assert update_checkout_mock.called


@patch("charm.Langpacks.build_langpacks")
def test_build_langpacks_success(build_langpacks_mock, ctx, base_state):
    out = ctx.run(
        ctx.on.action("build-langpacks", params={"release": "questing", "base": True}),
        base_state,
    )
    assert ctx.action_logs == ["Building langpacks, it may take a while"]
    assert out.unit_status == ActiveStatus()
    assert build_langpacks_mock.called


@patch("charm.Langpacks.build_langpacks")
@pytest.mark.parametrize("exception", [IOError, RequestException, CalledProcessError(1, "build")])
def test_build_langpacks_failure(mock, exception, ctx, base_state):
    mock.side_effect = exception
    out = ctx.run(
        ctx.on.action("build-langpacks", params={"release": "questing", "base": True}),
        base_state,
    )
    assert ctx.action_logs == [
        "Building langpacks, it may take a while",
        "Langpacks build failed",
    ]
    assert out.unit_status == ActiveStatus(
        "Failed to build langpacks. Check `juju debug-log` for details."
    )
    # assert build_langpacks_mock.called


@patch("charm.Langpacks.check_gpg_key")
@patch("charm.Langpacks.upload_langpacks")
def test_upload_langpacks_success(upload_langpacks_mock, check_gpg_key_mock, ctx, base_state):
    check_gpg_key_mock.return_value = True
    out = ctx.run(ctx.on.action("upload-langpacks"), base_state)
    assert ctx.action_logs == ["Uploading langpacks, it may take a while"]
    assert out.unit_status == ActiveStatus()
    assert upload_langpacks_mock.called


@patch("charm.Langpacks.check_gpg_key")
def test_upload_langpacks_no_key(check_gpg_key_mock, ctx, base_state):
    check_gpg_key_mock.return_value = False
    out = ctx.run(ctx.on.action("upload-langpacks"), base_state)
    assert ctx.action_logs == ["Can't upload langpacks without a signing key"]
    assert out.unit_status == ActiveStatus(
        "Upload disabled. Set and grant 'uploader-secret-id' to enable."
    )


@patch("charm.Langpacks.check_gpg_key")
@patch("charm.Langpacks.upload_langpacks")
def test_upload_langpacks_failure(upload_langpacks_mock, check_gpg_key_mock, ctx, base_state):
    check_gpg_key_mock.return_value = True
    upload_langpacks_mock.side_effect = CalledProcessError(1, "upload")
    out = ctx.run(ctx.on.action("upload-langpacks"), base_state)
    assert out.unit_status == ActiveStatus(
        "Failed to upload langpacks. Check `juju debug-log` for details."
    )


@patch("charm.Langpacks.disable_crontab")
def test_stop_sucess(disable_crontab_mock, ctx, base_state):
    out = ctx.run(ctx.on.stop(), base_state)
    assert out.unit_status == MaintenanceStatus("Removing crontab")
    assert disable_crontab_mock.called


@patch("charm.Langpacks.disable_crontab")
def test_stop_failure(disable_crontab_mock, ctx, base_state):
    disable_crontab_mock.side_effect = CalledProcessError(1, "crontab")
    out = ctx.run(ctx.on.stop(), base_state)
    assert out.unit_status == MaintenanceStatus("Removing crontab")
    assert disable_crontab_mock.called

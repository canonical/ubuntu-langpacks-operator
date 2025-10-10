# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""Representation of the langpacks service."""

import logging
import os
import shutil
import time
from pathlib import Path
from subprocess import PIPE, STDOUT, CalledProcessError, run

import charms.operator_libs_linux.v0.apt as apt
import requests
from charms.operator_libs_linux.v0.apt import PackageError, PackageNotFoundError

logger = logging.getLogger(__name__)

# Packages installed as part of the update process.
PACKAGES = [
    "build-essential",
    "libgettextpo-dev",
    "debhelper",
    "fakeroot",
    "python3-launchpadlib",
    "python3-apt",
    "dput-ng",
    "git",
    "devscripts",
    "lintian",
    "corkscrew",
]

BUILDDIR = Path("/app/build")
LOGDIR = Path("/app/log")
REPO_LOCATION = Path("/app/langpack-o-matic")
REPO_URL = "https://git.launchpad.net/langpack-o-matic"


class Langpacks:
    """Represent a langpacks instance in the workload."""

    def __init__(self, launchpad_client):
        logger.debug("Langpacks class init")
        self.launchpad_client = launchpad_client
        self.env = os.environ.copy()
        self.proxies = {}
        juju_http_proxy = self.env.get("JUJU_CHARM_HTTP_PROXY")
        juju_https_proxy = self.env.get("JUJU_CHARM_HTTPS_PROXY")
        if juju_http_proxy:
            logger.debug("Setting HTTP_PROXY env to %s", juju_http_proxy)
            self.env["HTTP_PROXY"] = juju_http_proxy
            self.proxies["http"] = juju_http_proxy
        if juju_https_proxy:
            logger.debug("Setting HTTPS_PROXY env to %s", juju_https_proxy)
            self.env["HTTPS_PROXY"] = juju_https_proxy
            self.proxies["https"] = juju_https_proxy

    def setup_crontab(self):
        """Configure the crontab for the service."""
        try:
            run(
                [
                    "crontab",
                    "src/crontab",
                ],
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
            )
            logger.debug("Crontab configured.")
            return
        except CalledProcessError as e:
            logger.debug("Installation of the crontab failed: '%s'", e.stdout)
            raise

    def install(self):
        """Install the langpack builder environment."""
        # Install the deb packages needed for the service
        try:
            apt.update()
            logger.debug("Apt index refreshed.")
        except CalledProcessError as e:
            logger.error("Failed to update package cache: %s", e)
            raise

        for p in PACKAGES:
            try:
                apt.add_package(p)
                logger.debug("Package %s installed", p)
            except PackageNotFoundError:
                logger.error("Failed to find package %s in package cache", p)
                raise
            except PackageError as e:
                logger.error("Failed to install %s: %s", p, e)
                raise

        # Clone the langpack-o-matic repo
        try:
            run(
                [
                    "git",
                    "clone",
                    "-b",
                    "master",
                    REPO_URL,
                    REPO_LOCATION,
                ],
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                env=self.env,
            )
            logger.debug("Langpack-o-matic vcs cloned.")
        except CalledProcessError as e:
            logger.debug("Git clone of the code failed: %s", e.stdout)
            raise

        # Create the build and log directories
        for dname in (BUILDDIR, LOGDIR):
            try:
                os.mkdir(dname)
                logger.debug("Directory %s created", dname)
            except OSError as e:
                logger.warning("Creating directory %s failed: %s", dname, e)
                raise

    def update_checkout(self):
        """Update the langpack-o-matic checkout."""
        try:
            run(
                [
                    "git",
                    "-C",
                    REPO_LOCATION,
                    "pull",
                ],
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                env=self.env,
            )
            logger.debug("Langpack-o-matic checkout updated.")

            result = run(
                [
                    "git",
                    "-C",
                    REPO_LOCATION,
                    "describe",
                    "--tags",
                    "--always",
                    "--dirty",
                ],
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                env=self.env,
            )
            workload_version = result.stdout.strip()
            logger.debug("langpack-o-matic current revision: %s", workload_version)
            return workload_version

        except CalledProcessError as e:
            logger.debug("Git pull of the langpack-o-matic repository failed: %s", e.stdout)
            raise

        # Call make target
        try:
            run(
                [
                    "make",
                    "-C",
                    REPO_LOCATION / "bin",
                ],
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
            )
            logger.debug("Langpack-o-matic bin/msgequal build.")
        except CalledProcessError as e:
            logger.debug("Build of bin/msgequal failed %s", e.stdout)
            raise

    def _clean_builddir(self, releasedir: Path):
        """Clean build cache."""
        if not os.path.exists(releasedir):
            return

        if os.path.exists(releasedir):
            try:
                shutil.rmtree(releasedir)
                logger.debug("Removed the existing cache directory: %s", releasedir)
            except OSError as e:
                logger.error("Failed to remove cache directory %s: %s", releasedir, e)

    def _download_tarball(self, url: str, filename: Path):
        try:
            with requests.get(url, stream=True, timeout=10, proxies=self.proxies) as r:
                r.raise_for_status()

                with open(filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception:
            raise

    def build_langpacks(self, base: bool, release: str):
        """Build the langpacks."""
        release = release.lower()
        active_series = self.launchpad_client.active_series()

        # check that the series used is valid
        if release not in active_series:
            logger.debug("Release %s isn't an active Ubuntu series", release)
            return

        releasedir = BUILDDIR / release

        if base:
            download_url = (
                f"https://translations.launchpad.net/ubuntu/{release}/+latest-full-language-pack"
            )
            tarball = REPO_LOCATION / f"ubuntu-{release}-translations.tar.gz"
            import_options = ["-v", "--treshold=10"]

            # Clean existing cache directories before starting a base build
            self._clean_builddir(releasedir)

        else:
            download_url = (
                f"https://translations.launchpad.net/ubuntu/{release}/+latest-delta-language-pack"
            )
            tarball = REPO_LOCATION / f"ubuntu-{release}-translations-update.tar.gz"
            import_options = ["-v", "--update", "--treshold=10"]

        # Create the build target directory
        try:
            os.makedirs(releasedir, exist_ok=True)
            logger.debug("Directory %s created", releasedir)
        except OSError as e:
            logger.warning("Creating directory %s failed: %s", releasedir, e)
            raise

        # Download the current translations tarball from launchpad
        try:
            self._download_tarball(download_url, tarball)
            logger.debug("Translations tarball downloaded.")
        except Exception as e:
            logger.debug("Downloading %s failed: %s", download_url, e)
            raise

        # Call the import script that prepares the packages
        logger.debug("Creating the packages.")
        try:
            logpath = LOGDIR / release
            with open(logpath, "a") as logfile:
                run(
                    [REPO_LOCATION / "import"]
                    + import_options
                    + [
                        tarball,
                        release,
                        BUILDDIR / release,
                    ],
                    check=True,
                    cwd=BUILDDIR,
                    stdout=logfile,
                    stderr=STDOUT,
                    text=True,
                )
            logger.debug("Translations packages prepared.")
        except Exception as e:
            logger.debug("Building the langpacks source failed: %s", e.stdout)
            raise

    def upload_langpacks(self):
        """Upload the packages."""
        try:
            logpath = LOGDIR / "upload.log"
            with open(logpath, "a") as logfile:
                run(
                    [
                        REPO_LOCATION / "packages",
                        "upload",
                    ],
                    cwd=BUILDDIR,
                    check=True,
                    stdout=logfile,
                    stderr=STDOUT,
                    text=True,
                )
            logger.debug("Language packs uploaded.")
        except CalledProcessError as e:
            logger.debug("Uploading the langpacks failed: %s", e.stdout)
            raise

    def disable_crontab(self):
        """Disable the crontab."""
        try:
            run(
                [
                    "crontab",
                    "-r",
                ],
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
            )
        except CalledProcessError as e:
            logger.debug("Disabling of crontab failed: %s", e.stdout)
            raise

    def import_gpg_key(self, key: str):
        """Import the private gpg key."""
        try:
            response = run(
                [
                    "gpg",
                    "--import",
                ],
                check=True,
                input=key,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
            )
            logger.debug("GPG key imported: %s", response.stdout)
        except CalledProcessError as e:
            logger.debug("Importing key failed: %s", e.stdout)
            raise

    def import_ssh_key(self, key: str):
        """Import the private ssh key."""
        sshfile = "/root/.ssh/id_ed25519"

        try:
            os.makedirs("/root/.ssh", exist_ok=True)
        except Exception as e:
            logger.debug("Error creating /root/.ssh: %s", e)
            raise

        if os.path.exists(sshfile):
            try:
                with open(sshfile, "r", encoding="utf-8") as f:
                    currentssh = f.read()
            except IOError as e:
                logger.debug("Error reading existing ssh key: %s", e)
                raise

            if key == currentssh:
                logger.debug("the ssh key didn't change")
                return

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backupfile = f"{sshfile}.bak_{timestamp}"

            try:
                os.rename(sshfile, backupfile)
            except OSError as e:
                logger.debug("Error renaming sshkey: %s", e)
                raise

        try:
            fd = os.open(sshfile, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
            os.write(fd, key.encode("utf-8"))
            os.close(fd)
        except IOError as e:
            logger.debug("Error creating sshkey: %s", e)
            raise

        logger.debug("SSH key imported")

    def check_gpg_key(self):
        """Check if a private gpg key is configured."""
        try:
            response = run(
                [
                    "gpg",
                    "--list-secret-keys",
                    "--with-colons",
                ],
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
            )
            for line in response.stdout.splitlines():
                # if the output includes 'sec' then there is a secret key
                if line.startswith("sec:"):
                    return True
            return False
        except Exception as e:
            logger.debug("Listing available gpg keys failed: %s", e)
            return False

    def set_dput_config(self, dputcfg: str):
        """Write the dput configuration from the option."""
        if not dputcfg:
            logger.debug("No dput config to write")
            return

        try:
            os.makedirs("/root/.dput.d/profiles", exist_ok=True)
        except Exception as e:
            logger.debug("Error creating /root/.dput.d/profiles: %s", e)
            raise

        try:
            with open("/root/.dput.d/profiles/ubuntu.json", "w") as f:
                f.write(dputcfg)
        except IOError as e:
            logger.debug("Error writing the dput configuration: %s", e)
            raise

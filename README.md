# Ubuntu Langpacks Operator


**Ubuntu Langpacks Operator** is a [charm](https://juju.is/charms-architecture) for deploying an Ubuntu language pack builder environment.

This reposistory contains the code for the charm, the application is coming from that [repository](https://git.launchpad.net/langpack-o-matic).

## Basic usage

Assuming you have access to a bootstrapped [Juju](https://juju.is) controller, you can deploy the charm with:

```bash
❯ juju deploy ubuntu-langpacks
```

Once the charm is deployed, you can check the status with Juju status:

```bash
❯ $ juju status
Model        Controller  Cloud/Region         Version  SLA          Timestamp
welcome-lxd  lxd         localhost/localhost  3.6.7    unsupported  13:29:50+02:00

App       Version  Status  Scale  Charm             Channel  Rev  Exposed  Message
langpack           active      1  ubuntu-langpacks             0  no

Unit          Workload  Agent  Machine  Public address  Ports  Message
langpack/0*  active    idle    1       10.142.46.109

Machine  State    Address        Inst id         Base          AZ  Message
1        started  10.142.46.109  juju-fd4fe1-1   ubuntu@24.04      Running
```

On first start up, the charm will install the application and setup a cronjob to build regular language packs updates for the supported Ubuntu series. 

The charm relies on the launchpad ~langpack-uploader user's private gpg key to be provided as a secret.

```
$ juju add-secret langpack-gpg-key key#file=langpack.priv.asc
$ juju grant-secret langpack-gpg-key ubuntu-langpacks
```

There charm has those configuration options:

`uploader-secret-id`, which you can set:

```bash
❯ juju config ubuntu-langpacks uploader-secret-id=secret:SECRET_ID
```

where SECRET_ID is the ID of the juju secret.

`dput-ng-config`, which is dput-ng configuration provided as a string:

```bash
❯ $ juju config ubuntu-langpacks 'dput-ng-config={ "default_host_main": "ubuntu", "login": "langpack-uploader", "method": "secure_sftp" }'
```


To build the langpacks, you can use the provided Juju [Action](https://documentation.ubuntu.com/juju/3.6/howto/manage-actions/):

```bash
❯ juju run ubuntu-langpacks/0 build-langpacks base=true|false release="<codename>"
```

## Contribute to Ubuntu Langpacks Operator

Ubuntu Langpacks Operator is open source and part of the Canonical family. We would love your help.

If you're interested, start with the [contribution guide](CONTRIBUTING.md).

## License and copyright

Ubuntu Langpacks Operator is released under the [GPL-3.0 license](LICENSE).

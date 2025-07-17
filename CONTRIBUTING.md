# Contributing

This documents explains the processes and practices recommended for contributing enhancements to
this operator.

- Generally, before developing enhancements to this charm, you should consider [opening an issue
  ](https://github.com/canonical/ubuntu-manpages-operator/issues) explaining your use case.
- If you would like to chat with us about your use-cases or proposed implementation, you can reach
  us [on Matrix](https://ubuntu.com/community/communications/matrix) or [Discourse](https://discourse.charmhub.io/).
- Familiarising yourself with the [Operator Framework](https://ops.readthedocs.io/en/latest/) library
  will help you a lot when working on new features or bug fixes.
- All enhancements require review before being merged. Code review typically examines
  - code quality
  - test coverage
  - user experience for Juju administrators this charm.
- Please help us out in ensuring easy to review branches by rebasing your pull request branch onto
  the `main` branch. This also avoids merge commits and creates a linear Git commit history.

## Developing

This project uses [`uv`](https://github.com/astral-sh/uv) for managing dependencies and virtual
environments.

You can create a virtual environment manually should you wish, though most of that is taken
care of automatically if you use the `Makefile` provided:

```bash
❯ make format        # update your code according to linting rules
❯ make lint          # code style
❯ make unit          # run unit tests
```

To create the environment manually:

```bash
❯ uv venv
❯ source .venv/bin/activate
❯ uv sync --all-extras
```

## Running tests

Unit tests can be run locally with no additional tools by running `make unit`. All of the project's unit tests are designed to run agnostic of machine and network, and shouldn't require any additional dependencies other than those injected by `uv run` and the `Make` target.

## Build charm

Build the charm in this git repository using:

```bash
charmcraft pack
```

### Deploy

```bash
# Create a model
❯ juju add-model dev

# Enable DEBUG logging
❯ juju model-config logging-config="<root>=INFO;unit=DEBUG"

# Deploy the charm
❯ juju deploy ./ubuntu-langpacks_amd64.charm
```

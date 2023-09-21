# quantready-api

A template to build and deploy fastapi applications

Built using [quantready](https://github.com/closedloop-technologies/quantready) using template ([https://github.com/closedloop-technologies/quantready-base])[https://github.com/closedloop-technologies/quantready-base]

# quantready-base

Publish public or private python libraries - using the modern python stack

## ✨ Features

Clean Code:

* ✔️ [poetry](https://python-poetry.org/) for dependency management
* ✔️ [pre-commit](https://pre-commit.com/) hooks for code formatting, linting, and testing
* ✔️ [unittest](https://docs.python.org/3/library/unittest.html) for testing
* ✔️ [gitleaks](https://gitleaks.io/) for secrets scanning

Deployment:

* ✔️ [github actions](https://github.com/actions) for CI/CD
* ✔️ [docker](https://docker.com) for building containers
* ✔️ [twine](https://twine.readthedocs.io/en/latest/) for publishing to pypi or private repositories
* 🔲 [gcloud](https://cloud.google.com/sdk/gcloud) for publishing to private repositories

## 📦 Installation

There are two ways to install:

### 1. Install using `quantready` cli

It is best to install as a template using [gh](https://cli.github.com/)

```bash
pip install quantready

# Create a new repo
quantready create <your-repo> --template quantready/quantready-base

```

### 2. Install as a template

To install and configure yourself using [gh](https://cli.github.com/)

```bash
gh template copy quantready/quantready-base <your-repo>

pip install typer
python configure.py
```

## 💻 Development

### Install dependencies

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
poetry install

# Install pre-commit hooks
pre-commit install --install-hooks

# Create a .env file and modify it's contents
cp .env.example .env

```

## 🚀 Deployment

The best way is to use quantready cli

```bash
# Configure the project and cloud providers
quantready configure
```

This will create a .quantready file in the root of the project.

### GitHub Actions: On push to `main`

Github actions are configured to run on push to main.
It will read the config from .quantready file and
publish the library to pypi or private repository as well as build the docker image and push it to docker hub or gcr.

### Push Docker image

```bash
# Build the image
docker build -t quantready/quantready-base .

# Run the image
docker run -it --rm quantready/quantready-base

# Push the image to docker hub
docker push quantready/quantready-base

# Push the image to gcr
docker tag quantready/quantready-base gcr.io/<your-project>/quantready-base
```

### Publish to pypi

```bash
# Build the package
poetry build
poetry run twine upload dist/*
```

Get `PYPI_API_TOKEN` from <https://pypi.org/manage/account/token/>
And set it as a github secret <https://github.com/><username>/<repo>/settings/secrets/actions

### Publish to private repository

```bash
# Build the package
poetry build
poetry run twine upload --repository-url https://pypi.yourdomain.com dist/*

```

## 📝 License

This project is licensed under the terms of the [MIT license](/LICENSE).

## 📚 Resources

* [Python Packaging User Guide](https://packaging.python.org/)
* [Poetry](https://python-poetry.org/)
* [Pre-commit](https://pre-commit.com/)
* [Github Actions](
https://docs.github.com/en/actions)
* [Docker](https://docker.com)
* [Twine](https://twine.readthedocs.io/en/latest/)
* [Gcloud](https://cloud.google.com/sdk/gcloud)
* [GitHub CLI](https://cli.github.com/)

## ✅✅✅ QuantReady Stack - Templates

* [quantready](https://github.com/closedloop-technologies/quantready)
  * CLI for creating and configuring projects and using the quantready-* templates
* [quantready-base](https://github.com/closedloop-technologies/quantready)
  * This template - build and publish python libraries and docker images
* [quantready-api](https://github.com/closedloop-technologies/quantready-api) - A template to build and deploy fastapi applications
  * authentication - api key or oauth
  * authorization - RBAC via OSO
  * rate limiting - via redis
  * job-queues to support long-running tasks
  * workers
  * caching
  * github actions to deploy to gcloud
  * all other features of quantready-base
* [quantready-vendor](https://github.com/closedloop-technologies/quantready-vendor) - A template to sell and meter access to your APIs. Supports time-based and usage-based pricing.
  * supports free and paid endpoints
  * billing per API call or per time-period
  * stripe-cli integration for managing products and billing
  * pricing-tables, account management and checkout
  * usage tracking api
  * all other features of quantready-api
* [quantready-chat]
  * A template to build and deploy chatbots
  * Supports Websockets
  * Slack Integration
  * all other features of quantready-vendor

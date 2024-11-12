# MLModelScope API components

This repository provides the main parts of the MLModelScope API

## Getting started

### Prerequisites

* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)
* [Python](https://www.python.org/downloads/) (for the Python API, version 3.8 or later)

### Cloning the repository

To clone the repository, run:

```bash
git clone https://github.com/c3sr/mlmodelscope-api.git
cd mlmodelscope-api
```

### Environment variables

The API requires two environment files to be present in the project root folder `mlmodelscope-api`:

* `.env` - contains environment variables for the API
* `.env.companion` - contains environment variables for the Companion service

The `.env` file should contain the following variables:

- `DOCKER_REGISTRY` - the Docker registry to pull images from, defaults to `c3sr`
- `ENVIRONMENT` - the environment the API is running in such as `local.`
- `API_VERSION` - the version of the API
- `DB_HOST` - the hostname of the PostgreSQL database
- `DB_PORT` - the port of the PostgreSQL database
- `DB_USER` - the username for the PostgreSQL database
- `DB_PASSWORD` - the password for the PostgreSQL database
- `DB_DBNAME` - the name of the PostgreSQL database
- `MQ_HOST` - the hostname of the RabbitMQ message queue
- `MQ_PORT` - the port of the RabbitMQ message queue
- `MQ_USER` - the username for the RabbitMQ message queue
- `MQ_PASSWORD` - the password for the RabbitMQ message queue
- `MQ_ERLANG_COOKIE` - the Erlang cookie for RabbitMQ
- `tracer_PORT` - the port for the Jaeger tracer
- `tracer_HOST` - the hostname for the Jaeger tracer
- `TRACER_ADDRESS` - the address for the Jaeger tracer

The `.env.companion` file should contain the following variables:

- `COMPANION_AWS_KEY` - the AWS key for the Companion service
- `COMPANION_AWS_SECRET` - the AWS secret for the Companion service
- `COMPANION_AWS_BUCKET` - the AWS bucket for the Companion service
- `COMPANION_AWS_REGION` - the AWS region for the Companion service

As this file will
likely contain private credentials it should **never** be committed to source control!

### Running

To run a local version of the API you will need to have Docker and Docker
Compose installed. The following command will build the latest API image
and run it alongside the other necessary system components:

`docker compose up -d --build`

The additional components launched are:

* RabbitMQ - message queue providing communication between the API and ML agents
* PostgreSQL - the database
  * The database is initialized from the file `docker/data/c3sr-bootstrap.sql.gz`
* Companion - assists in cloud storage uploads
* Traefik - reverse proxy, see below for details
* Consul - service discovery
* A suite of services to support monitoring with Prometheus/Grafana

## Deployment

The `DOCKER_REGISTRY` environment variable must be set to build or pull
the correct image tags for development, staging, or production. The `.env`
file sets this to `c3sr` by default so that images will be tagged and
pulled from the C3SR namespace on Docker Hub. Change this if you want to
use a private registry to host your own modified images.

This repository contains a Github workflow that will automatically build and
push an API image to the Github Container Registry each time new commits
are pushed to Github on the `master` branch.

You can read more about the Docker Compose configuration [here](docs/docker-compose.md).

## API

There are two API implementations in this repository: a Go API and a Python API. The Go API is the default API for the project, and the Python API is provided for compatibility with existing code.

### Go API

The `/api` directory contains a Go application that provides API endpoints for mlmodelscope. Docker Compose is configured to run the Go API by default.

#### Running unit tests

To run the unit tests, change to the `/api` directory and run:

```bash
go test ./...
```

Add the `-v` flag to see detailed output from the tests:

```bash
go test -v ./...
```

#### Debugging in a container

It is possible to debug the Go API endpoints while they run in a container
(this can be useful to test behavior when the API is running on a Docker
network alongside ML agents.) To enable debugging in the container, run
the API from the `docker/Dockerfile.api-debug` Dockerfile. This Dockerfile
creates a container that runs the API app with the [Delve](https://github.com/go-delve/delve) 
debugger attached. Delve listens on port 2345, which is exposed to the host
machine. The API itself will not begin running until a debugging client is
attached to Delve.

### Python API

The `/python_api` directory contains a Python application that provides API endpoints for mlmodelscope.

#### Setting up an environment

Python API requires Python 3.8 or later. We recommend using a virtual environment to manage dependencies such as `virtualenv` or `conda`.

To install the dependencies, run:

```bash
pip install -r python_api/requirements.txt
```

#### Editing the configuration

The Python API uses configuration environment variables to connect to the database and message queue. These variables are coded in the `python_api/db.py` and `python_api/mq.py` files. You can edit these files to change the configuration or set the environment variables in your shell.

#### Running the API

To run the Python API, change to the `/python_api` directory and run:

```bash
fastapi run api.py --reload
```

The default port is `8000` but if you want to change the port you can set with `--port` flag

```bash
fastapi run api.py --reload --port 8001
```

You may need to set the port for the API to connect to [`mlmodelscope`](https://github.com/c3sr/mlmodelscope) which is running on port configured as `REACT_APP_API_PORT` in the `mlmodelscope/.env` file.

## Traefik

[Traefik](https://doc.traefik.io/traefik/) is used as a reverse proxy for local
development to provide services at URLs such as http://api.local.mlmodelscope.org/.
If you are running a local copy of the
[MLModelScope React App](https://github.com/c3sr/mlmodelscope) on port 3000, Traefik
will proxy that at http://local.mlmodelscope.org/.

## Running an agent alongside the API

The `scripts/run-agent.sh` script will run an agent container for one of the
following ML frameworks:

    * pytorch
    * tensorflow
    * onnxruntime
    * jax
    * mxnet

For example, to run a PyTorch agent, run:

```bash
./scripts/run-agent.sh pytorch
```

The `docker/carml-config-examle.yml` file will be copied to `.carml_config.yml` and
that file will be mapped into the running container as a Docker volume. If you
need to modify the configuration in any way, you should edit the `.carml_config.yml`
file and **not** `docker/carml-config-example.yml`.

## Project Wiki

https://wiki.mlmodelscope.org/

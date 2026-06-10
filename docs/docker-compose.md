# Docker Compose / Swarm Configuration

This repository provides Compose files necessary to run the MLModelScope API and its dependencies in a local
Docker environment or in a Docker Swarm. Service configuration is separated across multiple Compose files
for use in different environments.

| File                        | Description                                                                                                                   |
|-----------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| docker-compose.yml          | The primary Compose file that defines the core services for the API                                                           |
| docker-compose.override.yml | This file is used in a development environment to provide additional services and configuration needed to run the API locally |
| docker-compose.swarm.yml    | This file is used in a Swarm environment to provide additional services and configuration needed to run the API in a Swarm    |

## Services

The following services are defined in the primary Compose file:

| Service   | Description                                               |
|-----------|-----------------------------------------------------------|
| api       | The MlModelScope API                                      |
| companion | Companion assists with file uploads to cloud storage (S3) |
| consul    | Service discovery used by RabbitMQ                        |
| mq        | RabbitMQ message queue                                    |
| trace     | Jaeger tracing service, required by ML agents             |

The Compose Override file defines the following additional services:

| Service | Description                                                                 |
|---------|-----------------------------------------------------------------------------|
| db      | PostgreSQL database for storage of model data and inference results         |
| traefik | Traefik reverse proxy, used to route requests to the API and other services |

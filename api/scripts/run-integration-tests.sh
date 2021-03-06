#!/usr/bin/env sh

cd `git rev-parse --show-toplevel`/api

source ./scripts/functions.sh

set_environment
start_postgres
start_rabbitmq
start_mock_agent

echo "\nRunning integration tests..."
go clean -testcache && go test -v -coverprofile integration.out --tags integration ./...

stop_postgres
stop_rabbitmq
stop_mock_agent

cd - 2>&1 >> /dev/null

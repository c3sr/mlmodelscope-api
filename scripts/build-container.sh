#!/usr/bin/env bash

cd `git rev-parse --show-toplevel`
source "scripts/functions.sh"

USAGE="Usage: ${0} <target> <version> (registry)

    target        (required) The service to build into a container, i.e. 'uploader':

    version       (required) The version number to tag the image with
                      Note: image will always be tagged as 'latest'

    registry      (optional) The Docker registry to tag images against
                      Defaults to 'mlmodelscope-api'"

TARGET="$1"
TARGET_DIR="./$TARGET"
VERSION="$2"
REGISTRY="$3"
: ${REGISTRY:="mlmodelscope-api"}
DOCKERFILE="./docker/Dockerfile.$1"

if [ -z $TARGET ]; then
    die_with_message "$USAGE"
fi

if [ ! -d "$TARGET" ]; then
    die_with_message "Target ${TARGET} does not exist"
fi

if [ -z $VERSION ]; then
    die_with_message "$USAGE"
fi

if [ ! -f "$DOCKERFILE" ]; then
    die_with_message "Dockerfile ${DOCKERFILE} does not exist"
fi

docker build -t "$REGISTRY-$TARGET:$VERSION" --file "$DOCKERFILE" "$TARGET_DIR"
docker tag "$REGISTRY-$TARGET:$VERSION" "$REGISTRY-$TARGET:latest"

cleanup_and_exit

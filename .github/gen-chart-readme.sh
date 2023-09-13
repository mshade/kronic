#!/usr/bin/env bash

docker run --rm -v "$PWD/chart:/helm-docs" jnorwood/helm-docs@sha256:e438eb9f879e4bb8389ce4acd0f7e9193e3d62e877a1a3cd5abd0393dbe55fe5

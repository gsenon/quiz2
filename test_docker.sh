#!/bin/bash
docker build --no-cache -t test-final -f Dockerfile.content . > /dev/null 2>&1
docker run --rm test-final

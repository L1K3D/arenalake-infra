# Shared Docker images

This directory contains the reusable workspace image and Spark worker image.
The workspace Dockerfile is built with the repository root as its context:

```bash
docker build -t arenalake-workspace:latest -f docker/Dockerfile.workspace .
```

The workspace image publication workflow watches
`docker/Dockerfile.workspace`.

The workspace build context uses
[`Dockerfile.workspace.dockerignore`](Dockerfile.workspace.dockerignore), a
Dockerfile-specific ignore file that keeps unnecessary repository files out of
the image build context.

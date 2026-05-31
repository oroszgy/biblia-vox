---
phase: 04-transcription-based-alignment
plan: 1
subsystem: alignment-infrastructure
tags:
  - docker
  - gpu
  - configuration
dependency_graph:
  requires:
    - INF-01
    - INF-03
    - INF-04
    - INF-05
  provides:
    - GPU Docker environment
    - Model Gauntlet settings
  affects:
    - Taskfile targets
tech_stack:
  added:
    - docker
    - nvidia-docker
    - pydantic-settings
    - huggingface_hub
  patterns:
    - Containerized ML inference
key_files:
  created:
    - docker/Dockerfile.align
    - docker-compose.yml
  modified:
    - bibliavox/config.py
    - Taskfile.yml
    - pyproject.toml
decisions:
  - "Use a separate docker container (align service) for heavy model dependencies (faster-whisper, vibevoice) with GPU passthrough."
  - "Configured Model Gauntlet in Pydantic settings with default faster-whisper and vibevoice model IDs."
  - "Taskfile script leverages huggingface_hub directly to ensure weights are pre-downloaded to data/models locally."
metrics:
  duration: 10m
  tasks_completed: 3
  files_changed: 5
  commits: 3
---

# Phase 04 Plan 1: GPU Docker Infrastructure and Model Gauntlet Settings Summary

Configured the baseline GPU infrastructure and model gauntlet settings for the alignment pipeline.

## Execution Details

1. Created `docker/Dockerfile.align` with a PyTorch CUDA base image and dependencies for `faster-whisper`, `rapidfuzz`, and `vibevoice`.
2. Created `docker-compose.yml` to set up the `align` service, bind mounting the `./data` directory and passing through the NVIDIA GPU using `deploy` configuration.
3. Added `ModelGauntletSettings` to `bibliavox/config.py` to allow execution configuration of multiple models (faster-whisper, vibevoice). 
4. Implemented `align:setup` in `Taskfile.yml` that uses `huggingface_hub` to pre-download model weights to `./data/models`, preventing runtime download blocks.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED
- `docker/Dockerfile.align` exists
- `docker-compose.yml` exists
- Commits exist: 26d3b9a, c34966c, eee6588

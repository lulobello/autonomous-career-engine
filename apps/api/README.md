# API application

This directory will contain the Python API entry point that composes domain packages, applies authentication and redaction policy, and exposes workflow operations. Domain rules belong in `packages/`, not in transport handlers.

The API framework and runtime will be selected with the first executable vertical slice. No production API exists in the foundation stage.

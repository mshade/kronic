# Project Guidelines for Kronic

This document outlines the essential commands and code style guidelines for contributing to the Kronic codebase.

## Environment Setup

*   **Activate Virtual Environment**: `source venv/bin/activate` (Run once per terminal session)

## Build, Lint, and Test Commands

*   **Install Dependencies**: `pip install -r requirements.txt -r requirements-dev.txt`
*   **Run All Tests**: `pytest`
*   **Run a Single Test**: `pytest tests/test_kron.py::test_get_human_readable_time_difference_past` (Replace with specific test file and function)
*   **Lint (Check Only)**: `black --check .`
*   **Lint (Fix Issues)**: `black .`
*   **Build Docker Image**: `docker build . -t kronic`

## Code Style Guidelines (Python)

*   **Formatting**: Adhere strictly to [Black](https://github.com/psf/black) formatting. Run `black .` to automatically format your code.
*   **Imports**: Imports should be grouped as follows: standard library, third-party libraries, and then local application modules. Each group should be sorted alphabetically.
    ```python
    import os
    import sys
    from datetime import datetime

    import pytest
    from flask import Flask

    import config
    from kron import get_cronjobs
    ```
*   **Naming Conventions**: Use `snake_case` for variables, functions, and module names. Class names should use `CamelCase`.
*   **Type Hinting**: Utilize type hints for function arguments and return values to improve code clarity and maintainability.
*   **Error Handling**: Implement explicit error handling using `try...except` blocks for operations that may fail (e.g., API calls, file I/O). Provide informative error messages.
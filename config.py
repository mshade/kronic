import os

## Configuration
# Comma separated list of namespaces to allow access to
ALLOW_NAMESPACES = os.environ.get("KRONIC_ALLOW_NAMESPACES", None)
# Boolean of whether this is a test environment
TEST = os.environ.get("KRONIC_TEST", False)

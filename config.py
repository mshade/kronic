import os

## Configuration
# Comma separated list of namespaces to allow access to
ALLOW_NAMESPACES = os.environ.get("KRONIC_ALLOW_NAMESPACES", None)

# Boolean of whether this is a test environment, disables kubeconfig setup
TEST = os.environ.get("KRONIC_TEST", False)

# Limit to local namespace. Supercedes `ALLOW_NAMESPACES`
NAMESPACE_ONLY = os.environ.get("KRONIC_NAMESPACE_ONLY", False)
KRONIC_NAMESPACE = os.environ.get("KRONIC_NAMESPACE", None)

# Set allowed namespaces to the installed namespace only
if NAMESPACE_ONLY:
    ALLOW_NAMESPACES = KRONIC_NAMESPACE

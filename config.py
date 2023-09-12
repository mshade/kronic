import logging
import os
import sys

log = logging.getLogger("app.config")

## Configuration
# Comma separated list of namespaces to allow access to
ALLOW_NAMESPACES = os.environ.get("KRONIC_ALLOW_NAMESPACES", None)

# Boolean of whether this is a test environment, disables kubeconfig setup
TEST = os.environ.get("KRONIC_TEST", False)

# Limit to local namespace. Supercedes `ALLOW_NAMESPACES`
NAMESPACE_ONLY = os.environ.get("KRONIC_NAMESPACE_ONLY", False)

# Set allowed namespaces to the installed namespace only
if NAMESPACE_ONLY:
    try:
        KRONIC_NAMESPACE = os.environ["KRONIC_NAMESPACE"]
    except KeyError as e:
        log.error(
            "ERROR: KRONIC_NAMESPACE variable not set and a NAMESPACE_ONLY mode was specified."
        )
        sys.exit(1)

    ALLOW_NAMESPACES = KRONIC_NAMESPACE

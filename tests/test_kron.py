import os
import sys
from kubernetes import client

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import kron
from objects import cronjobList


def test_itemFields():
    assert kron._itemFields(cronjobList) == [
        {"name": "first"},
        {"name": "second"},
        {"name": "third"},
        {"name": "fourth"},
        {"name": "fifth"},
    ]

def test_cleanObject():
    for job in cronjobList.items:
        assert job.metadata.name == kron._cleanObject(job)["metadata"]["name"]
        assert job.metadata.namespace == kron._cleanObject(job)["metadata"]["namespace"]

def test_hasLabel():
    cronjob = kron._cleanObject(cronjobList.items[0])
    assert kron._hasLabel(cronjob, "app", "test") == True


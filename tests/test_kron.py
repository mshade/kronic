import os
import sys
import pytest

from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import kron
from objects import cronjobList


# Define a fixture to create a timestamp in the past
@pytest.fixture
def past_timestamp():
    return (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

# Define a fixture to create a timestamp in the future
@pytest.fixture
def future_timestamp():
    return (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

def test_get_human_readable_time_difference_past(past_timestamp):
    result = kron._get_time_since(past_timestamp)
    assert "d" in result  # Check if the result contains 'd' for days

def test_get_human_readable_time_difference_future(future_timestamp):
    result = kron._get_time_since(future_timestamp)
    assert result == "In the future"  # Check if the result is "In the future"

def test_get_human_readable_time_difference_now():
    result = kron._get_time_since(datetime.now(timezone.utc).isoformat())
    assert result == "0s"  # Check if the result is "0s" for the current time

def test_get_human_readable_time_difference_invalid_format():
    with pytest.raises(ValueError):
        kron._get_time_since("invalid_timestamp")


def test_filter_object_fields():
    assert kron._filter_object_fields(cronjobList) == [
        {"name": "first"},
        {"name": "second"},
        {"name": "third"},
        {"name": "fourth"},
        {"name": "fifth"},
    ]

def test_clean_api_object():
    for job in cronjobList.items:
        assert job.metadata.name == kron._clean_api_object(job)["metadata"]["name"]
        assert job.metadata.namespace == kron._clean_api_object(job)["metadata"]["namespace"]
        assert "managedFields" not in kron._clean_api_object(job)["metadata"]

def test_has_label():
    cronjob = kron._clean_api_object(cronjobList.items[0])
    assert kron._has_label(cronjob, "app", "test") == True
    assert kron._has_label(cronjob, "app", "badlabel") == False


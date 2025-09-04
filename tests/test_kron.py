import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config

config.TEST = True

import kron
from objects import create_cronjob, create_cronjob_list, create_job


class TestTimeCalculations:
    @pytest.fixture
    def past_timestamp(self):
        return (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    @pytest.fixture
    def future_timestamp(self):
        return (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    @pytest.fixture
    def fixed_current_time(self):
        return datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_get_time_since_past(self, past_timestamp):
        result = kron._get_time_since(past_timestamp)
        assert "d" in result
        assert "h" in result
        assert "m" in result
        assert "s" in result

    def test_get_time_since_future(self, future_timestamp):
        result = kron._get_time_since(future_timestamp)
        assert result == "In the future"

    def test_get_time_since_now(self):
        now = datetime.now(timezone.utc)
        result = kron._get_time_since(now.isoformat(), now)
        assert result == "0s"

    def test_get_time_since_with_fixed_time(self, fixed_current_time):
        # Test with exactly 1 day difference
        past_time = (fixed_current_time - timedelta(days=1)).isoformat()
        result = kron._get_time_since(past_time, fixed_current_time)
        assert result == "1d 0h 0m 0s"

        # Test with exactly 2 hours difference
        past_time = (fixed_current_time - timedelta(hours=2)).isoformat()
        result = kron._get_time_since(past_time, fixed_current_time)
        assert result == "2h 0m 0s"

        # Test with exactly 30 minutes difference
        past_time = (fixed_current_time - timedelta(minutes=30)).isoformat()
        result = kron._get_time_since(past_time, fixed_current_time)
        assert result == "30m 0s"

        # Test with exactly 45 seconds difference
        past_time = (fixed_current_time - timedelta(seconds=45)).isoformat()
        result = kron._get_time_since(past_time, fixed_current_time)
        assert result == "45s"

    def test_get_time_since_invalid_format(self):
        with pytest.raises(ValueError):
            kron._get_time_since("invalid_timestamp")


class TestHelperFunctions:
    def test_filter_dict_fields(self):
        cron_dict_list = [
            {"metadata": {"name": "first", "namespace": "test", "uid": "123"}},
            {"metadata": {"name": "second", "namespace": "test", "uid": "456"}},
        ]

        # Test with default fields (name only)
        result = kron._filter_dict_fields(cron_dict_list)
        assert result == [
            {"name": "first"},
            {"name": "second"},
        ]

        # Test with multiple fields
        result = kron._filter_dict_fields(cron_dict_list, ["name", "namespace"])
        assert result == [
            {"name": "first", "namespace": "test"},
            {"name": "second", "namespace": "test"},
        ]

        # Test with all fields
        result = kron._filter_dict_fields(cron_dict_list, ["name", "namespace", "uid"])
        assert result == [
            {"name": "first", "namespace": "test", "uid": "123"},
            {"name": "second", "namespace": "test", "uid": "456"},
        ]

    def test_clean_api_object(self):
        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.sanitize_for_serialization.return_value = {
            "metadata": {
                "name": "test-job",
                "namespace": "test",
                "managedFields": {"some": "data"},
            }
        }

        # Create a mock API object
        mock_api_object = MagicMock()

        # Test the function
        result = kron._clean_api_object(mock_api_object, mock_api_client)

        # Verify the result
        assert "managedFields" not in result["metadata"]
        assert result["metadata"]["name"] == "test-job"
        assert result["metadata"]["namespace"] == "test"
        mock_api_client.sanitize_for_serialization.assert_called_once_with(
            mock_api_object
        )

    def test_has_label(self):
        # Test with matching label
        api_object = {
            "metadata": {"labels": {"app": "test", "environment": "production"}}
        }
        assert kron._has_label(api_object, "app", "test") is True
        assert kron._has_label(api_object, "environment", "production") is True

        # Test with non-matching label value
        assert kron._has_label(api_object, "app", "wrong") is False

        # Test with non-existent label key
        assert kron._has_label(api_object, "nonexistent", "value") is False

        # Test with no labels
        api_object_no_labels = {"metadata": {}}
        assert kron._has_label(api_object_no_labels, "app", "test") is False

    def test_pod_is_owned_by(self):
        # Test with matching owner reference
        api_dict = {
            "metadata": {
                "ownerReferences": [
                    {"name": "owner1", "kind": "Job"},
                    {"name": "owner2", "kind": "CronJob"},
                ]
            }
        }
        assert kron.pod_is_owned_by(api_dict, "owner1") is True
        assert kron.pod_is_owned_by(api_dict, "owner2") is True
        assert kron.pod_is_owned_by(api_dict, "nonexistent") is False

        # Test with no owner references
        api_dict_no_owners = {"metadata": {}}
        assert kron.pod_is_owned_by(api_dict_no_owners, "owner1") is False


class TestNamespaceFilter:
    def setup_method(self):
        # Save original ALLOW_NAMESPACES value
        self.original_allow_namespaces = config.ALLOW_NAMESPACES

    def teardown_method(self):
        # Restore original ALLOW_NAMESPACES value
        config.ALLOW_NAMESPACES = self.original_allow_namespaces

    def test_namespace_filter_denies_access(self):
        config.ALLOW_NAMESPACES = "qa,prod"

        @kron.namespace_filter
        def test_function(namespace, **kwargs):
            return True

        # Test with namespace not in allowed list
        result = test_function(namespace="test")
        assert result is False

    def test_namespace_filter_allows_access(self):
        config.ALLOW_NAMESPACES = "qa,test,prod"

        @kron.namespace_filter
        def test_function(namespace, **kwargs):
            return True

        # Test with namespace in allowed list
        result = test_function(namespace="test")
        assert result is True

    def test_namespace_filter_no_restrictions(self):
        config.ALLOW_NAMESPACES = None

        @kron.namespace_filter
        def test_function(namespace, **kwargs):
            return True

        # Test with no namespace restrictions
        result = test_function(namespace="any-namespace")
        assert result is True

    def test_namespace_filter_no_namespace_provided(self):
        config.ALLOW_NAMESPACES = "qa,test,prod"

        @kron.namespace_filter
        def test_function(namespace=None, **kwargs):
            return True

        # Test with no namespace provided
        result = test_function()
        assert result is True


@pytest.fixture
def mock_kubernetes_clients():
    # Create mock clients
    mock_v1 = MagicMock()
    mock_batch = MagicMock()
    mock_generic = MagicMock()

    # Configure generic client for serialization
    mock_generic.sanitize_for_serialization.side_effect = lambda obj: {
        "metadata": {
            "name": obj.metadata.name,
            "namespace": obj.metadata.namespace,
            "managedFields": {"some": "data"},
        },
        "spec": {"key": "value"},
        "status": {"startTime": datetime.now(timezone.utc).isoformat()},
    }

    return mock_v1, mock_batch, mock_generic


class TestKubernetesClientInitialization:
    @patch("os.path.exists")
    @patch("kron.kubeconfig.load_incluster_config")
    @patch("kron.kubeconfig.load_kube_config")
    def test_init_kubernetes_clients_in_cluster(
        self, mock_load_kube_config, mock_load_incluster_config, mock_path_exists
    ):
        # Setup
        mock_path_exists.return_value = True  # Simulate running in a Kubernetes cluster

        # Save original TEST value
        original_test_value = config.TEST
        config.TEST = False

        try:
            # Execute
            v1, batch, generic = kron.init_kubernetes_clients()

            # Verify
            mock_path_exists.assert_called_once_with(
                "/var/run/secrets/kubernetes.io/serviceaccount/token"
            )
            mock_load_incluster_config.assert_called_once()
            mock_load_kube_config.assert_not_called()

            assert v1 is not None
            assert batch is not None
            assert generic is not None
        finally:
            # Restore original TEST value
            config.TEST = original_test_value

    @patch("os.path.exists")
    @patch("kron.kubeconfig.load_incluster_config")
    @patch("kron.kubeconfig.load_kube_config")
    def test_init_kubernetes_clients_external(
        self, mock_load_kube_config, mock_load_incluster_config, mock_path_exists
    ):
        # Setup
        mock_path_exists.return_value = (
            False  # Simulate running outside a Kubernetes cluster
        )

        # Save original TEST value
        original_test_value = config.TEST
        config.TEST = False

        try:
            # Execute
            v1, batch, generic = kron.init_kubernetes_clients()

            # Verify
            mock_path_exists.assert_called_once_with(
                "/var/run/secrets/kubernetes.io/serviceaccount/token"
            )
            mock_load_incluster_config.assert_not_called()
            mock_load_kube_config.assert_called_once()

            assert v1 is not None
            assert batch is not None
            assert generic is not None
        finally:
            # Restore original TEST value
            config.TEST = original_test_value

    @patch("os.path.exists")
    @patch("kron.kubeconfig.load_incluster_config")
    @patch("kron.kubeconfig.load_kube_config")
    def test_init_kubernetes_clients_test_mode(
        self, mock_load_kube_config, mock_load_incluster_config, mock_path_exists
    ):
        # Setup
        # Save original TEST value
        original_test_value = config.TEST
        config.TEST = True

        try:
            # Execute
            v1, batch, generic = kron.init_kubernetes_clients()

            # Verify
            mock_path_exists.assert_not_called()
            mock_load_incluster_config.assert_not_called()
            mock_load_kube_config.assert_not_called()

            assert v1 is not None
            assert batch is not None
            assert generic is not None
        finally:
            # Restore original TEST value
            config.TEST = original_test_value


class TestCronjobFunctions:
    @patch("kron.pod_is_owned_by")
    @patch("kron._has_label")
    def test_get_cronjobs(
        self, mock_has_label, mock_pod_is_owned_by, mock_kubernetes_clients
    ):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Create mock cronjob list
        mock_cronjob_list = create_cronjob_list()
        mock_batch.list_namespaced_cron_job.return_value = mock_cronjob_list

        # Test get_cronjobs with namespace
        result = kron.get_cronjobs(
            namespace="test", batch_client=mock_batch, api_client=mock_generic
        )

        # Verify the function called the correct API
        mock_batch.list_namespaced_cron_job.assert_called_once_with(namespace="test")

        # Verify the result
        assert len(result) == 5
        assert all(isinstance(item, dict) for item in result)
        assert all("name" in item for item in result)
        assert all("namespace" in item for item in result)

        # Verify sorting
        names = [item["name"] for item in result]
        assert names == sorted(names)

    def test_get_cronjob(self, mock_kubernetes_clients):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Create mock cronjob
        mock_cronjob = create_cronjob("test-job")
        mock_batch.read_namespaced_cron_job.return_value = mock_cronjob

        # Test get_cronjob
        result = kron.get_cronjob(
            namespace="test",
            cronjob_name="test-job",
            batch_client=mock_batch,
            api_client=mock_generic,
        )

        # Verify the function called the correct API
        mock_batch.read_namespaced_cron_job.assert_called_once_with("test-job", "test")

        # Verify the result
        assert isinstance(result, dict)
        assert result["metadata"]["name"] == "test-job"
        assert result["metadata"]["namespace"] == "test"

        # Test get_cronjob with ApiException
        mock_batch.read_namespaced_cron_job.side_effect = kron.ApiException(status=404)
        result = kron.get_cronjob(
            namespace="test",
            cronjob_name="nonexistent",
            batch_client=mock_batch,
            api_client=mock_generic,
        )
        assert result is False

    @patch("kron.pod_is_owned_by")
    @patch("kron._has_label")
    def test_get_jobs(
        self, mock_has_label, mock_pod_is_owned_by, mock_kubernetes_clients
    ):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Configure mocks
        mock_job_list = MagicMock()
        mock_job_list.items = [create_job("job1"), create_job("job2")]
        mock_batch.list_namespaced_job.return_value = mock_job_list

        # Configure pod_is_owned_by to return True for the first job
        mock_pod_is_owned_by.side_effect = (
            lambda job, name: job["metadata"]["name"] == "job1"
        )

        # Configure _has_label to return True for the second job
        mock_has_label.side_effect = lambda job, k, v: job["metadata"]["name"] == "job2"

        # Test get_jobs
        result = kron.get_jobs(
            namespace="test",
            cronjob_name="parent-cronjob",
            batch_client=mock_batch,
            api_client=mock_generic,
        )

        # Verify the function called the correct API
        mock_batch.list_namespaced_job.assert_called_once_with(namespace="test")

        # Verify the result
        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)
        assert all("status" in item for item in result)
        assert all("age" in item["status"] for item in result)

    @patch("kron.pod_is_owned_by")
    def test_get_pods(self, mock_pod_is_owned_by, mock_kubernetes_clients):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Create mock pod list
        mock_pod1 = MagicMock()
        mock_pod1.metadata.name = "pod1"
        mock_pod1.metadata.namespace = "test"

        mock_pod2 = MagicMock()
        mock_pod2.metadata.name = "pod2"
        mock_pod2.metadata.namespace = "test"

        mock_pod_list = MagicMock()
        mock_pod_list.items = [mock_pod1, mock_pod2]
        mock_v1.list_namespaced_pod.return_value = mock_pod_list

        # Configure pod_is_owned_by to return True for the first pod
        mock_pod_is_owned_by.side_effect = (
            lambda pod, name: pod["metadata"]["name"] == "pod1"
        )

        # Test get_pods with job_name
        result = kron.get_pods(
            namespace="test",
            job_name="job1",
            v1_client=mock_v1,
            api_client=mock_generic,
        )

        # Verify the function called the correct API
        mock_v1.list_namespaced_pod.assert_called_once_with(namespace="test")

        # Verify the result
        assert len(result) == 1
        assert result[0]["metadata"]["name"] == "pod1"
        assert "age" in result[0]["status"]

    @patch("kron.get_jobs")
    @patch("kron.get_pods")
    @patch("kron.pod_is_owned_by")
    def test_get_jobs_and_pods(
        self,
        mock_pod_is_owned_by,
        mock_get_pods,
        mock_get_jobs,
        mock_kubernetes_clients,
    ):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Configure get_jobs mock
        mock_get_jobs.return_value = [
            {"metadata": {"name": "job1"}, "status": {}},
            {"metadata": {"name": "job2"}, "status": {}},
        ]

        # Configure get_pods mock
        mock_get_pods.return_value = [
            {"metadata": {"name": "pod1"}},
            {"metadata": {"name": "pod2"}},
        ]

        # Configure pod_is_owned_by to match pods to jobs
        mock_pod_is_owned_by.side_effect = lambda pod, name: (
            (pod["metadata"]["name"] == "pod1" and name == "job1")
            or (pod["metadata"]["name"] == "pod2" and name == "job2")
        )

        # Test get_jobs_and_pods
        result = kron.get_jobs_and_pods(
            namespace="test",
            cronjob_name="parent-cronjob",
            batch_client=mock_batch,
            v1_client=mock_v1,
            api_client=mock_generic,
        )

        # Verify the result
        assert len(result) == 2
        assert "pods" in result[0]
        assert "pods" in result[1]
        assert len(result[0]["pods"]) == 1
        assert len(result[1]["pods"]) == 1
        assert result[0]["pods"][0]["metadata"]["name"] == "pod1"
        assert result[1]["pods"][0]["metadata"]["name"] == "pod2"

    def test_get_pod_logs(self, mock_kubernetes_clients):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Configure mock
        mock_v1.read_namespaced_pod_log.return_value = "Log line 1\nLog line 2"

        # Test get_pod_logs
        result = kron.get_pod_logs(namespace="test", pod_name="pod1", v1_client=mock_v1)

        # Verify the function called the correct API
        mock_v1.read_namespaced_pod_log.assert_called_once_with(
            "pod1", "test", tail_lines=1000, timestamps=True
        )

        # Verify the result
        assert result == "Log line 1\nLog line 2"

        # Test with ApiException
        mock_v1.read_namespaced_pod_log.side_effect = kron.ApiException(
            status=404, reason="Not Found"
        )
        result = kron.get_pod_logs(
            namespace="test", pod_name="nonexistent", v1_client=mock_v1
        )
        assert "Error fetching logs" in result

    def test_trigger_cronjob(self, mock_kubernetes_clients):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Create mock cronjob
        mock_cronjob = create_cronjob("test-cronjob")
        mock_batch.read_namespaced_cron_job.return_value = mock_cronjob

        # Configure create_namespaced_job
        mock_job = create_job("test-job-manual")
        mock_batch.create_namespaced_job.return_value = mock_job

        # Fixed time for testing
        fixed_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Test trigger_cronjob
        result = kron.trigger_cronjob(
            namespace="test",
            cronjob_name="test-cronjob",
            batch_client=mock_batch,
            api_client=mock_generic,
            current_time=fixed_time,
        )

        # Verify the function called the correct APIs
        mock_batch.read_namespaced_cron_job.assert_called_once_with(
            name="test-cronjob", namespace="test"
        )
        mock_batch.create_namespaced_job.assert_called_once()

        # Verify job template was modified correctly
        job_template = mock_batch.create_namespaced_job.call_args[1]["body"]
        assert "test-cronjob-manual-" in job_template.metadata.name
        assert (
            job_template.metadata.labels["kronic.mshade.org/manually-triggered"]
            == "true"
        )
        assert (
            job_template.metadata.labels["kronic.mshade.org/created-from"]
            == "test-cronjob"
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "spec" in result

    def test_toggle_cronjob_suspend(self, mock_kubernetes_clients):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Create mock cronjob status
        mock_status = MagicMock()
        mock_status.spec.suspend = False
        mock_batch.read_namespaced_cron_job_status.return_value = mock_status

        # Create mock patched cronjob
        mock_cronjob = create_cronjob("test-cronjob")
        mock_batch.patch_namespaced_cron_job.return_value = mock_cronjob

        # Test toggle_cronjob_suspend
        result = kron.toggle_cronjob_suspend(
            namespace="test",
            cronjob_name="test-cronjob",
            batch_client=mock_batch,
            api_client=mock_generic,
        )

        # Verify the function called the correct APIs
        mock_batch.read_namespaced_cron_job_status.assert_called_once_with(
            name="test-cronjob", namespace="test"
        )

        # Verify patch body has inverted suspend value
        patch_body = mock_batch.patch_namespaced_cron_job.call_args[1]["body"]
        assert patch_body["spec"]["suspend"] is True

        # Verify the result
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "spec" in result

    def test_update_cronjob(self, mock_kubernetes_clients):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Create mock spec
        spec = {
            "metadata": {"name": "test-cronjob", "namespace": "test"},
            "spec": {"schedule": "*/5 * * * *"},
        }

        # Configure get_cronjob to return True (existing cronjob)
        with patch("kron.get_cronjob", return_value=True):
            # Create mock patched cronjob
            mock_cronjob = create_cronjob("test-cronjob")
            mock_batch.patch_namespaced_cron_job.return_value = mock_cronjob

            # Test update_cronjob for existing cronjob
            result = kron.update_cronjob(
                namespace="test",
                spec=spec,
                batch_client=mock_batch,
                api_client=mock_generic,
            )

            # Verify the function called the correct API
            mock_batch.patch_namespaced_cron_job.assert_called_once_with(
                "test-cronjob", "test", spec
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "metadata" in result
            assert "spec" in result

        # Configure get_cronjob to return False (new cronjob)
        with patch("kron.get_cronjob", return_value=False):
            # Reset mocks
            mock_batch.patch_namespaced_cron_job.reset_mock()

            # Create mock created cronjob
            mock_cronjob = create_cronjob("test-cronjob")
            mock_batch.create_namespaced_cron_job.return_value = mock_cronjob

            # Test update_cronjob for new cronjob
            result = kron.update_cronjob(
                namespace="test",
                spec=spec,
                batch_client=mock_batch,
                api_client=mock_generic,
            )

            # Verify the function called the correct API
            mock_batch.create_namespaced_cron_job.assert_called_once_with("test", spec)

            # Verify the result
            assert isinstance(result, dict)
            assert "metadata" in result
            assert "spec" in result

    def test_delete_cronjob(self, mock_kubernetes_clients):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Create mock deleted cronjob
        mock_cronjob = create_cronjob("test-cronjob")
        mock_batch.delete_namespaced_cron_job.return_value = mock_cronjob

        # Test delete_cronjob
        result = kron.delete_cronjob(
            namespace="test",
            cronjob_name="test-cronjob",
            batch_client=mock_batch,
            api_client=mock_generic,
        )

        # Verify the function called the correct API
        mock_batch.delete_namespaced_cron_job.assert_called_once_with(
            "test-cronjob", "test"
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "spec" in result

    def test_delete_job(self, mock_kubernetes_clients):
        mock_v1, mock_batch, mock_generic = mock_kubernetes_clients

        # Create mock deleted job
        mock_job = create_job("test-job")
        mock_batch.delete_namespaced_job.return_value = mock_job

        # Test delete_job
        result = kron.delete_job(
            namespace="test",
            job_name="test-job",
            batch_client=mock_batch,
            api_client=mock_generic,
        )

        # Verify the function called the correct API
        mock_batch.delete_namespaced_job.assert_called_once_with("test-job", "test")

        # Verify the result
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "spec" in result

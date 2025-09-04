import logging
import os

from kubernetes import client
from kubernetes import config as kubeconfig
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone
from typing import List, Optional, Union, Dict, Any

import config

log = logging.getLogger("app.kron")

# Initialize clients as None to be set by init_kubernetes_clients
v1 = None
batch = None
generic = None


def init_kubernetes_clients():
    """Initialize Kubernetes API clients

    Detects whether running in-cluster or external and loads appropriate config.

    Returns:
        tuple: (v1_client, batch_client, generic_client)
    """
    global v1, batch, generic

    if not config.TEST:
        # Check if running in a Kubernetes cluster by looking for the service account token file
        if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
            log.info("Running in-cluster, loading incluster config")
            kubeconfig.load_incluster_config()
        else:
            log.info("Running outside cluster, loading kubeconfig")
            print(f"Loading kubeconfig from local .kube/config")
            kubeconfig.load_kube_config()

    # Create the Api clients
    v1 = client.CoreV1Api()
    batch = client.BatchV1Api()
    generic = client.ApiClient()

    return v1, batch, generic


# Initialize clients if not in test mode
if not config.TEST:
    init_kubernetes_clients()


def namespace_filter(func):
    """Decorator that short-circuits and returns False if the wrapped function attempts to access an unlisted namespace

    Args:
        func (function): The function to wrap. Must have `namespace` as an arg to itself
    """

    def wrapper(namespace: str = None, *args, **kwargs):
        if config.ALLOW_NAMESPACES and namespace:
            if namespace in config.ALLOW_NAMESPACES.split(","):
                return func(namespace, *args, **kwargs)
        else:
            return func(namespace, *args, **kwargs)

        return False

    return wrapper


def _filter_dict_fields(
    items: List[Dict[str, Any]], fields: List[str] | None = None
) -> List[Dict[str, Any]]:
    """
    Filter a given list of API object down to only the metadata fields listed.

    Args:
        response (Obj): A kubernetes client API object or object list.
        filds (List of str): The desired fields to retain from the object

    Returns:
        dict: The object is converted to a dict and retains only the fields
            provided.

    """
    if fields is None:
        fields = ["name"]
    return [
        {field: item.get("metadata", {}).get(field) for field in fields}
        for item in items
    ]


def _clean_api_object(api_object: object, api_client=None) -> Dict:
    """Convert API object to JSON and strip managedFields

    Args:
        api_object: Kubernetes API object to clean
        api_client: Optional ApiClient for testing. Defaults to global generic client.

    Returns:
        dict: Cleaned API object as dictionary
    """
    if api_client is None:
        api_client = generic

    api_dict = api_client.sanitize_for_serialization(api_object)
    api_dict["metadata"].pop("managedFields", None)
    return api_dict


def _get_time_since(datestring: str, current_time: Optional[datetime] = None) -> str:
    """
    Calculate the time difference between the input datestring and the current time
    and return a human-readable string.

    Args:
        datestring (str): A string representing a timestamp in ISO format.
        current_time (datetime, optional): Current time for comparison. Defaults to datetime.now(timezone.utc).

    Returns:
        str: A human-readable time difference string.
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    input_time = datetime.fromisoformat(datestring)

    time_difference = current_time - input_time

    if time_difference.total_seconds() < 0:
        return "In the future"

    days = time_difference.days
    hours, remainder = divmod(time_difference.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def _has_label(api_object: object, k: str, v: str) -> bool:
    """
    Return True if a label is present with the specified key and value.

    Args:
        api_object (dict): The API object with metadata.
        k (str): The label key to check.
        v (str): The label value to check.

    Returns:
        bool: True if the label is present with the specified key and value, otherwise False.
    """
    metadata = api_object.get("metadata", {})
    labels = metadata.get("labels", {})
    return labels.get(k) == v


def pod_is_owned_by(api_dict: dict, owner_name: str) -> bool:
    """Return whether a job or pod contains an ownerReference to the given cronjob or job name

    Args:
        object (dict): A dict representation of a job or pod
        owner_name (str): The name of a cronjob or job which may have created the given job or pod

    Returns:
        bool: True if an ownerReference contains the given owner_name
    """
    owner_references = api_dict["metadata"].get("ownerReferences", [])
    return any(owner_ref["name"] == owner_name for owner_ref in owner_references)


@namespace_filter
def get_cronjobs(
    namespace: str = None, batch_client=None, api_client=None
) -> List[dict]:
    """Get names of cronjobs in a given namespace. If namespace is not provided, return CronJobs
        from all namespaces.

    Args:
        namespace (str, optional): namespace to examine. Defaults to None (all namespaces).
        batch_client: Optional BatchV1Api client for testing. Defaults to global batch client.
        api_client: Optional ApiClient for testing.

    Returns:
        List of dict: A list of dicts containing the name and namespace of each cronjob.
    """
    if batch_client is None:
        batch_client = batch

    try:
        cronjobs = []
        if not namespace:
            if not config.ALLOW_NAMESPACES:
                cronjobs = [
                    _clean_api_object(item, api_client)
                    for item in batch_client.list_cron_job_for_all_namespaces().items
                ]
            else:
                cronjobs = []
                for allowed in config.ALLOW_NAMESPACES.split(","):
                    cronjobs.extend(
                        [
                            _clean_api_object(item, api_client)
                            for item in batch_client.list_namespaced_cron_job(
                                namespace=allowed
                            ).items
                        ]
                    )
        else:
            cronjobs = [
                _clean_api_object(item, api_client)
                for item in batch_client.list_namespaced_cron_job(
                    namespace=namespace
                ).items
            ]

        fields = ["name", "namespace"]
        sorted_cronjobs = sorted(
            _filter_dict_fields(cronjobs, fields), key=lambda x: x["name"]
        )
        return sorted_cronjobs

    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response


@namespace_filter
def get_cronjob(
    namespace: str, cronjob_name: str, batch_client=None, api_client=None
) -> Union[Dict, bool]:
    """Get the details of a given CronJob as a dict

    Args:
        namespace (str): The namespace
        cronjob_name (str): The name of an existing CronJob
        batch_client: Optional BatchV1Api client for testing
        api_client: Optional ApiClient for testing

    Returns:
        dict: A dict of the CronJob API object or False if not found
    """
    if batch_client is None:
        batch_client = batch

    try:
        cronjob = batch_client.read_namespaced_cron_job(cronjob_name, namespace)
        return _clean_api_object(cronjob, api_client)
    except ApiException:
        return False


@namespace_filter
def get_jobs(
    namespace: str,
    cronjob_name: str,
    batch_client=None,
    api_client=None,
    current_time=None,
) -> List[dict]:
    """Return jobs belonging to a given CronJob name

    Args:
        namespace (str): The namespace
        cronjob_name (str): The CronJob which owns jobs to return
        batch_client: Optional BatchV1Api client for testing
        api_client: Optional ApiClient for testing
        current_time: Optional current time for testing

    Returns:
        List of dicts: A list of dicts of each job created by the given CronJob name
    """
    if batch_client is None:
        batch_client = batch

    try:
        jobs = batch_client.list_namespaced_job(namespace=namespace)
        cleaned_jobs = [_clean_api_object(job, api_client) for job in jobs.items]

        filtered_jobs = [
            job
            for job in cleaned_jobs
            if pod_is_owned_by(job, cronjob_name)
            or _has_label(job, "kronic.mshade.org/created-from", cronjob_name)
        ]

        for job in filtered_jobs:
            job["status"]["age"] = _get_time_since(
                job["status"]["startTime"], current_time
            )

        return filtered_jobs

    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response


@namespace_filter
def get_pods(
    namespace: str,
    job_name: str = None,
    v1_client=None,
    api_client=None,
    current_time=None,
) -> List[dict]:
    """Return pods related to jobs in a namespace

    Args:
        namespace (str): The namespace from which to fetch pods
        job_name (str, optional): Fetch pods owned by jobs. Defaults to None.
        v1_client: Optional CoreV1Api client for testing
        api_client: Optional ApiClient for testing
        current_time: Optional current time for testing

    Returns:
        List of dicts: A list of pod dicts
    """
    if v1_client is None:
        v1_client = v1

    try:
        all_pods = v1_client.list_namespaced_pod(namespace=namespace)
        cleaned_pods = [_clean_api_object(pod, api_client) for pod in all_pods.items]
        filtered_pods = [
            pod
            for pod in cleaned_pods
            if pod_is_owned_by(pod, job_name) or (not job_name)
        ]

        for pod in filtered_pods:
            pod["status"]["age"] = _get_time_since(
                pod["status"]["startTime"], current_time
            )

        return filtered_pods

    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response


@namespace_filter
def get_jobs_and_pods(
    namespace: str,
    cronjob_name: str,
    batch_client=None,
    v1_client=None,
    api_client=None,
    current_time=None,
) -> List[dict]:
    """Get jobs and their pods under a `pods` element for display purposes

    Args:
        namespace (str): The namespace
        cronjob_name (str): The CronJob name to filter jobs and pods by
        batch_client: Optional BatchV1Api client for testing
        v1_client: Optional CoreV1Api client for testing
        api_client: Optional ApiClient for testing
        current_time: Optional current time for testing

    Returns:
        List of dicts: A list of job dicts, each with a jobs element containing a list of pods the job created
    """
    jobs = get_jobs(namespace, cronjob_name, batch_client, api_client, current_time)
    all_pods = get_pods(namespace, None, v1_client, api_client, current_time)
    for job in jobs:
        job["pods"] = [
            pod for pod in all_pods if pod_is_owned_by(pod, job["metadata"]["name"])
        ]

    return jobs


@namespace_filter
def get_pod_logs(namespace: str, pod_name: str, v1_client=None) -> str:
    """Return plain text logs for <pod_name> in <namespace>

    Args:
        namespace (str): The namespace
        pod_name (str): The pod name
        v1_client: Optional CoreV1Api client for testing

    Returns:
        str: Pod logs or error message
    """
    if v1_client is None:
        v1_client = v1

    try:
        logs = v1_client.read_namespaced_pod_log(
            pod_name, namespace, tail_lines=1000, timestamps=True
        )
        return logs

    except ApiException as e:
        if e.status == 404:
            return f"Kronic> Error fetching logs: {e.reason}"


@namespace_filter
def trigger_cronjob(
    namespace: str,
    cronjob_name: str,
    batch_client=None,
    api_client=None,
    current_time=None,
) -> dict:
    """Trigger a CronJob manually

    Args:
        namespace (str): The namespace
        cronjob_name (str): The CronJob name
        batch_client: Optional BatchV1Api client for testing
        api_client: Optional ApiClient for testing
        current_time: Optional current time for testing

    Returns:
        dict: Created job or error response
    """
    if batch_client is None:
        batch_client = batch

    if current_time is None:
        current_time = datetime.now(timezone.utc)

    try:
        # Retrieve the CronJob template
        cronjob = batch_client.read_namespaced_cron_job(
            name=cronjob_name, namespace=namespace
        )
        job_template = cronjob.spec.job_template

        # Create a unique name indicating a manual invocation
        date_stamp = current_time.strftime("%Y%m%d%H%M%S-%f")
        job_template.metadata.name = (
            f"{cronjob.metadata.name[:16]}-manual-{date_stamp}"[:63]
        )

        # Set labels to identify jobs created by kronic
        job_template.metadata.labels = {
            "kronic.mshade.org/manually-triggered": "true",
            "kronic.mshade.org/created-from": cronjob_name,
        }

        trigger_job = batch_client.create_namespaced_job(
            body=job_template, namespace=namespace
        )
        return _clean_api_object(trigger_job, api_client)

    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response


@namespace_filter
def toggle_cronjob_suspend(
    namespace: str, cronjob_name: str, batch_client=None, api_client=None
) -> dict:
    """Toggle a CronJob's suspend flag on or off

    Args:
        namespace (str): The namespace
        cronjob_name (str): The cronjob name
        batch_client: Optional BatchV1Api client for testing
        api_client: Optional ApiClient for testing

    Returns:
        dict: The full cronjob object is returned as a dict
    """
    if batch_client is None:
        batch_client = batch

    try:
        suspended_status = batch_client.read_namespaced_cron_job_status(
            name=cronjob_name, namespace=namespace
        )
        patch_body = {"spec": {"suspend": not suspended_status.spec.suspend}}
        cronjob = batch_client.patch_namespaced_cron_job(
            name=cronjob_name, namespace=namespace, body=patch_body
        )
        return _clean_api_object(cronjob, api_client)

    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response


@namespace_filter
def update_cronjob(
    namespace: str, spec: dict, batch_client=None, api_client=None
) -> dict:
    """Update/edit a CronJob configuration via patch

    Args:
        namespace (str): The namespace
        spec (dict): A cronjob spec as a dict object
        batch_client: Optional BatchV1Api client for testing
        api_client: Optional ApiClient for testing

    Returns:
        dict: Returns the updated cronjob spec as a dict, or an error response
    """
    if batch_client is None:
        batch_client = batch

    try:
        name = spec["metadata"]["name"]
        if get_cronjob(namespace, name, batch_client, api_client):
            cronjob = batch_client.patch_namespaced_cron_job(name, namespace, spec)
        else:
            cronjob = batch_client.create_namespaced_cron_job(namespace, spec)
        return _clean_api_object(cronjob, api_client)

    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response


@namespace_filter
def delete_cronjob(
    namespace: str, cronjob_name: str, batch_client=None, api_client=None
) -> dict:
    """Delete a CronJob

    Args:
        namespace (str): The namespace
        cronjob_name (str): The name of the CronJob to delete
        batch_client: Optional BatchV1Api client for testing
        api_client: Optional ApiClient for testing

    Returns:
        dict: Returns a dict of the deleted CronJob, or an error status
    """
    if batch_client is None:
        batch_client = batch

    try:
        deleted = batch_client.delete_namespaced_cron_job(cronjob_name, namespace)
        return _clean_api_object(deleted, api_client)

    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response


@namespace_filter
def delete_job(
    namespace: str, job_name: str, batch_client=None, api_client=None
) -> dict:
    """Delete a Job

    Args:
        namespace (str): The namespace
        job_name (str): The name of the Job to delete
        batch_client: Optional BatchV1Api client for testing
        api_client: Optional ApiClient for testing

    Returns:
        dict: Returns a dict of the deleted Job, or an error status
    """
    if batch_client is None:
        batch_client = batch

    try:
        deleted = batch_client.delete_namespaced_job(job_name, namespace)
        return _clean_api_object(deleted, api_client)

    except ApiException as e:
        log.error(e)
        response = {
            "error": 500,
            "exception": {
                "status": e.status,
                "reason": e.reason,
                "message": e.body["message"],
            },
        }
        return response

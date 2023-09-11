import logging
import os

from kubernetes import client, config
from kubernetes.config import ConfigException
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone
from typing import List

log = logging.getLogger("app.kron")

if not os.environ.get("KRONIC_TEST", False):
    try:
        # Load configuration inside the Pod
        config.load_incluster_config()
    except ConfigException:
        # Load configuration from KUBECONFIG
        config.load_kube_config()

# Create the Api clients
v1 = client.CoreV1Api()
batch = client.BatchV1Api()
generic = client.ApiClient()


def _filter_object_fields(response: object, fields: List[str] = ["name"]) -> List[object]:
    """
    Filter a given API object down to only the metadata fields listed.

    Args:
        response (Obj): A kubernetes client API object or object list.
        filds (List of str): The desired fields to retain from the object

    Returns:
        dict: The object is converted to a dict and retains only the fields
            provided.

    """
    return [
        {field: getattr(item.metadata, field) for field in fields}
        for item in response.items
    ]


def _clean_api_object(api_object: object) -> dict:
    """Convert API object to JSON and strip managedFields"""
    api_dict = generic.sanitize_for_serialization(api_object)
    api_dict["metadata"].pop("managedFields", None)
    return api_dict


def _get_time_since(datestring: str) -> str:
    """
    Calculate the time difference between the input datestring and the current time
    and return a human-readable string.

    Args:
        datestring (str): A string representing a timestamp in ISO format.

    Returns:
        str: A human-readable time difference string.
    """
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


def _is_owned_by(object: object, owner_name: str) -> bool:
    """Return whether a job or pod contains an ownerReference to the given cronjob or job name

    Args:
        object (dict): A dict representation of a job or pod
        owner_name (str): The name of a cronjob or job which may have created the given job or pod

    Returns:
        bool: True if an ownerReference contains the given owner_name
    """
    owner_refernces = object["metadata"].get("ownerReferences", [])
    return any(owner_ref["name"] == owner_name for owner_ref in owner_refernces)


def get_cronjobs(namespace: str = "") -> List[dict]:
    """Get names of cronjobs in a given namespace. If namespace is not provided, return CronJobs
        from all namespaces.

    Args:
        namespace (str, optional): namespace to examine. Defaults to "" (all namespaces).

    Returns:
        List of dict: A list of dicts containing the name and namespace of each cronjob.
    """
    try:
        if namespace == "":
            cronjobs = batch.list_cron_job_for_all_namespaces()
        else:
            cronjobs = batch.list_namespaced_cron_job(namespace=namespace)

        fields = ["name", "namespace"]
        sorted_cronjobs = sorted(
            _filter_object_fields(cronjobs, fields), key=lambda x: x["name"]
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


def get_cronjob(namespace: str, cronjob_name: str) -> dict:
    """Get the details of a given CronJob as a dict

    Args:
        namespace (str): The namespace
        cronjob_name (str): The name of an existing CronJob

    Returns:
        dict: A dict of the CronJob API object
    """
    try:
        cronjob = batch.read_namespaced_cron_job(cronjob_name, namespace)
        return _clean_api_object(cronjob)
    except ApiException:
        return False


def get_jobs(namespace: str, cronjob_name: str) -> List[dict]:
    """Return jobs belonging to a given CronJob name

    Args:
        namespace (str): The namespace
        cronjob_name (str): The CronJob which owns jobs to return

    Returns:
        List of dicts: A list of dicts of each job created by the given CronJob name
    """
    try:
        jobs = batch.list_namespaced_job(namespace=namespace)
        cleaned_jobs = [_clean_api_object(job) for job in jobs.items]

        filtered_jobs = [
            job
            for job in cleaned_jobs
            if _is_owned_by(job, cronjob_name)
            or _has_label(job, "kron.mshade.org/created-from", cronjob_name)
        ]

        for job in filtered_jobs:
            job["status"]["age"] = _get_time_since(job["status"]["startTime"])

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


def get_pods(namespace: str, job_name: str = None) -> List[dict]:
    """Return pods related to jobs in a namespace

    Args:
        namespace (str): The namespace from which to fetch pods
        job_name (str, optional): Fetch pods owned by jobs. Defaults to None.

    Returns:
        List of dicts: A list of pod dicts
    """
    try:
        all_pods = v1.list_namespaced_pod(namespace=namespace)
        cleaned_pods = [_clean_api_object(pod) for pod in all_pods.items]
        filtered_pods = [
            pod for pod in cleaned_pods if _is_owned_by(pod, job_name) or (not job_name)
        ]

        for pod in filtered_pods:
            pod["status"]["age"] = _get_time_since(pod["status"]["startTime"])

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


def get_jobs_and_pods(namespace: str, cronjob_name:str ) -> List[dict]:
    """Get jobs and their pods under a `pods` element for display purposes

    Args:
        namespace (str): The namespace
        cronjob_name (str): The CronJob name to filter jobs and pods by

    Returns:
        List of dicts: A list of job dicts, each with a jobs element containing a list of pods the job created
    """
    jobs = get_jobs(namespace, cronjob_name)
    for job in jobs:
        job["pods"] = get_pods(namespace, job["metadata"]["name"])

    return jobs


def get_pod_logs(namespace: str, pod_name: str) -> str:
    """Return plain text logs for <pod_name> in <namespace>"""
    try:
        logs = v1.read_namespaced_pod_log(
            pod_name, namespace, tail_lines=1000, timestamps=True
        )
        return logs

    except ApiException as e:
        if e.status == 404:
            return f"Kronic> Error fetching logs: {e.reason}"


def trigger_cronjob(namespace: str, cronjob_name: str) -> dict:
    try:
        # Retrieve the CronJob template
        cronjob = batch.read_namespaced_cron_job(name=cronjob_name, namespace=namespace)
        job_template = cronjob.spec.job_template

        # Create a unique name indicating a manual invocation
        date_stamp = datetime.now().strftime("%Y%m%d%H%M%S-%f")
        job_template.metadata.name = (
            f"{job_template.metadata.name[:16]}-manual-{date_stamp}"[:63]
        )

        # Set labels to identify jobs created by kronic
        job_template.metadata.labels = {
            "kronic.mshade.org/manually-triggered": "true",
            "kronic.mshade.org/created-from": cronjob_name,
        }

        trigger_job = batch.create_namespaced_job(
            body=job_template, namespace=namespace
        )
        return _clean_api_object(trigger_job)

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


def toggle_cronjob_suspend(namespace: str, cronjob_name: str) -> dict:
    """Toggle a CronJob's suspend flag on or off

    Args:
        namespace (str): The namespace
        cronjob_name (str): The cronjob name

    Returns:
        dict: The full cronjob object is returned as a dict
    """
    try:
        suspended_status = batch.read_namespaced_cron_job_status(
            name=cronjob_name, namespace=namespace
        )
        patch_body = {"spec": {"suspend": not suspended_status.spec.suspend}}
        cronjob = batch.patch_namespaced_cron_job(
            name=cronjob_name, namespace=namespace, body=patch_body
        )
        return _clean_api_object(cronjob)

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


def update_cronjob(namespace: str, spec: str) -> dict:
    """Update/edit a CronJob configuration via patch

    Args:
        namespace (str): The namespace
        spec (dict): A cronjob spec as a dict object

    Returns:
        dict: Returns the updated cronjob spec as a dict, or an error response
    """
    try:
        name = spec["metadata"]["name"]
        if get_cronjob(namespace, name):
            cronjob = batch.patch_namespaced_cron_job(name, namespace, spec)
        else:
            cronjob = batch.create_namespaced_cron_job(namespace, spec)
        return _clean_api_object(cronjob)

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


def delete_cronjob(namespace: str, cronjob_name: str) -> dict:
    """Delete a CronJob

    Args:
        namespace (str): The namespace
        cronjob_name (str): The name of the CronJob to delete

    Returns:
        dict: Returns a dict of the deleted CronJob, or an error status
    """
    try:
        deleted = batch.delete_namespaced_cron_job(cronjob_name, namespace)
        return _clean_api_object(deleted)

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


def delete_job(namespace: str, job_name: str) -> dict:
    """Delete a Job

    Args:
        namespace (str): The namespace
        job_name (str): The name of the Job to delete

    Returns:
        str: Returns a dict of the deleted Job, or an error status
    """
    try:
        deleted = batch.delete_namespaced_job(job_name, namespace)
        return _clean_api_object(deleted)

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

import os

from kubernetes import client, config
from kubernetes.config import ConfigException
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone
import logging

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


def _filter_object_fields(response, fields=["name"]):
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


def _clean_api_object(api_object):
    """Convert API object to JSON and strip managedFields"""
    api_dict = generic.sanitize_for_serialization(api_object)
    api_dict["metadata"].pop("managedFields", None)
    return api_dict


def _get_time_since(datestring):
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


def _has_label(api_object, k, v):
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


def getCronJobs(namespace=""):
    if namespace == "":
        cronjobs = batch.list_cron_job_for_all_namespaces()
    else:
        cronjobs = batch.list_namespaced_cron_job(namespace=namespace)

    fields = ["name", "namespace"]
    sorted_cronjobs = sorted(_filter_object_fields(cronjobs, fields), key=lambda x: x["name"])
    return sorted_cronjobs


def getCronJob(namespace, cronjob_name):
    try:
        cronjob = batch.read_namespaced_cron_job(cronjob_name, namespace)
    except ApiException:
        return False

    return _clean_api_object(cronjob)


def getNamespaces():
    namespaces = v1.list_namespace()
    return _filter_object_fields(namespaces)


def getJobs(namespace, cronjob_name):
    jobs = batch.list_namespaced_job(namespace=namespace)
    cleaned = [_clean_api_object(job) for job in jobs.items]
    filtered = []
    if cronjob_name:
        for job in cleaned:
            if "ownerReferences" in job["metadata"]:
                if job["metadata"]["ownerReferences"][0]["name"] == cronjob_name:
                    filtered.append(job)
            elif _has_label(job, "kron.mshade.org/created-from", cronjob_name):
                filtered.append(job)
    else:
        filtered = cleaned

    for job in filtered:
        job["status"]["age"] = _get_time_since(job["status"]["startTime"])

    return filtered


def getPods(namespace, job_name=None):
    all_pods = v1.list_namespaced_pod(namespace=namespace)
    cleaned = [_clean_api_object(pod) for pod in all_pods.items]
    pods = []
    if job_name:
        for pod in cleaned:
            if "ownerReferences" in pod["metadata"]:
                if pod["metadata"]["ownerReferences"][0]["name"] == job_name:
                    pods.append(pod)
    else:
        pods = cleaned

    for pod in pods:
        pod["status"]["age"] = _getTimeSince(pod["status"]["startTime"])

    return pods


def getJobsAndPods(namespace, cronjob_name):
    jobs = getJobs(namespace, cronjob_name)
    for job in jobs:
        job["pods"] = getPods(namespace, job["metadata"]["name"])

    return jobs


def getPodLogs(namespace, pod_name):
    """Return plain text logs for <pod_name> in <namespace>"""
    try:
        logs = v1.read_namespaced_pod_log(
            pod_name, namespace, tail_lines=1000, timestamps=True
        )
    except ApiException as e:
        if e.status == 404:
            return f"Kronic> Error fetching logs: {e.reason}"
    return logs


def triggerCronJob(namespace, cronjob_name):
    cronjob = batch.read_namespaced_cron_job(name=cronjob_name, namespace=namespace)
    job = cronjob.spec.job_template
    date_stamp = datetime.now().strftime("%Y%m%d%H%M%S-%f")
    # Set a unique name that indicates this is a manual invocation
    job.metadata.name = str(job.metadata.name[:16] + "-manual-" + date_stamp)[:63]
    # Set a label to identify jobs created by kron
    job.metadata.labels = {
        "kron.mshade.org/manually-triggered": "true",
        "kron.mshade.org/created-from": cronjob_name,
    }

    try:
        trigger_job = batch.create_namespaced_job(body=job, namespace=namespace)
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
    return _clean_api_object(trigger_job)


def toggleCronJob(namespace, cronjob_name):
    suspended_status = batch.read_namespaced_cron_job_status(
        name=cronjob_name, namespace=namespace
    )
    patch_body = {"spec": {"suspend": not suspended_status.spec.suspend}}
    cronjob = batch.patch_namespaced_cron_job(
        name=cronjob_name, namespace=namespace, body=patch_body
    )
    return _clean_api_object(cronjob)


def updateCronJob(namespace, spec):
    name = spec["metadata"]["name"]
    if getCronJob(namespace, name):
        cronjob = batch.patch_namespaced_cron_job(name, namespace, spec)
    else:
        cronjob = batch.create_namespaced_cron_job(namespace, spec)
    return _clean_api_object(cronjob)


def deleteCronJob(namespace, cronjob_name):
    try:
        deleted = batch.delete_namespaced_cron_job(cronjob_name, namespace)
    except ApiException:
        return False
    return _clean_api_object(deleted)


def deleteJob(namespace, job_name):
    try:
        deleted = batch.delete_namespaced_job(job_name, namespace)
    except ApiException:
        return False
    return _clean_api_object(deleted)
